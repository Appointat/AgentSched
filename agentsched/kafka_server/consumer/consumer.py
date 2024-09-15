import json
from typing import Callable, List, Optional

from confluent_kafka import Consumer as ConfluentConsumer  # type: ignore[import]
from confluent_kafka import KafkaError, KafkaException  # type: ignore[import]

from agentsched.types import Message


class Consumer:
    """Kafka consumer model using confluent_kafka.

    Args:
        bootstrap_servers (str): Kafka broker(s). (default: "localhost:9092")
        group_id (str): Consumer group ID. (default: "my-consumer-group")
        auto_offset_reset (str): Where to start reading messages. (default: "latest")
        enable_auto_commit (bool): Whether to auto-commit offsets. (default: False)
        **kwargs: Additional configuration parameters for confluent_kafka.Consumer.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "my-consumer-group",
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = False,
        **kwargs,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit

        self.consumer = ConfluentConsumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": auto_offset_reset,
                "enable.auto.commit": enable_auto_commit,
                **kwargs,
            }
        )

        # Initialize the list of observer callbacks
        self.callbacks: List[Callable[[dict], None]] = []

    def register_callback(self, callback: Callable[[dict], None]):
        """Register a callback to be called when a message is received."""
        self.callbacks.append(callback)

    def subscribe(self, topics: List[str]):
        """Subscribe to the given list of topics."""
        try:
            self.consumer.subscribe(topics)
        except KafkaException as e:
            raise ValueError(f"Failed to subscribe to topics: {e}") from e

    def consume(self, timeout: Optional[float] = 1.0) -> Message:
        """Consume messages from subscribed topics."""
        try:
            confluent_message = None
            while confluent_message is None:
                confluent_message = self.consumer.poll(timeout)

            if confluent_message.error():
                if confluent_message.error().code() == KafkaError._PARTITION_EOF:
                    raise KafkaException(
                        f"Reached end of partition: {confluent_message.topic()} "
                        f"[{confluent_message.partition()}]"
                    )
                raise KafkaException(confluent_message.error())

            try:
                value = json.loads(confluent_message.value().decode("utf-8"))
                message = Message(**value)
                print(f"[debug] consumed message: {message}")

                self._notify_observers(message)  # notify observers with the message
                return message
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to decode message value as JSON: {e}") from e

        except KafkaException as e:
            raise KafkaException(f"Error while consuming message: {e}") from e

    def _notify_observers(self, message: Message):
        """Notify all registered callbacks."""
        for callback in self.callbacks:
            callback(
                message.model_dump()
            )  # call each registered observer with the message

    def commit(self):
        """Commit current offsets for all assigned partitions."""
        try:
            self.consumer.commit()
        except KafkaException as e:
            raise KafkaException(f"Failed to commit offsets: {e}") from e

    def close(self):
        """Close the consumer."""
        try:
            self.consumer.close()
        except KafkaException as e:
            raise KafkaException(f"Error while closing consumer: {e}") from e

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context related to this object."""
        self.close()
