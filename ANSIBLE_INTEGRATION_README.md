# Ansible-Compatible Structured Output Integration

## ✅ Implementation Complete

The AI Troubleshooter v10 now generates structured output compatible with Ansible EDA automation, matching the format used by the metrics AIOps project.

---

## 🎯 What Changed

### **1. New Files Created**

#### `v10_ansible_schemas.py`
- Pydantic v2 models for structured output
- `AnsibleRemediationOutput`: Complete remediation with RCA + Playbook
- `LogAlert`, `LogAlertPayload`, `AlertMeta`: Alert metadata structures
- `to_ansible_format()`: Formats output with `BEGINRCA`/`ENDRCA` delimiters

#### `v10_eda_integration.py`
- `EDAIntegration` class for future automation
- `send_to_eda()`: Placeholder for webhook integration (shows "not configured" message)
- `save_to_files()`: Saves RCA and playbook to local files
- `validate_playbook()`: Basic YAML validation

### **2. Updated Files**

#### `requirements.txt`
- Added `pydantic>=2.0.0` for schema validation

#### `v10_state_schema.py`
- Added `ansible_output: Optional[Dict[str, Any]]` - Structured remediation object
- Added `ansible_formatted: Optional[str]` - Formatted text with delimiters

#### `v10_graph_nodes.py` (generate method)
- **Backward compatible**: Existing markdown generation unchanged
- **New**: Parallel structured output generation (wrapped in try/except)
- Only generates for Kubernetes issues (when namespace exists)
- If structured generation fails, existing markdown still works
- Returns both `generation` (markdown) and `ansible_output` (structured)

#### `v10_streamlit_chat_app_opensearch.py`
- **Backward compatible**: Existing chat display unchanged
- **New**: Displays structured output if available:
  - ✅ Success indicator
  - 🔍 Expandable "Root Cause Analysis" section
  - 📋 Expandable "Ansible Playbook" section (YAML syntax highlighting)
  - 📤 "Send to EDA" button (shows placeholder message)
  - 💾 "Save Files" button (saves to `/tmp/aiops-remediation/`)
  - 📥 "Download" button (downloads YAML file)

---

## 🚀 How to Use

### **1. Regular Usage (No Change)**
- App works exactly as before
- Users see markdown analysis in chat
- No action required

### **2. Structured Output (New Feature)**
- When analyzing Kubernetes issues, AI generates both:
  - **Markdown** (displayed in chat as before)
  - **Structured Ansible output** (displayed below)

### **3. Viewing Remediation Plans**
After AI analyzes a Kubernetes issue:
1. See the regular markdown analysis (as before)
2. Below it, see "✅ AI has generated an Ansible remediation plan!"
3. Expand "🔍 Root Cause Analysis" to read detailed RCA
4. Expand "📋 Ansible Playbook" to see YAML playbook

### **4. Actions Available**
- **📤 Send to EDA**: Currently shows "EDA webhook not configured" (future automation)
- **💾 Save Files**: Saves RCA + Playbook to `/tmp/aiops-remediation/`
- **📥 Download**: Downloads the playbook as a `.yml` file

---

## 🔧 Technical Details

### **Structured Output Format**
Matches the metrics AIOps project:

```json
{
  "meta": {
    "endpoint": "alerts",
    "received_at": "2025-10-30T12:00:00Z",
    "source": {
      "name": "ai-troubleshooter-v10",
      "type": "log_analysis",
      "uuid": "..."
    }
  },
  "payload": {
    "alerts": [{
      "labels": {
        "alertname": "ConfigMapMissing",
        "namespace": "test-problematic-pods",
        "pod_name": "missing-config-app",
        "severity": "critical"
      },
      "annotations": {
        "summary": "ConfigMapMissing in test-problematic-pods",
        "description": "Pod is stuck in ContainerCreating"
      },
      "startsAt": "2025-10-30T12:00:00Z"
    }],
    "commonLabels": {...},
    "status": "firing"
  },
  "rca": "Root cause analysis text...",
  "playbook": "---\n- hosts: localhost\n  tasks:\n    - name: Check..."
}
```

### **Playbook Requirements**
- **Kubernetes only**: Uses `kubernetes.core.k8s` or `command` modules
- **Tasks included**: Check status → Diagnose → Fix → Validate
- **No sudo**: No `become: yes` for oc/kubectl commands
- **Error handling**: `ignore_errors: yes` for diagnostic tasks

### **Safety Features**
✅ **Non-breaking**: If structured generation fails, markdown still works
✅ **Namespace check**: Only generates for Kubernetes issues
✅ **Error isolation**: Try/except wraps all new code
✅ **Backward compatible**: Existing app behavior unchanged

---

## 🔌 Future EDA Integration

To enable automatic remediation:

### **1. Deploy Ansible EDA**
Set up Ansible EDA webhook receiver

### **2. Configure Webhook URL**
Add environment variable to deployment:
```yaml
env:
  - name: EDA_WEBHOOK_URL
    value: "http://eda-server:5000/alerts"
```

### **3. Update EDA Integration**
Uncomment webhook code in `v10_eda_integration.py`:
```python
import requests
response = requests.post(
    self.eda_webhook_url,
    json={"meta": remediation.meta.dict(), "payload": remediation.payload.dict()},
    headers={"Content-Type": "application/json"},
    timeout=10
)
```

### **4. Test**
Click "📤 Send to EDA" button → Playbook executes automatically

---

## 📊 Output Example

```
BEGINRCA
Pod is stuck in ContainerCreating state because:
1. Missing ConfigMap 'app-config'
2. Volume mount waiting for ConfigMap to exist
ENDRCA

BEGINPLAYBOOK
---
- hosts: localhost
  tasks:
    - name: Check pod status
      command: oc get pod missing-config-app -n test-problematic-pods
      register: pod_status
      ignore_errors: yes
    
    - name: Create missing ConfigMap
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: ConfigMap
          metadata:
            name: app-config
            namespace: test-problematic-pods
          data:
            config.yaml: "default config"
ENDPLAYBOOK
```

---

## ✅ Testing Checklist

- [x] Create new Pydantic schemas
- [x] Create EDA integration module
- [x] Update state schema
- [x] Update generate() agent
- [x] Update Streamlit UI
- [x] Add pydantic to requirements.txt
- [x] Verify no linter errors
- [x] Ensure backward compatibility

---

## 📝 Notes

- **Current Status**: Structured output generation implemented, EDA webhook is placeholder
- **Next Steps**: Deploy EDA webhook receiver and configure URL
- **Compatibility**: Works with existing v10 deployment (no breaking changes)
- **Kubernetes Only**: Structured output only for Kubernetes issues (not databases/servers/firewalls)

---

**Implementation Date**: October 30, 2025
**Version**: v10 with Ansible Integration




