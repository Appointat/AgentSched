import json
from typing import List, Optional

from confluent_kafka import Consumer as ConfluentConsumer
from confluent_kafka import KafkaError, KafkaException


class Consumer:
    """Kafka consumer model using confluent_kafka.

    Args:
        bootstrap_servers (str): Kafka broker(s). (default: "localhost:9092")
        group_id (str): Consumer group ID. (default: "my-consumer-group")
        auto_offset_reset (str): Where to start reading messages. (default: "earliest")
        enable_auto_commit (bool): Whether to auto-commit offsets. (default: False)
        **kwargs: Additional configuration parameters for confluent_kafka.Consumer.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "my-consumer-group",
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = False,
        **kwargs,
    ):
        config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": enable_auto_commit,
            # Add KRaft specific configurations
            "security.protocol": "PLAINTEXT",  # change if using SSL
        }
        config.update(kwargs)
        self.consumer = ConfluentConsumer(config)

    def subscribe(self, topics: List[str]):
        """Subscribe to the given list of topics.

        Args:
            topics (List[str]): List of topics to subscribe to.
        """
        try:
            self.consumer.subscribe(topics)
        except KafkaException as e:
            raise ValueError(f"Failed to subscribe to topics: {e}")

    def consume(self, timeout: Optional[float] = 1.0) -> Optional[dict]:
        """Consume messages from subscribed topics.

        Args:
            timeout (float, optional): The maximum time to block waiting for a message. (default: 1.0)

        Returns:
            dict: Deserialized message value, or None if no message was available.

        Raises:
            KafkaException: If there's an error while consuming messages.
            ValueError: If message decoding fails.
        """
        try:
            msg = self.consumer.poll(timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(
                        f"Reached end of partition: {msg.topic()} [{msg.partition()}]"
                    )
                    return None
                raise KafkaException(msg.error())

            try:
                value = json.loads(msg.value().decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to decode message value as JSON: {e}")

            return value
        except KafkaException as e:
            raise KafkaException(f"Error while consuming message: {e}")

    def commit(self):
        """Commit current offsets for all assigned partitions."""
        try:
            self.consumer.commit()
        except KafkaException as e:
            raise KafkaException(f"Failed to commit offsets: {e}")

    def close(self):
        """Close the consumer."""
        try:
            self.consumer.close()
        except KafkaException as e:
            raise KafkaException(f"Error while closing consumer: {e}")

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context related to this object."""
        self.close()
