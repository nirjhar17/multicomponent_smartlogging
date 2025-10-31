"""
Unified Inference Module for AI Troubleshooter v10
Provides a single interface for calling different model providers
"""

from llama_stack_client import LlamaStackClient
from openai import OpenAI
from typing import List, Dict, Any
from v10_model_config import ModelConfig


class UnifiedInference:
    """
    Unified interface for calling different model providers.
    
    Supports:
    - Llama Stack (local)
    - OpenAI API (GPT models)
    - X.ai API (Grok)
    - vLLM (OpenAI-compatible)
    """
    
    def __init__(self, model_config: ModelConfig):
        """
        Initialize inference client for the specified model.
        
        Args:
            model_config: Configuration for the model to use
        """
        self.config = model_config
        
        # Initialize appropriate client based on provider
        if model_config.provider == "llamastack":
            self.client = LlamaStackClient(base_url=model_config.endpoint)
            
        elif model_config.provider in ["openai", "groq"]:
            # OpenAI SDK works for OpenAI and Groq (both use OpenAI-compatible API)
            self.client = OpenAI(
                api_key=model_config.api_key,
                base_url=model_config.endpoint
            )
            
        elif model_config.provider == "vllm":
            # vLLM uses OpenAI-compatible API but doesn't need API key
            self.client = OpenAI(
                api_key="EMPTY",  # vLLM doesn't require API key
                base_url=model_config.endpoint
            )
        
        print(f"✅ Initialized {model_config.display_name} ({model_config.provider})")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.0
    ) -> str:
        """
        Generate chat completion across all providers.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            
        Returns:
            Generated text response
        """
        
        if self.config.provider == "llamastack":
            # Llama Stack has its own API format
            response = self.client.inference.chat_completion(
                model_id=self.config.model_id,
                messages=messages,
                sampling_params={
                    "strategy": {"type": "greedy"},
                    "max_tokens": max_tokens
                }
            )
            return response.completion_message.content
        
        else:
            # OpenAI-compatible API (OpenAI, Grok, vLLM)
            response = self.client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
    
    def get_model_name(self) -> str:
        """Get the display name of the current model"""
        return self.config.display_name
    
    def get_provider(self) -> str:
        """Get the provider type"""
        return self.config.provider

