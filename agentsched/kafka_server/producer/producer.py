import json
from typing import Any, Optional

from confluent_kafka import KafkaError, Message  # type: ignore[import]
from confluent_kafka import Producer as ConfluentProducer  # type: ignore[import]


class Producer:
    """Kafka producer model using confluent_kafka.

    Args:
        bootstrap_servers (str): Kafka broker(s). (default: "localhost:9092")
        topic (str): Default topic to produce to. (default: "default_topic")
        max_request_size (int): Maximum request size in bytes. (default: 104857600)
        batch_size (int): Maximum number of messages to batch in one request.
            If 0, messages are sent immediately.
            And it could be set to a large number to improve throughput.
        **kwargs: Additional configuration parameters for confluent_kafka.Producer.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "default_topic",
        max_request_size: int = 104857600,
        batch_size=0,
        **kwargs,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.max_request_size = max_request_size

        self.producer = ConfluentProducer(
            bootstrap_servers=bootstrap_servers,
            max_request_size=max_request_size,
            batch_size=batch_size,
            **kwargs,
        )

    def delivery_report(self, err: Optional[KafkaError], msg: Message):
        """Delivery report handler for produced messages."""
        if err:
            raise ValueError(f"Message delivery failed: {err}")
        else:
            print(f"[Kafka Log] Message delivered to {msg.topic()} [{msg.partition()}]")

    def produce(
        self,
        value: Any,
        key: Optional[str] = None,
        topic: Optional[str] = None,
        partition: Optional[int] = None,
    ):
        """Produce a message to Kafka.

        Args:
            value (Any): The message value that will be serialized to JSON format.
            key (str, optional): Optional message key.
            topic (str, optional): Optional topic override.
            partition (int, optional): Specific partition to produce to.
        """
        topic = topic or self.topic

        try:
            value_json = json.dumps(value)
        except TypeError as e:
            raise ValueError(f"Value must be JSON serializable: {e}")

        try:
            kwargs = {
                "topic": topic,
                "value": value_json,
                "callback": self.delivery_report,
            }
            if key is not None:
                kwargs["key"] = key
            if partition is not None:
                kwargs["partition"] = partition

            self.producer.produce(**kwargs)
            # Serve delivery callback queue
            self.producer.poll(0)
        except BufferError:
            print("[Kafka Log] Local producer queue is full, waiting for free space...")
            self.producer.poll(1)
            self.produce(value, key, topic, partition)  # retry

    def flush(self, timeout: float = -1):
        """Wait for any outstanding messages to be delivered."""
        return self.producer.flush(timeout)

    def close(self):
        """Flush and close the producer."""
        self.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
