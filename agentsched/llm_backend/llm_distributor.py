import random
from threading import Lock
from typing import Dict, Optional

from agentsched.llm_backend.sglang_model import SGLangModel


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

    def get_suitable_model(self, task: dict) -> Optional[str]:
        """Select a suitable model for the given task."""
        with self.lock:
            suitable_models = [
                model
                for model in self.models.values()
                if task["task_type"] in model.supported_tasks
                and model.current_load < model.capacity
            ]

            if not suitable_models:
                return None

            # TODO: implement more sophisticated model selection algorithm
            # For now, we're using a simple random selection among suitable models
            return random.choice(suitable_models).model_id

    def get_model_stats(self) -> Dict[str, Dict]:
        """Get statistics for all LLM models."""
        return {
            model_id: {
                "current_load": model.current_load,
                "total_processed_tasks": model.total_processed_tasks,
                "average_processing_time": model.get_average_processing_time(),
            }
            for model_id, model in self.models.items()
        }
