"""
BGE Reranker Client for AI Troubleshooter v7
Integrates BAAI BGE Reranker v2-m3 via vLLM inference service
"""

import os
import requests
from typing import List, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BGEReranker:
    """
    Client for BGE Reranker v2-m3 inference service
    Uses vLLM's score API endpoint for reranking
    """
    
    def __init__(
        self,
        reranker_url: str = None,
        model_name: str = "bge-reranker",
        timeout: int = 30
    ):
        """
        Initialize BGE Reranker client
        
        Args:
            reranker_url: URL to BGE reranker inference service
            model_name: Name of the model served
            timeout: Request timeout in seconds
        """
        self.reranker_url = reranker_url or os.getenv(
            "BGE_RERANKER_URL",
            "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com"
        )
        self.model_name = model_name
        self.timeout = timeout
        
        # Ensure URL has proper protocol
        if not self.reranker_url.startswith(('http://', 'https://')):
            self.reranker_url = f"http://{self.reranker_url}"
        
        logger.info(f"Initialized BGE Reranker: {self.reranker_url}")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents using BGE Reranker
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            top_k: Number of top documents to return
            
        Returns:
            List of (original_index, score) tuples, sorted by score descending
        """
        if not documents:
            logger.warning("No documents to rerank")
            return []
        
        try:
            # Prepare request payloads for vLLM score endpoint
            # vLLM reranker expects pairwise comparisons: {"text_1": query, "text_2": document}
            # We need to score each document individually
            
            logger.info(f"Reranking {len(documents)} documents...")
            
            scores = []
            score_url = f"{self.reranker_url}/score"
            
            for idx, doc in enumerate(documents):
                payload = {
                    "model": self.model_name,
                    "text_1": query,
                    "text_2": doc
                }
                
                logger.debug(f"Scoring document {idx+1}/{len(documents)}")
                
                response = requests.post(
                    score_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )
            
                if response.status_code != 200:
                    logger.error(f"Reranker API error for doc {idx}: {response.status_code} - {response.text}")
                    # Use fallback score for this document
                    scores.append({"index": idx, "score": 0.5})
                    continue
                
                # Parse response
                result = response.json()
                
                # vLLM score endpoint returns:
                # {"data": [{"index": 0, "object": "score", "score": 0.028...}], ...}
                if isinstance(result, dict) and "data" in result:
                    if isinstance(result["data"], list) and len(result["data"]) > 0:
                        score_data = result["data"][0]
                        if isinstance(score_data, dict) and "score" in score_data:
                            score = float(score_data["score"])
                        else:
                            logger.warning(f"No score in data for doc {idx}: {score_data}")
                            score = 0.5
                    elif isinstance(result["data"], dict) and "score" in result["data"]:
                        score = float(result["data"]["score"])
                    else:
                        logger.warning(f"Unexpected data format for doc {idx}: {result}")
                        score = 0.5
                elif isinstance(result, dict) and "score" in result:
                    score = float(result["score"])
                else:
                    logger.warning(f"Unexpected response format for doc {idx}: {result}")
                    score = 0.5
                
                scores.append({"index": idx, "score": score})
            
            # Sort by score descending
            ranked = sorted(
                [(s["index"], s["score"]) for s in scores],
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            logger.info(f"✅ Reranked to top {len(ranked)} documents")
            for idx, (orig_idx, score) in enumerate(ranked[:3]):
                logger.debug(f"  {idx+1}. Doc {orig_idx}: {score:.4f}")
            
            return ranked
            
        except requests.exceptions.Timeout:
            logger.error(f"Reranker request timeout after {self.timeout}s")
            return self._fallback_ranking(documents, top_k)
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to reranker service: {e}")
            return self._fallback_ranking(documents, top_k)
            
        except Exception as e:
            logger.error(f"Reranking error: {e}", exc_info=True)
            return self._fallback_ranking(documents, top_k)
    
    def rerank_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank a list of document dictionaries
        
        Args:
            query: The search query
            documents: List of document dicts with 'content' field
            top_k: Number of top documents to return
            
        Returns:
            Reranked list of documents with updated scores
        """
        if not documents:
            return []
        
        # Extract content
        doc_contents = [doc.get('content', '') for doc in documents]
        
        # Get reranking scores
        ranked = self.rerank(query, doc_contents, top_k=top_k)
        
        if not ranked:
            # Fallback: return original top_k
            return documents[:top_k]
        
        # Build reranked document list
        reranked_docs = []
        for rank, (orig_idx, score) in enumerate(ranked, start=1):
            if orig_idx < len(documents):
                doc = documents[orig_idx].copy()
                doc['rerank_score'] = float(score)
                doc['original_rank'] = orig_idx + 1
                doc['new_rank'] = rank
                # Update main score to rerank score
                doc['score'] = float(score)
                reranked_docs.append(doc)
        
        return reranked_docs
    
    def _fallback_ranking(self, documents: List[str], top_k: int) -> List[Tuple[int, float]]:
        """
        Fallback ranking when reranker is unavailable
        Returns original order with synthetic scores
        """
        logger.warning("Using fallback ranking (original order)")
        return [(i, 1.0 - (i * 0.1)) for i in range(min(top_k, len(documents)))]
    
    def health_check(self) -> bool:
        """
        Check if reranker service is healthy
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            health_url = f"{self.reranker_url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ BGE Reranker service is healthy")
                return True
            else:
                logger.warning(f"⚠️ BGE Reranker health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ BGE Reranker service unavailable: {e}")
            return False


def test_bge_reranker():
    """Test function for BGE reranker"""
    
    # Initialize reranker
    reranker = BGEReranker()
    
    # Test health check
    is_healthy = reranker.health_check()
    print(f"Service healthy: {is_healthy}")
    
    # Test query
    query = "Why is my pod crashing with OOMKilled error?"
    
    # Sample documents
    documents = [
        "Pod ai-app-123 is running normally with 1/1 containers ready",
        "Container in pod ai-app-456 was terminated with exit code 137 (OOMKilled)",
        "Network connectivity issue detected in namespace default",
        "Memory limit exceeded: container requested 2Gi but limit is 1Gi",
        "ImagePullBackOff error for container nginx:latest"
    ]
    
    print(f"\nQuery: {query}")
    print(f"Documents to rerank: {len(documents)}")
    
    # Rerank
    ranked = reranker.rerank(query, documents, top_k=3)
    
    print("\n📊 Reranked Results:")
    for rank, (idx, score) in enumerate(ranked, start=1):
        print(f"{rank}. [Score: {score:.4f}] {documents[idx][:80]}...")


if __name__ == "__main__":
    test_bge_reranker()

