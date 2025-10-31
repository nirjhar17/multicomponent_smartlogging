"""
Model Configuration for AI Troubleshooter v10
Manages multiple AI models (local and foundation models)
"""

from dataclasses import dataclass
from typing import Optional, Dict
import os


@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    id: str
    display_name: str
    provider: str  # 'llamastack', 'openai', 'grok', 'vllm'
    endpoint: str
    api_key: Optional[str] = None
    model_id: str = None
    description: str = ""


# Model registry - all available models
MODELS = {
    "llama-3b": ModelConfig(
        id="llama-3b",
        display_name="🦙 Llama 3.2 3B (Fast, Local)",
        provider="llamastack",
        endpoint=os.getenv("LLAMA_STACK_URL", "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"),
        model_id="llama-32-3b-instruct",
        description="Fast local model, good for quick analysis"
    ),
    "qwen-32b": ModelConfig(
        id="qwen-32b",
        display_name="🌟 Qwen 2.5 32B (Powerful, Local)",
        provider="vllm",
        endpoint=os.getenv("QWEN_ENDPOINT", ""),  # To be set after RHOAI deployment
        model_id="Qwen/Qwen2.5-32B-Instruct",
        description="More capable local model for complex issues"
    ),
    "granite-8b": ModelConfig(
        id="granite-8b",
        display_name="💎 Granite 3.1 8B (Local)",
        provider="vllm",
        endpoint=os.getenv("GRANITE_ENDPOINT", ""),  # Alternative to Qwen
        model_id="ibm-granite/granite-3.1-8b-instruct",
        description="IBM Granite model for enterprise workloads"
    ),
    "groq": ModelConfig(
        id="groq",
        display_name="⚡ Groq (Lightning Fast)",
        provider="groq",
        endpoint="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY", ""),
        model_id="llama-3.3-70b-versatile",
        description="Ultra-fast inference with Groq LPU"
    ),
    "gpt-4o": ModelConfig(
        id="gpt-4o",
        display_name="🧠 GPT-4o (OpenAI Foundation)",
        provider="openai",
        endpoint="https://api.openai.com/v1",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model_id="gpt-4o",
        description="Most capable OpenAI model"
    ),
    "gpt-4o-mini": ModelConfig(
        id="gpt-4o-mini",
        display_name="⚡ GPT-4o Mini (OpenAI, Fast)",
        provider="openai",
        endpoint="https://api.openai.com/v1",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model_id="gpt-4o-mini",
        description="Faster, cheaper OpenAI model"
    )
}


def get_available_models() -> Dict[str, ModelConfig]:
    """
    Returns only models that have required configuration.
    
    A model is considered available if:
    - Local models (llamastack/vllm): endpoint is configured
    - Foundation models (openai/grok): API key is provided
    
    Returns:
        Dict mapping model IDs to ModelConfig objects
    """
    available = {}
    
    for model_id, config in MODELS.items():
        # Check if model is properly configured
        if config.provider == "llamastack":
            # Llama Stack always available (default endpoint)
            if config.endpoint:
                available[model_id] = config
                
        elif config.provider == "vllm":
            # vLLM models need endpoint configured
            if config.endpoint:
                available[model_id] = config
                
        elif config.provider in ["openai", "groq"]:
            # Foundation models need API key
            if config.api_key:
                available[model_id] = config
    
    return available


def get_model_by_id(model_id: str) -> Optional[ModelConfig]:
    """Get a specific model configuration by ID"""
    return MODELS.get(model_id)

