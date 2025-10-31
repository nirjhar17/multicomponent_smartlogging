"""
LangSmith Configuration for AI Troubleshooter v10
Enables tracing, monitoring, and debugging of LangGraph workflows
"""

import os
from langsmith import Client
from typing import Optional

# LangSmith Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")  # Set via environment variable
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-troubleshooter-v10")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

def setup_langsmith() -> Optional[Client]:
    """
    Initialize LangSmith client and set environment variables
    
    Returns:
        LangSmith Client instance or None if disabled
    """
    # Set environment variables for automatic tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    
    try:
        client = Client(
            api_key=LANGSMITH_API_KEY,
            api_url=LANGSMITH_ENDPOINT
        )
        
        print(f"✅ LangSmith tracing enabled")
        print(f"   📊 Project: {LANGSMITH_PROJECT}")
        print(f"   🔗 Dashboard: https://smith.langchain.com/o/default/projects/p/{LANGSMITH_PROJECT}")
        
        return client
        
    except Exception as e:
        print(f"⚠️  LangSmith initialization failed: {e}")
        print(f"   Continuing without tracing...")
        return None


def create_run_metadata(
    namespace: str = None,
    pod_name: str = None,
    question: str = None,
    **kwargs
) -> dict:
    """
    Create metadata for LangSmith run tracking
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name being analyzed
        question: User's question
        **kwargs: Additional metadata
        
    Returns:
        Metadata dictionary for LangSmith
    """
    metadata = {
        "version": "v10",
        "application": "ai-troubleshooter"
    }
    
    if namespace:
        metadata["namespace"] = namespace
    if pod_name:
        metadata["pod_name"] = pod_name
    if question:
        metadata["question"] = question[:100]  # Truncate long questions
    
    # Add any additional metadata
    metadata.update(kwargs)
    
    return metadata


def get_langsmith_tags(iteration: int = 0) -> list:
    """
    Generate tags for LangSmith runs
    
    Args:
        iteration: Current iteration number
        
    Returns:
        List of tags
    """
    tags = ["ai-troubleshooter", "v10", "kubernetes", "troubleshooting"]
    
    if iteration > 0:
        tags.append(f"iteration-{iteration}")
        tags.append("self-correction")
    
    return tags


# Initialize LangSmith on module import
langsmith_client = setup_langsmith()



