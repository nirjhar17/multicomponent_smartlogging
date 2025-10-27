# 🐛 Bug Fixes: v9 → v10

## Summary

v10 is **NOT** just about LangSmith integration. It's also a **critical bug fix** that makes the AI actually work for Kubernetes troubleshooting.

---

## 🔴 The Problem (v9)

### Issue #1: Placeholder Data

**v9 Kubernetes log fetching:**
```python
# v9_streamlit_chat_app_opensearch.py (lines 663-689)
logs = f"[Kubernetes logs for namespace {namespace}]"  # FAKE!
events = f"[Kubernetes events for namespace {namespace}]"  # FAKE!
```

**Result**: AI never saw real data, gave generic answers.

---

### Issue #2: level_filter Bug (When Fixed in v9)

When someone tried to replace placeholders with real OpenSearch fetching in v9:

```python
# Wrong approach (blocks events):
logs = opensearch_fetcher.fetch_logs(
    component_type='kubernetes',
    namespace=namespace,
    pod_name=pod_name,
    level_filter=['CRITICAL', 'ERROR', 'WARNING']  # ❌ Blocks events!
)

# OpenSearch query:
must_clauses.append({'terms': {'level.keyword': level_filter}})
# Filters for: level IN ['CRITICAL', 'ERROR', 'WARNING']

# But EventRouter events have:
level = "warn" (lowercase!)  # ❌ Doesn't match!
level = "default"            # ❌ Doesn't match!

# Result: 0 events retrieved → AI gives generic answer
```

**Why this happened:**
- Application logs: `CRITICAL`, `ERROR`, `WARNING` (uppercase)
- EventRouter events: `warn`, `default`, `info` (lowercase + different values)
- The `level_filter` was designed for application logs, not events

---

### Issue #3: Wrong OpenSearch Fields

**v9 query (wrong):**
```python
{'term': {'namespace.keyword': namespace}}
{'term': {'pod_name.keyword': pod_name}}
```

**Actual OpenSearch schema:**
```json
{
  "kubernetes": {
    "namespace_name": "test-problematic-pods",
    "pod_name": "missing-config-app-xxx",
    "container_name": "kube-eventrouter"
  }
}
```

**Result**: 0 matches → No logs retrieved.

---

## ✅ The Solution (v10)

### Fix #1: Real OpenSearch Fetching

**v10 implementation:**
```python
# v10_streamlit_chat_app_opensearch.py
logs = st.session_state.opensearch_fetcher.fetch_logs(
    component_type='kubernetes',
    namespace=namespace,
    pod_name=pod_name,
    time_range=time_range,
    level_filter=level_filter,  # Used internally but disabled for K8s
    max_logs=1000
)
```

**Result**: Real logs + events retrieved from OpenSearch.

---

### Fix #2: Skip level_filter for Kubernetes

**v10 implementation:**
```python
# v10_opensearch_fetcher.py (lines 200-207)
# Add level filter (use .keyword for exact match)
# NOTE: For Kubernetes, we DON'T apply level filter because:
# 1. We're fetching both application logs AND events
# 2. Events have different level values (e.g., "warn", "default") 
# 3. Filtering would exclude important events like FailedMount
# This matches v9 behavior where K8s didn't use level filtering
if level_filter and component_type != 'kubernetes':
    must_clauses.append({'terms': {'level.keyword': level_filter}})
```

**Why this works:**
- Other components (database, storage, server): Still filtered by level ✅
- Kubernetes: No filtering, retrieve ALL logs + events ✅
- Matches v9's placeholder behavior (no filtering) ✅

---

### Fix #3: Correct OpenSearch Field Paths

**v10 queries:**
```python
# Application logs
{'term': {'kubernetes.namespace_name.keyword': namespace}}
{'term': {'kubernetes.pod_name.keyword': pod_name}}

# Events from EventRouter
{'term': {'kubernetes.container_name.keyword': 'kube-eventrouter'}}
{'term': {'old_event.involvedObject.name.keyword': pod_name}}
{'term': {'old_event.involvedObject.namespace.keyword': namespace}}
```

**Result**: Correct nested field access → Logs + events retrieved.

---

### Fix #4: Hybrid Query (Logs + Events)

