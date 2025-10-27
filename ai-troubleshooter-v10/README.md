# 🤖 AI Troubleshooter v10 - Multi-Agent RAG with LangSmith Observability

> **Production-Ready Multi-Component AIOps System with Full Observability**

v10 builds on v9's multi-component architecture and adds **LangSmith integration** for complete workflow tracing, debugging, and monitoring.

---

## 🆕 What's New in v10

### LangSmith Integration ⭐
- **Full Workflow Tracing**: See every agent execution, retrieval, reranking, and generation step
- **Metadata Tracking**: Namespace, pod name, component type, iteration count
- **Performance Metrics**: Token usage, latency, error rates per agent
- **Debugging**: Identify which agent failed, which documents were retrieved, relevance scores
- **Production Monitoring**: Track usage patterns, common queries, failure modes

### Real Kubernetes Log Fetching
- **No More Placeholders**: v10 fetches real logs and events from OpenSearch
- **EventRouter Integration**: Captures Kubernetes events (FailedMount, CrashLoopBackOff, etc.)
- **Hybrid Queries**: Combines application logs + events for complete context

### Bug Fixes from v9
- ✅ Fixed level_filter blocking Kubernetes events
- ✅ Proper nested field queries (kubernetes.namespace_name.keyword)
- ✅ Event formatting with Type, Reason, Message structure
- ✅ No filtering on Kubernetes (events have inconsistent levels)

---

## 🏗️ Architecture

```
User Query
    ↓
📥 Fetch Logs & Events (OpenSearch + EventRouter)
    ↓
🤖 Agent 1: Hybrid Retrieval (BM25 + FAISS + RRF)
    ↓
🎯 Agent 2: BGE Reranking (cross-encoder)
    ↓
✅ Agent 3: Grade Documents (LLM relevance check)
    ↓ (if relevant docs found)
💬 Agent 4: Generate Answer (LLM with context)
    ↓ (if no relevant docs OR bad answer)
🔄 Agent 5: Transform Query (rewrite & retry)
    ↓
📊 LangSmith: Trace complete workflow
```

---

## 📊 LangSmith Observability

### What LangSmith Captures

**1. Run Metadata:**
```json
{
  "namespace": "test-problematic-pods",
  "pod_name": "missing-config-app-7b8598699b-gjjj2",
  "question": "why we have errors",
  "component_type": "kubernetes",
  "thread_id": "8e3d04d4-fe8b-446b-9510-a07863e8942c"
}
```

**2. Tags:**
```python
["iteration-0", "troubleshooting", "kubernetes", "v10"]
# Self-correction runs get: ["iteration-1", "self-correction", ...]
```

**3. Workflow Steps:**
- `retrieve`: Documents fetched, query used, retrieval time
- `rerank`: Reranking scores, top-k selection
- `grade_documents`: Relevance scores per document
- `generate`: LLM response, tokens used
- `transform_query`: Rewritten query

**4. Performance Metrics:**
- Total latency per run
- Tokens consumed (prompt + completion)
- Success/failure rates
- Agent-specific timing

---

## 🚀 Quick Start

### 1. Set LangSmith API Key

```bash
export LANGSMITH_API_KEY="lsv2_pt_YOUR_KEY_HERE"
export LANGSMITH_PROJECT="ai-troubleshooter-v10"
```

Get your API key from: https://smith.langchain.com/settings

### 2. Deploy to OpenShift

```bash
# Create namespace
oc new-project ai-troubleshooter-v10

# Create OpenSearch credentials secret
oc create secret generic opensearch-credentials \
  --from-literal=username=admin \
  --from-literal=password='YOUR_PASSWORD' \
  -n ai-troubleshooter-v10

# Create configmaps
oc create configmap v10-app-config \
  --from-file=v10_opensearch_fetcher.py \
  --from-file=v10_bge_reranker.py \
  --from-file=k8s_hybrid_retriever.py \
  --from-file=v10_graph_nodes.py \
  --from-file=v10_graph_edges.py \
  --from-file=v10_main_graph.py \
  --from-file=v10_state_schema.py \
  --from-file=v10_langsmith_config.py \
  --from-file=requirements.txt \
  -n ai-troubleshooter-v10

oc create configmap v10-streamlit-app \
  --from-file=v10_streamlit_chat_app_opensearch.py \
  -n ai-troubleshooter-v10

# Deploy application
oc apply -f deployment-v10.yaml
```

