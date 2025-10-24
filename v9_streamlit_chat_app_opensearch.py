#!/usr/bin/env python3
"""
AI Troubleshooter v9 - OpenSearch Multi-Component Analysis
Multi-Agent RAG with OpenSearch for analyzing logs from multiple infrastructure components
"""

import streamlit as st
import subprocess
import json
import os
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import sys

# Add v9 modules to path
sys.path.insert(0, os.path.dirname(__file__))

# Import v9 multi-agent components
try:
    from v9_main_graph import create_workflow, run_analysis
    from v9_state_schema import GraphState
    from langgraph.checkpoint.memory import MemorySaver
    from llama_stack_client import LlamaStackClient
    from v9_opensearch_fetcher import OpenSearchLogFetcher, create_opensearch_fetcher
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.error("Make sure all v9 modules are present and OpenSearch fetcher is available.")
    st.stop()

# Configuration
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321")
LLAMA_STACK_MODEL = os.getenv("LLAMA_STACK_MODEL", "llama-32-3b-instruct")
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "openshift-logs-v9")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
BGE_RERANKER_URL = os.getenv("BGE_RERANKER_URL", "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com")

# Input Parser Functions
def extract_namespace_pod_from_message(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract namespace and pod name from user message
    
    Patterns supported:
    - "check pod mysql-456 in production"
    - "what's wrong with app-123 in default namespace"
    - "analyze nginx-pod"
    - "pod abc in ns xyz"
    
    Args:
        message: User's chat message
        
    Returns:
        Tuple of (namespace, pod_name) - either can be None if not found
    """
    message_lower = message.lower()
    
    # Extract namespace
    namespace = None
    namespace_patterns = [
        r'in\s+(\w+)[\s-]*(?:namespace|ns)',  # "in production namespace"
        r'namespace[:\s]+(\w+)',                # "namespace: production"
        r'ns[:\s]+(\w+)',                       # "ns: production"
        r'in\s+(\w+)(?:\s+(?:check|analyze|show))',  # "in production check"
    ]
    
    for pattern in namespace_patterns:
        match = re.search(pattern, message_lower)
        if match:
            namespace = match.group(1)
            break
    
    # Extract pod name
    pod = None
    pod_patterns = [
        r'pod[:\s]+([a-z0-9][-a-z0-9]*)',      # "pod: mysql-456"
        r'pod\s+([a-z0-9][-a-z0-9]*)',         # "pod mysql-456"
        r'check\s+([a-z0-9][-a-z0-9]*)',       # "check mysql-456"
        r'analyze\s+([a-z0-9][-a-z0-9]*)',     # "analyze mysql-456"
        r'(?:what.*?with|wrong.*?with)\s+([a-z0-9][-a-z0-9]*)',  # "what's wrong with mysql-456"
    ]
    
    for pattern in pod_patterns:
        match = re.search(pattern, message_lower)
        if match:
            pod_candidate = match.group(1)
            # Validate it's a reasonable pod name (not a common word)
            if len(pod_candidate) > 3 and '-' in pod_candidate or any(c.isdigit() for c in pod_candidate):
                pod = pod_candidate
                break
    
    return namespace, pod

# Kubernetes Data Collector
class KubernetesDataCollector:
    """Collects data from OpenShift/Kubernetes cluster"""
    
    def __init__(self):
        self.use_mcp = False  # Use oc commands
        self.data_source = "oc commands"
        
    def get_namespaces(self):
        try:
            result = subprocess.run(['oc', 'get', 'namespaces', '--no-headers'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return [line.split()[0] for line in result.stdout.strip().split('\n') if line.strip()]
        except:
            pass
        return ["default"]
    
    def get_pods_in_namespace(self, namespace: str):
        try:
            result = subprocess.run(['oc', 'get', 'pods', '-n', namespace, '--no-headers'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                pods = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if parts:
                            pods.append(parts[0])
                return pods
        except:
            pass
        return []
    
    def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 100):
        try:
            result = subprocess.run(['oc', 'logs', pod_name, '-n', namespace, f'--tail={tail_lines}'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_events(self, namespace: str):
        """Get ALL events from namespace (use for namespace-wide analysis)"""
        try:
            result = subprocess.run(['oc', 'get', 'events', '-n', namespace, '--sort-by=.lastTimestamp'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_events(self, pod_name: str, namespace: str):
        """Get events ONLY for specific pod (CRITICAL for single-pod analysis)"""
        try:
            result = subprocess.run([
                'oc', 'get', 'events', '-n', namespace,
                f'--field-selector=involvedObject.name={pod_name}',
                '--sort-by=.lastTimestamp'
            ], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_info(self, pod_name: str, namespace: str):
        try:
            result = subprocess.run(['oc', 'get', 'pod', pod_name, '-n', namespace, '-o', 'json'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return {}
    
    def get_pod_describe(self, pod_name: str, namespace: str):
        """Get complete pod description (CRITICAL for full context)"""
        try:
            result = subprocess.run(['oc', 'describe', 'pod', pod_name, '-n', namespace], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_status(self, pod_name: str, namespace: str):
        """Get quick pod status"""
        try:
            result = subprocess.run(['oc', 'get', 'pod', pod_name, '-n', namespace, '--no-headers'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    return {"name": parts[0], "ready": parts[1], "status": parts[2]}
        except:
            pass
        return {}

# Initialize components
if 'k8s_collector' not in st.session_state:
    st.session_state.k8s_collector = KubernetesDataCollector()

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Initialize context
if 'current_namespace' not in st.session_state:
    st.session_state.current_namespace = None
if 'current_pod' not in st.session_state:
    st.session_state.current_pod = None
if 'current_context' not in st.session_state:
    st.session_state.current_context = {}

# Initialize thread management for conversation memory
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    print(f"🆔 New conversation thread: {st.session_state.thread_id}")

# Initialize checkpointer (in-memory) for conversation persistence
if 'checkpointer' not in st.session_state:
    st.session_state.checkpointer = MemorySaver()
    print("💾 In-memory checkpointer initialized")

# Initialize workflow with checkpointer
if 'workflow' not in st.session_state:
    st.session_state.workflow = create_workflow(
        llama_stack_url=LLAMA_STACK_URL,
        max_iterations=MAX_ITERATIONS,
        vector_db_id=VECTOR_DB_ID,
        reranker_url=BGE_RERANKER_URL,
        checkpointer=st.session_state.checkpointer
    )
    print("✅ Workflow initialized with memory")

# Initialize OpenSearch fetcher for multi-component analysis
if 'opensearch_fetcher' not in st.session_state:
    try:
        st.session_state.opensearch_fetcher = create_opensearch_fetcher()
        print("✅ OpenSearch fetcher initialized")
    except Exception as e:
        st.error(f"❌ Failed to initialize OpenSearch: {e}")
        st.error("Check OpenSearch credentials and endpoint in environment variables.")
        st.stop()

# Initialize component selection
if 'component_type' not in st.session_state:
    st.session_state.component_type = "kubernetes"
if 'current_device' not in st.session_state:
    st.session_state.current_device = None

# Page configuration
st.set_page_config(
    page_title="AI Troubleshooter v9 - Multi-Component AIOps",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with proper contrast
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6, #10b981);
        color: white !important;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid #3b82f6;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
    }
    
    .chat-header {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: bold;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .context-badge {
        background: #f0f9ff;
        color: #0c4a6e;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    
    /* User message styling - Blue background with white text */
    [data-testid="stChatMessageContent"][data-testid*="user"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) {
        background-color: #3b82f6 !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) span {
        color: white !important;
    }
    
    /* Assistant message styling - Light gray background with dark text */
    [data-testid="stChatMessageContent"][data-testid*="assistant"] {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) {
        background-color: #f1f5f9 !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        border-left: 4px solid #10b981 !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) span {
        color: #1e293b !important;
    }
    
    /* Alternative selectors for user messages */
    .stChatMessage.user {
        background-color: #3b82f6 !important;
        border-radius: 15px;
        padding: 1rem;
    }
    
    .stChatMessage.user * {
        color: white !important;
    }
    
    /* Alternative selectors for assistant messages */
    .stChatMessage.assistant {
        background-color: #f1f5f9 !important;
        border-radius: 15px;
        padding: 1rem;
        border-left: 4px solid #10b981;
    }
    
    .stChatMessage.assistant * {
        color: #1e293b !important;
    }
    
    /* Broad selector for all chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Chat message content */
    [data-testid="stChatMessageContent"] {
        padding: 0.5rem !important;
    }
    
    /* Chat input styling - Dark to match chat bubbles */
    [data-testid="stChatInput"] {
        background-color: #1e293b !important;
    }
    
    [data-testid="stChatInput"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    [data-testid="stChatInput"] textarea {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Input placeholder text */
    [data-testid="stChatInput"] input::placeholder,
    [data-testid="stChatInput"] textarea::placeholder {
        color: #94a3b8 !important;
    }
    
    /* Ensure readable text */
    .main .block-container {
        color: #1e293b;
    }
    
    /* Avatar styling for better contrast */
    [data-testid="chatAvatarIcon-user"] {
        background-color: #ef4444 !important;
    }
    
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #f97316 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🔍 AI Troubleshooter v9 - Multi-Component AIOps</h1>
    <p>Analyze logs from Storage, Servers, Databases, Kubernetes & Firewalls | Multi-Agent RAG with OpenSearch</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔧 Configuration")
    
    # Data source info
    st.info(f"📊 **Data Source**: OpenSearch")
    st.info(f"🤖 **AI Model**: {LLAMA_STACK_MODEL}")
    st.info(f"🎯 **BGE Reranker**: Enabled")
    
    st.markdown("---")
    st.markdown("## 📍 Component Selection")
    
    # Component type selection
    component_types = {
        "kubernetes": "☸️ Kubernetes/OpenShift",
        "storage": "💾 Storage Devices",
        "server": "🖥️ Application Servers",
        "database": "🗄️ Database Servers",
        "firewall": "🔥 Firewalls"
    }
    
    selected_component = st.selectbox(
        "Component Type:",
        options=list(component_types.keys()),
        format_func=lambda x: component_types[x],
        index=list(component_types.keys()).index(st.session_state.component_type),
        key="component_selector"
    )
    
    # Update component type
    if selected_component != st.session_state.component_type:
        st.session_state.component_type = selected_component
        st.session_state.current_device = None
        st.session_state.current_namespace = None
        st.session_state.current_pod = None
    
    # Component-specific selection
    if selected_component == "kubernetes":
        # Get namespaces from OpenSearch
        st.markdown("#### Kubernetes Context")
        
        # Fetch real OpenShift namespaces from openshift-logs index
        try:
            namespaces = st.session_state.opensearch_fetcher.get_namespace_list()
            if not namespaces:
                namespaces = ["default", "kube-system"]
                st.warning("⚠️  Could not fetch namespaces from OpenSearch. Using defaults.")
        except Exception as e:
            st.error(f"Error fetching namespaces: {e}")
            namespaces = ["default", "kube-system"]
        
        selected_namespace = st.selectbox(
            "📁 Namespace:",
            options=namespaces,
            index=0,
            key="namespace_selector"
        )
        st.session_state.current_namespace = selected_namespace
        
        # Pod selection dropdown - fetch pods for selected namespace
        try:
            pods = st.session_state.opensearch_fetcher.get_pod_list(selected_namespace)
            if pods:
                pod_options = ["All Pods"] + pods
                selected_pod = st.selectbox(
                    "🐳 Pod (optional):",
                    options=pod_options,
                    key="pod_selector"
                )
                if selected_pod != "All Pods":
                    st.session_state.current_pod = selected_pod
                else:
                    st.session_state.current_pod = None
            else:
                st.warning(f"⚠️  No pods found in namespace '{selected_namespace}'")
                st.session_state.current_pod = None
        except Exception as e:
            st.error(f"Error loading pods: {e}")
            st.session_state.current_pod = None
            
    else:
        # For other components, allow device selection
        st.markdown(f"#### {component_types[selected_component]} Selection")
        
        # Get devices from OpenSearch
        try:
            devices = st.session_state.opensearch_fetcher.get_device_list(selected_component)
            if devices:
                device_options = ["All Devices"] + devices
                selected_device = st.selectbox(
                    "Device/Host:",
                    options=device_options,
                    key="device_selector"
                )
                if selected_device != "All Devices":
                    st.session_state.current_device = selected_device
                else:
                    st.session_state.current_device = None
            else:
                st.warning(f"No {selected_component} devices found in OpenSearch")
                device_name = st.text_input("Device Name:", key="device_input")
                st.session_state.current_device = device_name if device_name else None
        except Exception as e:
            st.error(f"Error loading devices: {e}")
            device_name = st.text_input("Device Name:", key="device_input_error")
            st.session_state.current_device = device_name if device_name else None
    
    st.markdown("---")
    st.markdown("## 🎛️ Options")
    
    time_range = st.selectbox(
        "⏱️ Time Range:",
        options=["1h", "6h", "12h", "24h", "7d"],
        index=3,  # Default to 24h
        key="time_range"
    )
    
    level_filter = st.multiselect(
        "🎚️ Log Levels:",
        options=["CRITICAL", "ERROR", "WARNING", "INFO"],
        default=["CRITICAL", "ERROR", "WARNING", "INFO"],  # Include INFO by default
        key="level_filter"
    )
    
    max_iterations = st.slider("🔄 Max Iterations", 1, 5, MAX_ITERATIONS)
    
    st.markdown("---")
    
    # Clear chat button
    st.markdown("### 🔄 Context Management")
    st.info(f"💾 **Thread ID**: `{st.session_state.thread_id[:8]}...`")
    st.caption("💡 **Tip**: Clear history for fresh start, or keep it for follow-up questions")
    if st.button("🗑️ Clear Chat & Start New Thread", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.success(f"✅ New thread started: {st.session_state.thread_id[:8]}...")
        st.rerun()
    
    # Quick examples
    st.markdown("### 💡 Example Questions")
    if selected_component == "kubernetes":
        st.markdown("""
        - Why is my pod failing?
        - What errors are in the logs?
        - Show me recent issues
        """)
    elif selected_component == "storage":
        st.markdown("""
        - Is NAS-02 healthy?
        - Check RAID status
        - What storage issues exist?
        """)
    elif selected_component == "database":
        st.markdown("""
        - Why are queries slow?
        - Check connection pool
        - Show database errors
        """)
    else:
        st.markdown("""
        - Find all issues
        - What's the problem?
        - Show recent errors
        """)

# Main chat interface
st.markdown("## 💬 Chat with AI Troubleshooter")

# Display current context
if st.session_state.component_type == "kubernetes" and st.session_state.current_namespace:
    context_text = f"📍 **Kubernetes**: Namespace `{st.session_state.current_namespace}`"
    if st.session_state.current_pod:
        context_text += f" → Pod `{st.session_state.current_pod}`"
    st.markdown(f'<div class="context-badge">{context_text}</div>', unsafe_allow_html=True)
elif st.session_state.component_type != "kubernetes" and st.session_state.current_device:
    component_label = {
        "database": "Database",
        "storage": "Storage", 
        "server": "Server",
        "firewall": "Firewall"
    }.get(st.session_state.component_type, st.session_state.component_type.title())
    context_text = f"📍 **{component_label}**: `{st.session_state.current_device}`"
    st.markdown(f'<div class="context-badge">{context_text}</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show metadata if present
        if "metadata" in message:
            with st.expander("📊 Analysis Details"):
                st.json(message["metadata"])

# Chat input
if prompt := st.chat_input("Ask about your pods, logs, or cluster issues..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤖 Analyzing..."):
            try:
                # Get selected component type
                component_type = st.session_state.component_type
                
                # Component-specific validation and log fetching
                if component_type == "kubernetes":
                    # Kubernetes: requires namespace
                    extracted_namespace, extracted_pod = extract_namespace_pod_from_message(prompt)
                    namespace = extracted_namespace or st.session_state.current_namespace
                    pod_name = extracted_pod or st.session_state.current_pod
                    
                    if not namespace:
                        st.error("❌ Please select a namespace from dropdown or mention it in your message")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "❌ No namespace specified. Please select one from the sidebar."
                        })
                        st.stop()
                    
                    # Show context
                    context_info = f"📍 **Kubernetes**: Namespace `{namespace}`"
                    if pod_name:
                        context_info += f" → Pod `{pod_name}`"
                    st.info(context_info)
                    
                    # Augment query for Kubernetes
                    if pod_name:
                        augmented_query = f"{prompt} [Context: Kubernetes pod '{pod_name}' in namespace '{namespace}']"
                    else:
                        augmented_query = f"{prompt} [Context: Kubernetes namespace '{namespace}']"
                    
                    # Fetch Kubernetes logs (placeholder - would use oc commands)
                    logs = f"[Kubernetes logs for namespace {namespace}"
                    if pod_name:
                        logs += f", pod {pod_name}"
                    logs += "]"
                    events = ""
                    
                else:
                    # Other components: use device name and OpenSearch
                    device_name = st.session_state.current_device
                    
                    if not device_name:
                        st.error(f"❌ Please select a device from the dropdown")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"❌ No device selected. Please select a {component_type} device from the sidebar."
                        })
                        st.stop()
                    
                    # Show context
                    component_label = {
                        "database": "Database Server",
                        "storage": "Storage Device", 
                        "server": "Application Server",
                        "firewall": "Firewall"
                    }.get(component_type, component_type.title())
                    
                    context_info = f"📍 **{component_label}**: `{device_name}`"
                    st.info(context_info)
                    
                    # Augment query with component context
                    augmented_query = f"{prompt} [Context: {component_label} '{device_name}']"
                    
                    # Fetch logs from OpenSearch
                    namespace = None  # Not used for non-K8s components
                    pod_name = None
                    events = ""
                    
                    try:
                        # Get time range and log levels from sidebar
                        time_range = st.session_state.get('time_range', '1h')
                        level_filter = st.session_state.get('level_filter', ['CRITICAL', 'ERROR', 'WARNING'])
                        
                        st.caption(f"🔍 Fetching logs: {component_type} / {device_name} / {time_range} / {level_filter}")
                        
                        logs = st.session_state.opensearch_fetcher.fetch_logs(
                            component_type=component_type,
                            device_name=device_name,
                            time_range=time_range,
                            level_filter=level_filter
                        )
                        
                        # Debug: Show what we got
                        st.caption(f"📊 Fetched {len(logs) if logs else 0} chars of logs")
                        
                        if not logs or logs.strip() == "":
                            logs = f"No logs found for {device_name} in the last {time_range}"
                            st.warning(f"⚠️ No logs returned from OpenSearch for {device_name}")
                        else:
                            st.success(f"✅ Retrieved {len(logs)} characters of log data")
                            with st.expander("📋 Show fetched logs"):
                                st.text(logs[:1000])  # Show first 1000 chars
                            
                    except Exception as e:
                        st.error(f"❌ Error fetching logs from OpenSearch: {e}")
                        st.code(str(e))
                        logs = f"Error fetching logs for {device_name}: {str(e)}"
                
                # FIX #1: Use workflow with thread_id for conversation memory
                # Prepare initial state
                initial_state = {
                    "question": augmented_query,
                    "namespace": namespace,
                    "pod_name": pod_name or "",
                    "log_context": logs,
                    "pod_events": events,
                    "pod_status": {},
                    "retrieved_docs": [],
                    "reranked_docs": [],
                    "relevance_scores": [],
                    "generation": "",
                    "iteration": 0,
                    "max_iterations": max_iterations,
                    "transformation_history": [],
                    "timestamp": datetime.now().isoformat(),
                    "time_window": 30,
                    "data_source": "oc"
                }
                
                # Invoke workflow with thread_id for memory!
                final_state = st.session_state.workflow.invoke(
                    initial_state,
                    config={
                        "configurable": {
                            "thread_id": st.session_state.thread_id
                        }
                    }
                )
                
                # Extract result
                result = {
                    "success": True,
                    "answer": final_state.get("generation", ""),
                    "iterations": final_state.get("iteration", 0),
                    "relevant_docs": final_state.get("reranked_docs", []),
                    "metadata": {
                        "namespace": namespace,
                        "pod_name": pod_name or "All Pods",
                        "num_docs_retrieved": len(final_state.get("retrieved_docs", [])),
                        "num_docs_relevant": len(final_state.get("reranked_docs", [])),
                    },
                    "timestamp": final_state.get("timestamp", datetime.now().isoformat())
                }
                
                # Extract answer
                if result and "answer" in result:
                    answer = result["answer"]
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Prepare metadata
                    metadata = {
                        "namespace": namespace,
                        "pod": pod_name or "All Pods",
                        "iterations": result.get("iterations", 1),
                        "docs_retrieved": result.get("metadata", {}).get("num_docs_retrieved", 0),
                        "docs_reranked": result.get("metadata", {}).get("num_docs_relevant", 0),
                        "timestamp": result.get("timestamp", datetime.now().isoformat())
                    }
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "metadata": metadata
                    })
                    
                else:
                    error_msg = "❌ Analysis failed. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
            except Exception as e:
                error_msg = f"❌ Error during analysis: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🤖 Model: {LLAMA_STACK_MODEL}")
with col2:
    st.caption(f"💬 Messages: {len(st.session_state.messages)}")
with col3:
    st.caption(f"📍 Context: {st.session_state.current_namespace or 'Not set'}")

