import time
from typing import Dict, List, Optional

import openai
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.completion import Completion
from openai.types.create_embedding_response import CreateEmbeddingResponse

from agentsched.types import OpenAIConfig, Task, TaskStatus, TaskType


class SGLangModel:
    """Represents an SGLang model with advanced features for task management and
        performance tracking.

    Args:
        model_id (str): Unique identifier for the model.
        capacity (int): Maximum number of concurrent tasks the model can handle.
        supported_tasks (List[TaskType]): List of task types this model supports.
        base_url (str): OpenAI compatibility API base URL.
        openai_config (OpenAIConfig): Configuration for OpenAI API. If it is None,
            it will be set to OpenAIConfig() in the constructor.
        api_key (str): OpenAI compatibility API key.
        warm_up_time (float): Time in seconds the model needs to warm up before
            processing tasks.
        cool_down_time (float): Time in seconds the model needs to cool down after
            reaching max capacity.
    """

    def __init__(
        self,
        model_id: str,
        capacity: int,
        supported_tasks: List[TaskType],
        base_url: str,
        openai_config: OpenAIConfig,
        api_key: str = "EMPTY",
        warm_up_time: float = 5.0,
        cool_down_time: float = 10.0,
    ):
        # Model attributes
        self.model_id: str = model_id
        self.capacity: int = capacity
        self.max_tokens: int = openai_config.max_tokens
        self.supported_tasks: List[TaskType] = supported_tasks
        self.warm_up_time: float = warm_up_time
        self.cool_down_time: float = cool_down_time
        self.openai_config: OpenAIConfig = openai_config or OpenAIConfig()

        # Task management attributes
        self.current_load: int = 0
        self.tasks_mapping: Dict[str, Dict] = {}
        self.total_processed_tasks: int = 0
        self.total_processing_time: float = 0
        self.last_task_completion_time: Optional[float] = None
        self.is_warming_up: bool = False
        self.is_cooling_down: bool = False
        self.cool_down_start_time: float = 0
        self.warm_up_start_time: float = 0

        # OpenAI client
        self.base_url = base_url
        self.api_key = api_key
        self.client = openai.Client(base_url=base_url, api_key=api_key)

    def add_task(self, task: Task) -> bool:
        """Add a task to the model if capacity allows and task type is supported."""
        if self.is_cooling_down:
            return False

        if self.is_warming_up:
            if time.time() - self.warm_up_start_time < self.warm_up_time:
                return False
            self.is_warming_up = False

        if (
            self.current_load < self.capacity
            and task.task_type
            in [_task_type.value for _task_type in self.supported_tasks]
            and self._check_token_limit(task)
        ):
            self.tasks_mapping[task.id] = {
                "task": task,
                "status": TaskStatus.PENDING,
                "start_time": None,
            }
            self.current_load += 1

            if self.current_load == self.capacity:
                self.is_cooling_down = True
                self.cool_down_start_time = time.time()

            return True
        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the model."""
        if task_id in self.tasks_mapping:
            task = self.tasks_mapping.pop(task_id)
            self.current_load -= 1

            if task["status"] == TaskStatus.COMPLETED:
                self.total_processed_tasks += 1
                self.total_processing_time += time.time() - task["start_time"]
                self.last_task_completion_time = time.time()

            if self.is_cooling_down:
                if time.time() - self.cool_down_start_time >= self.cool_down_time:
                    self.is_cooling_down = False
                    self.is_warming_up = True
                    self.warm_up_start_time = time.time()

            return True
        return False

    def start_processing(self, task_id: str) -> bool:
        """Mark a task as processing and record its start time."""
        if (
            task_id in self.tasks_mapping
            and self.tasks_mapping[task_id]["status"] == TaskStatus.PENDING
        ):
            self.tasks_mapping[task_id]["status"] = TaskStatus.PROCESSING
            self.tasks_mapping[task_id]["start_time"] = time.time()
            return True
        return False

    def complete_task(self, task_id: str, result: Dict) -> bool:
        """Mark a task as completed and store its result."""
        if (
            task_id in self.tasks_mapping
            and self.tasks_mapping[task_id]["status"] == TaskStatus.PROCESSING
        ):
            self.tasks_mapping[task_id]["status"] = TaskStatus.COMPLETED
            self.tasks_mapping[task_id]["result"] = result
            return True
        return False

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a task as failed and store the error message."""
        if task_id in self.tasks_mapping:
            self.tasks_mapping[task_id]["status"] = TaskStatus.FAILED
            self.tasks_mapping[task_id]["error"] = error
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the current status of a task."""
        if task_id in self.tasks_mapping:
            return self.tasks_mapping[task_id]["status"]
        return None

    def get_average_processing_time(self) -> float:
        """Calculate the average processing time for completed tasks."""
        if self.total_processed_tasks == 0:
            return 0
        return self.total_processing_time / self.total_processed_tasks

    def _check_token_limit(self, task: Task) -> bool:
        """Check if the task's token count is within the model's limit."""
        task_tokens = task.token_count
        return task_tokens <= self.max_tokens

    def text_completion(
        self,
        prompt: str,
    ) -> str:
        """Perform text completion using the SGLang model."""
        try:
            response: Completion = self.client.completions.create(
                model=self.model_id,
                prompt=prompt,
                **self.openai_config.to_dict(),
            )
        except Exception as e:
            print(f"[LLM log] Error completing task: {e}")
        return response.choices[0].text

    def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
    ) -> str:
        """Perform chat completion using the SGLang model."""
        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                **self.openai_config.to_dict(),
            )
        except Exception as e:
            print(f"[LLM log] Error completing task: {e}")
        return response.choices[0].message.content or ""

    def text_embedding(self, input_text: str) -> List[float]:
        """Generate text embedding using the SGLang model."""
        try:
            response: CreateEmbeddingResponse = self.client.embeddings.create(
                model=self.model_id,
                input=input_text,
                **self.openai_config.to_dict(),
            )
        except Exception as e:
            print(f"[LLM log] Error completing task: {e}")
        return response.data[0].embedding

    def __str__(self) -> str:
        return (
            f"SGLangModel(id={self.model_id}, capacity={self.capacity}, "
            f"current_load={self.current_load}, "
            f"processed_tasks={self.total_processed_tasks})"
        )