**v10 implementation:**
```python
# v10_opensearch_fetcher.py (lines 122-154)
if component_type == 'kubernetes':
    if namespace and pod_name:
        should_clauses = [
            # Application logs from the pod itself
            {'bool': {
                'must': [
                    {'term': {'kubernetes.namespace_name.keyword': namespace}},
                    {'term': {'kubernetes.pod_name.keyword': pod_name}},
                    {'bool': {'must_not': [
                        {'term': {'kubernetes.container_name.keyword': 'kube-eventrouter'}}
                    ]}}
                ]
            }},
            # Events from EventRouter for this specific pod
            {'bool': {
                'must': [
                    {'term': {'kubernetes.container_name.keyword': 'kube-eventrouter'}},
                    {'term': {'old_event.involvedObject.name.keyword': pod_name}}
                ]
            }}
        ]
        must_clauses.append({'bool': {'should': should_clauses, 'minimum_should_match': 1}})
```

**Result**: Fetches BOTH application logs AND Kubernetes events in a single query.

---

### Fix #5: Proper Event Formatting

**v10 log formatting:**
```python
# v10_opensearch_fetcher.py (lines 251-277)
if 'old_event' in log and k8s.get('container_name') == 'kube-eventrouter':
    # This is a Kubernetes event
    event = log.get('old_event', {})
    involved_obj = event.get('involvedObject', {})
    log_line = (
        f"[{log.get('@timestamp', 'N/A')}] "
        f"EVENT | "
        f"Type: {event.get('type', 'N/A')} | "
        f"Reason: {event.get('reason', 'N/A')} | "
        f"Pod: {involved_obj.get('name', 'N/A')} | "
        f"Namespace: {involved_obj.get('namespace', 'N/A')} | "
        f"{event.get('message', '')}"
    )
else:
    # This is an application log
    log_line = (
        f"[{log.get('@timestamp', 'N/A')}] "
        f"{log.get('level', 'default')} | "
        f"Pod: {k8s.get('pod_name', 'N/A')} | "
        f"Namespace: {k8s.get('namespace_name', 'N/A')} | "
        f"{log.get('message', '')}"
    )
```

**Result**: Clear distinction between logs and events, proper context for AI.

---

## 📊 Impact

| Metric | v9 (Placeholder) | v9 (Fixed Attempt) | v10 (Final) |
|--------|------------------|-------------------|-------------|
| **Logs Retrieved** | 0 (fake) | 0 (filter bug) | 677 ✅ |
| **Events Retrieved** | 0 (fake) | 0 (filter bug) | 677 ✅ |
| **AI Detection** | Generic | Generic | Specific (FailedMount) ✅ |
| **Root Cause ID** | ❌ | ❌ | ✅ (missing ConfigMap) |

---

## 🎓 Lessons Learned

### 1. **Don't Mix Application Logs and Events in level_filter**

Events have different semantics than application logs:
- Application logs: Severity-based (`ERROR`, `WARNING`, `INFO`)
- Kubernetes events: Type-based (`Normal`, `Warning`) + Reason (`FailedMount`, `Pulling`)

Solution: Skip filtering for Kubernetes entirely.

---

### 2. **Always Check OpenSearch Schema**

Don't assume field names:
```bash
# Check actual schema:
curl -u admin:password \
  "https://opensearch-endpoint/openshift-logs/_search?size=1&pretty" \
  | jq '.hits.hits[0]._source'

# Use correct nested paths:
kubernetes.namespace_name.keyword  ✅
namespace.keyword                  ❌ (doesn't exist)
```

---

### 3. **Use Hybrid Queries for Multi-Source Data**

Kubernetes troubleshooting needs:
- Application logs (stdout/stderr from containers)
- Events (from Kubernetes API via EventRouter)

Use OpenSearch `bool` query with `should` clause to fetch both.

---

### 4. **LangSmith Helps Debug These Issues**

With LangSmith in v10:
1. See `retrieve` step → 0 documents
2. Check input query → See `level_filter`
3. Check OpenSearch response → No matches
4. Identify bug in 5 minutes

Without LangSmith in v9:
1. Add print statements
2. Redeploy
3. Test again
4. Check logs
5. Repeat... (hours of debugging)

---

## 🔗 Related Files

- **v10_opensearch_fetcher.py**: Core fix implementation
- **v10_streamlit_chat_app_opensearch.py**: Real log fetching
- **LANGSMITH_INTEGRATION.md**: Debugging with traces
- **README.md**: v10 features and setup

---

## 🚀 Upgrade Path: v9 → v10

**If you're using v9 with placeholders:**
1. Deploy v10
2. Configure OpenSearch credentials
3. Set LangSmith API key (optional but recommended)
4. Test with a failing pod

**If you tried to fix v9 yourself:**
1. Compare your `opensearch_fetcher.py` with `v10_opensearch_fetcher.py`
2. Look for `level_filter` logic
3. Check field names (nested `kubernetes.*` paths)
4. Verify event fetching logic

---

**Bottom Line**: v10 doesn't just add observability. It makes Kubernetes troubleshooting actually work. 🎯

