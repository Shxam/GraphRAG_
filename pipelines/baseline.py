"""
Baseline LLM Pipeline for PostMortemIQ
Processes incidents with full raw context (no graph traversal)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from llm.prompt_builder import PromptBuilder
from llm.groq_client import GroqClient


class BaselinePipeline:
    """Baseline pipeline using full raw context"""
    
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = GroqClient()
    
    def assemble_context(self, incident_id: str, incident_data: Dict[str, Any]) -> str:
        """
        Assemble realistic baseline context for an incident.
        Uses real post-mortem reports + realistic log patterns.
        Target: ~8,000-12,000 tokens (proving the comparison is honest).
        
        Args:
            incident_id: The incident identifier
            incident_data: Complete incident information
            
        Returns:
            Full context string with real content
        """
        import pathlib
        import random
        
        parts = []
        
        # Part 1: Load real post-mortem documents if available (~3,000-6,000 tokens)
        pm_dir = pathlib.Path("data/postmortems")
        if pm_dir.exists():
            docs = sorted(pm_dir.glob("*.md"))[:3]  # Top 3 most recent
            for doc in docs:
                content = doc.read_text()
                parts.append(f"=== POST-MORTEM REPORT: {doc.stem} ===\n{content}\n")
        else:
            # Fallback: inline a realistic post-mortem (~3,500 tokens)
            parts.append("""=== POST-MORTEM REPORT: pm_001_auth_failure ===
# Incident: Auth Service JWT Expiry Misconfiguration
Date: 2024-01-15 | Duration: 47 min | Severity: P1
Services affected: auth-svc, payment-svc, checkout-svc, user-svc

## Timeline
14:32 UTC — Deployment v2.4.1 pushed to auth-svc
14:32:45 — JWT token validation errors begin (0.3% error rate)
14:33:10 — Error rate climbs to 12%
14:33:45 — payment-svc health checks begin failing
14:34:00 — Alert fired: "High 5xx error rate auth-svc"
14:35:00 — checkout-svc begins receiving auth failures from payment-svc
14:36:00 — SRE paged via PagerDuty
14:38:00 — Incident bridge opened
14:45:00 — Engineer begins log analysis
14:51:00 — Root cause found: JWT_EXPIRY changed 3600→60 in v2.4.1
14:52:00 — Rollback initiated
15:18:00 — Rollback complete, error rate returns to baseline
15:20:00 — All-clear declared

## Raw Logs (sample, 847 lines total)
2024-01-15T14:32:45Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_9482 ttl_remaining=-12s
2024-01-15T14:32:45Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_2847 ttl_remaining=-8s
2024-01-15T14:32:46Z payment-svc WARN [auth_client] Auth check returned 401 for request /api/v1/payment/process
2024-01-15T14:32:47Z payment-svc ERROR [circuit_breaker] Auth service failure rate 15.3% — threshold is 10%
2024-01-15T14:32:48Z checkout-svc ERROR [payment_client] Payment service unavailable: connection refused after 3 retries
2024-01-15T14:32:50Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_1193 ttl_remaining=-45s
2024-01-15T14:33:00Z nginx ERROR [upstream] 502 Bad Gateway from auth-svc pool (3/8 instances unhealthy)
2024-01-15T14:33:05Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_5621 ttl_remaining=-67s
2024-01-15T14:33:10Z payment-svc ERROR [health_check] Auth dependency check failed: 5 consecutive failures
2024-01-15T14:33:15Z checkout-svc WARN [retry_handler] Payment service retry exhausted after 5 attempts
2024-01-15T14:33:20Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_8834 ttl_remaining=-92s
2024-01-15T14:33:25Z api-gateway ERROR [auth_middleware] Authentication timeout after 5000ms
2024-01-15T14:33:30Z user-svc ERROR [session_manager] Session validation failed: auth service unreachable
2024-01-15T14:33:35Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_3421 ttl_remaining=-115s
2024-01-15T14:33:40Z payment-svc ERROR [circuit_breaker] Circuit opened for auth-svc after 20 failures
2024-01-15T14:33:45Z checkout-svc ERROR [dependency_monitor] Critical dependency auth-svc unavailable
2024-01-15T14:33:50Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_7712 ttl_remaining=-138s
2024-01-15T14:33:55Z nginx ERROR [upstream] All auth-svc instances marked unhealthy
2024-01-15T14:34:00Z monitoring ERROR [alertmanager] Firing alert: HIGH_5XX_RATE_AUTH_SVC severity=P1
2024-01-15T14:34:05Z auth-svc ERROR [jwt_validator] Token validation failed: token expired for user_id=usr_2156 ttl_remaining=-163s
[... 827 more log lines ...]

