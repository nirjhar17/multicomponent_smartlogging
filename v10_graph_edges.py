"""
AI Troubleshooter v9 - Graph Edges
Conditional routing logic for self-correction
"""

from typing import Literal
from v10_state_schema import GraphState


class Edge:
    """
    Edge decision functions for routing in the workflow
    These implement the self-correction logic
    """
    
    @staticmethod
    def decide_to_generate(
        state: GraphState
    ) -> Literal["generate", "transform_query"]:
        """
        DECISION 1: After grading, should we generate or transform query?
        
        Logic:
        - If we have relevant documents → generate
        - If no relevant documents and haven't hit max iterations → transform_query
        - If no relevant documents and hit max iterations → generate (with empty context)
        
        Args:
            state: Current graph state
            
        Returns:
            "generate" or "transform_query"
        """
        print("\n🤔 DECISION: Should we generate or transform query?")
        
        reranked_docs = state.get("reranked_docs", [])
        relevance_scores = state.get("relevance_scores", [])
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        
        # Calculate relevance ratio
        if relevance_scores:
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
        else:
            avg_relevance = 0.0
        
        num_relevant = len(reranked_docs)
        
        print(f"   📊 Relevant docs: {num_relevant}")
        print(f"   📊 Avg relevance: {avg_relevance:.2f}")
        print(f"   📊 Iteration: {iteration}/{max_iterations}")
        
        # Decision logic
        if num_relevant == 0:
            if iteration < max_iterations:
                print("   ➡️  DECISION: No relevant docs, transform query and retry")
                return "transform_query"
            else:
                print("   ➡️  DECISION: Max iterations reached, generate with what we have")
                return "generate"
        
        elif avg_relevance < 0.7 and num_relevant < 3:
            if iteration < max_iterations:
                print("   ➡️  DECISION: Low relevance, transform query for better results")
                return "transform_query"
            else:
                print("   ➡️  DECISION: Max iterations reached, generate answer")
                return "generate"
        
        else:
            print("   ➡️  DECISION: Sufficient relevant docs, proceed to generate")
            return "generate"
    
    @staticmethod
    def grade_generation_vs_documents_and_question(
        state: GraphState
    ) -> Literal["useful", "not useful", "not supported"]:
        """
        DECISION 2: After generation, is the answer good enough?
        
        Logic:
        - Check if answer is useful and supported by docs
        - If not useful and haven't hit max iterations → transform_query
        - If hit max iterations → accept answer
        
        Args:
            state: Current graph state
            
        Returns:
            "useful", "not useful", or "not supported"
        """
        print("\n🤔 DECISION: Is the generated answer useful?")
        
        generation = state.get("generation", "")
        reranked_docs = state.get("reranked_docs", [])
        question = state.get("question", "")
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        
        # Simple heuristic checks
        has_content = len(generation) > 100
        has_docs = len(reranked_docs) > 0
        has_error_marker = "❌" in generation or "error" in generation.lower()
        
        print(f"   📊 Answer length: {len(generation)} chars")
        print(f"   📊 Has docs: {has_docs}")
        print(f"   📊 Iteration: {iteration}/{max_iterations}")
        
        # If we hit max iterations, accept the answer
        if iteration >= max_iterations:
            print("   ➡️  DECISION: Max iterations reached, accepting answer (useful)")
            return "useful"
        
        # Check if answer has content and is supported
        if has_content and has_docs:
            # Check if answer seems to address the question
            question_keywords = set(question.lower().split())
            answer_keywords = set(generation.lower().split())
            
            # At least some overlap
            overlap = len(question_keywords & answer_keywords)
            
            if overlap > 2:
                print("   ➡️  DECISION: Answer appears useful (useful)")
                return "useful"
            else:
                print("   ➡️  DECISION: Answer doesn't address question well (not useful)")
                return "not useful"
        
        elif not has_docs:
            print("   ➡️  DECISION: No supporting documents (not supported)")
            return "not supported"
        
        else:
            print("   ➡️  DECISION: Answer too short or incomplete (not useful)")
            return "not useful"


def test_edge_decisions():
    """Test edge decision functions"""
    
    # Test 1: Good docs, should generate
    state1: GraphState = {
        "question": "Why is the pod failing?",
        "namespace": "default",
        "pod_name": "test-pod",
        "time_window": 30,
        "log_context": "",
        "pod_events": "",
        "pod_status": {},
        "retrieved_docs": [{"content": "doc1"}, {"content": "doc2"}],
        "reranked_docs": [{"content": "doc1"}, {"content": "doc2"}],
        "relevance_scores": [1.0, 1.0],
        "generation": "",
        "iteration": 0,
        "max_iterations": 3,
        "transformation_history": [],
        "timestamp": "",
        "data_source": ""
    }
    
    decision1 = Edge.decide_to_generate(state1)
    print(f"\nTest 1 Result: {decision1}")
    assert decision1 == "generate", "Should generate with good docs"
    
    # Test 2: No docs, should transform
    state2 = state1.copy()
    state2["reranked_docs"] = []
    state2["relevance_scores"] = []
    
    decision2 = Edge.decide_to_generate(state2)
    print(f"\nTest 2 Result: {decision2}")
    assert decision2 == "transform_query", "Should transform with no docs"
    
    # Test 3: Max iterations, should generate anyway
    state3 = state2.copy()
    state3["iteration"] = 3
    
    decision3 = Edge.decide_to_generate(state3)
    print(f"\nTest 3 Result: {decision3}")
    assert decision3 == "generate", "Should generate at max iterations"
    
    print("\n✅ All edge tests passed!")


if __name__ == "__main__":
    test_edge_decisions()