### 3. Access Application

```bash
# Get route URL
oc get route ai-troubleshooter-v10 -n ai-troubleshooter-v10 \
  -o jsonpath='{.spec.host}'
```

### 4. View Traces in LangSmith

Visit: https://smith.langchain.com/o/default/projects/p/ai-troubleshooter-v10

---

## 📁 File Structure

```
ai-troubleshooter-v10/
├── README.md                                 # This file
├── LANGSMITH_INTEGRATION.md                  # Detailed LangSmith guide
│
├── Core Application (9 files)
│   ├── k8s_hybrid_retriever.py               # Agent 1: Hybrid Retrieval
│   ├── v10_bge_reranker.py                   # Agent 2: Reranking
│   ├── v10_graph_nodes.py                    # Agents 3,4,5 implementations
│   ├── v10_graph_edges.py                    # Graph routing logic
│   ├── v10_main_graph.py                     # LangGraph workflow
│   ├── v10_opensearch_fetcher.py             # OpenSearch client (REAL fetching!)
│   ├── v10_state_schema.py                   # State management
│   ├── v10_langsmith_config.py               # ⭐ LangSmith setup
│   └── v10_streamlit_chat_app_opensearch.py  # Chat UI with LangSmith
│
├── Configuration (2 files)
│   ├── requirements.txt                      # Python dependencies
│   └── deployment-v10.yaml                   # OpenShift deployment
```

---

## 🔧 Configuration

### Environment Variables

```yaml
# Required
LLAMA_STACK_URL: "http://llamastack-service.model.svc.cluster.local:8321"
OPENSEARCH_ENDPOINT: "your-opensearch-endpoint.amazonaws.com"
OPENSEARCH_USERNAME: "admin"
OPENSEARCH_PASSWORD: "your-password"

# LangSmith (NEW in v10)
LANGSMITH_API_KEY: "lsv2_pt_YOUR_KEY"
LANGSMITH_PROJECT: "ai-troubleshooter-v10"
LANGCHAIN_TRACING_V2: "true"
LANGCHAIN_ENDPOINT: "https://api.smith.langchain.com"

# Optional
BGE_RERANKER_URL: "https://bge-reranker-model.apps.your-cluster.com"
VECTOR_DB_ID: "openshift-logs-v10"
MAX_ITERATIONS: "3"
```

---

## 📖 LangSmith Integration Details

### Code Changes from v9

**1. New File: `v10_langsmith_config.py`**
```python
from langsmith import Client

def setup_langsmith() -> Optional[Client]:
    """Initializes LangSmith client"""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        return None
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = "ai-troubleshooter-v10"
    
    return Client(api_key=api_key)
```

**2. Updated: `v10_streamlit_chat_app_opensearch.py`**
```python
# Import LangSmith config
from v10_langsmith_config import setup_langsmith, create_run_metadata, get_langsmith_tags

# Initialize on startup
langsmith_client = setup_langsmith()

# Pass metadata to workflow
final_state = workflow.invoke(
    initial_state,
    config={
        "metadata": create_run_metadata(
            namespace=namespace,
            pod_name=pod_name,
            question=prompt,
            component_type=component_type
        ),
        "tags": get_langsmith_tags(iteration=0)
    }
)
```

### Viewing Traces

1. **Go to LangSmith Dashboard**: https://smith.langchain.com
2. **Select Project**: "ai-troubleshooter-v10"
3. **View Runs**: See all user queries
4. **Click a Run**: See full workflow trace
5. **Inspect Steps**:
   - `retrieve`: 10 documents fetched
   - `rerank`: Top 5 selected
   - `grade_documents`: 4/5 relevant (80%)
   - `generate`: Final answer with 234 tokens

