from typing import Optional

from agentsched.llm_backend.llm_distributor import ModelDistributor
from agentsched.llm_backend.sglang_model import SGLangModel
from agentsched.types import OpenAIConfig, TaskType


def setup_single_sglang_model_server(
    model_id: str,
    base_url: str,
    api_key: Optional[str] = None,
    capacity: int = 10,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> ModelDistributor:
    """Setup a single SGLang model server with ModelDistributor.

    Args:
        model_id: The model identifier
        base_url: Base URL for the OpenAI compatible API
        api_key: API key for authentication (optional)
        capacity: Maximum number of concurrent tasks (default: 10)
        max_tokens: Maximum tokens per request (default: 2048)
        temperature: Sampling temperature (default: 0.7)
        top_p: Top-p sampling parameter (default: 0.9)

    Returns:
        ModelDistributor: Initialized model distributor with single SGLang model
    """
    # Create OpenAI configuration
    openai_config = OpenAIConfig(
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    # Initialize SGLang model
    model = SGLangModel(
        model_id=model_id,
        capacity=capacity,
        supported_tasks=[
            TaskType.TEXT_GENERATION,
            TaskType.IMAGE_ANALYSIS,
            TaskType.DATA_PROCESSING,
        ],
        base_url=base_url,
        openai_config=openai_config,
        api_key=api_key or "EMPTY",
    )

    # Setup model distributor
    distributor = ModelDistributor()
    distributor.add_model(model)

    return distributor


if __name__ == "__main__":
    distributor = setup_single_sglang_model_server(
        model_id="sglang-1",
        base_url="https://api.openai.com/v1/engines/davinci-codex/completions",
        api_key="YOUR_API_KEY",
    )
    print(distributor.models)