## Deployment History (last 10)
{"service":"auth-svc","version":"v2.4.1","timestamp":"2024-01-15T14:32:00Z","deployer":"eng@company.com","diff":"JWT_EXPIRY: 3600 -> 60, added rate limiting headers"}
{"service":"auth-svc","version":"v2.4.0","timestamp":"2024-01-10T09:15:00Z","deployer":"dev2@company.com","diff":"Updated session handling, bumped bcrypt rounds 10->12"}
{"service":"payment-svc","version":"v3.1.2","timestamp":"2024-01-14T16:00:00Z","deployer":"dev3@company.com","diff":"Add Apple Pay support, refactor webhook handler"}
{"service":"checkout-svc","version":"v1.8.5","timestamp":"2024-01-13T11:30:00Z","deployer":"dev4@company.com","diff":"Cart persistence fix, update auth-svc client timeout 5s->10s"}
{"service":"user-svc","version":"v2.2.1","timestamp":"2024-01-12T14:00:00Z","deployer":"dev5@company.com","diff":"Profile cache optimization, add Redis fallback"}
{"service":"api-gateway","version":"v4.0.3","timestamp":"2024-01-11T10:30:00Z","deployer":"dev6@company.com","diff":"Rate limiting per endpoint, update nginx config"}
{"service":"auth-svc","version":"v2.3.9","timestamp":"2024-01-08T15:45:00Z","deployer":"dev1@company.com","diff":"Security patch: update JWT library to v3.2.1"}
{"service":"payment-svc","version":"v3.1.1","timestamp":"2024-01-07T11:00:00Z","deployer":"dev3@company.com","diff":"Fix payment retry logic, add idempotency keys"}
{"service":"notification-svc","version":"v1.5.2","timestamp":"2024-01-06T09:30:00Z","deployer":"dev7@company.com","diff":"Email template updates, add SMS fallback"}
{"service":"checkout-svc","version":"v1.8.4","timestamp":"2024-01-05T16:15:00Z","deployer":"dev4@company.com","diff":"Inventory check optimization, reduce DB queries"}

## Config Change History (last 20 changes)
{"service":"auth-svc","key":"JWT_EXPIRY","old":"3600","new":"60","timestamp":"2024-01-15T14:32:00Z","changed_by":"deployment v2.4.1"}
{"service":"auth-svc","key":"RATE_LIMIT_RPM","old":"1000","new":"500","timestamp":"2024-01-15T14:32:00Z","changed_by":"deployment v2.4.1"}
{"service":"payment-svc","key":"AUTH_TIMEOUT_MS","old":"5000","new":"10000","timestamp":"2024-01-13T11:30:00Z","changed_by":"deployment v1.8.5"}
{"service":"user-svc","key":"CACHE_TTL_SECONDS","old":"300","new":"600","timestamp":"2024-01-12T14:00:00Z","changed_by":"deployment v2.2.1"}
{"service":"api-gateway","key":"MAX_REQUESTS_PER_MINUTE","old":"10000","new":"5000","timestamp":"2024-01-11T10:30:00Z","changed_by":"deployment v4.0.3"}
{"service":"auth-svc","key":"SESSION_TIMEOUT","old":"1800","new":"3600","timestamp":"2024-01-10T09:15:00Z","changed_by":"deployment v2.4.0"}
{"service":"payment-svc","key":"RETRY_MAX_ATTEMPTS","old":"3","new":"5","timestamp":"2024-01-07T11:00:00Z","changed_by":"deployment v3.1.1"}
{"service":"checkout-svc","key":"INVENTORY_CHECK_TIMEOUT","old":"2000","new":"1000","timestamp":"2024-01-05T16:15:00Z","changed_by":"deployment v1.8.4"}
[... 12 more config changes ...]

## Current Alert Status
Alert: HIGH_5XX_RATE_AUTH_SVC | Status: FIRING | Start: 14:34 | Severity: P1
Alert: PAYMENT_SVC_HEALTH_CHECK | Status: FIRING | Start: 14:33 | Severity: P2
Alert: CHECKOUT_DEPENDENCY_FAILURE | Status: FIRING | Start: 14:35 | Severity: P2

## Service Dependency Map
auth-svc: upstream=[] downstream=[payment-svc, checkout-svc, user-svc, admin-portal]
payment-svc: upstream=[auth-svc, fraud-svc] downstream=[ledger-svc, notification-svc]
checkout-svc: upstream=[auth-svc, payment-svc, inventory-svc] downstream=[fulfillment-svc]
user-svc: upstream=[auth-svc, profile-svc] downstream=[recommendation-svc]
api-gateway: upstream=[auth-svc] downstream=[all-services]

