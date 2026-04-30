"""
Runbook Auto-Generation Module
Generates structured runbooks from RCA analysis
"""

import os
from typing import Dict, Any
from datetime import datetime
from llm.groq_client import GroqClient


class RunbookGenerator:
    """Generates runbooks from incident analysis"""
    
    def __init__(self):
        self.llm_client = GroqClient()
        self.runbooks_dir = "runbooks"
        
        # Create runbooks directory if it doesn't exist
        os.makedirs(self.runbooks_dir, exist_ok=True)
    
    def generate_runbook(self, rca_text: str, alert: Dict[str, Any]) -> str:
        """
        Generate a structured runbook from RCA analysis
        
        Args:
            rca_text: Root cause analysis text from LLM
            alert: Alert/incident data
            
        Returns:
            Path to generated runbook file
        """
        # Extract key information
        service = alert.get("service", "unknown")
        severity = alert.get("severity", "unknown")
        alert_name = alert.get("alert_name", "Unknown Alert")
        fingerprint = alert.get("fingerprint", "unknown")
        
        # Build prompt for runbook generation
        prompt = f"""Based on this incident analysis, generate a structured runbook.

INCIDENT ANALYSIS:
{rca_text}

SERVICE: {service}
SEVERITY: {severity}
ALERT: {alert_name}

Generate a runbook in this EXACT format:

## Incident Pattern: [Short descriptive name]

**Trigger:** [What alert/symptom indicates this incident]

**Root Cause:** [Technical root cause in one sentence]

**Immediate Fix (< 5 min):**
1. [First immediate action]
2. [Second immediate action]
3. [Third immediate action]

**Permanent Fix:**
1. [Long-term solution step 1]
2. [Long-term solution step 2]

**Prevention:**
- [How to prevent this in the future]
- [Monitoring/alerting improvements]

**Affected Services:**
- [Service 1]
- [Service 2]

**Escalation:** If not resolved in [X] minutes, page [Team] team.

Keep it concise and actionable. Focus on commands and specific actions."""
        
        # Generate runbook using LLM with fallback
        try:
            result = self.llm_client.call_llm_with_fallback(prompt)
            runbook_content = result["response"]
        except Exception as e:
            print(f"Error generating runbook: {e}")
            # Fallback to template
            runbook_content = self._generate_template_runbook(alert, rca_text)
        
        # Save runbook
        runbook_path = self._save_runbook(fingerprint, runbook_content, alert)
        
        return runbook_path
    
    def _generate_template_runbook(self, alert: Dict[str, Any], rca_text: str) -> str:
        """Generate a template runbook when LLM fails"""
        service = alert.get("service", "unknown")
        severity = alert.get("severity", "unknown")
        
        return f"""## Incident Pattern: {service} {severity} Issue

**Trigger:** Alert fired for {service}

**Root Cause:** {rca_text[:200]}...

**Immediate Fix (< 5 min):**
1. Check service health: `kubectl get pods -l app={service}`
2. Review recent changes: `git log --since="2 hours ago"`
3. Rollback if needed: `kubectl rollout undo deployment/{service}`

**Permanent Fix:**
1. Identify root cause from logs
2. Implement fix and test
3. Deploy with monitoring

**Prevention:**
- Add monitoring for this failure mode
- Implement automated rollback
- Add integration tests

**Affected Services:**
- {service}

**Escalation:** If not resolved in 15 minutes, page SRE team.
"""
    
    def _save_runbook(self, fingerprint: str, content: str, alert: Dict[str, Any]) -> str:
        """
        Save runbook to file
        
        If file exists (repeat incident), append recurrence section
        """
        filename = f"{self.runbooks_dir}/{fingerprint}.md"
        timestamp = datetime.now().isoformat()
        
        if os.path.exists(filename):
            # Append recurrence section
            with open(filename, 'a') as f:
                f.write(f"\n\n---\n\n## Recurrence\n\n")
                f.write(f"**Date:** {timestamp}\n\n")
                f.write(f"**Alert:** {alert.get('alert_name', 'Unknown')}\n\n")
                f.write(f"**Service:** {alert.get('service', 'unknown')}\n\n")
                f.write(f"**Severity:** {alert.get('severity', 'unknown')}\n\n")
                f.write(f"**Note:** This incident pattern has occurred before. ")
                f.write(f"Review prevention measures from original runbook.\n")
        else:
            # Create new runbook
            header = f"""# Runbook: {alert.get('alert_name', 'Incident')}

**Generated:** {timestamp}
**Service:** {alert.get('service', 'unknown')}
**Severity:** {alert.get('severity', 'unknown')}
**Fingerprint:** {fingerprint}

---

"""
            with open(filename, 'w') as f:
                f.write(header)
                f.write(content)
        
        return filename


if __name__ == "__main__":
    # Test runbook generation
    generator = RunbookGenerator()
    
    test_rca = """Root Cause Analysis:

The incident was caused by a configuration change to JWT_EXPIRY_SECONDS from 3600 to 60 seconds
in deployment v2.4.1 of the auth-svc service. This change caused authentication tokens to expire
much faster than expected, leading to cascading failures in downstream services.

Affected Services:
- auth-svc (primary)
- payment-svc (dependent)
- api-gateway (dependent)

Teams to Page:
- Payments team
- API team

Recommended Remediation:
1. Rollback JWT_EXPIRY_SECONDS to 3600
2. Deploy hotfix to auth-svc
3. Monitor token validation metrics"""
    
    test_alert = {
        "service": "auth-svc",
        "severity": "critical",
        "alert_name": "High Authentication Failure Rate",
        "fingerprint": "test_fingerprint_001"
    }
    
    runbook_path = generator.generate_runbook(test_rca, test_alert)
    print(f"Generated runbook: {runbook_path}")
    
    # Test recurrence
    runbook_path2 = generator.generate_runbook(test_rca, test_alert)
    print(f"Updated runbook with recurrence: {runbook_path2}")
