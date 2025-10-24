# File Guide

Quick reference for what each file does. Use this when you return to the project after months.

---

## 📚 Documentation Files

### README.md
**Purpose:** Project overview and quick start  
**Contains:** Features, installation, deployment steps  
**When to update:** New features, deployment changes  
**Read first:** Yes, start here

### ARCHITECTURE.md
**Purpose:** System design and how agents work  
**Contains:** 5-agent workflow, data flow, design decisions  
**When to update:** Architecture changes, new agents  
**Read when:** Understanding the system

### FILE_GUIDE.md
**Purpose:** This file - what each file does  
**Contains:** File descriptions, key functions, dependencies  
**When to update:** New files added, file purposes change  
**Read when:** Finding where to make changes

### CRITICAL_FIXES_APPLIED.md
**Purpose:** Technical details of 3 critical fixes  
**Contains:** Root cause analysis, before/after, code examples  
**When to update:** Major bug fixes, performance improvements  
**Read when:** Understanding why things work this way

---

## 🐍 Python Files (Core Logic)

### v7_graph_nodes.py
**Purpose:** Implements all 5 agents  
**Contains:**
- `Nodes` class with 5 methods (one per agent)
- `retrieve()` - Agent 1: Hybrid retrieval
- `rerank()` - Agent 2: BGE reranking
- `grade_documents()` - Agent 3: Document filtering
- `generate()` - Agent 4: Answer generation
- `transform_query()` - Agent 5: Query rewriting

**Key Functions:**
```python
class Nodes:
    def retrieve(state) -> retrieved_docs
    def rerank(state) -> reranked_docs
    def grade_documents(state) -> filtered_docs
    def generate(state) -> final_answer
    def transform_query(state) -> new_query
```

**Dependencies:**
- `k8s_hybrid_retriever.py` (retrieval)
- `v7_bge_reranker.py` (reranking)
- `llama_stack_client` (LLM calls)

**When to modify:**
- Change agent behavior
- Update prompts
- Adjust grading criteria
- Modify output format

---

### v7_graph_edges.py
**Purpose:** Routing logic between agents  
**Contains:**
- `Edge` class with routing decisions
- `decide_to_generate()` - Check document quality
- `grade_generation()` - Check answer quality

**Key Functions:**
```python
class Edge:
    def decide_to_generate(state):
        # If docs relevant → generate
        # If not → transform query
    
    def grade_generation(state):
        # If answer good → end
        # If not → transform query
```

**Dependencies:**
- `v7_state_schema.py` (state definition)

**When to modify:**
- Change routing rules
- Add new decision points
- Modify self-correction logic

---

### v7_main_graph.py
**Purpose:** Orchestrates the workflow using LangGraph  
**Contains:**
- `create_workflow()` - Builds the agent graph
- `run_analysis()` - Entry point for analysis

**Key Functions:**
```python
def create_workflow():
    # Connects 5 agents + routing
    # Returns compiled workflow

def run_analysis(question, namespace, pod_name, ...):
    # Runs workflow
    # Returns final answer
```

**Dependencies:**
- `v7_graph_nodes.py` (agents)
- `v7_graph_edges.py` (routing)
- `v7_state_schema.py` (state)
- `langgraph` (framework)

**When to modify:**
- Change workflow structure
- Add/remove agents
- Modify state flow

---

### v7_state_schema.py
**Purpose:** Defines workflow state (data passed between agents)  
**Contains:**
- `GraphState` TypedDict with all fields

**Key Structure:**
```python
class GraphState(TypedDict):
    question: str           # User query
    namespace: str          # K8s namespace
    pod_name: str           # Pod name
    log_context: str        # Raw logs
    retrieved_docs: list    # From Agent 1
    reranked_docs: list     # From Agent 2
    generation: str         # From Agent 4
    iteration: int          # Self-correction count
    # ... more fields
```

**Dependencies:** None (pure data structure)

**When to modify:**
- Add new data fields
- Change state structure
- Add metadata

---

### k8s_hybrid_retriever.py
**Purpose:** Hybrid retrieval (BM25 + FAISS + RRF)  
**Contains:**
- `GraniteEmbeddings` class (Granite 125M wrapper)
- `K8sHybridRetriever` class (main retriever)

