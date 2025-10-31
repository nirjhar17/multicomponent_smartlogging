"""
EDA Integration Module (Placeholder for Future Ansible EDA Integration)
Provides API contract for sending remediation plans to Ansible automation
"""

import os
import json
import yaml
from typing import Dict, Optional
from datetime import datetime
from v10_ansible_schemas import AnsibleRemediationOutput


class EDAIntegration:
    """
    Integration with Ansible EDA for unified automation.
    Currently a placeholder - webhook integration can be added later.
    """
    
    def __init__(self, eda_webhook_url: Optional[str] = None):
        """
        Initialize EDA integration.
        
        Args:
            eda_webhook_url: URL for EDA webhook (optional for now)
        """
        self.eda_webhook_url = eda_webhook_url or os.getenv("EDA_WEBHOOK_URL", "")
    
    def send_to_eda(self, remediation: AnsibleRemediationOutput) -> Dict[str, any]:
        """
        Send log alert to EDA webhook (sends alert only, no playbook).
        
        Args:
            remediation: Structured alert output
            
        Returns:
            Dict with success status and message
        """
        if not self.eda_webhook_url:
            return {
                "success": False,
                "message": "⚠️ EDA webhook not configured. Set EDA_WEBHOOK_URL environment variable.",
                "action": "Configure EDA webhook URL to enable automatic remediation"
            }
        
        # Placeholder: Future implementation would POST alert to webhook
        # EDA will generate and execute the playbook
        # import requests
        # response = requests.post(
        #     self.eda_webhook_url,
        #     json=remediation.to_eda_webhook(),  # Alert only, no playbook
        #     headers={"Content-Type": "application/json"},
        #     timeout=10
        # )
        
        return {
            "success": False,
            "message": "🚧 EDA webhook integration not yet implemented",
            "action": "This is a placeholder for future automation"
        }
    
    def save_to_files(
        self, 
        remediation: AnsibleRemediationOutput, 
        base_path: str = "/tmp/aiops-remediation"
    ) -> Dict[str, str]:
        """
        Save RCA and Playbook to files (alternative to webhook).
        Same format as metrics project for consistency.
        
        Args:
            remediation: Structured remediation output
            base_path: Directory to save files
            
        Returns:
            Dict with file paths
        """
        try:
            os.makedirs(base_path, exist_ok=True)
            
            # Generate filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_name = remediation.payload.commonLabels.get("alertname", "LogAlert")
            
            # Save alert info (complete JSON)
            alert_file = os.path.join(base_path, f"alert_{alert_name}_{timestamp}.json")
            with open(alert_file, "w") as f:
                f.write(remediation.model_dump_json(indent=2))
            
            # Save RCA (text file)
            rca_file = os.path.join(base_path, f"RCA_{alert_name}_{timestamp}.txt")
            with open(rca_file, "w") as f:
                f.write(remediation.rca)
            
            # No playbook saved - EDA generates this
            
            return {
                "success": True,
                "alert_file": alert_file,
                "rca_file": rca_file,
                "message": f"✅ Files saved to {base_path}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to save files: {str(e)}"
            }
    
    def validate_playbook(self, playbook_yaml: str) -> Dict[str, any]:
        """
        Basic YAML validation for playbook.
        
        Args:
            playbook_yaml: Playbook YAML string
            
        Returns:
            Dict with validation status
        """
        try:
            # Parse YAML
            playbook = yaml.safe_load(playbook_yaml)
            
            # Basic structure checks
            if not isinstance(playbook, list):
                return {
                    "valid": False,
                    "message": "Playbook must be a list of plays"
                }
            
            if len(playbook) == 0:
                return {
                    "valid": False,
                    "message": "Playbook is empty"
                }
            
            # Check first play has required fields
            first_play = playbook[0]
            if "hosts" not in first_play:
                return {
                    "valid": False,
                    "message": "Play must have 'hosts' field"
                }
            
            if "tasks" not in first_play:
                return {
                    "valid": False,
                    "message": "Play must have 'tasks' field"
                }
            
            return {
                "valid": True,
                "message": "✅ Playbook structure is valid",
                "num_plays": len(playbook),
                "num_tasks": len(first_play.get("tasks", []))
            }
            
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "message": f"❌ YAML parsing error: {str(e)}"
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"❌ Validation error: {str(e)}"
            }

