import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional, Tuple

from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer
from agentsched.llm_backend.llm_distributor import ModelDistributor
from agentsched.llm_backend.sglang_model import SGLangModel, TaskStatus
from agentsched.load_balancing.connection_pool import ConnectionPool


@dataclass
class SchedulerConfig:
    """Configuration class for the Scheduler.

    This class encapsulates all the configuration parameters needed to initialize
    and run a Scheduler instance. It uses the dataclass decorator to automatically
    generate methods like __init__(), __repr__(), and __eq__().

    Attributes:
        bootstrap_servers (str): A comma-separated list of host:port pairs for
            establishing the initial connection to the Kafka cluster.
        input_topics (List[str]): A list of Kafka topics to consume messages from.
        output_topic (str): The Kafka topic to produce processed messages to.
        group_id (str): The consumer group ID for Kafka. Defaults to "scheduler-group".
        consumer_kwargs (Dict): Additional keyword arguments to pass to the Kafka
            consumer. Defaults to an empty dict.
        producer_kwargs (Dict): Additional keyword arguments to pass to the Kafka
            producer. Defaults to an empty dict.
        max_workers (int): The maximum number of worker threads for the thread pool
            executor. Defaults to 10.

    Example:
        config = SchedulerConfig(
            bootstrap_servers="localhost:9092",
            input_topics=["input1", "input2"],
            output_topic="output",
            consumer_kwargs={"auto_offset_reset": "earliest"},
            max_workers=15
        )
    """

    bootstrap_servers: str
    input_topics: List[str]
    output_topic: str
    group_id: str = "scheduler-group"
    consumer_kwargs: Dict = field(default_factory=dict)
    producer_kwargs: Dict = field(default_factory=dict)
    max_workers: int = 10


class Scheduler:
    """Scheduler with load balancing capabilities, acting as an observer for the
        Consumer.

    Args:
        scheduler_config (SchedulerConfig): Configuration parameters for the Scheduler.
    """

    def __init__(
        self,
        scheduler_config: SchedulerConfig,
    ):
        self.scheduler_config = scheduler_config
        self.consumer = Consumer(
            bootstrap_servers=scheduler_config.bootstrap_servers,
            group_id=scheduler_config.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            **scheduler_config.consumer_kwargs,
        )
        self.consumer.register_callback(self.handle_task)
        self.consumer.subscribe(scheduler_config.input_topics)

        self.producer = Producer(
            bootstrap_servers=scheduler_config.bootstrap_servers,
            **scheduler_config.producer_kwargs,
        )

        self.output_topic = scheduler_config.output_topic
        self.model_distributor = ModelDistributor()
        self.connection_pool = ConnectionPool()
        self.task_queue: List[Tuple[str, dict]] = []
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=scheduler_config.max_workers)

    def add_llm_model(
        self,
        model_id: str,
        capacity: int,
        max_tokens: int,
        supported_tasks: List[str],
        warm_up_time: float = 5.0,
        cool_down_time: float = 10.0,
    ) -> None:
        """Add a new LLM model to the scheduler."""
        model = SGLangModel(
            model_id=model_id,
            capacity=capacity,
            max_tokens=max_tokens,
            supported_tasks=supported_tasks,
            warm_up_time=warm_up_time,
            cool_down_time=cool_down_time,
        )
        self.model_distributor.add_model(model)

    def remove_llm_model(self, model_id: str) -> None:
        """Remove an LLM model from the scheduler."""
        self.model_distributor.remove_model(model_id)

    def handle_task(self, message: dict) -> None:
        """Handle incoming task messages. This is the callback method for the Consumer."""
        try:
            task_type = message.get("task_type")
            priority = message.get("priority", "medium")

            if task_type not in [
                "text_generation",
                "image_analysis",
                "data_processing",
            ]:
                raise ValueError(f"Unsupported task type: {task_type}")

            with self.lock:
                self.task_queue.append((priority, message))
                self.task_queue.sort(
                    key=lambda x: {"high": 0, "medium": 1, "low": 2}[x[0]]
                )

            self.balance_load()
        except Exception as e:
            raise RuntimeError(f"Failed to process message: {e}") from e

    def balance_load(self) -> None:
        """Balance the load across available LLM models."""
        with self.lock:
            for priority, task in self.task_queue:
                model_id = self.model_distributor.get_suitable_model(task)
                if model_id:
                    self.task_queue.remove((priority, task))
                    self.executor.submit(self.process_task, model_id, task)
                else:
                    # If no model available, leave task in queue
                    break

    def process_task(self, model_id: str, task: dict) -> None:
        """Process a task using the specified model."""
        conn = self.connection_pool.get_connection()
        if not conn:
            # If no connection available, put task back in queue
            with self.lock:
                self.task_queue.append(("high", task))  # Prioritize retried tasks
            return

        try:
            model = self.model_distributor.models[model_id]
            task_id = task["id"]

            # Start processing the task
            if not model.start_processing(task_id):
                raise RuntimeError(f"Failed to start processing task {task_id}")

            # TODO: Implement actual task processing logic using the connection
            time.sleep(2)  # simulating processing time

            # Complete the task
            result = {"output": f"Processed by model {model_id}"}
            if not model.complete_task(task_id, result):
                raise RuntimeError(f"Failed to complete task {task_id}")

            # Produce result to output topic
            output_message = {
                "task_id": task_id,
                "result": result["output"],
                "status": "completed",
            }
            self.producer.produce(value=output_message, topic=self.output_topic)
            self.producer.flush()
        except Exception as e:
            # Mark task as failed
            self.model_distributor.models[model_id].fail_task(task["id"], str(e))
            raise RuntimeError(f"Error processing task: {e}") from e
        finally:
            self.connection_pool.release_connection(conn)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a specific task."""
        for model in self.model_distributor.models.values():
            status = model.get_task_status(task_id)
            if status is not None:
                return status
        return None

    def get_model_stats(self) -> Dict[str, Dict]:
        """Get statistics for all models."""
        return self.model_distributor.get_model_stats()

    def run(self) -> None:
        """Run the scheduler."""
        try:
            while True:
                self.consumer.consume()
                self.balance_load()  # continuously balance load
                self.connection_pool.cleanup_stale_connections()  # periodically cleanup stale connections  # noqa: E501
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self) -> None:
        """Close the consumer, producer, and executor."""
        self.consumer.close()
        self.producer.close()
        self.executor.shutdown(wait=True)

    def __enter__(self) -> "Scheduler":
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context related to this object."""
        self.close()
