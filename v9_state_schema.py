"""
AI Troubleshooter v7 - State Schema
Multi-Agent Self-Corrective RAG for OpenShift Log Analysis
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from datetime import datetime


class GraphState(TypedDict):
    """
    State for OpenShift Log Analysis Multi-Agent Workflow
    
    Attributes:
        # Input
        question: User's question/query about the issue
        namespace: OpenShift namespace to analyze
        pod_name: Specific pod name (optional)
        time_window: Time window for log collection (minutes)
        
        # Log Context
        log_context: Raw logs collected from OpenShift
        pod_events: Kubernetes events related to pods
        pod_status: Pod status information
        
        # Retrieval
        retrieved_docs: Documents retrieved by hybrid retrieval
        reranked_docs: Documents after reranking
        relevance_scores: Scores for each document
        
        # Generation
        generation: LLM-generated answer
        
        # Self-Correction
        iteration: Current iteration count
        max_iterations: Maximum allowed iterations
        transformation_history: List of query transformations
        
        # Metadata
        timestamp: When the analysis started
        data_source: Source of data (MCP or oc commands)
    """
    # Input
    question: str
    namespace: str
    pod_name: Optional[str]
    time_window: int  # minutes
    
    # Log Context
    log_context: str
    pod_events: str
    pod_status: Dict[str, Any]
    
    # Retrieval
    retrieved_docs: List[Dict[str, Any]]
    reranked_docs: List[Dict[str, Any]]
    relevance_scores: List[float]
    
    # Generation
    generation: str
    
    # Self-Correction
    iteration: int
    max_iterations: int
    transformation_history: List[str]
    
    # Metadata
    timestamp: str
    data_source: str


class LogDocument(TypedDict):
    """Structured log document"""
    content: str
    namespace: str
    pod_name: str
    container: Optional[str]
    timestamp: str
    log_type: str  # 'log', 'event', 'status'
    metadata: Dict[str, Any]


class RetrievalResult(TypedDict):
    """Result from hybrid retrieval"""
    documents: List[LogDocument]
    scores: List[float]
    retrieval_method: str  # 'bm25', 'vector', 'hybrid'
    query: str


class GradingResult(TypedDict):
    """Result from document grading"""
    relevant: bool
    score: float
    reasoning: str
    document_id: int

