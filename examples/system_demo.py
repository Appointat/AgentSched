import random
import time
from threading import Thread
from typing import List

from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer
from agentsched.load_balancing.scheduler import Scheduler

# Kafka configuration
BOOTSTRAP_SERVERS = "localhost:9092"
TOPICS = ["high_priority", "medium_priority", "low_priority", "results"]


def create_topics(
    bootstrap_servers: str,
    topics: List[str],
    num_partitions: int = 1,
    replication_factor: int = 1,
):
    """Create Kafka topics if they don't exist."""
    admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})

    new_topics = [
        NewTopic(
            topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )
        for topic in topics
    ]
    fs = admin_client.create_topics(new_topics)

    for topic, f in fs.items():
        try:
            f.result()  # the result itself is None
            print(f"Topic {topic} created")
        except Exception as e:
            if "already exists" in str(e):
                print(f"Topic {topic} already exists")
            else:
                raise KafkaException(f"Failed to create topic {topic}: {e}")


def simulate_input_messages(producer: Producer, num_messages: int = 5):
    """Simulate input messages to the system."""
    task_types = ["text_generation", "image_analysis", "data_processing"]
    priority_options = ["high", "medium", "low"]

    for _ in range(num_messages):
        message = {
            "id": f"task_{random.randint(1000, 9999)}",
            "task_type": random.choice(task_types),
            "priority": random.choice(priority_options),
            "content": f"Sample task content {random.randint(1, 100)}",
            "token_count": random.randint(10, 2000),
        }
        topic = message["priority"] + "_priority"
        producer.produce(value=message, topic=topic)
        print(f"Produced message: {message}")
        time.sleep(0.5)  # simulate some delay between messages


def process_output(consumer: Consumer):
    """Process output messages from the system."""
    while True:
        try:
            message = consumer.consume(timeout=1.0)
            if message:
                print(f"Received result: {message}")
        except KafkaException as e:
            print(f"Error processing output: {e}")
            time.sleep(1)  # wait a bit before retrying


def main():
    # Create Kafka topics
    create_topics(BOOTSTRAP_SERVERS, TOPICS)

    # Initialize components
    input_producer = Producer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
    )
    output_consumer = Consumer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id="output-consumer-group",
        auto_offset_reset="earliest",
    )
    output_consumer.subscribe(["results"])

    scheduler = Scheduler(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        input_topics=TOPICS[:-1],  # exclude 'results' topic
        output_topic="results",
    )

    # Add LLM models
    scheduler.add_llm_model(
        "gpt-3.5",
        capacity=5,
        max_tokens=2048,
        supported_tasks=["text_generation", "data_processing"],
    )
    scheduler.add_llm_model(
        "gpt-4-turbo",
        capacity=3,
        max_tokens=4096,
        supported_tasks=["text_generation", "data_processing", "image_analysis"],
    )
    scheduler.add_llm_model(
        "gpt-4-o",
        capacity=10,
        max_tokens=512,
        supported_tasks=["text_generation"],
    )

    # Start threads
    input_thread = Thread(target=simulate_input_messages, args=(input_producer,))
    output_thread = Thread(target=process_output, args=(output_consumer,))
    scheduler_thread = Thread(target=scheduler.run)

    input_thread.start()
    output_thread.start()
    scheduler_thread.start()

    # Wait for input simulation to complete
    input_thread.join()

    # Allow some time for processing
    time.sleep(10)

    # Cleanup
    scheduler.close()
    input_producer.close()
    output_consumer.close()

    print("Demo completed.")


if __name__ == "__main__":
    main()
