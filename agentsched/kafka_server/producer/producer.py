import json
from typing import Any, Optional
from uuid import uuid4

from confluent_kafka import KafkaError  # type: ignore[import]
from confluent_kafka import Message as ConfluentMessage  # type: ignore[import]
from confluent_kafka import Producer as ConfluentProducer  # type: ignore[import]


class Producer:
    """Kafka producer model using confluent_kafka.

    Args:
        bootstrap_servers (str): Kafka broker(s). (default: "localhost:9092")
        topic (str): Default topic to produce to. (default: "default_topic")
        message_max_bytes (int): Maximum request size in bytes. (default: 104857600)
        batch_size (int): Maximum number of messages to batch in one request.
            If set to 1, messages are sent individually. Increasing this number can enhance throughput. (Default: 1)
        **kwargs: Additional configuration parameters for confluent_kafka.Producer.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "default_topic",
        message_max_bytes: int = 104857600,
        batch_size: int = 1,
        **kwargs,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.message_max_bytes = message_max_bytes

        self.producer = ConfluentProducer(
            {
                "bootstrap.servers": bootstrap_servers,
                "message.max.bytes": message_max_bytes,
                "batch.size": batch_size,
                **kwargs,
            }
        )

    def delivery_report(self, err: Optional[KafkaError], message: ConfluentMessage):
        """Delivery report handler for produced messages."""
        if err:
            raise ValueError(f"Message delivery failed: {err}")
        print(f"[Kafka Log] Message {message} delivered to {message.topic()}")

    def produce(
        self,
        value: Any,
        key: Optional[str] = None,
        topic: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[dict] = None,
    ):
        """Produce a message to Kafka.

        Args:
            value (Any): The message value that will be serialized to JSON format.
            key (str, optional): Optional message key.
            topic (str, optional): Optional topic override.
            partition (int, optional): Specific partition to produce to.
            headers (dict, optional): Optional message headers.
        """
        topic = topic or self.topic

        try:
            value_json = json.dumps(value)
            print(f"[debug] produced message: {value_json}")
        except TypeError as e:
            raise ValueError(f"Value must be JSON serializable: {e}") from e

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
            if headers is not None:
                kwargs["headers"] = [(k, v.encode("utf-8")) for k, v in headers.items()]
            else:
                kwargs["headers"] = {
                    "correlation_id": str(uuid4()).encode("utf-8"),
                }  # generate unique correlation_id if not provided

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
