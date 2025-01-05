from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.dataclasses import dataclass


class TaskType(Enum):
    """Enumeration of task types for the Scheduler."""

    TEXT_GENERATION = "text_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DATA_PROCESSING = "data_processing"


class Priority(Enum):
    """Enumeration of task priorities."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    """Enumeration of task statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    """Represents a message received from Kafka."""

    id: str
    task_type: str = TaskType.TEXT_GENERATION.value
    priority: str = Priority.MEDIUM.value
    content: str
    token_count: int
    correlation_id: str
    model_id: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class Task(BaseModel):
    """Represents a task to be processed by the system."""

    id: str
    task_type: str = TaskType.TEXT_GENERATION.value
    priority: str = Priority.MEDIUM.value
    content: str
    token_count: int
    correlation_id: str
    model_id: Optional[str] = None

    @classmethod
    def from_message(cls, message: Message) -> "Task":
        """Create a Task instance from a Message."""
        return cls(
            id=message.id,
            task_type=message.task_type,
            priority=message.priority,
            content=message.content,
            token_count=message.token_count,
            correlation_id=message.correlation_id,
            model_id=message.model_id,
        )

    model_config = ConfigDict(protected_namespaces=())


class ModelStats(BaseModel):
    """Statistics for a single model."""

    current_load: int = 0
    total_processed_tasks: int = 0
    average_processing_time: float


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
    consumer_kwargs: Dict = Field(default_factory=dict)
    producer_kwargs: Dict = Field(default_factory=dict)
    max_workers: int = 10


@dataclass
class OpenAIConfig:
    """Configuration class for OpenAI API.

    This class encapsulates all the configuration parameters needed to interact with
    the OpenAI API. It uses the dataclass decorator to automatically generate methods
    like __init__(), __repr__(), and __eq__(). It also provides default values for
    commonly used parameters.

    Attributes:
        temperature (float): Controls randomness. Lower values make the model more
            deterministic.
        max_tokens (int): The maximum number of tokens to generate in the completion.
        top_p (float): Controls diversity via nucleus sampling.
        frequency_penalty (float): Decreases the model's likelihood to repeat the same
            line verbatim.
        presence_penalty (float): Increases the model's likelihood to talk about new
            topics.
        stop (Optional[List[str]]): Up to 4 sequences where the API will stop generating
            further tokens.
        n (int): The number of the completions to generate for each prompt.
        stream (bool): Whether to stream back partial progress.
        logprobs (Optional[int]): Include the log probabilities on the logprobs most
            likely tokens.
        echo (bool): Echo back the prompt in addition to the completion.
        best_of (int): Generates best_of completions server-side and returns the "best".
        logit_bias (dict): Modify the likelihood of specified tokens appearing in the
            completion.
        user (str): A unique identifier representing your end-user.
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    n: int = 1
    stream: bool = False
    logprobs: Optional[int] = None
    echo: bool = False
    best_of: int = 1
    logit_bias: Dict = Field(default_factory=dict)
    user: str = ""

    def to_dict(self):
        """Convert the config to a dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
