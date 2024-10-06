import random
from enum import Enum
from threading import Lock
from typing import Dict, Optional

from agentsched.llm_backend.sglang_model import SGLangModel
from agentsched.types import ModelStats, Task


class DistributionAlgorithm(Enum):
    """Enumeration of distribution algorithms for task assignment."""

    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    LEAST_LOAD = "least_load"


class ModelDistributor:
    """Distributes tasks among available LLM models.

    Args:
        models (Dict): Dictionary of available LLM models.
        lock (Lock): Threading lock for managing concurrent access to the models.
    """

    def __init__(self):
        self.models: Dict[str, SGLangModel] = {}
        self.lock = Lock()

    def add_model(self, model: SGLangModel) -> None:
        """Add a new LLM model to the distributor."""
        with self.lock:
            self.models[model.model_id] = model

    def remove_model(self, model_id: str) -> None:
        """Remove an LLM model from the distributor."""
        with self.lock:
            if model_id in self.models:
                del self.models[model_id]

    def get_suitable_model(
        self,
        task: Task,
        algo: DistributionAlgorithm = DistributionAlgorithm.RANDOM,
    ) -> Optional[str]:
        """Select a suitable model for the given task."""
        with self.lock:
            suitable_models = [
                model
                for model in self.models.values()
                if task.task_type in [_task.value for _task in model.supported_tasks]
                and model.current_load < model.capacity
            ]

            if not suitable_models:
                return None

            # TODO: implement more sophisticated model selection algorithm
            if algo == DistributionAlgorithm.RANDOM:
                return random.choice(suitable_models).model_id
            if algo == DistributionAlgorithm.ROUND_ROBIN:
                return suitable_models[0].model_id
            if algo == DistributionAlgorithm.LEAST_LOAD:
                suitable_models.sort(key=lambda x: x.current_load)
                return suitable_models[0].model_id

    def get_model_stats(self) -> Dict[str, ModelStats]:
        """Get statistics for all LLM models."""
        return {
            model_id: ModelStats(
                current_load=model.current_load,
                total_processed_tasks=model.total_processed_tasks,
                average_processing_time=model.get_average_processing_time(),
            )
            for model_id, model in self.models.items()
        }