**Key Functions:**
```python
class K8sHybridRetriever:
    def __init__(log_content, llama_stack_url):
        # Chunks logs (1K chars, 20% overlap)
        # Builds BM25 index
        # Builds FAISS index
    
    def retrieve(query, k=10):
        # BM25 search
        # FAISS search
        # RRF fusion
        # Returns top-k docs
```

**Dependencies:**
- `langchain` (text splitting, retrieval)
- `faiss` (vector search)
- `rank_bm25` (BM25 search)
- `llama_stack_client` (embeddings)

**When to modify:**
- Change chunk size
- Adjust BM25/FAISS weights
- Modify RRF formula
- Change k value

**Critical Fix:** Chunk size = 1000 (fits BGE's 512 token limit)

---

### k8s_log_fetcher.py
**Purpose:** Fetches logs from OpenShift/Kubernetes  
**Contains:**
- `K8sLogFetcher` class with oc/kubectl commands

**Key Functions:**
```python
class K8sLogFetcher:
    def fetch_pod_logs(namespace, pod_name):
        # Runs: oc logs pod
        # Returns log content
    
    def fetch_logs_as_text(namespace, pod_name):
        # Runs: oc describe pod
        # Returns formatted text
```

**Dependencies:**
- `subprocess` (run oc commands)

**When to modify:**
- Change log fetch method
- Add filtering
- Support different K8s versions

---

### v7_bge_reranker.py
**Purpose:** BGE Reranker v2-m3 client  
**Contains:**
- `BGEReranker` class (HTTP client)

**Key Functions:**
```python
class BGEReranker:
    def __init__(reranker_url):
        # Set up HTTP client
    
    def rerank_documents(query, documents, top_k):
        # Calls BGE API
        # Returns reranked docs
```

**Dependencies:**
- `httpx` (HTTP requests)

**When to modify:**
- Change reranker endpoint
- Adjust scoring
- Handle errors differently

---

### v7_hybrid_retriever.py
**Purpose:** Alternative retriever using Milvus (not currently used)  
**Contains:**
- `HybridRetriever` class with BM25 + Milvus

**Note:** This is an alternative implementation. Current deployment uses `k8s_hybrid_retriever.py` (FAISS-based).

**When to use:**
- If you have Milvus deployed
- For persistent vector storage
- For production-scale retrieval

---

### v7_log_collector.py
**Purpose:** Log collection and indexing into Milvus  
**Contains:**
- `OpenShiftLogCollector` class

**Note:** Alternative to on-demand log fetching. Useful if you want to pre-index logs.

**When to use:**
- Pre-index logs for faster queries
- Use Milvus for storage
- Need log history

---

### v7_streamlit_app.py
**Purpose:** Alternative Streamlit UI (older version)  
**Contains:** Streamlit interface

**Note:** Current deployment uses `v8_streamlit_chat_app.py`. This is kept for reference.

---

### v8_streamlit_chat_app.py
**Purpose:** Main Streamlit chat interface (current version)  
**Contains:**
- Chat UI with message history
- Namespace/pod selection
- Integration with v7_main_graph

**Key Functions:**
```python
# Streamlit app structure
st.title("Smart Logging")
st.chat_input("Ask a question...")
# Calls run_analysis()
# Displays results
```

**Dependencies:**
- `streamlit` (UI framework)
- `v7_main_graph` (workflow)

**When to modify:**
- Change UI layout
- Add new features
- Modify display format

---

## 📋 Configuration Files

### v7_requirements.txt
**Purpose:** Python dependencies  
**Contains:** List of pip packages

**Key Dependencies:**
```
langgraph>=0.2.0        # Workflow framework
langchain>=0.3.0        # LLM framework
llama-stack-client      # Llama Stack
faiss-cpu>=1.9.0        # Vector search
rank-bm25>=0.2.2        # BM25 search
streamlit>=1.28.0       # UI
```

**When to update:**
- Add new libraries
- Update versions
- Fix compatibility issues

---

### Dockerfile.v7
**Purpose:** Container build instructions  
**Contains:** Docker build steps

**When to modify:**
- Change base image
- Add system dependencies
- Optimize build

---

## ☸️ Kubernetes Files

### v7-deployment.yaml
**Purpose:** Main Kubernetes deployment  
**Contains:**
- Deployment spec
- Service definition
- Route/Ingress
- Environment variables

**Key Config:**
```yaml
env:
- LLAMA_STACK_URL: "http://..."
- BGE_RERANKER_URL: "https://..."
- LLAMA_STACK_MODEL: "llama-32-3b-instruct"
- EMBEDDING_MODEL: "granite-embedding-125m"
```

**When to modify:**
- Change environment variables
- Adjust resources (CPU/memory)
- Update image
- Change replica count

---

### v8-rbac.yaml
**Purpose:** Role-Based Access Control  
**Contains:**
- ServiceAccount
- ClusterRole (permissions)
- ClusterRoleBinding

**Permissions Granted:**
```yaml
- pods: get, list, watch
- pods/log: get, list
- events: get, list
- namespaces: get, list
```

**When to modify:**
- Add new permissions
- Restrict access
- Change service account

---

### v7-configmap.yaml
**Purpose:** Template for ConfigMap (reference only)  
**Note:** Not used in deployment. Code is mounted via `oc create configmap --from-file`.

---

### v8-nvidia-configmap.yaml
**Purpose:** Alternative ConfigMap template  
**Note:** Reference only

---

## 🗂️ Special Directories

### nvidia-reference/
**Purpose:** NVIDIA's original implementation  
**Contains:** Reference code from NVIDIA's blog

**Files:**
- `multiagent.py` - Their hybrid retriever
- `graphnodes.py` - Their agent nodes
- `prompt.json` - Their prompts

**When to reference:**
- Compare approaches
- Understand original design
- Find implementation ideas

---

### nvidia-reranker/
**Purpose:** BGE reranker deployment files  
**Contains:** KServe/ModelMesh configs for reranker

**When to use:**
- Deploy BGE reranker yourself
- Customize reranker setup

---

## 🎯 Quick Reference: "I need to..."

### Change chunk size
→ Edit `k8s_hybrid_retriever.py`, line ~128  
→ Change `chunk_size=1000` to your value

### Modify agent prompts
→ Edit `v7_graph_nodes.py`  
→ Find the agent method (retrieve, grade, generate, etc.)  
→ Update prompt strings

### Add new environment variable
→ Edit `v7-deployment.yaml`  
→ Add to `env:` section  
→ Redeploy: `oc apply -f v7-deployment.yaml`

### Change LLM model
→ Edit `v7-deployment.yaml`  
→ Change `LLAMA_STACK_MODEL` value  
→ Restart pod

### Update code
→ Edit Python files  
→ Run: `oc create configmap ... --dry-run=client -o yaml | oc apply -f -`  
→ Restart: `oc rollout restart deployment/smart-logging`

### Debug agents
→ Check logs: `oc logs deployment/smart-logging`  
→ Look for: "NODE 1", "NODE 2", etc.  
→ Check: "Retrieved X documents", "Filtered to Y documents"

### Fix detection issues
→ Read `CRITICAL_FIXES_APPLIED.md` first  
→ Check chunk size (should be 1000)  
→ Verify full document grading (no [:500])  
→ Confirm inclusive philosophy in prompts

---

## 📊 File Dependency Map

```
Deployment:
v7-deployment.yaml
    ↓
v8_streamlit_chat_app.py (UI)
    ↓
v7_main_graph.py (Orchestrator)
    ↓
v7_graph_nodes.py (5 Agents)
    ├── k8s_hybrid_retriever.py (Agent 1)
    │   └── k8s_log_fetcher.py
    ├── v7_bge_reranker.py (Agent 2)
    └── Llama Stack (Agents 3, 4, 5)

Routing:
v7_graph_edges.py
    └── v7_state_schema.py
```

---

## 🔄 Version History

**v8 (Current):**
- Hybrid retrieval (BM25 + FAISS)
- BGE reranker integration
- 3 critical fixes applied
- 100% detection rate

**v7:**
- Multi-agent workflow
- Milvus-based retrieval
- Self-correction loops

**v6:**
- Single-pass RAG
- Vector-only retrieval

---

## 📚 Related Documentation

- **README.md** - Start here
- **ARCHITECTURE.md** - How it works
- **CRITICAL_FIXES_APPLIED.md** - Technical fixes

---

**Last Updated:** October 17, 2025