### Filtering Traces

```python
# In LangSmith UI, filter by:
- metadata.namespace = "test-problematic-pods"
- metadata.component_type = "kubernetes"
- tags = "self-correction"
- status = "error"
```

---

## 🐛 Debugging with LangSmith

### Common Issues

**1. No Documents Retrieved**
- **LangSmith shows**: `retrieve` step returned 0 documents
- **Check**: OpenSearch connection, index exists, query syntax

**2. Low Relevance Scores**
- **LangSmith shows**: `grade_documents` all scored < 0.5
- **Check**: Query quality, embedding model alignment

**3. Self-Correction Loop**
- **LangSmith shows**: Multiple `transform_query` iterations
- **Check**: Are original logs relevant? Is question too vague?

**4. Generation Hallucination**
- **LangSmith shows**: `generate` output doesn't match documents
- **Check**: Document relevance, LLM prompt, temperature

---

## 📊 Metrics Dashboard

LangSmith automatically tracks:

| Metric | Description |
|--------|-------------|
| **Total Runs** | Number of troubleshooting queries |
| **Success Rate** | % of queries that produced answers |
| **Avg Latency** | P50, P95, P99 response times |
| **Token Usage** | Total tokens consumed (cost tracking) |
| **Error Rate** | % of failed runs |
| **Retrieval Quality** | Avg # docs retrieved, relevance scores |

Access at: https://smith.langchain.com/o/default/projects/p/ai-troubleshooter-v10/dashboard

---

## 🔍 Example Trace

**Query**: "why we have errors" (Pod: missing-config-app-7b8598699b-gjjj2)

**LangSmith Trace**:
```
1. retrieve (0.13s)
   ├─ Query: "why we have errors [Context: pod...]"
   ├─ Retrieved: 10 documents
   └─ Method: BM25 + FAISS + RRF

2. rerank (0.05s)
   ├─ Input: 10 documents
   ├─ BGE Reranker scores: [0.89, 0.84, 0.76, ...]
   └─ Output: Top 5 documents

3. grade_documents (0.19s)
   ├─ LLM grading each document
   ├─ Relevant: 5/5 (100%)
   └─ Avg relevance: 0.92

4. generate (6.19s)
   ├─ LLM: llama-32-3b-instruct
   ├─ Prompt tokens: 1234
   ├─ Completion tokens: 156
   └─ Answer: "FailedMount: configmap 'nonexistent-configmap' not found"

Total: 6.58s | Status: success | Iteration: 0
```

---

## 🆚 Comparison: v9 vs v10

| Feature | v9 | v10 |
|---------|----|----|
| **Kubernetes Logs** | Placeholder strings | ✅ Real OpenSearch fetching |
| **Events** | Not included | ✅ EventRouter integration |
| **Observability** | None | ✅ **Full LangSmith tracing** |
| **Debugging** | Print statements | ✅ **Visual workflow inspection** |
| **Monitoring** | Manual | ✅ **Automated metrics dashboard** |
| **Metadata** | None | ✅ **Namespace, pod, component tracking** |
| **Performance** | Unknown | ✅ **Per-agent timing & token usage** |
| **Level Filtering** | Broken for events | ✅ **Fixed (no filter for K8s)** |

---

## 🔗 Links

- **LangSmith Dashboard**: https://smith.langchain.com
- **LangSmith Docs**: https://docs.smith.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Original v9 Project**: https://github.com/nirjhar17/multicomponent_smartlogging

---

## 🤝 Contributing

Key improvements for v10+:

- Enhanced LangSmith metadata (user IDs, severity, resolution time)
- Custom evaluation metrics for troubleshooting quality
- Alert rules based on LangSmith metrics
- A/B testing different prompts via LangSmith
- Integration with incident management systems

---

## 📝 License

Apache 2.0

---

**Built with ❤️ for Production AIOps**

_From black-box troubleshooting to fully observable AI workflows_

