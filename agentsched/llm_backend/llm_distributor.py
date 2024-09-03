import random
from threading import Lock
from typing import Dict, Optional

from agentsched.llm_backend.vllm_model import vLLMModel


class ModelDistributor:
    """Distributes tasks among available LLM models.

    Args:
        models (Dict): Dictionary of available LLM models.
        lock (Lock): Threading lock for managing concurrent access to the models.
    """

    def __init__(self):
        self.models: Dict[str, vLLMModel] = {}
        self.lock = Lock()

    def add_model(self, model: vLLMModel) -> None:
        with self.lock:
            self.models[model.model_id] = model

    def remove_model(self, model_id: str) -> None:
        with self.lock:
            if model_id in self.models:
                del self.models[model_id]

    def get_suitable_model(self, task: dict) -> Optional[str]:
        with self.lock:
            suitable_models = [
                model
                for model in self.models.values()
                if task["task_type"] in model.supported_tasks
                and model.current_load < model.capacity
            ]

            if not suitable_models:
                return None

            # TODO: Implement more sophisticated model selection algorithm
            # For now, we're using a simple random selection among suitable models
            return random.choice(suitable_models).model_id

    def get_model_stats(self) -> Dict[str, Dict]:
        return {
            model_id: {
                "current_load": model.current_load,
                "total_processed_tasks": model.total_processed_tasks,
                "average_processing_time": model.get_average_processing_time(),
            }
            for model_id, model in self.models.items()
        }
