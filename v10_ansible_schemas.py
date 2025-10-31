"""
Pydantic v2 Schemas for Ansible-Compatible Structured Output
Matches the metrics AIOps project format for unified automation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class LogAlert(BaseModel):
    """
    Log-based alert matching metrics alert structure
    """
    labels: Dict[str, str] = Field(
        description="Alert metadata: alertname, instance, namespace, pod_name, severity"
    )
    annotations: Dict[str, str] = Field(
        description="Human-readable summary and description"
    )
    startsAt: str = Field(
        description="When issue started (ISO format)"
    )
    endsAt: str = Field(
        default="0001-01-01T00:00:00Z",
        description="When issue ended (default: still ongoing)"
    )
    generatorURL: str = Field(
        description="Link to OpenSearch/logs"
    )


class LogAlertPayload(BaseModel):
    """
    Payload matching metrics project alert structure
    """
    alerts: List[LogAlert]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    groupKey: str
    receiver: str = "Ansible"
    status: str = "firing"
    version: str = "4"


class AlertMeta(BaseModel):
    """
    Metadata for the alert
    """
    endpoint: str = "alerts"
    received_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    source: Dict[str, str] = Field(
        default_factory=lambda: {
            "name": "ai-troubleshooter-v10",
            "type": "log_analysis",
            "uuid": ""
        }
    )


class AnsibleRemediationOutput(BaseModel):
    """
    Complete output matching the metrics AIOps format.
    This allows both logging and metrics solutions to feed into same Ansible automation.
    """
    meta: AlertMeta
    payload: LogAlertPayload
    rca: str = Field(
        description="Root cause analysis"
    )
    playbook: Optional[str] = Field(
        default=None,
        description="Ansible playbook YAML (optional, EDA can generate this)"
    )
    
    def to_eda_webhook(self) -> Dict:
        """
        Format for EDA webhook (alert only, no playbook)
        """
        return {
            "meta": self.meta.model_dump(),
            "payload": self.payload.model_dump()
        }
    
    def to_display_format(self) -> Dict[str, str]:
        """
        Format for Streamlit display
        """
        return {
            "rca": self.rca,
            "playbook": self.playbook if self.playbook else "",
            "alert_name": self.payload.commonLabels.get("alertname", "LogAlert"),
            "severity": self.payload.commonLabels.get("severity", "warning"),
            "namespace": self.payload.commonLabels.get("namespace", "unknown"),
            "pod_name": self.payload.commonLabels.get("pod_name", ""),
        }

