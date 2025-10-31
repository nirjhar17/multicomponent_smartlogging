"""
AI Troubleshooter v10 - Graph Nodes
Implements each step of the multi-agent workflow
UPDATED: Supports multiple AI models (local and foundation models)
"""

import os
from typing import Dict, Any, List
from llama_stack_client import LlamaStackClient
from v10_state_schema import GraphState
from k8s_hybrid_retriever import K8sHybridRetriever  # NVIDIA-style retriever
from v10_bge_reranker import BGEReranker
from v10_model_config import ModelConfig
from v10_model_inference import UnifiedInference
import json


class Nodes:
    """
    Node implementations for the LangGraph workflow
    Each node is a specialized agent for a specific task
    """
    
    def __init__(
        self,
        model_config: ModelConfig,  # NEW: Accept model config
        llama_stack_url: str,
        vector_db_id: str = None,  # Not used in NVIDIA approach
        embedding_model: str = "granite-embedding-125m",
        reranker_url: str = None
    ):
        """
        Initialize nodes with selected AI model.
        
        Args:
            model_config: Configuration for the AI model to use for generation
            llama_stack_url: URL for Llama Stack (used for embeddings)
            vector_db_id: Not used (NVIDIA approach)
            embedding_model: Model for embeddings (always local)
            reranker_url: URL for BGE reranker
        """
        # Initialize inference client with selected model
        self.inference = UnifiedInference(model_config)
        self.model_config = model_config
        
        # Keep Llama Stack client for embeddings (always use local)
        self.llama_client = LlamaStackClient(base_url=llama_stack_url)
        self.llama_stack_url = llama_stack_url
        self.embedding_model = embedding_model
        
        # NVIDIA approach: No persistent retriever, build fresh each time
        # Retriever will be created per-query with fresh log data
        
        # Initialize BGE reranker
        self.reranker = BGEReranker(reranker_url=reranker_url)
        print(f"✅ Initialized AI Model: {model_config.display_name}")
        print(f"✅ Initialized BGE Reranker: {self.reranker.reranker_url}")
        print(f"✅ Using NVIDIA-style retrieval (FAISS, no Milvus)")
    
    def retrieve(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 1: NVIDIA-Style Hybrid Retrieval
        Builds fresh BM25 + FAISS indexes from current log context
        NO Milvus - all in-memory, ephemeral
        """
        print("\n" + "="*60)
        print("🔍 NODE 1: RETRIEVE (NVIDIA: BM25 + FAISS + RRF)")
        print("="*60)
        
        question = state["question"]
        log_context = state.get("log_context", "")
        pod_events = state.get("pod_events", "")
        
        # Combine logs and events
        combined_logs = log_context
        if pod_events:
            combined_logs = f"{log_context}\n\n=== Pod Events ===\n{pod_events}"
        
        if not combined_logs or len(combined_logs) < 50:
            print("⚠️  No log context provided, retrieval will be limited")
            return {
                "retrieved_docs": [],
                "question": question
            }
        
        print(f"📊 Log context size: {len(combined_logs)} chars")
        
        # NVIDIA APPROACH: Create fresh retriever with current logs
        # This builds BM25 + FAISS indexes automatically
        print("🏗️  Building NVIDIA-style retriever (BM25 + FAISS)...")
        try:
            retriever = K8sHybridRetriever(
                log_content=combined_logs,
                llama_stack_url=self.llama_stack_url
            )
            
            # Build enhanced query with context
            enhanced_query = self._build_enhanced_query(question, log_context, state)
            
            print(f"📝 Original Query: {question}")
            print(f"📝 Enhanced Query: {enhanced_query}")
            
            # Retrieve using NVIDIA's approach (EnsembleRetriever with RRF)
            # k=10 to ensure we get both Environment (secret) and Volumes (configmap) sections
            langchain_docs = retriever.retrieve(
                query=enhanced_query,
                k=10
            )
            
            # Convert LangChain Documents to our format
            retrieved_docs = []
            for i, doc in enumerate(langchain_docs):
                retrieved_docs.append({
                    'content': doc.page_content,
                    'score': 1.0 / (i + 1),  # Simple ranking score
                    'retrieval_method': 'nvidia_hybrid',
                    'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
                })
            
            print(f"✅ Retrieved {len(retrieved_docs)} documents using NVIDIA approach")
            
            return {
                "retrieved_docs": retrieved_docs,
                "question": question
            }
            
        except Exception as e:
            print(f"❌ NVIDIA retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "retrieved_docs": [],
                "question": question
            }
    
    def rerank(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 2: Reranking
        Reranks retrieved documents using BGE Reranker v2-m3
        """
        print("\n" + "="*60)
        print("🎯 NODE 2: RERANK (BGE Reranker v2-m3)")
        print("="*60)
        
        question = state["question"]
        retrieved_docs = state["retrieved_docs"]
        
        if not retrieved_docs:
            print("⚠️  No documents to rerank")
            return {"reranked_docs": [], "question": question}
        
        try:
            print(f"📊 Reranking {len(retrieved_docs)} documents with BGE...")
            
            # Use BGE Reranker
            reranked_docs = self.reranker.rerank_documents(
                query=question,
                documents=retrieved_docs,
                top_k=10  # Keep all retrieved docs to ensure complete context
            )
            
            # Log reranking results
            print(f"\n✅ BGE Reranked to top {len(reranked_docs)} documents:")
            for i, doc in enumerate(reranked_docs, 1):
                print(f"  {i}. Score: {doc.get('rerank_score', 0):.4f} | "
                      f"Original Rank: {doc.get('original_rank', 'N/A')} → New Rank: {doc.get('new_rank', i)}")
                print(f"     {doc['content'][:100]}...")
            
            return {
                "reranked_docs": reranked_docs,
                "question": question
            }
            
        except Exception as e:
            print(f"❌ BGE Reranking error: {e}")
            print("⚠️  Falling back to score-based ranking")
            # Fallback: just take top 5 by score
            top_docs = sorted(
                retrieved_docs,
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:5]
            return {"reranked_docs": top_docs, "question": question}
    
    def grade_documents(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 3: Grade Documents
        Scores each document for relevance to the question
        """
        print("\n" + "="*60)
        print("📊 NODE 3: GRADE DOCUMENTS")
        print("="*60)
        
        question = state["question"]
        reranked_docs = state["reranked_docs"]
        
        if not reranked_docs:
            print("⚠️  No documents to grade")
            return {
                "reranked_docs": [],
                "relevance_scores": [],
                "question": question
            }
        
        # Grade each document
        filtered_docs = []
        relevance_scores = []
        
        for i, doc in enumerate(reranked_docs):
            print(f"\n📄 Grading document {i+1}/{len(reranked_docs)}...")
            
            # Build grading prompt with NVIDIA's inclusive philosophy
            grading_prompt = f"""You are a document relevance evaluator for OpenShift troubleshooting.

CRITICAL INSTRUCTION:
⭐ Even PARTIAL relevance should be considered as 'yes' to avoid missing important context.
⭐ Configuration details (Secrets, ConfigMaps, Volumes, Environment) are RELEVANT even without explicit errors.

Question: {question}

Log Document:
{doc['content']}

EVALUATION CRITERIA:
- Contains error messages, warnings, failures → YES
- Contains resource references (Secrets, ConfigMaps, Volumes) → YES
- Contains pod status, conditions, or events → YES
- Contains environment variables or mounts → YES
- Only completely unrelated information → NO

Is this document relevant? Respond ONLY with 'yes' or 'no'.
"""
            
            try:
                # Use selected model for grading
                grade_text = self.inference.chat_completion(
                    messages=[
                        {"role": "user", "content": grading_prompt}
                    ],
                    max_tokens=100,
                    temperature=0.0
                ).lower()
                
                # Parse response
                if 'yes' in grade_text:
                    print(f"   ✅ RELEVANT")
                    filtered_docs.append(doc)
                    relevance_scores.append(1.0)
                else:
                    print(f"   ❌ NOT RELEVANT")
                    relevance_scores.append(0.0)
                    
            except Exception as e:
                print(f"   ⚠️  Grading error: {e}, assuming relevant")
                filtered_docs.append(doc)
                relevance_scores.append(0.5)
        
        print(f"\n✅ Filtered to {len(filtered_docs)}/{len(reranked_docs)} relevant documents")
        
        return {
            "reranked_docs": filtered_docs,
            "relevance_scores": relevance_scores,
            "question": question
        }
    
    def generate(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 4: Generate Answer
        Generates final answer using LLM with context
        """
        print("\n" + "="*60)
        print("🤖 NODE 4: GENERATE ANSWER")
        print("="*60)
        
        question = state["question"]
        reranked_docs = state["reranked_docs"]
        namespace = state.get("namespace", "unknown")
        pod_name = state.get("pod_name", "")
        
        if not reranked_docs:
            generation = "❌ No relevant log data found to answer the question. Please try rephrasing or check if logs are available."
            return {"generation": generation, "question": question}
        
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(reranked_docs, 1):
            context_parts.append(f"**Log Snippet {i}** (Score: {doc.get('score', 0):.3f}):\n{doc['content']}\n")
        
        context = "\n".join(context_parts)
        
        # System prompt for multi-component infrastructure troubleshooting
        system_prompt = f"""You are an expert AIOps engineer analyzing logs from various IT infrastructure components (databases, servers, storage, firewalls, Kubernetes).

⚠️ CRITICAL INSTRUCTIONS - STRICT GROUNDING RULES:

1. **ONLY use information explicitly present in the log snippets provided**
   - DO NOT invent error codes (e.g., 'E00001') that don't appear in logs
   - DO NOT assume component types (MySQL, PostgreSQL, etc.) unless explicitly mentioned
   - DO NOT reference specific technologies unless they're in the logs

2. **Component Type Awareness** (check namespace/pod_name fields):
   - If namespace is None/empty AND pod_name is None/empty → This is a DATABASE/STORAGE/SERVER/FIREWALL log
   - If namespace exists → This is a Kubernetes/OpenShift pod log
   - NEVER suggest "oc" or "kubectl" commands for non-Kubernetes components!

3. **Resolution Commands** - Component-Specific:
   - For **Kubernetes/OpenShift pods**: Use ONLY "oc" commands (NOT kubectl) WITH NAMESPACE: -n {namespace}
   - ALWAYS include -n {namespace} in ALL oc commands
   - This is an OpenShift/ROSA environment - use "oc" CLI exclusively
   - Use full resource names from the logs
   - For **Databases**: Use database admin tools (mysql, psql, etc.) or suggest contacting DBA
   - For **Storage/Servers**: Use system admin commands (systemctl, iostat, etc.) or suggest contacting system admin
   - For **Firewalls**: Use vendor-specific CLI or suggest contacting network admin
   - If unsure of component type: Provide general troubleshooting steps, not specific commands

4. **Conversation Context** (for follow-up questions):
   - If user asks "is it repeating" → they're asking if the SAME ISSUE appears multiple times in logs
   - If user asks "what about X" → reference the previous analysis
   - DO NOT transform simple questions into complex queries with invented details

5. **Health Status**:
   - If logs only show INFO/DEBUG → System is HEALTHY
   - If logs show WARNING → Minor issues, not critical
   - If logs show ERROR/CRITICAL → Actual problems exist
   - DO NOT report problems if no ERROR/CRITICAL logs exist!

🎯 **FORMATTING REQUIREMENTS** (CRITICAL):
- You MUST put each section on a SEPARATE LINE
- Add a blank line between each section for readability
- Use the exact format shown below
- For commands, use proper markdown code blocks with ```bash syntax
- DO NOT mix different resource types in one command
- If multiple resources are missing, list EACH ONE separately
- ALWAYS include namespace in commands: -n {namespace}

Provide your analysis in this EXACT format (each section on its own line):

🚨 **ISSUE**: [List ALL real issues found - if multiple resources missing, list each one]

📋 **ROOT CAUSE**: [Based on actual error evidence, explain why pod cannot start]

⚡ **IMMEDIATE ACTIONS**: [Only if real issues exist - list each action clearly]

🔧 **RESOLUTION**: [Only if real issues exist - use proper command formatting WITH namespace]

Example for missing resources in namespace '{namespace}':
🚨 **ISSUE**: Multiple missing resources:
- Missing ConfigMap: nonexistent-configmap
- Missing Secret: nonexistent-secret

📋 **ROOT CAUSE**: Pod stuck in ContainerCreating because:
1. Volume mount failing due to missing ConfigMap
2. Environment variable references missing Secret

⚡ **IMMEDIATE ACTIONS**:
1. Create the missing ConfigMap in namespace {namespace}
2. Create the missing Secret in namespace {namespace}

🔧 **RESOLUTION**:
Create the missing ConfigMap:
```bash
oc create configmap nonexistent-configmap -n {namespace} --from-literal=config.yaml="sample content"
```

Create the missing Secret:
```bash
oc create secret generic nonexistent-secret -n {namespace} --from-literal=database-url="postgresql://localhost:5432/db"
```

Maximum 300 words. BE HONEST if no issues exist! Use proper line breaks and code formatting!

═══════════════════════════════════════
📚 OC COMMAND REFERENCE (OPENSHIFT/ROSA)
═══════════════════════════════════════
⚠️ THIS IS AN OPENSHIFT ENVIRONMENT - USE "oc" NOT "kubectl"!

✅ VALID COMMANDS (use ONLY these):

📋 View Resources:
- oc get <resource> [-n <namespace>]
- oc describe <resource> <name> -n <namespace>
- oc logs <pod> [-n <namespace>] [--previous] [--tail=N]
- oc top pods [-n <namespace>]
- oc top nodes

🔧 Modify Resources:
- oc delete pod <name> -n <namespace>
- oc edit <resource> <name> -n <namespace>
- oc scale deployment <name> --replicas=N -n <namespace>

🔄 Rollout (Deployments):
- oc rollout restart deployment/<name> -n <namespace>
- oc rollout status deployment/<name> -n <namespace>
- oc rollout undo deployment/<name> -n <namespace>

🐛 Debug:
- oc exec <pod> -n <namespace> -- <command>
- oc debug pod/<pod> -n <namespace>
- oc rsh <pod> -n <namespace>

🏗️ Create:
- oc create -f <file.yaml>
- oc create configmap <name> -n <namespace> --from-literal=key=value
- oc create secret generic <name> -n <namespace> --from-literal=key=value

❌ INVALID COMMANDS (DO NOT USE):
🚫 oc restart pod (DOES NOT EXIST!)
🚫 oc restart -n (DOES NOT EXIST!)
🚫 oc reboot (DOES NOT EXIST!)
🚫 kubectl (USE "oc" INSTEAD - this is OpenShift!)

🔄 CORRECT WAYS TO RESTART:
1. Delete pod: oc delete pod <name> -n <namespace>
2. Rollout restart: oc rollout restart deployment/<name> -n <namespace>
3. Scale down/up: oc scale deployment/<name> --replicas=0/3 -n <namespace>

CRITICAL: Use ONLY commands listed above. If unsure, don't suggest commands.
═══════════════════════════════════════
"""
        
        # User prompt - component-aware
        if namespace and namespace.lower() != 'none':
            # Kubernetes component
            component_context = f"""**Component Type**: Kubernetes/OpenShift Pod
**Namespace**: {namespace}
**Pod**: {pod_name or "All pods in namespace"}"""
        else:
            # Non-Kubernetes component (Database, Storage, Server, Firewall)
            component_context = f"""**Component Type**: Infrastructure Server (NOT a Kubernetes pod)
**Note**: This is a database, storage, server, or firewall being monitored via log aggregation.
**DO NOT suggest "oc exec" or "kubectl" commands - these won't work!**"""
        
        user_prompt = f"""Analyze these infrastructure logs:

{component_context}
**Question**: {question}

**Log Evidence**:
{context}

Provide your analysis in the format specified. Remember: Only reference information explicitly present in the logs above.
"""
        
        try:
            # Generate answer using selected model
            generation = self.inference.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.0
            )
            
            # Add metadata
            generation += f"\n\n---\n**🎯 Analysis Metadata**:\n"
            generation += f"- **Model**: {self.model_config.display_name}\n"
            generation += f"- **Provider**: {self.model_config.provider}\n"
            generation += f"- **Evidence**: {len(reranked_docs)} log snippets\n"
            generation += f"- **Iteration**: {state.get('iteration', 0)}\n"
            
            print(f"✅ Generated answer ({len(generation)} chars)")
            
            # NEW: Generate structured Ansible output (parallel, non-blocking)
            ansible_output = None
            ansible_formatted = None
            
            # Only generate for Kubernetes issues (namespace exists)
            if namespace and namespace.lower() not in ['none', 'unknown', '']:
                try:
                    from v10_ansible_schemas import AnsibleRemediationOutput, AlertMeta, LogAlertPayload, LogAlert
                    import uuid
                    from datetime import datetime
                    
                    print("🔧 Generating structured Ansible output...")
                    
                    # Enhanced prompt for structured output
                    ansible_system_prompt = f"""You are an AIOps agent generating structured alerts for Kubernetes issues.

**Context:**
- Namespace: {namespace}
- Pod: {pod_name or "pod-name"}

Generate a JSON response with these fields:

1. **alert_name**: Type of issue (ConfigMapMissing, PodCrashLoop, etc.)
2. **severity**: critical, warning, or info
3. **rca**: Detailed root cause analysis explaining the issue
4. **diagnostic_commands**: Commands to diagnose (MUST include -n {namespace})

CRITICAL RULES:
- Use ONLY information from the log evidence
- Be specific and detailed in the RCA
- ALWAYS include namespace in commands: -n {namespace}
- Include full pod names when available
- Use actual resource names from the logs

Format your response as JSON:
{{
  "alert_name": "ConfigMapMissing",
  "severity": "critical",
  "rca": "Detailed root cause analysis...",
  "diagnostic_commands": "kubectl get cm nonexistent-configmap -n {namespace}; kubectl describe pod {pod_name or 'pod-name'} -n {namespace}"
}}
"""
                    
                    ansible_user_prompt = f"""Analyze and create structured alert:

**Context:**
- Namespace: {namespace}
- Pod: {pod_name or "All pods"}
- Question: {question}

**Log Evidence:**
{context}

Generate JSON with alert_name, severity, and rca fields."""

                    # Generate structured output
                    ansible_response = self.inference.chat_completion(
                        messages=[
                            {"role": "system", "content": ansible_system_prompt},
                            {"role": "user", "content": ansible_user_prompt}
                        ],
                        max_tokens=1500,
                        temperature=0.0
                    )
                    
                    # Parse JSON response
                    import json
                    import re
                    
                    # Extract JSON from markdown code blocks if present
                    json_text = ansible_response
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    
                    parsed = json.loads(json_text)
                    
                    # Build structured output
                    alert_name = parsed.get("alert_name", "KubernetesPodIssue")
                    severity = parsed.get("severity", "warning")
                    rca_text = parsed.get("rca", "Root cause analysis not available")
                    # No playbook generation - EDA will handle this
                    playbook_yaml = None
                    
                    # Create Pydantic model
                    timestamp = datetime.utcnow().isoformat() + "Z"
                    instance = f"{namespace}/{pod_name}" if pod_name else namespace
                    
                    remediation = AnsibleRemediationOutput(
                        meta=AlertMeta(
                            endpoint="alerts",
                            received_at=timestamp,
                            source={
                                "name": "ai-troubleshooter-v10",
                                "type": "log_analysis",
                                "uuid": str(uuid.uuid4())
                            }
                        ),
                        payload=LogAlertPayload(
                            alerts=[
                                LogAlert(
                                    labels={
                                        "alertname": alert_name,
                                        "instance": instance,
                                        "namespace": namespace,
                                        "pod_name": pod_name or "",
                                        "severity": severity
                                    },
                                    annotations={
                                        "summary": f"{alert_name} in {namespace}",
                                        "description": question
                                    },
                                    startsAt=timestamp,
                                    endsAt="0001-01-01T00:00:00Z",
                                    generatorURL=f"http://ai-troubleshooter-v10/logs?namespace={namespace}"
                                )
                            ],
                            commonLabels={
                                "alertname": alert_name,
                                "namespace": namespace,
                                "severity": severity
                            },
                            commonAnnotations={
                                "summary": f"{alert_name} in {namespace}"
                            },
                            externalURL="http://ai-troubleshooter-v10",
                            groupKey=f"alertname:{alert_name}",
                            receiver="Ansible",
                            status="firing",
                            version="4"
                        ),
                        rca=rca_text,
                        playbook=playbook_yaml
                    )
                    
                    # Convert to dict for state
                    ansible_output = remediation.model_dump()
                    ansible_formatted = None  # Not needed - EDA generates playbook
                    
                    print(f"✅ Generated structured alert: {alert_name}")
                    
                except Exception as ansible_error:
                    print(f"⚠️  Ansible generation failed (non-critical): {ansible_error}")
                    # Don't fail the entire generation, just skip structured output
                    ansible_output = None
                    ansible_formatted = None
            
            return {
                "generation": generation,
                "question": question,
                "ansible_output": ansible_output,
                "ansible_formatted": ansible_formatted
            }
            
        except Exception as e:
            error_msg = f"❌ Generation error: {str(e)}"
            print(error_msg)
            return {"generation": error_msg, "question": question}
    
    def transform_query(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 5: Transform Query
        Rewrites the query for better retrieval (self-correction)
        """
        print("\n" + "="*60)
        print("🔄 NODE 5: TRANSFORM QUERY (Self-Correction)")
        print("="*60)
        
        original_question = state["question"]
        iteration = state.get("iteration", 0) + 1
        log_context = state.get("log_context", "")
        
        print(f"📝 Original Question: {original_question}")
        print(f"🔁 Iteration: {iteration}")
        
        # Build transformation prompt with actual log context
        log_preview = log_context[:500] if log_context else "No logs available"
        
        transform_prompt = f"""You are helping refine a log analysis query that didn't retrieve good results.

Original Question: {original_question}

⚠️ CRITICAL GROUNDING RULES:
1. ONLY use information that appears in the log preview below
2. DO NOT invent error codes, status codes, or component names
3. DO NOT add specific technologies unless they're explicitly in the logs
4. Keep the question SIMPLE and focused on what's actually in the logs

Log Preview (first 500 chars):
{log_preview}

Based on what you see in these actual logs, rewrite the question to better match the log content.
If the logs show errors, focus on those error patterns.
If the logs are generic, keep the question generic.

Return ONLY the rewritten question, nothing else.
"""
        
        try:
            # Use selected model for query transformation
            new_question = self.inference.chat_completion(
                messages=[
                    {"role": "user", "content": transform_prompt}
                ],
                max_tokens=100,
                temperature=0.0
            ).strip()
            
            # Track transformation history
            transformation_history = state.get("transformation_history", [])
            transformation_history.append(original_question)
            
            print(f"📝 New Question: {new_question}")
            
            return {
                "question": new_question,
                "iteration": iteration,
                "transformation_history": transformation_history
            }
            
        except Exception as e:
            print(f"❌ Transformation error: {e}, keeping original question")
            return {
                "question": original_question,
                "iteration": iteration
            }
    
    def _build_enhanced_query(
        self,
        question: str,
        log_context: str,
        state: GraphState
    ) -> str:
        """
        Build enhanced query with additional context
        """
        enhanced_parts = [question]
        
        # Add pod name if available
        if state.get("pod_name"):
            enhanced_parts.append(f"pod:{state['pod_name']}")
        
        # Add namespace
        if state.get("namespace"):
            enhanced_parts.append(f"namespace:{state['namespace']}")
        
        # Extract key terms from log context (errors, statuses, resources)
        if log_context:
            # Look for common error patterns
            error_patterns = [
                'error', 'failed', 'crash', 'oom', 'timeout',
                'backoff', 'terminated', 'killed', 'unavailable'
            ]
            for pattern in error_patterns:
                if pattern in log_context.lower():
                    enhanced_parts.append(pattern)
                    break  # Only add one error pattern to avoid query bloat
            
            # Look for missing resource indicators
            resource_patterns = [
                ('secret', 'secret'),
                ('configmap', 'configmap'),
                ('environment:', 'environment'),
                ('volumes:', 'volume'),
                ('mountvolume', 'mount')
            ]
            for pattern, keyword in resource_patterns:
                if pattern in log_context.lower():
                    enhanced_parts.append(keyword)
        
        return " ".join(enhanced_parts)


# Singleton instance (will be initialized in main workflow)
_nodes_instance = None

def get_nodes_instance(
    model_config: ModelConfig,
    llama_stack_url: str = None,
    vector_db_id: str = None,
    reranker_url: str = None
) -> Nodes:
    """
    Get or create nodes instance with specified model.
    
    Args:
        model_config: Configuration for the AI model to use
        llama_stack_url: URL for Llama Stack (embeddings)
        vector_db_id: Vector database ID
        reranker_url: URL for BGE reranker
        
    Returns:
        Nodes instance configured with specified model
    """
    global _nodes_instance
    # Always create new instance to support model switching
    if llama_stack_url is None:
        llama_stack_url = os.getenv(
            "LLAMA_STACK_URL",
            "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
        )
    if vector_db_id is None:
        vector_db_id = os.getenv("VECTOR_DB_ID", "openshift-logs-v8")
    if reranker_url is None:
        reranker_url = os.getenv("BGE_RERANKER_URL", "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com")
    
    _nodes_instance = Nodes(
        model_config=model_config,
        llama_stack_url=llama_stack_url,
        vector_db_id=vector_db_id,
        reranker_url=reranker_url
    )
    return _nodes_instance

