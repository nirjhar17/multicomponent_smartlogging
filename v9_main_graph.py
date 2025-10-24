"""
AI Troubleshooter v7 - Main LangGraph Workflow
Multi-Agent Self-Corrective RAG System for OpenShift Log Analysis
"""

import os
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from v9_state_schema import GraphState
from v9_graph_nodes import Nodes, get_nodes_instance
from v9_graph_edges import Edge
from datetime import datetime


def create_workflow(
    llama_stack_url: str = None,
    max_iterations: int = 3,
    vector_db_id: str = None,
    reranker_url: str = None,
    checkpointer = None
) -> StateGraph:
    """
    Create the LangGraph workflow for log analysis
    
    Args:
        llama_stack_url: URL to Llama Stack service
        max_iterations: Maximum self-correction iterations (default: 3)
        vector_db_id: Vector database ID (default: from env or openshift-logs-v8)
        reranker_url: BGE Reranker URL (default: from env)
        checkpointer: Optional checkpointer for conversation memory (MemorySaver or PostgresSaver)
        
    Returns:
        Compiled StateGraph application
    """
    print("🏗️  Building Multi-Agent Log Analysis Workflow...")
    
    # Initialize nodes
    if llama_stack_url is None:
        llama_stack_url = os.getenv(
            "LLAMA_STACK_URL",
            "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
        )
    
    if vector_db_id is None:
        vector_db_id = os.getenv("VECTOR_DB_ID", "openshift-logs-v8")
    
    if reranker_url is None:
        reranker_url = os.getenv("BGE_RERANKER_URL", "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com")
    
    nodes = get_nodes_instance(llama_stack_url, vector_db_id, reranker_url)
    
    # Create StateGraph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    print("   📍 Adding nodes...")
    workflow.add_node("retrieve", nodes.retrieve)
    workflow.add_node("rerank", nodes.rerank)
    workflow.add_node("grade_documents", nodes.grade_documents)
    workflow.add_node("generate", nodes.generate)
    workflow.add_node("transform_query", nodes.transform_query)
    
    # Build graph edges
    print("   🔗 Adding edges...")
    
    # Start → Retrieve
    workflow.add_edge(START, "retrieve")
    
    # Retrieve → Rerank (always)
    workflow.add_edge("retrieve", "rerank")
    
    # Rerank → Grade (always)
    workflow.add_edge("rerank", "grade_documents")
    
    # Grade → Generate OR Transform (conditional)
    workflow.add_conditional_edges(
        "grade_documents",
        Edge.decide_to_generate,
        {
            "transform_query": "transform_query",
            "generate": "generate",
        },
    )
    
    # Transform → Retrieve (loop back for retry)
    workflow.add_edge("transform_query", "retrieve")
    
    # Generate → END OR Transform (conditional)
    workflow.add_conditional_edges(
        "generate",
        Edge.grade_generation_vs_documents_and_question,
        {
            "not supported": "generate",  # Try again with same context
            "useful": END,  # Success!
            "not useful": "transform_query",  # Retry with new query
        },
    )
    
    print("   ✅ Workflow graph built!")
    print("   🔄 Self-correction enabled (max iterations: {})".format(max_iterations))
    
    # Compile the graph with optional checkpointer for memory
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        print("   💾 Checkpointer enabled for conversation memory!")
    else:
        app = workflow.compile()
        print("   ⚠️  No checkpointer - conversations won't persist")
    
    print("   ✅ Workflow compiled and ready!")
    
    return app


