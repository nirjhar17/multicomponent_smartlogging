# AI Troubleshooter v10 - Multi-Component AIOps System

**Multi-agent self-corrective RAG system for analyzing logs from ANY infrastructure component**

[![Status](https://img.shields.io/badge/status-production--ready-green)]()
[![Detection Rate](https://img.shields.io/badge/detection--rate-100%25-brightgreen)]()
[![Components](https://img.shields.io/badge/components-5-blue)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)]()

> **📢 NEW: [v10 with LangSmith Integration](./ai-troubleshooter-v10/)** - Full observability, tracing, and debugging!

---

## 📚 Table of Contents

- [Versions](#-versions)
- [Overview](#-overview)
- [What's New in v10](#-whats-new-in-v10)
- [Supported Components](#-supported-components)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [OpenSearch Integration](#-opensearch-integration)
- [Technical Details](#-technical-details)
- [Repository Structure](#-repository-structure)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)

---

## 📦 Versions

| Version | Description | Status | Key Features |
|---------|-------------|--------|--------------|
| **[v10](./ai-troubleshooter-v10/)** | Production + Observability | ✅ **LATEST** | LangSmith tracing, real log fetching, full debugging |
| **v9** | Multi-Component AIOps | ✅ Stable | 5 components, OpenSearch, hybrid retrieval |
| v7/v8 | Kubernetes-only | ⚠️ Legacy | Single namespace, oc commands |

**Choose v10 if you need:**
- 📊 Complete workflow tracing and debugging
- 🔍 Real-time performance monitoring
- 🐛 Visual inspection of agent decisions
- 📈 Production-ready observability with LangSmith

**Choose v9 if you need:**
- 🚀 Stable, battle-tested multi-component system
- 📡 OpenSearch integration without external dependencies
- 🔧 Simple deployment without observability tools

---

## 🎯 Overview

AI Troubleshooter v10 extends our proven 5-agent RAG system to analyze logs from **ANY infrastructure component** - not just Kubernetes. It uses OpenSearch as a centralized log aggregation platform and applies the same intelligent analysis across databases, servers, storage devices, firewalls, and Kubernetes pods.

### Key Features

- 🌐 **Multi-Component Support** - Analyzes logs from 5+ infrastructure types
- 📊 **OpenSearch Integration** - Centralized log aggregation and retrieval
- ✅ **100% Detection Rate** - Proven accuracy from v7/v8
- 🔍 **Hybrid Retrieval** - BM25 (lexical) + FAISS (semantic) with RRF
- 🎯 **BGE Reranker v2-m3** - Advanced result refinement
- 🔄 **Self-Corrective** - Iterative query transformation (up to 3 iterations)
- 🤖 **5 Specialized Agents** - Retrieve, Rerank, Grade, Generate, Transform
- 🚀 **Fast** - 5-10 second response time per component
- 📡 **OpenShift Log Forwarding** - Real-time cluster log streaming

---

## 🆕 What's New in v10

### Expanded Beyond Kubernetes

**v7/v8**: Kubernetes-only log analysis  
**v10**: Multi-component infrastructure analysis

### New Capabilities

1. **OpenSearch Integration**
   - Centralized log aggregation
   - Multi-component log storage
   - Dynamic namespace/pod discovery

2. **Multi-Component Support**
   - Database servers (PostgreSQL, MySQL, etc.)
   - Application servers (Java, Node.js, etc.)
   - Storage devices (NAS, SAN, RAID arrays)
   - Firewalls (Security appliances, IDS/IPS)
   - Kubernetes pods (existing v7/v8 functionality)

3. **OpenShift Log Forwarding**
   - ClusterLogForwarder integration
   - EventRouter for Kubernetes events
   - Real-time log streaming to OpenSearch

4. **Component-Aware Analysis**
   - Tailored prompts per component type
   - Component-specific resolution commands
   - Cross-component issue correlation

---

## 🏭 Supported Components

| Component | Log Sources | Example Issues Detected |
|-----------|-------------|------------------------|
| **Kubernetes** | Pods, Events, Describe | ImagePullBackOff, CrashLoopBackOff, Missing ConfigMaps/Secrets |
| **Database** | PostgreSQL, MySQL, MongoDB | Deadlocks, Slow queries, Replication lag, Connection pool exhaustion |
| **Server** | Application logs, System logs | High CPU/memory, Process crashes, Network timeouts, I/O bottlenecks |
| **Storage** | NAS, SAN, RAID | RAID degradation, Disk failures, I/O latency spikes, Capacity issues |
| **Firewall** | Security logs, IDS/IPS | DDoS attacks, Port scans, Intrusion attempts, Rate limiting |

---

## 🏗️ Architecture

```
User Query → Component Selection
              ↓
    ┌─────────────────────────┐
    │  OpenSearch Log Fetcher │
    │  • Fetch by component   │
    │  • Time range filter    │
    │  • Log level filter     │
    └─────────────────────────┘
              ↓
    ┌─────────────────────────┐
    │ Agent 1: Retrieve        │
    │ • Chunk logs (1K chars) │
    │ • BM25 + FAISS (768-dim)│
    │ • Granite 125M embeddings│
    └─────────────────────────┘
              ↓
    ┌─────────────────────────┐
    │ Agent 2: Rerank          │
    │ • BGE Reranker v2-m3    │
    │ • Top-k selection       │
    └─────────────────────────┘
              ↓
    ┌─────────────────────────┐
    │ Agent 3: Grade           │
    │ • Relevance scoring     │
    │ • Inclusive philosophy  │
    └─────────────────────────┘
              ↓
    ┌─────────────────────────┐
    │ Agent 4: Generate        │
    │ • Llama 3.2 3B Instruct │
    │ • Component-aware       │
    │ • Actionable solutions  │
    └─────────────────────────┘
              ↓
    ┌─────────────────────────┐
    │ Agent 5: Transform       │
    │ • Query refinement      │
    │ • Loop back to retrieve │
    └─────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **OpenShift 4.x** or Kubernetes 1.20+
- **OpenSearch** (AWS OpenSearch Service or self-hosted)
- **Llama Stack** with:
  - LLM: `llama-32-3b-instruct`
  - Embeddings: `granite-embedding-125m` (768 dimensions)
- **BGE Reranker v2-m3** service
- `oc` CLI installed

### Deploy v10 in 5 Minutes

```bash
# 1. Create namespace
oc new-project ai-troubleshooter-v10

# 2. Create OpenSearch credentials secret
oc create secret generic opensearch-credentials \
  --from-literal=username=admin \
  --from-literal=password='YourPassword' \
  -n ai-troubleshooter-v10

# 3. Create ConfigMap with application code
oc create configmap v10-app-config \
  --from-file=k8s_hybrid_retriever.py \
  --from-file=v10_bge_reranker.py \
  --from-file=v10_graph_edges.py \
  --from-file=v10_graph_nodes.py \
  --from-file=v10_main_graph.py \
  --from-file=v10_opensearch_fetcher.py \
  --from-file=v10_state_schema.py \
  --from-file=v10_streamlit_chat_app_opensearch.py \
  --from-file=requirements.txt \
  -n ai-troubleshooter-v10

# 4. Update environment variables in v10_deployment_new.yaml
# - LLAMA_STACK_URL
# - RERANKER_URL
# - OPENSEARCH_ENDPOINT
# - OPENSEARCH_USERNAME
# - OPENSEARCH_PASSWORD

# 5. Deploy the application
oc apply -f v10_deployment_new.yaml

# 6. Get the application URL
oc get route ai-troubleshooter-v10-route -n ai-troubleshooter-v10
```

---

## ⚙️ Configuration

### Environment Variables

Edit in `v10_deployment_new.yaml`:

```yaml
env:
  # Llama Stack Configuration
  - name: LLAMA_STACK_URL
    value: "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
  - name: LLAMA_STACK_MODEL
    value: "llama-32-3b-instruct"
  - name: EMBEDDING_MODEL
    value: "granite-embedding-125m"
  - name: EMBEDDING_DIMENSION
    value: "768"
  
  # Reranker Configuration
  - name: RERANKER_URL
    value: "https://bge-reranker-model.apps.rosa.example.com/rerank"
  
  # OpenSearch Configuration
  - name: OPENSEARCH_ENDPOINT
    value: "search-your-domain.region.es.amazonaws.com"
  - name: OPENSEARCH_USERNAME
    value: "admin"
  - name: OPENSEARCH_PASSWORD
    value: "YourPassword"
  
  # Optional
  - name: VECTOR_DB_ID
    value: "k8s-logs-db"
```

### OpenSearch Index Structure

v10 expects logs in the following format:

```json
{
  "@timestamp": "2025-10-24T10:30:00Z",
  "level": "ERROR",
  "message": "Connection timeout to database",
  "component": "database",
  "host": "db-server-01",
  "device": "db-server-01"
}
```

**For Kubernetes (forwarded via ClusterLogForwarder):**
```json
{
  "@timestamp": "2025-10-24T10:30:00Z",
  "message": "Pod failed to start",
  "kubernetes": {
    "namespace_name": "production",
    "pod_name": "app-xxx",
    "container_name": "app"
  }
}
```

---

## 🧪 Usage Examples

### 1. Database Analysis

```
Component: Database Servers
Device: db-server-01
Query: What's causing the slow queries?

Response:
🚨 ISSUE: Multiple slow queries and connection pool exhaustion
📋 ROOT CAUSE: High I/O wait due to degraded RAID array on storage
⚡ IMMEDIATE ACTIONS:
  1. Check RAID status on NAS-02
  2. Optimize most frequent queries
  3. Scale connection pool
🔧 RESOLUTION:
  # Check database performance
  psql -d orders -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
  
  # Analyze slow queries
  psql -d orders -c "EXPLAIN ANALYZE SELECT * FROM orders WHERE status='pending';"
```

### 2. Storage Analysis

```
Component: Storage Devices
Device: NAS-02
Query: Why is disk latency so high?

Response:
🚨 ISSUE: RAID array degraded - Disk 3 failed
📋 ROOT CAUSE: Single disk failure in RAID-5 array
⚡ IMMEDIATE ACTIONS:
  1. Replace failed disk immediately
  2. Monitor I/O latency
  3. Check for data loss
🔧 RESOLUTION:
  # Check RAID status
  mdadm --detail /dev/md0
  
  # Replace failed disk
  mdadm --manage /dev/md0 --remove /dev/sdd
  mdadm --manage /dev/md0 --add /dev/sde
```

### 3. Kubernetes Analysis (OpenShift Logs)

```
Component: Kubernetes
Namespace: test-problematic-pods
Pod: missing-config-app-xxx
Query: Why is this pod failing?

Response:
🚨 ISSUE: Missing ConfigMap 'app-config'
📋 ROOT CAUSE: ConfigMap not found in namespace
⚡ IMMEDIATE ACTIONS:
  1. Create missing ConfigMap
  2. Verify pod configuration
🔧 RESOLUTION:
  # Create ConfigMap
  oc create configmap app-config \
    --from-literal=DATABASE_URL=postgres://... \
    -n test-problematic-pods
  
  # Restart pod
  oc delete pod missing-config-app-xxx -n test-problematic-pods
```

### 4. Cross-Component Analysis

```
Query: Why are my application servers timing out?

Response:
🚨 ISSUE: Cascading failure across infrastructure
📋 ROOT CAUSE: 
  1. RAID degradation on NAS-02 (Storage)
  2. High I/O wait on app-server-01 (Server)  
  3. Database connection timeouts (Database)
  4. Application pod crashes (Kubernetes)

⚡ IMMEDIATE ACTIONS:
  1. Replace failed disk in RAID array (Priority 1)
  2. Restart affected application servers
  3. Scale database connection pool
  4. Monitor pod recovery

🔧 RESOLUTION: Fix storage layer first, then cascade upward
```

---

## 📡 OpenSearch Integration

### Forwarding OpenShift Logs to OpenSearch

v10 includes support for real-time OpenShift log forwarding:

```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: logging
  namespace: openshift-logging
spec:
  outputs:
    - name: external-opensearch
      type: elasticsearch
      elasticsearch:
        url: https://your-opensearch-endpoint
        version: 8
        index: openshift-logs
        authentication:
          username:
            secretName: opensearch-credentials
            key: username
          password:
            secretName: opensearch-credentials
            key: password
  pipelines:
    - name: forward-to-opensearch
      inputRefs:
        - application
        - infrastructure
      outputRefs:
        - external-opensearch
```

### EventRouter for Kubernetes Events

Deploy EventRouter to capture pod lifecycle events:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eventrouter
  namespace: openshift-logging
spec:
  template:
    spec:
      serviceAccountName: eventrouter
      containers:
        - name: eventrouter
          image: registry.redhat.io/openshift-logging/eventrouter-rhel9:v0.4
          volumeMounts:
            - name: config-volume
              mountPath: /etc/eventrouter
      volumes:
        - name: config-volume
          configMap:
            name: eventrouter
```

---

## 🔧 Technical Details

### Hybrid Retrieval

- **BM25**: Lexical/keyword matching (lightweight)
- **FAISS**: Semantic similarity using 768-dim Granite 125M embeddings
- **RRF**: Reciprocal Rank Fusion for combining results

### Embedding Model

- **Model**: IBM Granite 125M (English)
- **Dimensions**: 768
- **Hosting**: Built into Llama Stack via sentence-transformers provider
- **Location**: `llamastack-custom-distribution` pod

### Chunking Strategy

- **Chunk Size**: 1,000 characters (optimized for BGE's 512 token limit)
- **Overlap**: 200 characters (20%)
- **Separators**: `\n\n`, `\n`, ` `

### Component-Specific Prompts

v10 uses tailored system prompts for each component:

- **Database**: Suggests `psql`, `mysql`, SQL optimization commands
- **Server**: Suggests `iostat`, `top`, `systemctl` commands
- **Storage**: Suggests `mdadm`, `df`, storage health checks
- **Firewall**: Suggests security analysis, rate limiting configs
- **Kubernetes**: Suggests `oc` commands, pod troubleshooting

---

## 📁 Repository Structure

```
ai-troubleshooter-v10/
├── README.md                             # This file
├── ARCHITECTURE.md                       # System design
├── CRITICAL_FIXES_APPLIED.md             # Technical fixes (v7/v8)
├── FILE_GUIDE.md                         # File reference
├── INFRASTRUCTURE.md                     # Infrastructure setup
│
├── Core Application (8 files)
│   ├── k8s_hybrid_retriever.py           # Agent 1: Hybrid Retrieval
│   ├── v10_bge_reranker.py                # Agent 2: Reranking
│   ├── v10_graph_nodes.py                 # Agents 3,4,5 implementations
│   ├── v10_graph_edges.py                 # Graph routing logic
│   ├── v10_main_graph.py                  # LangGraph workflow
│   ├── v10_opensearch_fetcher.py          # OpenSearch client
│   ├── v10_state_schema.py                # State management
│   └── v10_streamlit_chat_app_opensearch.py # Chat UI
│
├── Configuration (2 files)
│   ├── requirements.txt                  # Python dependencies (NO PyTorch!)
│   └── v10_deployment_new.yaml            # OpenShift deployment
│
└── Supporting Directories
    ├── infrastructure/                   # Deployment configs
    ├── nvidia-reference/                 # Reference materials
    └── nvidia-reranker/                  # BGE reranker setup
```

---

## 📚 Documentation

### Quick Reference

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **README.md** | Overview & Deploy | First time setup |
| **ARCHITECTURE.md** | How it works | Understanding the system |
| **FILE_GUIDE.md** | File reference | Finding specific code |
| **INFRASTRUCTURE.md** | Infrastructure setup | Deploying from scratch |
| **CRITICAL_FIXES_APPLIED.md** | v7/v8 technical fixes | Historical reference |

---

## 🔍 Troubleshooting

### Pod Not Starting

```bash
# Check pod status
oc get pods -n ai-troubleshooter-v10

# Check logs
oc logs -n ai-troubleshooter-v10 -l app=ai-troubleshooter-v10

# Common issues:
# 1. OpenSearch connection failed - check OPENSEARCH_ENDPOINT
# 2. Llama Stack unreachable - verify LLAMA_STACK_URL
# 3. BGE Reranker timeout - check RERANKER_URL
```

### No Logs in OpenSearch

```bash
# Verify ClusterLogForwarder is running
oc get clusterlogforwarder -n openshift-logging

# Check Vector collector logs
oc logs -n openshift-logging -l component=collector

# Verify OpenSearch has data
curl -u admin:password https://your-opensearch-endpoint/_cat/indices
```

### Agent Not Retrieving Documents

```bash
# Check pod logs for retrieval errors
oc logs -n ai-troubleshooter-v10 -l app=ai-troubleshooter-v10 | grep -i "retriev\|embedding"

# Verify Llama Stack is serving embeddings
oc logs -n model -l app=llamastack-custom-distribution | grep "inference/embeddings"

# Check if Granite model is loaded
oc exec -n model llamastack-pod -- ls /.llama/hub/ | grep granite
```

### Dimension Mismatch Errors

```bash
# Verify EMBEDDING_DIMENSION matches Granite model
oc get deployment ai-troubleshooter-v10 -n ai-troubleshooter-v10 \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="EMBEDDING_DIMENSION")].value}'

# Should output: 768 (Granite 125M uses 768 dimensions, NOT 384)
```

---

## 🎓 Inspiration

Based on [NVIDIA's Multi-Agent Log Analysis](https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/) architecture, adapted and extended for:

### v7/v8 Adaptations (Kubernetes-only)
- NVIDIA NV-EmbedQA-1B → Granite 125M
- NVIDIA Nemotron 49B → Llama 3.2 3B
- NVIDIA NV-RerankQA-1B → BGE Reranker v2-m3
- Generic logs → OpenShift-specific

### v10 Extensions (Multi-Component)
- Kubernetes-only → Multi-component infrastructure
- `oc` commands → OpenSearch queries
- Single namespace → Multiple component types
- Pod-focused → Infrastructure-wide analysis

---


## 🔗 Links

- **OpenShift Logging v6**: https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html/logging/cluster-logging-deploying

---

**Built with ❤️ for Multi-Component AIOps**

*From Kubernetes troubleshooting to full infrastructure observability*
