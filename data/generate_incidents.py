"""
Generates synthetic_incidents.json — the incident corpus for RAG pipelines.
Target: 2M+ tokens (approximately 2,500+ detailed incident records).
Run: python data/generate_incidents.py
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

# ── Schema ────────────────────────────────────────────────────────────────────
SERVICES = [
    {"id": "svc_1", "name": "auth-svc",         "team": "Platform",  "lang": "Go",     "tier": "critical"},
    {"id": "svc_2", "name": "payment-svc",       "team": "Payments",  "lang": "Java",   "tier": "critical"},
    {"id": "svc_3", "name": "api-gateway",       "team": "API",       "lang": "Nginx",  "tier": "critical"},
    {"id": "svc_4", "name": "checkout-svc",      "team": "Commerce",  "lang": "Python", "tier": "high"},
    {"id": "svc_5", "name": "user-svc",          "team": "Identity",  "lang": "Node",   "tier": "high"},
    {"id": "svc_6", "name": "order-svc",         "team": "Commerce",  "lang": "Python", "tier": "high"},
    {"id": "svc_7", "name": "inventory-svc",     "team": "Supply",    "lang": "Go",     "tier": "medium"},
    {"id": "svc_8", "name": "notification-svc",  "team": "Platform",  "lang": "Node",   "tier": "medium"},
    {"id": "svc_9", "name": "fraud-svc",         "team": "Risk",      "lang": "Python", "tier": "high"},
    {"id": "svc_10","name": "ledger-svc",        "team": "Finance",   "lang": "Java",   "tier": "critical"},
]

INCIDENT_TEMPLATES = [
    {
        "type": "jwt_expiry",
        "alert": "High 5xx error rate — auth token validation failures",
        "config_key": "JWT_EXPIRY_SECONDS",
        "config_old": "3600", "config_new": "60",
        "root_cause": "JWT expiry reduced from 1hr to 1min in deployment. All active tokens expired within 60s, causing auth failures across all dependent services.",
        "resolution": "Rolled back JWT_EXPIRY_SECONDS to 3600. Added config guard: JWT_EXPIRY_SECONDS must be >= 600.",
        "mttr_minutes": 12,
        "affected_services": ["auth-svc", "payment-svc", "checkout-svc", "user-svc"],
    },
    {
        "type": "db_connection_pool",
        "alert": "Database connection pool exhausted — new connections refused",
        "config_key": "DB_POOL_SIZE",
        "config_old": "50", "config_new": "5",
        "root_cause": "DB_POOL_SIZE reduced in deployment. Combined with missing db.close() in new batch processing code, pool exhausted within 33 minutes.",
        "resolution": "Reverted DB_POOL_SIZE to 50. Fixed connection leak in batch processor. Added pool utilization alert at 80%.",
        "mttr_minutes": 23,
        "affected_services": ["order-svc", "inventory-svc", "ledger-svc"],
    },
    {
        "type": "rate_limit",
        "alert": "API gateway returning 429 Too Many Requests",
        "config_key": "GLOBAL_RATE_LIMIT_RPM",
        "config_old": "10000", "config_new": "100",
        "root_cause": "Rate limit config reduced by factor of 100 in migration script error. Legitimate traffic throttled immediately after deployment.",
        "resolution": "Reverted GLOBAL_RATE_LIMIT_RPM to 10000. Added human approval step for rate-limit config changes.",
        "mttr_minutes": 8,
        "affected_services": ["api-gateway", "auth-svc", "payment-svc"],
    },
    {
        "type": "redis_eviction",
        "alert": "Cache miss rate spike — Redis returning MISS on all keys",
        "config_key": "REDIS_MAXMEMORY_POLICY",
        "config_old": "allkeys-lru", "config_new": "noeviction",
        "root_cause": "Redis eviction policy changed to noeviction. Memory filled up and Redis began rejecting writes. All subsequent reads returned MISS.",
        "resolution": "Reverted REDIS_MAXMEMORY_POLICY to allkeys-lru. Added Redis memory monitoring alert at 85% utilization.",
        "mttr_minutes": 15,
        "affected_services": ["checkout-svc", "user-svc", "fraud-svc"],
    },
    {
        "type": "timeout_cascade",
        "alert": "Downstream service timeout cascade — p99 latency > 30s",
        "config_key": "UPSTREAM_TIMEOUT_MS",
        "config_old": "5000", "config_new": "30000",
        "root_cause": "Upstream timeout increased to 30s. One slow dependency caused thread pool saturation as all threads waited 30s before failing. Thread exhaustion cascaded to all endpoints.",
        "resolution": "Reverted UPSTREAM_TIMEOUT_MS to 5000. Implemented circuit breaker with 2s timeout and 50% error threshold.",
        "mttr_minutes": 31,
        "affected_services": ["api-gateway", "payment-svc", "checkout-svc", "order-svc"],
    },
    {
        "type": "ssl_cert_expiry",
        "alert": "SSL certificate expired — TLS handshake failures",
        "config_key": "SSL_CERT_EXPIRY_DATE",
        "config_old": "2025-12-31", "config_new": "EXPIRED",
        "root_cause": "SSL certificate for api.company.com expired. No renewal alert was configured. CDN began rejecting connections from all clients.",
        "resolution": "Renewed SSL certificate via Let's Encrypt. Added monitoring for certs expiring within 30/14/7 days. Enabled auto-renewal.",
        "mttr_minutes": 45,
        "affected_services": ["api-gateway", "auth-svc"],
    },
    {
        "type": "memory_leak",
        "alert": "OOM kills — pods being evicted by Kubernetes",
        "config_key": "MEMORY_LIMIT_MB",
        "config_old": "2048", "config_new": "512",
        "root_cause": "Memory limit halved in deployment. New feature introduced unbounded cache growth. Pods hit limit and were OOM-killed every 8-12 minutes.",
        "resolution": "Reverted memory limit to 2048MB. Fixed LRU cache to enforce max_size=10000. Added memory growth alert.",
        "mttr_minutes": 19,
        "affected_services": ["payment-svc", "fraud-svc"],
    },
    {
        "type": "kafka_consumer_lag",
        "alert": "Kafka consumer lag > 1M messages — processing falling behind",
        "config_key": "KAFKA_CONSUMER_GROUP_ID",
        "config_old": "payment-consumer-v1", "config_new": "payment-consumer-v2",
        "root_cause": "Consumer group ID changed in deployment. New group started from offset 0 (auto.offset.reset=earliest), reprocessing 1M+ historical messages.",
        "resolution": "Reverted consumer group ID to payment-consumer-v1. Added migration script to transfer committed offsets when renaming consumer groups.",
        "mttr_minutes": 67,
        "affected_services": ["payment-svc", "ledger-svc", "notification-svc"],
    },
    {
        "type": "dns_ttl",
        "alert": "Intermittent DNS resolution failures — service discovery broken",
        "config_key": "DNS_TTL_SECONDS",
        "config_old": "300", "config_new": "5",
        "root_cause": "DNS TTL reduced to 5s for 'faster propagation'. Resolver flood: 300 DNS queries/second per service instance overwhelmed the DNS server.",
        "resolution": "Reverted DNS_TTL_SECONDS to 300. Added DNS query rate monitoring. DNS server autoscaling enabled.",
        "mttr_minutes": 14,
        "affected_services": ["api-gateway", "auth-svc", "payment-svc", "order-svc"],
    },
    {
        "type": "daylight_saving",
        "alert": "Scheduled job failed to run — data pipeline 2 hours late",
        "config_key": "SCHEDULER_TIMEZONE",
        "config_old": "UTC", "config_new": "America/New_York",
        "root_cause": "Scheduler timezone changed to local time. During DST spring-forward, 2:00 AM became 3:00 AM. Job scheduled for 2:30 AM was skipped entirely.",
        "resolution": "Reverted SCHEDULER_TIMEZONE to UTC. All scheduled jobs now defined in UTC. Added DST-aware monitoring for scheduler jobs.",
        "mttr_minutes": 127,
        "affected_services": ["order-svc", "ledger-svc", "notification-svc"],
    },
]

def make_timestamp(days_ago: int, hour: int = 14, minute: int = 32) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23))
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()

def make_log_lines(service: str, error_type: str, count: int = 50) -> list:
    """Generate realistic log lines for a service incident."""
    lines = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    errors = {
        "jwt_expiry":       "Token expired: user={uid} ttl={ttl}s issued={ts}",
        "db_connection_pool": "Connection refused: pool exhausted (active={n}/5 max=5)",
        "rate_limit":       "429 Too Many Requests: client={ip} rpm={n} limit=100",
        "redis_eviction":   "Cache MISS: key={key} Redis returned NOKEY after SET failed",
        "timeout_cascade":  "Upstream timeout: service={svc} waited 30000ms — circuit open",
        "memory_leak":      "OOMKilled: pod {pod} memory 512Mi/512Mi limit exceeded",
        "kafka_consumer_lag": "Consumer lag: partition={n} lag=1{m}00000 group=payment-consumer-v2",
        "ssl_cert_expiry":  "TLS handshake failed: certificate expired 2025-12-31",
        "dns_ttl":          "DNS query failed: SERVFAIL for {svc}.internal after 3 retries",
        "daylight_saving":  "Job skipped: scheduled 2:30 AM UTC-5 during DST spring-forward",
    }
    template = errors.get(error_type, "ERROR unexpected failure in {svc}")
    for i in range(count):
        ts = (base_time + timedelta(seconds=i * 6)).strftime("%Y-%m-%dT%H:%M:%SZ")
        msg = template.format(
            uid=f"usr_{random.randint(1000,9999)}",
            ttl=random.randint(-120, -1),
            ts=(base_time - timedelta(seconds=random.randint(60, 3600))).strftime("%H:%M:%S"),
            n=random.randint(1, 50),
            ip=f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            key=f"session:{uuid.uuid4().hex[:8]}",
            svc=service,
            pod=f"{service}-{uuid.uuid4().hex[:6]}",
            m=random.randint(1, 9),
        )
        lines.append(f"{ts} {service} ERROR [incident] {msg}")
    return lines

def generate_incident(idx: int, template: dict, service: dict) -> dict:
    """Generate one full incident record."""
    incident_id = f"INC-{1000 + idx}"
    deploy_id   = f"deploy_{idx}"
    config_id   = f"config_{idx}"
    alert_id    = f"alert_{1000 + idx}"
    days_ago    = random.randint(1, 180)
    start_time  = make_timestamp(days_ago)
    
    return {
        "incident_id":        incident_id,
        "alert_id":           alert_id,
        "alert_name":         template["alert"],
        "severity":           "critical" if service["tier"] == "critical" else "high",
        "service_id":         service["id"],
        "service_name":       service["name"],
        "team":               service["team"],
        "start_time":         start_time,
        "mttr_minutes":       template["mttr_minutes"] + random.randint(-3, 10),
        "deployment": {
            "deploy_id":      deploy_id,
            "version":        f"v{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}",
            "deployer":       f"eng{random.randint(1,20)}@company.com",
            "timestamp":      start_time,
        },
        "config_change": {
            "config_id":      config_id,
            "key":            template["config_key"],
            "old_value":      template["config_old"],
            "new_value":      template["config_new"],
        },
        "root_cause":         template["root_cause"],
        "affected_services":  template["affected_services"],
        "resolution":         template["resolution"],
        "incident_type":      template["type"],
        "logs":               make_log_lines(service["name"], template["type"], count=60),
        "postmortem_text": (
            f"# Post-Mortem: {template['alert']}\n"
            f"**Incident ID:** {incident_id} | **Date:** {start_time[:10]} | "
            f"**Severity:** {'P1' if service['tier']=='critical' else 'P2'} | "
            f"**MTTR:** {template['mttr_minutes']} min\n\n"
            f"## Root Cause\n{template['root_cause']}\n\n"
            f"## Affected Services\n"
            + "\n".join(f"- {s}" for s in template["affected_services"]) +
            f"\n\n## Config Change\n"
            f"`{template['config_key']}` changed from `{template['config_old']}` "
            f"to `{template['config_new']}` in deployment {deploy_id}.\n\n"
            f"## Resolution\n{template['resolution']}\n\n"
            f"## Lessons Learned\n"
            f"- Config changes to {template['config_key']} require change-approval review.\n"
            f"- Alert added for {template['config_key']} drift from baseline.\n"
            f"- Runbook updated with rollback procedure.\n"
        ),
    }

def main():
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    
    incidents = []
    idx = 0
    
    # Generate enough incidents to hit 2M+ tokens
    # Each incident ~800 tokens → need ~2,500 incidents
    total_target = 2500
    template_cycle = INCIDENT_TEMPLATES * (total_target // len(INCIDENT_TEMPLATES) + 1)
    service_cycle  = SERVICES * (total_target // len(SERVICES) + 1)
    
    for i in range(total_target):
        template = template_cycle[i]
        service  = service_cycle[i]
        incidents.append(generate_incident(idx + i, template, service))
        if (i + 1) % 250 == 0:
            print(f"  Generated {i+1}/{total_target} incidents...")
    
    out_path = out_dir / "synthetic_incidents.json"
    with open(out_path, "w") as f:
        json.dump(incidents, f, indent=2)
    
    # Estimate token count
    total_chars = sum(len(json.dumps(inc)) for inc in incidents)
    est_tokens  = total_chars // 4  # ~4 chars per token
    print(f"\n✅ Generated {len(incidents)} incidents")
    print(f"   File: {out_path}")
    print(f"   Size: {out_path.stat().st_size / 1_048_576:.1f} MB")
    print(f"   Estimated tokens: {est_tokens:,} ({est_tokens/1_000_000:.1f}M)")
    
    # Also write a small summary for verification
    summary = {
        "total_incidents": len(incidents),
        "incident_types":  list({t["type"] for t in INCIDENT_TEMPLATES}),
        "services":        [s["name"] for s in SERVICES],
        "estimated_tokens": est_tokens,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
    }
    with open(out_dir / "synthetic_incidents_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"   Summary: data/synthetic_incidents_summary.json")

if __name__ == "__main__":
    main()
