"""
K8s Hybrid Retriever - NVIDIA's Approach Adapted for OpenShift
Based on: GenerativeAIExamples/community/log_analysis_multi_agent_rag/multiagent.py

Key Features:
- In-memory FAISS vector store (no persistent DB)
- BM25 + FAISS with RRF via LangChain's EnsembleRetriever
- 20K character chunks with 50% overlap (NVIDIA's proven settings)
- Fresh logs fetched on-demand from OpenShift
- Uses Granite 125M embeddings (self-hosted via Llama Stack)
"""

import os
import logging
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.embeddings import Embeddings
from llama_stack_client import LlamaStackClient

logger = logging.getLogger(__name__)


class GraniteEmbeddings(Embeddings):
    """
    Embeddings wrapper for Granite 125M via Llama Stack
    (Replaces NVIDIA embeddings with our self-hosted model)
    """
    
    def __init__(self, llama_stack_url: str, embedding_model: str = "granite-embedding-125m"):
        self.client = LlamaStackClient(base_url=llama_stack_url)
        self.embedding_model = embedding_model
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        embeddings = []
        for text in texts:
            try:
                # Use Llama Stack's embedding API
                response = self.client.inference.embeddings(
                    model_id=self.embedding_model,
                    contents=[text]
                )
                # Extract embedding vector
                if hasattr(response, 'embeddings') and len(response.embeddings) > 0:
                    embeddings.append(response.embeddings[0])
                else:
                    logger.warning(f"No embedding returned for text: {text[:100]}")
                    embeddings.append([0.0] * 768)  # Granite 125M dimension (same as v8)
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                embeddings.append([0.0] * 768)  # Granite 125M dimension (same as v8)
                
        return embeddings
        
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        return self.embed_documents([text])[0]


class K8sHybridRetriever:
    """
    NVIDIA-style Hybrid Retriever for Kubernetes Logs
    
    Workflow:
    1. Fetch logs from OpenShift (on-demand)
    2. Chunk into 20K chars with 50% overlap
    3. Build in-memory BM25 index
    4. Build in-memory FAISS vector store
    5. Combine with EnsembleRetriever (RRF)
    6. Return results
    7. Discard indexes (ephemeral)
    """
    
    def __init__(self, log_content: str, llama_stack_url: str):
        """
        Initialize hybrid retriever with log content
        
        Args:
            log_content: Raw log text (from K8sLogFetcher)
            llama_stack_url: URL to Llama Stack for embeddings
        """
        self.log_content = log_content
        self.llama_stack_url = llama_stack_url
        
        # Initialize embeddings (Granite 125M via Llama Stack)
        logger.info("Initializing Granite embeddings...")
        embedding_model = os.getenv("EMBEDDING_MODEL", "granite-embedding-125m")
        self.embeddings = GraniteEmbeddings(
            llama_stack_url=llama_stack_url,
            embedding_model=embedding_model
        )
        
        # Load and chunk documents (NVIDIA's settings: 20K chars, 50% overlap)
        logger.info("Chunking documents...")
        self.doc_splits = self.load_and_split_documents()
        logger.info(f"Created {len(self.doc_splits)} chunks")
        
        # Create retrievers
        logger.info("Building BM25 index...")
        self.bm25_retriever = self.create_bm25_retriever()
        
        logger.info("Building FAISS vector store...")
        self.faiss_retriever = self.create_faiss_retriever()
        
        # Create hybrid retriever (RRF via EnsembleRetriever)
        logger.info("Creating hybrid retriever with RRF...")
        self.hybrid_retriever = self.create_hybrid_retriever()
        
        logger.info("✅ Hybrid retriever ready!")
        
    def load_and_split_documents(self) -> List[Document]:
        """
        Chunk log content using NVIDIA's proven settings
        
        Returns:
            List of LangChain Document objects
        """
        # Create a single Document from log content
        doc = Document(page_content=self.log_content, metadata={"source": "k8s_logs"})
        
        # Adapted chunking for BGE Reranker (512 token limit)
        # 1K chars ≈ 250 tokens, well within BGE's limit
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,       # 1K characters per chunk (fits BGE reranker)
            chunk_overlap=200,     # 20% overlap
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        doc_splits = text_splitter.split_documents([doc])
        return doc_splits
        
    def create_bm25_retriever(self) -> BM25Retriever:
        """
        Create BM25 retriever (lexical/keyword matching)
        
        Returns:
            BM25Retriever instance
        """
        bm25_retriever = BM25Retriever.from_documents(self.doc_splits)
        bm25_retriever.k = 10  # Return top 10 results
        return bm25_retriever
        
    def create_faiss_retriever(self):
        """
        Create FAISS retriever (semantic vector search)
        
        Returns:
            FAISS retriever instance
        """
        # Build FAISS index with Granite embeddings
        faiss_vectorstore = FAISS.from_documents(
            self.doc_splits,
            self.embeddings
        )
        
        # Configure retriever
        faiss_retriever = faiss_vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={'k': 10}  # Return top 10 results
        )
        
        return faiss_retriever
        
    def create_hybrid_retriever(self) -> EnsembleRetriever:
        """
        Create hybrid retriever combining BM25 + FAISS with RRF
        (Exact same approach as NVIDIA)
        
        Returns:
            EnsembleRetriever with RRF
        """
        hybrid_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, self.faiss_retriever],
            weights=[0.5, 0.5]  # Equal weights (50/50) - NVIDIA's setting
        )
        return hybrid_retriever
        
    def get_retriever(self) -> EnsembleRetriever:
        """
        Get the hybrid retriever instance
        
        Returns:
            EnsembleRetriever ready for queries
        """
        return self.hybrid_retriever
        
    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User question
            k: Number of results to return
            
        Returns:
            List of relevant Document objects
        """
        # Update k for retrievers
        self.bm25_retriever.k = k
        self.faiss_retriever.search_kwargs['k'] = k
        
        # Retrieve using hybrid approach (RRF happens automatically)
        # LangChain 1.0+ uses invoke() instead of get_relevant_documents()
        documents = self.hybrid_retriever.invoke(query)
        
        logger.info(f"Retrieved {len(documents)} documents for query: {query[:100]}")
        return documents[:k]


def create_k8s_hybrid_retriever(
    log_content: str,
    llama_stack_url: str
) -> K8sHybridRetriever:
    """
    Factory function to create hybrid retriever
    
    Args:
        log_content: Raw log text from OpenShift
        llama_stack_url: URL to Llama Stack service
        
    Returns:
        Initialized K8sHybridRetriever
    """
    return K8sHybridRetriever(log_content, llama_stack_url)

