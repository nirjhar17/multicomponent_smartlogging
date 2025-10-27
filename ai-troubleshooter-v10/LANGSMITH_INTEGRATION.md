# 📊 LangSmith Integration Guide - AI Troubleshooter v10

> **Complete guide to observability, tracing, and debugging with LangSmith**

---

## 📖 Table of Contents

1. [Why LangSmith?](#why-langsmith)
2. [Architecture](#architecture)
3. [Setup & Configuration](#setup--configuration)
4. [Code Implementation](#code-implementation)
5. [Viewing Traces](#viewing-traces)
6. [Debugging Workflows](#debugging-workflows)
7. [Performance Monitoring](#performance-monitoring)
8. [Advanced Features](#advanced-features)

---

## 🎯 Why LangSmith?

### The Problem (v9 without LangSmith)

**Scenario**: User reports "AI gave me a generic answer instead of identifying the FailedMount error"

**v9 Debugging Process:**
```bash
1. Check pod logs manually
   oc logs ai-troubleshooter-v9-xxx | grep -i error

2. Add print statements to code
   print(f"Retrieved {len(documents)} documents")
   
3. Redeploy and test again
   oc delete pod ai-troubleshooter-v9-xxx
   
4. Manually inspect each agent
   - Did retrieval work? (print logs)
   - Did reranker work? (print logs)
   - Did grading work? (print logs)
   
5. Hours of debugging... 😫
```

### The Solution (v10 with LangSmith)

**Same scenario in v10:**

```bash
1. Open LangSmith dashboard
   https://smith.langchain.com/o/default/projects/p/ai-troubleshooter-v10

2. Find the user's query (search by timestamp or metadata)

3. See ENTIRE workflow visually:
   ✅ Retrieve: 677 documents fetched
   ✅ Rerank: Top 20 selected
   ❌ Grade: 0/20 relevant (THIS IS THE PROBLEM!)
   ⚠️  Transform: Query rewritten
   
4. Click on "Grade" step → See why documents were rejected
   → Discover: level_filter blocked all events!
   
5. Fix identified in 5 minutes! ✨
```

---

## 🏗️ Architecture

### LangSmith in the Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        LangSmith Platform                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Tracing    │  │  Monitoring  │  │  Debugging   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ HTTP POST (traces)
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    v10 Streamlit Application                    │
│                                                                 │
│  User Query → [LangSmith wrapper] → LangGraph Workflow         │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │ Retrieve │ → │  Rerank  │ → │  Grade   │ → │ Generate │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│   [trace]        [trace]        [trace]        [trace]        │
└─────────────────────────────────────────────────────────────────┘
```

### What Gets Traced

**Every LangGraph Node:**
- Input state
- Output state
- Execution time
- Errors (if any)

**Metadata:**
- Namespace
- Pod name
- Component type
- Iteration count
- Thread ID

**Tags:**
- `iteration-N`
- `troubleshooting`
- `kubernetes` / `database` / etc.
- `self-correction` (if query transformed)
- `v10`

---

## 🚀 Setup & Configuration

### 1. Get LangSmith API Key

```bash
# Go to: https://smith.langchain.com/settings
# Click "API Keys" → "Create API Key"
# Copy the key (starts with lsv2_pt_...)
```

### 2. Set Environment Variables

**Option A: Local Development**
```bash
export LANGSMITH_API_KEY="lsv2_pt_YOUR_KEY_HERE"
export LANGSMITH_PROJECT="ai-troubleshooter-v10"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
```

**Option B: OpenShift Deployment**
```yaml
# In deployment-v10.yaml
env:
  - name: LANGSMITH_API_KEY
    value: "lsv2_pt_YOUR_KEY_HERE"
  - name: LANGSMITH_PROJECT
    value: "ai-troubleshooter-v10"
  - name: LANGCHAIN_TRACING_V2
    value: "true"
  - name: LANGCHAIN_ENDPOINT
    value: "https://api.smith.langchain.com"
```

**Option C: Kubernetes Secret (Production)**
```bash
# Create secret
oc create secret generic langsmith-credentials \
  --from-literal=api-key='lsv2_pt_YOUR_KEY_HERE' \
  -n ai-troubleshooter-v10

# Reference in deployment
env:
  - name: LANGSMITH_API_KEY
    valueFrom:
      secretKeyRef:
        name: langsmith-credentials
        key: api-key
```

### 3. Verify Setup

```bash
# Test connection
python -c "
from langsmith import Client
client = Client(api_key='lsv2_pt_YOUR_KEY')
print('✅ LangSmith connection successful!')
print(f'Projects: {[p.name for p in client.list_projects()]}')
"
```

---

## 💻 Code Implementation

### File 1: `v10_langsmith_config.py`

```python
"""LangSmith configuration and utility functions"""
import os
from typing import Optional, Dict, Any, List
from langsmith import Client

def setup_langsmith() -> Optional[Client]:
    """
    Initializes LangSmith client and configures environment variables
    
    Returns:
        Client if API key is set, None otherwise
    """
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("⚠️  LangSmith API key not set. Tracing disabled.")
        return None
    
    # Configure LangChain tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    # Set project name
    project = os.getenv("LANGSMITH_PROJECT", "ai-troubleshooter-v10")
    os.environ["LANGCHAIN_PROJECT"] = project
    
    try:
        client = Client(api_key=api_key)
        print(f"✅ LangSmith initialized: Project '{project}'")
        return client
    except Exception as e:
        print(f"❌ LangSmith initialization failed: {e}")
        return None

def create_run_metadata(
    namespace: str,
    pod_name: str,
    question: str,
    component_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Creates metadata dictionary for LangSmith run
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name being analyzed
        question: User's query
        component_type: Component type (kubernetes, database, etc.)
        **kwargs: Additional metadata fields
    
    Returns:
        Metadata dictionary
    """
    metadata = {
        "namespace": namespace,
        "pod_name": pod_name,
        "question": question,
        "component_type": component_type,
        **kwargs
    }
    return metadata

def get_langsmith_tags(iteration: int = 0) -> List[str]:
    """
    Generates tags for LangSmith run
    
    Args:
        iteration: Current iteration number (0 = first attempt)
    
    Returns:
        List of tags
    """
    tags = [
        f"iteration-{iteration}",
        "troubleshooting",
        "v10"
    ]
    
    if iteration > 0:
        tags.append("self-correction")
    
    return tags
```

### File 2: `v10_streamlit_chat_app_opensearch.py` (Key Changes)

```python
# Add imports
from v10_langsmith_config import (
    setup_langsmith, 
    create_run_metadata, 
    get_langsmith_tags
)

# Initialize LangSmith on startup
if 'langsmith_client' not in st.session_state:
    st.session_state.langsmith_client = setup_langsmith()

# In UI, show LangSmith status
if st.session_state.langsmith_client:
    st.success("📈 **LangSmith**: Tracing Active")
    project = os.getenv("LANGSMITH_PROJECT", "ai-troubleshooter-v10")
    st.markdown(
        f"🔗 [View Traces](https://smith.langchain.com/o/default/projects/p/{project})"
    )
else:
    st.info("📈 **LangSmith**: Not configured (tracing disabled)")

# When invoking workflow, pass metadata and tags
final_state = workflow.invoke(
    initial_state,
    config={
        "configurable": {
            "thread_id": st.session_state.thread_id
        },
        "metadata": create_run_metadata(
            namespace=namespace,
            pod_name=pod_name,
            question=prompt,  # User's query
            component_type=component_type
        ),
        "tags": get_langsmith_tags(iteration=0)
    }
)
```

### How It Works

1. **`setup_langsmith()`**: Called once on app startup, configures environment
2. **`create_run_metadata()`**: Called for each user query, attaches context
3. **`get_langsmith_tags()`**: Called for each query, adds searchable tags
4. **LangGraph auto-traces**: Every node execution is automatically captured

---

## 🔍 Viewing Traces

### Access Dashboard

1. Go to: https://smith.langchain.com
2. Sign in with your account
3. Navigate to: **Projects** → `ai-troubleshooter-v10`

### Trace List View

```
┌────────────────────────────────────────────────────────────────┐
│ ai-troubleshooter-v10                           [Filter] [▼]   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ ✅ "why we have errors"                         6.58s  Oct 27  │
│    kubernetes | test-problematic-pods | missing-config-app     │
│                                                                │
│ ✅ "database connection timeout"                4.23s  Oct 27  │
│    database | production | postgres-0                          │
│                                                                │
│ ❌ "storage full?"                              2.11s  Oct 27  │
│    storage | storage-cluster | nas-02                          │
│    Error: ConnectionTimeout                                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Detailed Trace View

Click on a trace to see:

```
┌────────────────────────────────────────────────────────────────┐
│ Run: "why we have errors" (6.58s total)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ 📊 Metadata:                                                   │
│    namespace: test-problematic-pods                            │
│    pod_name: missing-config-app-7b8598699b-gjjj2               │
│    component_type: kubernetes                                  │
│    thread_id: 8e3d04d4-fe8b-446b-9510-a07863e8942c             │
│                                                                │
│ 🏷️  Tags: iteration-0, troubleshooting, kubernetes, v10        │
│                                                                │
│ 🔄 Workflow Steps:                                             │
│                                                                │
│  1. ▶ retrieve (0.13s) ✅                                       │
│     └─ Retrieved 677 documents from OpenSearch                 │
│                                                                │
│  2. ▶ rerank (0.05s) ✅                                         │
│     └─ Reranked to top 20 documents (BGE scores: 0.89-0.65)    │
│                                                                │
│  3. ▶ grade_documents (0.19s) ✅                                │
│     └─ 18/20 documents relevant (90%)                          │
│                                                                │
│  4. ▶ generate (6.19s) ✅                                       │
│     └─ Generated answer (156 tokens)                           │
│        "FailedMount: configmap 'nonexistent-configmap'..."     │
│                                                                │
│  5. ▶ decide_to_finish (0.02s) ✅                               │
│     └─ Answer quality: sufficient → END                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Inspecting a Step

Click on `grade_documents` to see:

```json
{
  "input": {
    "question": "why we have errors",
    "documents": [
      {
        "page_content": "[2025-10-25T14:23:45Z] EVENT | Type: Warning | Reason: FailedMount...",
        "metadata": {"timestamp": "2025-10-25T14:23:45Z"}
      },
      // ... 19 more documents
    ]
  },
  "output": {
    "filtered_documents": [
      // 18 relevant documents
    ],
    "relevance_scores": [0.95, 0.92, 0.89, ...]
  },
  "latency_ms": 190,
  "tokens": {
    "prompt": 3456,
    "completion": 234
  }
}
```

---

## 🐛 Debugging Workflows

### Common Debugging Scenarios

#### 1. No Documents Retrieved

**Symptom**: AI says "I don't have enough information"

**LangSmith Investigation:**
```
1. Open trace → Click "retrieve" step
2. See: "Retrieved: 0 documents"
3. Check input:
   - Query: "why pod failing"
   - Component: kubernetes
   - Namespace: test-problematic-pods
   - Pod: missing-config-app-xxx
4. Check OpenSearch connection status
5. Verify index exists: openshift-logs
```

**Root Cause**: OpenSearch index was empty (ClusterLogForwarder not running)

---

#### 2. Low Relevance Scores

**Symptom**: AI gives generic answer despite having logs

**LangSmith Investigation:**
```
1. Open trace → Click "grade_documents" step
2. See: "Relevant: 0/20 (0%)"
3. Check document content:
   - All documents have level="warn" (lowercase)
4. Check query filters:
   - level_filter=['CRITICAL', 'ERROR', 'WARNING'] (uppercase)
5. Discover: Case mismatch!
```

**Root Cause**: level_filter blocking all events

---

#### 3. Self-Correction Loop

**Symptom**: Query takes 20+ seconds, multiple iterations

**LangSmith Investigation:**
```
1. Open trace → See multiple "transform_query" steps
2. Iteration 0: "why errors" → 0 relevant docs
   ├─ transform_query: "What are the Kubernetes events for pod X?"
3. Iteration 1: Transformed query → 5 relevant docs
   ├─ grade_documents: 2/5 relevant (40%)
   ├─ transform_query: "Show FailedMount events for pod X"
4. Iteration 2: Transformed query → 18 relevant docs
   ├─ grade_documents: 18/18 relevant (100%)
   └─ generate: Answer produced ✅
```

**Root Cause**: Original query was too vague, self-correction worked correctly

---

#### 4. Generation Hallucination

**Symptom**: AI mentions errors that don't exist in logs

**LangSmith Investigation:**
```
1. Open trace → Click "generate" step
2. See input documents (context provided to LLM)
3. See output answer
4. Compare: Answer mentions "OOMKilled" but no docs mention it
5. Check LLM temperature: 0.7 (too high for factual tasks)
```

**Root Cause**: Temperature setting too high, causing hallucination

---

## 📊 Performance Monitoring

### Built-in Metrics

LangSmith automatically tracks:

| Metric | Description | Use Case |
|--------|-------------|----------|
| **Total Runs** | Count of troubleshooting queries | Usage tracking |
| **Success Rate** | % of queries that produced answers | Quality monitoring |
| **P50/P95/P99 Latency** | Response time percentiles | Performance SLO |
| **Token Usage** | Prompt + completion tokens | Cost management |
| **Error Rate** | % of failed runs | Reliability monitoring |
| **Retrieval Count** | Avg # documents retrieved | Tuning max_logs |
| **Relevance Rate** | % of retrieved docs that are relevant | Retrieval quality |

### Custom Dashboards

**Example 1: Component-Specific Performance**
```
Filter: metadata.component_type = "kubernetes"
Metrics: Avg latency, success rate, token usage
Result: Kubernetes queries are 2x slower than database queries
Action: Optimize Kubernetes log fetching
```

**Example 2: Self-Correction Frequency**
```
Filter: tags = "self-correction"
Metrics: Count, avg iterations
Result: 30% of queries require self-correction
Action: Improve initial prompts
```

**Example 3: Error Hotspots**
```
Filter: status = "error"
Group by: error_type
Result: 80% are "OpenSearch ConnectionTimeout"
Action: Scale up OpenSearch cluster
```

---

## 🚀 Advanced Features

### 1. A/B Testing Prompts

Test different system prompts:

```python
# Version A: Current prompt
prompt_a = "You are an expert Kubernetes troubleshooter..."

# Version B: More detailed prompt
prompt_b = "You are an expert SRE specializing in Kubernetes..."

# Tag runs
if use_prompt_b:
    tags.append("prompt-v2")
else:
    tags.append("prompt-v1")

# Compare in LangSmith:
# - Filter by tag: prompt-v1 vs prompt-v2
# - Compare: success rate, relevance scores, user feedback
```

### 2. Custom Evaluations

Define quality metrics:

```python
from langsmith import evaluate

def answer_contains_pod_name(run, example):
    """Check if answer mentions the specific pod name"""
    pod_name = run.metadata.get("pod_name")
    answer = run.outputs.get("answer", "")
    return pod_name in answer

def answer_has_action_items(run, example):
    """Check if answer provides actionable steps"""
    answer = run.outputs.get("answer", "")
    action_keywords = ["run", "check", "verify", "restart", "scale"]
    return any(keyword in answer.lower() for keyword in action_keywords)

# Run evaluations
results = evaluate(
    "ai-troubleshooter-v10",
    evaluators=[answer_contains_pod_name, answer_has_action_items],
    data="recent-runs"
)
```

### 3. Alert Rules

Set up alerts for:

```yaml
# Alert if error rate > 10% (1 hour window)
- name: High Error Rate
  condition: error_rate > 0.10
  window: 1h
  action: Send email to ops@company.com

# Alert if P95 latency > 30s
- name: High Latency
  condition: p95_latency > 30
  window: 15m
  action: Send Slack notification

# Alert if token usage spikes (cost control)
- name: Token Usage Spike
  condition: token_usage > 1000000
  window: 1h
  action: Throttle requests
```

### 4. Feedback Collection

Add user feedback buttons in Streamlit:

```python
# After showing answer
col1, col2 = st.columns(2)
with col1:
    if st.button("👍 Helpful"):
        langsmith_client.create_feedback(
            run_id=st.session_state.last_run_id,
            key="user-feedback",
            score=1.0,
            comment="Helpful"
        )
with col2:
    if st.button("👎 Not Helpful"):
        langsmith_client.create_feedback(
            run_id=st.session_state.last_run_id,
            key="user-feedback",
            score=0.0,
            comment="Not helpful"
        )
```

Then filter by feedback in LangSmith:
```
Feedback score < 0.5 → Investigate low-rated answers
```

---

## 📈 Best Practices

### 1. Metadata Strategy

**Always include**:
- User context (namespace, pod, component)
- Query metadata (timestamp, user_id, session_id)
- System metadata (model version, embedding version)

**Example**:
```python
metadata = {
    # User context
    "namespace": namespace,
    "pod_name": pod_name,
    "component_type": component_type,
    
    # Query metadata
    "timestamp": datetime.now().isoformat(),
    "user_id": user_id,  # If authentication enabled
    "session_id": session_id,
    
    # System metadata
    "app_version": "v10",
    "llm_model": "llama-32-3b-instruct",
    "embedding_model": "granite-125m",
    "reranker_model": "bge-reranker-v2-m3"
}
```

### 2. Tag Strategy

Use hierarchical tags:
```python
tags = [
    f"iteration-{iteration}",     # Specific
    "troubleshooting",             # Category
    component_type,                # Type
    "v10",                         # Version
    severity_level                 # Priority (if available)
]
```

### 3. Cost Management

Monitor token usage:
```python
# In LangSmith dashboard
Total tokens (last 30 days): 12,456,789
Estimated cost (GPT-4): $124.57
Estimated cost (Llama 3.2): $0 (self-hosted)

# Set budget alerts
if monthly_tokens > 10_000_000:
    send_alert("Token budget exceeded")
```

### 4. Privacy & Security

**Sensitive data handling**:
```python
def sanitize_metadata(metadata):
    """Remove sensitive fields before sending to LangSmith"""
    safe_metadata = metadata.copy()
    
    # Remove sensitive fields
    for key in ['password', 'token', 'api_key']:
        safe_metadata.pop(key, None)
    
    # Mask pod names if needed
    if 'pod_name' in safe_metadata:
        safe_metadata['pod_name_hash'] = hash(safe_metadata['pod_name'])
        del safe_metadata['pod_name']
    
    return safe_metadata
```

---

## 🔗 Resources

- **LangSmith Docs**: https://docs.smith.langchain.com/
- **LangSmith API**: https://api.smith.langchain.com/redoc
- **LangGraph Tracing**: https://langchain-ai.github.io/langgraph/how-tos/tracing/
- **Best Practices**: https://docs.smith.langchain.com/evaluation/best-practices

---

## 🎓 Conclusion

LangSmith transforms v10 from a black-box AI system into a **fully observable, debuggable, and optimizable** production application. 

**Key Takeaways**:
- ✅ Every workflow step is traced automatically
- ✅ Rich metadata enables powerful filtering and analysis
- ✅ Debugging is visual, not print-statement-based
- ✅ Performance metrics are built-in, no custom instrumentation
- ✅ A/B testing and evaluations are trivial to set up

**Production Readiness**:
- 🚀 Deploy with confidence knowing you can debug issues quickly
- 📊 Monitor quality and performance in real-time
- 💰 Track costs and optimize token usage
- 🔒 Maintain privacy with metadata sanitization

---

**Need Help?**
- LangSmith Support: https://support.langchain.com
- GitHub Issues: https://github.com/nirjhar17/multicomponent_smartlogging/issues

