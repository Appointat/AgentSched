from agentsched.kafka_server.consumer import Consumer
from agentsched.kafka_server.producer import Producer


def produce_messages():
    """Produce messages to the Kafka topic."""
    # Define the topic
    topic = "test_topic"

    # Create a producer instance
    with Producer(bootstrap_servers="localhost:9092", topic=topic) as producer:
        print("Producer created.")

        # Produce messages
        messages_to_send = [{"id": i, "message": f"Hello Kafka {i}"} for i in range(5)]
        for message in messages_to_send:
            producer.produce(value=message)
            print(f"Produced: {message}")

        # Wait for all messages to be sent
        producer.flush()
        print("All messages produced.")

    print("Producer closed.")


def consume_messages():
    """Consume messages from the Kafka topic."""
    # Define the topic
    topic = "test_topic"

    # Create a consumer instance
    with Consumer(
        bootstrap_servers="localhost:9092",
        group_id="example_group",
        auto_offset_reset="earliest",
    ) as consumer:
        consumer.subscribe([topic])
        print("Consumer subscribed to topic.")

        # Start consuming
        print("Starting to consume messages...")
        message_count = 0
        max_messages = 3  # set this to the number of messages you expect to receive

        while message_count < max_messages:
            message = consumer.consume(timeout=5.0)  # Increased timeout
            if message is not None:
                print(f"Consumed: {message}")
                message_count += 1
            else:
                print("No message received. Waiting...")

        print("Finished consuming messages.")

    print("Consumer closed.")


def run_kafka_example():
    """Run the Kafka producer and consumer example."""
    produce_messages()
    print("================================")
    consume_messages()


if __name__ == "__main__":
    run_kafka_example()
