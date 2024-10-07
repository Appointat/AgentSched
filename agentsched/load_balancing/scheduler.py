from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Dict, List, Optional

from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer
from agentsched.llm_backend.llm_distributor import (
    DistributionAlgorithm,
    ModelDistributor,
)
from agentsched.llm_backend.sglang_model import SGLangModel, TaskStatus
from agentsched.load_balancing.connection_pool import ConnectionPool
from agentsched.types import (
    Message,
    ModelStats,
    Priority,
    SchedulerConfig,
    Task,
    TaskType,
)


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
        self.task_queue: List[Task] = []
        self.task_model_mapping: Dict[
            str, str
        ] = {}  # check the distribution of tasks to models
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=scheduler_config.max_workers)

    def add_llm_model(
        self,
        model_id: str,
        capacity: int,
        supported_tasks: List[TaskType],
        base_url: str,
        api_key: str = "EMPTY",
        warm_up_time: float = 5.0,
        cool_down_time: float = 10.0,
    ) -> None:
        """Add a new LLM model to the scheduler."""
        model = SGLangModel(
            model_id=model_id,
            capacity=capacity,
            supported_tasks=supported_tasks,
            base_url=base_url,
            api_key=api_key,
            warm_up_time=warm_up_time,
            cool_down_time=cool_down_time,
        )
        self.model_distributor.add_model(model)

    def remove_llm_model(self, model_id: str) -> None:
        """Remove an LLM model from the scheduler."""
        self.model_distributor.remove_model(model_id)

    def handle_task(self, message_dict: dict) -> None:
        """Handle incoming task messages. This is the callback method for the
        Consumer.
        """
        try:
            # TODO: correlation_id is not defined
            message = Message(**message_dict)
            task = Task.from_message(message)
            with self.lock:
                self.task_queue.append(task)
                # (property) value: Literal['high', 'medium', 'low']
                self.task_queue.sort(key=lambda x: (x.priority), reverse=True)

            self.balance_load()
        except Exception as e:
            raise RuntimeError(f"Failed to process message: {e}") from e

    def balance_load(self) -> None:
        """Balance the load across available LLM models."""
        with self.lock:
            for task in self.task_queue[:]:
                model_id = self.model_distributor.get_suitable_model(
                    task, DistributionAlgorithm.LEAST_LOAD
                )
                if model_id:
                    model = self.model_distributor.models[model_id]
                    if model.add_task(task):
                        self.task_queue.remove(task)
                        self.task_model_mapping[task.id] = model_id
                        task.model_id = model_id
                        self.executor.submit(self.process_task, model_id, task)
                else:
                    # If no model available, leave task in queue,
                    # and wait for next iteration
                    break

    def auto_scale(self) -> None:
        """Automatically scale the number of model instances based on load."""
        # TODO: Implement auto-scaling logic
        # pass

    def process_task(self, model_id: str, task: Task) -> None:
        """Process a task using the specified model."""
        conn = self.connection_pool.get_connection()
        if not conn:
            # If no connection available, put task back in queue
            with self.lock:
                task.priority = Priority.HIGH.value  # prioritize retied task
                self.task_queue.append(task)
            print("[Scheduler log] No connection available. Retrying task...")
            return

        try:
            model = self.model_distributor.models[model_id]

            # TODO: Wait for model to be ready before processing task
            if not model.start_processing(task.id):
                raise RuntimeError(f"Failed to start processing task {task.id}")

            # Invoke the model to process the task (generate a response)
            # TODO: Implement actual task processing logic using the connection
            response = model.text_completion(prompt=task.content)

            # Complete the task
            result = {
                "response": response,
                "log": f"Processed by model {model_id}",
            }  # TODO: define the llm result format in types.py
            if not model.complete_task(task.id, result):
                raise RuntimeError(f"Failed to complete task {task.id}")

            model.remove_task(task.id)
            del self.task_model_mapping[task.id]

            # Produce result to response topic
            output_message = Message(
                id=task.id,
                task_type=task.task_type,
                priority=Priority.HIGH.value,
                content=response,
                token_count=len(response.split()),  # TODO: implement token count
                correlation_id=task.correlation_id,
                model_id=model_id,
                status="completed",
            )
            print(f"[debug] output_message: {output_message}")
            self.producer.produce(
                value=output_message.model_dump(),
                topic=self.output_topic,
            )
            self.producer.flush()

            self.send_response_to_agent(task, result)
        except Exception as e:
            model.fail_task(task.id, str(e))
            raise RuntimeError(f"Error processing task: {e}") from e
        finally:
            self.connection_pool.release_connection(conn)

    def send_response_to_agent(self, task: Task, result: Dict[str, str]) -> None:
        """Send the response to the input agent."""
        # TODO: Implement actual response sending logic, send response to agent
        pass

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a specific task."""
        for model in self.model_distributor.models.values():
            status = model.get_task_status(task_id)
            if status is not None:
                return status
        return None

    def get_model_stats(self) -> Dict[str, ModelStats]:
        """Get statistics for all models."""
        return self.model_distributor.get_model_stats()

    def run(self) -> None:
        """Run the scheduler."""
        try:
            while True:
                message = self.consumer.consume()
                self.handle_task(message.model_dump())
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