## On-Call Contacts
auth-svc owner: Platform Team | On-call: alice@company.com | Escalation: bob@company.com
payment-svc owner: Payments Team | On-call: charlie@company.com | Escalation: diana@company.com
checkout-svc owner: Commerce Team | On-call: eve@company.com | Escalation: frank@company.com
""")
        
        # Part 2: Generate realistic noise logs (~2,000 tokens of plausible but irrelevant logs)
        services = ["api-gateway", "cdn-edge", "metrics-collector", "log-aggregator",
                    "health-checker", "config-service", "feature-flag-svc", "cache-warmer"]
        levels = ["INFO", "INFO", "INFO", "DEBUG", "WARN"]
        noise_lines = []
        for i in range(150):
            svc = random.choice(services)
            lvl = random.choice(levels)
            noise_lines.append(
                f"2024-01-15T14:{(30 + i//10):02d}:{(i%10)*6:02d}Z "
                f"{svc} {lvl} [handler] Processed request "
                f"req_id=req_{random.randint(10000,99999)} duration={random.randint(8,120)}ms "
                f"status={random.choice([200, 200, 200, 201, 304, 400, 404])}"
            )
        parts.append("=== SYSTEM LOGS (unfiltered, last 15 minutes) ===\n" + "\n".join(noise_lines))
        
        # Part 3: Additional context (~2,000 tokens)
        parts.append("""
=== RUNBOOK REFERENCES ===
Runbook: auth-service-high-error-rate
URL: https://wiki.company.com/runbooks/auth-svc-errors
Last Updated: 2024-01-10
Steps:
1. Check auth-svc health endpoints
2. Review recent deployments
3. Check JWT configuration
4. Verify database connectivity
5. Check Redis cache status
6. Review rate limiting settings
7. Check upstream dependencies
8. Escalate to Platform Team if unresolved after 15 minutes

Runbook: jwt-token-validation-failures
URL: https://wiki.company.com/runbooks/jwt-validation
Last Updated: 2024-01-08
Common Causes:
- Token expiry misconfiguration
- Clock skew between services
- Invalid signing key
- Corrupted token format
- Network latency causing timeout
Resolution:
- Verify JWT_EXPIRY setting
- Check NTP sync across services
- Validate signing key rotation
- Review token generation logic

=== METRICS SNAPSHOT (14:30-14:35 UTC) ===
auth-svc:
  - requests_per_second: 1250 → 1180 (declining due to errors)
  - error_rate: 0.1% → 15.3% (spike at 14:33)
  - p50_latency: 45ms → 52ms
  - p99_latency: 180ms → 890ms
  - cpu_usage: 35% → 42%
  - memory_usage: 2.1GB / 4GB
  - active_connections: 450 → 380

payment-svc:
  - requests_per_second: 850 → 620 (declining)
  - error_rate: 0.2% → 8.7%
  - p50_latency: 120ms → 450ms
  - circuit_breaker_state: CLOSED → OPEN (for auth-svc)
  
checkout-svc:
  - requests_per_second: 650 → 420 (declining)
  - error_rate: 0.3% → 12.1%
  - dependency_health: auth-svc=UNHEALTHY, payment-svc=DEGRADED
""")
        
        full_context = "\n\n".join(parts)
        return full_context
    
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run baseline pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Complete incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost
        """
        # Assemble full context
        context = self.assemble_context(incident_id, incident_data)
        
        # Count ACTUAL tokens (not fake estimates)
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            actual_tokens = len(enc.encode(context))
        except ImportError:
            # Fallback: rough word count estimate (1 token ≈ 0.75 words)
            import re
            word_count = len(re.findall(r'\S+', context))
            actual_tokens = int(word_count * 0.75)
        
        # Build prompt
        prompt = self.prompt_builder.build_baseline_prompt(context, incident_id)
        
        # Call LLM
        llm_result = self.llm_client.call_llm(prompt)
        
        # Calculate cost
        cost = self.llm_client.calculate_cost(
            llm_result["input_tokens"],
            llm_result["output_tokens"]
        )
        
        return {
            "pipeline": "baseline",
            "incident_id": incident_id,
            "rca_report": llm_result["response"],
            "input_tokens": llm_result["input_tokens"],
            "output_tokens": llm_result["output_tokens"],
            "total_tokens": llm_result["total_tokens"],
            "latency_ms": llm_result["latency_ms"],
            "cost_usd": cost,
            "context_size": len(context),
            "context_tokens_actual": actual_tokens  # NEW: Real token count
        }


if __name__ == "__main__":
    pipeline = BaselinePipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    result = pipeline.run("incident_1", test_incident)
    print(f"Baseline Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Context size: {result['context_size']} chars")
