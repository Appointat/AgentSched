import time
from enum import Enum
from typing import Dict, List, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class vLLMModel:
    """Represents an LLM model with advanced features for task management and performance tracking.

    Args:
        model_id (str): Unique identifier for the model.
        capacity (int): Maximum number of concurrent tasks the model can handle.
        max_tokens (int): Maximum number of tokens the model can process.
        supported_tasks (List[str]): List of task types this model supports.
        warm_up_time (float): Time in seconds the model needs to warm up before processing tasks.
        cool_down_time (float): Time in seconds the model needs to cool down after reaching max capacity.
    """

    def __init__(
        self,
        model_id: str,
        capacity: int,
        max_tokens: int,
        supported_tasks: List[str],
        warm_up_time: float = 5.0,
        cool_down_time: float = 10.0,
    ):
        self.model_id: str = model_id
        self.capacity: int = capacity
        self.max_tokens: int = max_tokens
        self.supported_tasks: List[str] = supported_tasks
        self.warm_up_time: float = warm_up_time
        self.cool_down_time: float = cool_down_time

        self.current_load: int = 0
        self.tasks: Dict[str, Dict] = {}
        self.total_processed_tasks: int = 0
        self.total_processing_time: float = 0
        self.last_task_completion_time: Optional[float] = None
        self.is_warming_up: bool = False
        self.is_cooling_down: bool = False

    def add_task(self, task: dict) -> bool:
        """Add a task to the model if capacity allows and task type is supported."""
        if self.is_cooling_down:
            return False

        if self.is_warming_up:
            if time.time() - self.warm_up_start_time < self.warm_up_time:
                return False
            self.is_warming_up = False

        if (
            self.current_load < self.capacity
            and task.get("task_type") in self.supported_tasks
            and self._check_token_limit(task)
        ):
            task_id = task.get("id", str(len(self.tasks)))
            self.tasks[task_id] = {
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
        if task_id in self.tasks:
            task = self.tasks.pop(task_id)
            self.current_load -= 1

            if task["status"] == TaskStatus.COMPLETED:
                self.total_processed_tasks += 1
                self.total_processing_time += time.time() - task["start_time"]
                self.last_task_completion_time = time.time()

            if self.is_cooling_down:
                if time.time() - self.cool_down_start_time >= self.cool_down_time:
                    self.is_cooling_down = False
                    self.is_warming_up = True
                    self.warm_up_start_time: float = time.time()

            return True
        return False

    def start_processing(self, task_id: str) -> bool:
        """Mark a task as processing and record its start time."""
        if (
            task_id in self.tasks
            and self.tasks[task_id]["status"] == TaskStatus.PENDING
        ):
            self.tasks[task_id]["status"] = TaskStatus.PROCESSING
            self.tasks[task_id]["start_time"] = time.time()
            return True
        return False

    def complete_task(self, task_id: str, result: Dict) -> bool:
        """Mark a task as completed and store its result."""
        if (
            task_id in self.tasks
            and self.tasks[task_id]["status"] == TaskStatus.PROCESSING
        ):
            self.tasks[task_id]["status"] = TaskStatus.COMPLETED
            self.tasks[task_id]["result"] = result
            return True
        return False

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a task as failed and store the error message."""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = TaskStatus.FAILED
            self.tasks[task_id]["error"] = error
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the current status of a task."""
        if task_id in self.tasks:
            return self.tasks[task_id]["status"]
        return None

    def get_average_processing_time(self) -> float:
        """Calculate the average processing time for completed tasks."""
        if self.total_processed_tasks == 0:
            return 0
        return self.total_processing_time / self.total_processed_tasks

    def _check_token_limit(self, task: dict) -> bool:
        """Check if the task's token count is within the model's limit."""
        task_tokens = task.get("token_count", 0)
        return task_tokens <= self.max_tokens

    def __str__(self) -> str:
        return (
            f"vLLMModel(id={self.model_id}, capacity={self.capacity}, "
            f"current_load={self.current_load}, processed_tasks={self.total_processed_tasks})"
        )
