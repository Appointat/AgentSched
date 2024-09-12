import random
import time
from threading import Thread
from typing import List

from confluent_kafka import KafkaException  # type: ignore[import]
from confluent_kafka.admin import AdminClient, NewTopic  # type: ignore[import]

from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer
from agentsched.load_balancing.scheduler import Scheduler, SchedulerConfig, TaskType

# Kafka configuration
BOOTSTRAP_SERVERS = "localhost:9092"
TOPICS = ["high_priority", "medium_priority", "low_priority", "results"]
SGLANG_BASE_URL = "http://127.0.0.1:30000/v1"
LLM_API_KEY = "EMPTY"


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
        except KafkaException as e:
            if "already exists" in str(e):
                print(f"Topic {topic} already exists")
            else:
                raise KafkaException(f"Failed to create topic {topic}: {e}") from e


def simulate_input_messages(producer: Producer, num_messages: int = 5):
    """Simulate input messages to the system."""
    priority_options = ["high", "medium", "low"]

    prompts = [
        "Summarize the main points of climate change.",
        "Explain the concept of artificial intelligence.",
        "Describe the process of photosynthesis.",
        "What are the key features of a democratic government?",
        "How does the internet work?",
    ]

    task_types = [  # get all task types from TaskType into a list
        getattr(TaskType, attr)
        for attr in dir(TaskType)
        if not attr.startswith("__") and isinstance(getattr(TaskType, attr), str)
    ]

    for _ in range(num_messages):
        message = {
            "id": f"task_{random.randint(1000, 9999)}",
            "task_type": random.choice(task_types),
            "priority": random.choice(priority_options),
            "content": random.choice(prompts),
            "token_count": random.randint(10, 2000),
        }
        topic = f"{message['priority']}_priority"
        producer.produce(value=message, topic=topic)
        print(f"Produced message: {message}")
        time.sleep(0.5)  # simulate some delay between messages


def process_output(consumer: Consumer):
    """Process output messages from the system."""
    while True:
        try:
            message = consumer.consume(timeout=1.0)
            if message:
                # TODO: add to monitoring system
                print(f"Received result: Task {message['task_id']}")
                print(f"Model: {message['model_id']}")
                print(f"Status: {message['status']}")
                print(f"Result: {message['result'][:100]}...")
                print("-" * 50)
        except KafkaException as e:
            print(f"Error processing output: {e}")
            time.sleep(1)  # wait a bit before retrying


def main():
    """Main function to run the system demo."""
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
        SchedulerConfig(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            input_topics=TOPICS[:-1],
            output_topic="results",
            max_workers=10,
        )
    )

    # Add LLM models
    scheduler.add_llm_model(
        "gpt-3.5",
        capacity=5,
        supported_tasks=[
            TaskType.TEXT_GENERATION,
            TaskType.DATA_PROCESSING,
        ],
        base_url=SGLANG_BASE_URL,
        api_key=LLM_API_KEY,
    )
    scheduler.add_llm_model(
        "gpt-4-turbo",
        capacity=3,
        supported_tasks=[
            TaskType.TEXT_GENERATION,
            TaskType.IMAGE_ANALYSIS,
            TaskType.DATA_PROCESSING,
        ],
        base_url=SGLANG_BASE_URL,
        api_key=LLM_API_KEY,
    )
    scheduler.add_llm_model(
        "gpt-4-o",
        capacity=10,
        supported_tasks=[
            TaskType.TEXT_GENERATION,
        ],
        base_url=SGLANG_BASE_URL,
        api_key=LLM_API_KEY,
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
    time.sleep(5)

    # Print model stats
    print("Model Stats:")
    for model_id, stats in scheduler.get_model_stats().items():
        print(f"Model {model_id}:")
        print(f"  Current load: {stats['current_load']}")
        print(f"  Total processed tasks: {stats['total_processed_tasks']}")
        print(
            f"  Average processing time: {stats['average_processing_time']:.2f} seconds"
        )

    # Cleanup
    scheduler.close()
    input_producer.close()
    output_consumer.close()

    print("Demo completed.")


if __name__ == "__main__":
    main()
