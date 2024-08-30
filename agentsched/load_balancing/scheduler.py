import time
from threading import Lock
from typing import Dict, List, Optional, Tuple

from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer
from agentsched.llm_backend.vllm_model import TaskStatus, vLLMModel


class Scheduler:
    """Scheduler with load balancing capabilities, acting as an observer for the Consumer.

    Args:
        bootstrap_servers (str): Kafka broker(s).
        input_topics (List[str]): List of input topics to subscribe to.
        output_topic (str): Output topic for results produced by the scheduler.
        group_id (str): Consumer group ID. (default: "scheduler-group")
        consumer_kwargs (Optional[Dict]): Additional configuration parameters for the Consumer.
        producer_kwargs (Optional[Dict]): Additional configuration parameters for the Producer.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        input_topics: List[str],
        output_topic: str,
        group_id: str = "scheduler-group",
        consumer_kwargs: Optional[Dict] = None,
        producer_kwargs: Optional[Dict] = None,
    ):
        self.consumer = Consumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            **(consumer_kwargs or {}),
        )
        self.consumer.register_callback(self.handle_task)
        self.consumer.subscribe(input_topics)

        self.producer = Producer(
            bootstrap_servers=bootstrap_servers,
            **(producer_kwargs or {}),
        )

        self.output_topic = output_topic
        self.llm_models: Dict[str, vLLMModel] = {}
        self.task_queue: List[Tuple[str, dict]] = []
        self.lock = Lock()

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
        with self.lock:
            self.llm_models[model_id] = vLLMModel(
                model_id=model_id,
                capacity=capacity,
                max_tokens=max_tokens,
                supported_tasks=supported_tasks,
                warm_up_time=warm_up_time,
                cool_down_time=cool_down_time,
            )

    def remove_llm_model(self, model_id: str) -> None:
        """Remove an LLM model from the scheduler."""
        with self.lock:
            if model_id in self.llm_models:
                del self.llm_models[model_id]

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
            raise RuntimeError(f"Failed to process message: {e}")

    def balance_load(self) -> None:
        """Balance the load across available LLM models."""
        with self.lock:
            for priority, task in self.task_queue:
                assigned = False
                for model in sorted(
                    self.llm_models.values(), key=lambda m: m.current_load
                ):
                    if model.add_task(task):
                        assigned = True
                        break

                if assigned:
                    self.task_queue.remove((priority, task))
                    self.process_task(model.model_id, task)
                else:
                    # If no model available, leave task in queue
                    break

    def process_task(self, model_id: str, task: dict) -> None:
        """Process a task using the specified model."""
        try:
            model = self.llm_models[model_id]
            task_id = task["id"]

            # Start processing the task
            if not model.start_processing(task_id):
                raise RuntimeError(f"Failed to start processing task {task_id}")

            # Simulate task processing
            time.sleep(2)  # simulating processing time

            # Complete the task
            result = {"output": f"Processed by model {model_id}"}
            if not model.complete_task(task_id, result):
                raise RuntimeError(f"Failed to complete task {task_id}")

            # Remove task from model
            if not model.remove_task(task_id):
                raise RuntimeError(f"Failed to remove task {task_id} from model")

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
            self.llm_models[model_id].fail_task(task["id"], str(e))
            raise RuntimeError(f"Error processing task: {e}")

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a specific task."""
        for model in self.llm_models.values():
            status = model.get_task_status(task_id)
            if status is not None:
                return status
        return None

    def get_model_stats(self) -> Dict[str, Dict]:
        """Get statistics for all models."""
        return {
            model_id: {
                "current_load": model.current_load,
                "total_processed_tasks": model.total_processed_tasks,
                "average_processing_time": model.get_average_processing_time(),
            }
            for model_id, model in self.llm_models.items()
        }

    def run(self) -> None:
        """Run the scheduler."""
        try:
            while True:
                self.consumer.consume()
                self.balance_load()  # continuously balance load
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self) -> None:
        """Close the consumer and producer."""
        self.consumer.close()
        self.producer.close()

    def __enter__(self) -> "Scheduler":
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context related to this object."""
        self.close()


# Usage example:
# if __name__ == "__main__":
#     scheduler = Scheduler(
#         bootstrap_servers="localhost:9092",
#         input_topics=["high_priority", "medium_priority", "low_priority"],
#         output_topic="results",
#     )
#
#     # Add some LLM models
#     scheduler.add_llm_model(
#         "gpt-3",
#         capacity=5,
#         max_tokens=2048,
#         supported_tasks=["text_generation", "data_processing"]
#     )
#     scheduler.add_llm_model(
#         "gpt-4",
#         capacity=3,
#         max_tokens=4096,
#         supported_tasks=["text_generation", "data_processing", "image_analysis"]
#     )
#     scheduler.add_llm_model(
#         "bert",
#         capacity=10,
#         max_tokens=512,
#         supported_tasks=["text_generation"]
#     )
#
#     scheduler.run()