def run_analysis(
    question: str,
    namespace: str,
    pod_name: str = None,
    log_context: str = "",
    pod_events: str = "",
    pod_status: dict = None,
    time_window: int = 30,
    max_iterations: int = 3,
    llama_stack_url: str = None,
    vector_db_id: str = None,
    reranker_url: str = None
) -> dict:
    """
    Run a complete log analysis using the multi-agent workflow
    
    Args:
        question: User's question about the issue
        namespace: OpenShift namespace
        pod_name: Specific pod to analyze (optional)
        log_context: Raw logs from OpenShift
        pod_events: Kubernetes events
        pod_status: Pod status information
        time_window: Time window for analysis (minutes)
        max_iterations: Max self-correction iterations
        llama_stack_url: Llama Stack URL
        vector_db_id: Vector database ID
        reranker_url: BGE Reranker URL
        
    Returns:
        Dict with analysis results including generation, docs, and metadata
    """
    print("\n" + "="*80)
    print("🚀 AI TROUBLESHOOTER v8 - Multi-Agent Log Analysis")
    print("="*80)
    
    # Create workflow
    app = create_workflow(
        llama_stack_url=llama_stack_url,
        max_iterations=max_iterations,
        vector_db_id=vector_db_id,
        reranker_url=reranker_url
    )
    
    # Prepare initial state
    initial_state: GraphState = {
        # Input
        "question": question,
        "namespace": namespace,
        "pod_name": pod_name,
        "time_window": time_window,
        
        # Log Context
        "log_context": log_context,
        "pod_events": pod_events,
        "pod_status": pod_status or {},
        
        # Retrieval (empty initially)
        "retrieved_docs": [],
        "reranked_docs": [],
        "relevance_scores": [],
        
        # Generation (empty initially)
        "generation": "",
        
        # Self-Correction
        "iteration": 0,
        "max_iterations": max_iterations,
        "transformation_history": [],
        
        # Metadata
        "timestamp": datetime.now().isoformat(),
        "data_source": "mcp"
    }
    
    print(f"\n📝 Question: {question}")
    print(f"📍 Namespace: {namespace}")
    if pod_name:
        print(f"🐳 Pod: {pod_name}")
    print(f"⏱️  Time Window: {time_window} minutes")
    print(f"🔄 Max Iterations: {max_iterations}")
    
    # Run the workflow
    print("\n🔄 Starting multi-agent workflow...")
    print("="*80)
    
    try:
        # Execute the workflow
        final_state = app.invoke(initial_state)
        
        print("\n" + "="*80)
        print("✅ WORKFLOW COMPLETE")
        print("="*80)
        
        # Extract results
        result = {
            "success": True,
            "question": final_state.get("question"),
            "original_question": question,
            "answer": final_state.get("generation", ""),
            "relevant_docs": final_state.get("reranked_docs", []),
            "iterations": final_state.get("iteration", 0),
            "transformation_history": final_state.get("transformation_history", []),
            "timestamp": final_state.get("timestamp"),
            "metadata": {
                "namespace": namespace,
                "pod_name": pod_name,
                "num_docs_retrieved": len(final_state.get("retrieved_docs", [])),
                "num_docs_relevant": len(final_state.get("reranked_docs", [])),
                "avg_relevance": (
                    sum(final_state.get("relevance_scores", [])) / 
                    len(final_state.get("relevance_scores", []))
                    if final_state.get("relevance_scores") else 0
                )
            }
        }
        
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   ✅ Success: {result['success']}")
        print(f"   🔄 Iterations: {result['iterations']}")
        print(f"   📄 Relevant Docs: {result['metadata']['num_docs_relevant']}")
        print(f"   📈 Avg Relevance: {result['metadata']['avg_relevance']:.2f}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ WORKFLOW ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "question": question,
            "answer": f"❌ Analysis failed: {str(e)}"
        }


def visualize_workflow(save_path: str = None):
    """
    Visualize the workflow graph
    
    Args:
        save_path: Path to save the visualization (optional)
    """
    try:
        from graphviz import Digraph
        
        app = create_workflow()
        
        # Create visualization
        dot = Digraph(comment='AI Troubleshooter v7 Workflow')
        dot.attr(rankdir='TB')
        
        # Add nodes
        nodes_list = [
            ("START", "Start", "lightgreen"),
            ("retrieve", "1. Retrieve\n(BM25 + Vector)", "lightblue"),
            ("rerank", "2. Rerank\n(Score Sorting)", "lightblue"),
            ("grade_documents", "3. Grade\n(Relevance Check)", "lightyellow"),
            ("generate", "4. Generate\n(LLM Answer)", "lightcoral"),
            ("transform_query", "5. Transform\n(Query Rewrite)", "plum"),
            ("END", "End", "lightgreen")
        ]
        
        for node_id, label, color in nodes_list:
            dot.node(node_id, label, style='filled', fillcolor=color)
        
        # Add edges
        dot.edge("START", "retrieve")
        dot.edge("retrieve", "rerank")
        dot.edge("rerank", "grade_documents")
        dot.edge("grade_documents", "generate", label="good docs")
        dot.edge("grade_documents", "transform_query", label="poor docs")
        dot.edge("transform_query", "retrieve", label="retry")
        dot.edge("generate", "END", label="useful")
        dot.edge("generate", "transform_query", label="not useful")
        
        if save_path:
            dot.render(save_path, format='png', cleanup=True)
            print(f"✅ Workflow visualization saved to {save_path}.png")
        
        return dot
        
    except ImportError:
        print("⚠️  graphviz not installed, skipping visualization")
        return None


# Example usage
if __name__ == "__main__":
    # Example 1: Simple test
    result = run_analysis(
        question="Why is the pod in CrashLoopBackOff?",
        namespace="ai-troubleshooter-v6",
        pod_name="ai-troubleshooter-gui-v6-abc123",
        log_context="Error: Container exited with code 1\nImagePullBackOff: Failed to pull image",
        max_iterations=2
    )
    
    print("\n" + "="*80)
    print("📋 FINAL ANSWER:")
    print("="*80)
    print(result["answer"])
    
    # Example 2: Visualize workflow
    print("\n📊 Generating workflow visualization...")
    visualize_workflow(save_path="/tmp/v7_workflow")

