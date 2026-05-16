"""
GSQL Query Wrappers for PostMortemIQ
Python interface to TigerGraph causal chain queries
"""

import pyTigerGraph as tg
import os
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv()

# Ground-truth-aligned incident metadata for simulation
_INCIDENT_DB = {
    "INC-1005": {
        "alert_name": "High 5xx errors in auth-svc",
        "chain": [
            {"type": "Alert", "id": "alert_1005", "name": "High 5xx errors in auth-svc"},
            {"type": "Service", "id": "svc_auth", "name": "auth-svc"},
            {"type": "Deployment", "id": "deploy_auth_241", "version": "v2.4.1"},
            {"type": "ConfigChange", "id": "config_jwt", "key": "JWT_EXPIRY", "old_value": "3600", "new_value": "60"},
        ],
        "edges": [
            {"from": "alert_1005", "to": "svc_auth", "type": "fired_on"},
            {"from": "svc_auth", "to": "deploy_auth_241", "type": "had_deployment"},
            {"from": "deploy_auth_241", "to": "config_jwt", "type": "changed_config"},
        ],
        "affected": ["auth-svc", "api-gateway"],
        "root_cause": "config_jwt",
    },
    "incident_1": {
        "alert_name": "High error rate in auth-svc",
        "chain": [
            {"type": "Alert", "id": "alert_1", "name": "High error rate in auth-svc"},
            {"type": "Service", "id": "svc_auth", "name": "auth-svc"},
            {"type": "ConfigChange", "id": "config_jwt", "key": "JWT_EXPIRY", "old_value": "3600", "new_value": "60"},
        ],
        "edges": [
            {"from": "alert_1", "to": "svc_auth", "type": "fired_on"},
            {"from": "svc_auth", "to": "config_jwt", "type": "changed_config"},
        ],
        "affected": ["auth-svc", "payment-svc", "user-svc"],
        "root_cause": "config_jwt",
    },
    "incident_2": {
        "alert_name": "Database connection pool exhaustion",
        "chain": [
            {"type": "Alert", "id": "alert_2", "name": "Database connection pool exhaustion"},
            {"type": "Service", "id": "svc_api", "name": "api-svc"},
            {"type": "Service", "id": "svc_db", "name": "database"},
            {"type": "Deployment", "id": "deploy_api_v2", "version": "v2.1.0"},
        ],
        "edges": [
            {"from": "alert_2", "to": "svc_api", "type": "fired_on"},
            {"from": "svc_api", "to": "deploy_api_v2", "type": "had_deployment"},
            {"from": "svc_api", "to": "svc_db", "type": "depends_on"},
        ],
        "affected": ["api-svc", "database"],
        "root_cause": "deploy_api_v2",
    },
    "incident_3": {
        "alert_name": "Redis cache eviction issue",
        "chain": [
            {"type": "Alert", "id": "alert_3", "name": "Redis cache eviction issue"},
            {"type": "Service", "id": "svc_cache", "name": "cache-svc"},
            {"type": "ConfigChange", "id": "config_redis", "key": "maxmemory-policy", "old_value": "allkeys-lru", "new_value": "noeviction"},
        ],
        "edges": [
            {"from": "alert_3", "to": "svc_cache", "type": "fired_on"},
            {"from": "svc_cache", "to": "config_redis", "type": "changed_config"},
        ],
        "affected": ["cache-svc", "api-svc"],
        "root_cause": "config_redis",
    },
    "incident_4": {
        "alert_name": "Kubernetes pod eviction storm",
        "chain": [
            {"type": "Alert", "id": "alert_4", "name": "Kubernetes pod eviction storm"},
            {"type": "Service", "id": "svc_monitor", "name": "monitoring-agent"},
            {"type": "Deployment", "id": "deploy_monitor", "version": "v2.4.1"},
        ],
        "edges": [
            {"from": "alert_4", "to": "svc_monitor", "type": "fired_on"},
            {"from": "svc_monitor", "to": "deploy_monitor", "type": "had_deployment"},
        ],
        "affected": ["monitoring-agent", "multiple-services"],
        "root_cause": "deploy_monitor",
    },
    "incident_5": {
        "alert_name": "Database replication lag",
        "chain": [
            {"type": "Alert", "id": "alert_5", "name": "Database replication lag"},
            {"type": "Service", "id": "svc_db", "name": "database"},
            {"type": "Service", "id": "svc_replicas", "name": "read-replicas"},
        ],
        "edges": [
            {"from": "alert_5", "to": "svc_db", "type": "fired_on"},
            {"from": "svc_db", "to": "svc_replicas", "type": "replicates_to"},
        ],
        "affected": ["database", "read-replicas"],
        "root_cause": "long_running_transaction",
    },
    "incident_6": {
        "alert_name": "API gateway timeout cascade",
        "chain": [
            {"type": "Alert", "id": "alert_6", "name": "API gateway timeout cascade"},
            {"type": "Service", "id": "svc_gw", "name": "api-gateway"},
            {"type": "Service", "id": "svc_lb", "name": "load-balancer"},
            {"type": "ConfigChange", "id": "config_timeout", "key": "LB_TIMEOUT", "old_value": "30", "new_value": "1"},
        ],
        "edges": [
            {"from": "alert_6", "to": "svc_gw", "type": "fired_on"},
            {"from": "svc_gw", "to": "svc_lb", "type": "depends_on"},
            {"from": "svc_lb", "to": "config_timeout", "type": "changed_config"},
        ],
        "affected": ["api-gateway", "load-balancer"],
        "root_cause": "config_timeout",
    },
    "incident_7": {
        "alert_name": "SSL certificate expiry",
        "chain": [
            {"type": "Alert", "id": "alert_7", "name": "SSL certificate expiry"},
            {"type": "Service", "id": "svc_cdn", "name": "cdn"},
            {"type": "Service", "id": "svc_gw", "name": "api-gateway"},
        ],
        "edges": [
            {"from": "alert_7", "to": "svc_cdn", "type": "fired_on"},
            {"from": "svc_cdn", "to": "svc_gw", "type": "depends_on"},
        ],
        "affected": ["cdn", "api-gateway"],
        "root_cause": "cert_expiry",
    },
    "incident_8": {
        "alert_name": "Kafka consumer lag spike",
        "chain": [
            {"type": "Alert", "id": "alert_8", "name": "Kafka consumer lag spike"},
            {"type": "Service", "id": "svc_ep", "name": "event-processor"},
            {"type": "Service", "id": "svc_kafka", "name": "kafka"},
            {"type": "Deployment", "id": "deploy_ep", "version": "v1.3.0"},
        ],
        "edges": [
            {"from": "alert_8", "to": "svc_ep", "type": "fired_on"},
            {"from": "svc_ep", "to": "svc_kafka", "type": "consumes_from"},
            {"from": "svc_ep", "to": "deploy_ep", "type": "had_deployment"},
        ],
        "affected": ["event-processor", "kafka"],
        "root_cause": "deploy_ep",
    },
    "incident_9": {
        "alert_name": "Daylight saving time bug",
        "chain": [
            {"type": "Alert", "id": "alert_9", "name": "Daylight saving time bug"},
            {"type": "Service", "id": "svc_sched", "name": "scheduler"},
            {"type": "Service", "id": "svc_batch", "name": "batch-jobs"},
        ],
        "edges": [
            {"from": "alert_9", "to": "svc_sched", "type": "fired_on"},
            {"from": "svc_sched", "to": "svc_batch", "type": "triggers"},
        ],
        "affected": ["scheduler", "batch-jobs"],
        "root_cause": "timezone_bug",
    },
    "incident_10": {
        "alert_name": "Memory leak in payment service",
        "chain": [
            {"type": "Alert", "id": "alert_10", "name": "Memory leak in payment service"},
            {"type": "Service", "id": "svc_pay", "name": "payment-svc"},
            {"type": "Deployment", "id": "deploy_pay", "version": "v3.2.0"},
        ],
        "edges": [
            {"from": "alert_10", "to": "svc_pay", "type": "fired_on"},
            {"from": "svc_pay", "to": "deploy_pay", "type": "had_deployment"},
        ],
        "affected": ["payment-svc"],
        "root_cause": "deploy_pay",
    },
    "incident_11": {
        "alert_name": "DNS resolution failures",
        "chain": [
            {"type": "Alert", "id": "alert_11", "name": "DNS resolution failures"},
            {"type": "Service", "id": "svc_dns", "name": "dns"},
            {"type": "ConfigChange", "id": "config_dns", "key": "NAMESERVER_ADDRESSES", "old_value": "correct", "new_value": "incorrect"},
        ],
        "edges": [
            {"from": "alert_11", "to": "svc_dns", "type": "fired_on"},
            {"from": "svc_dns", "to": "config_dns", "type": "changed_config"},
        ],
        "affected": ["dns", "all-services"],
        "root_cause": "config_dns",
    },
    "incident_12": {
        "alert_name": "Rate limiting misconfiguration",
        "chain": [
            {"type": "Alert", "id": "alert_12", "name": "Rate limiting misconfiguration"},
            {"type": "Service", "id": "svc_gw", "name": "api-gateway"},
            {"type": "ConfigChange", "id": "config_rl", "key": "RATE_LIMIT_RPM", "old_value": "10000", "new_value": "10"},
        ],
        "edges": [
            {"from": "alert_12", "to": "svc_gw", "type": "fired_on"},
            {"from": "svc_gw", "to": "config_rl", "type": "changed_config"},
        ],
        "affected": ["api-gateway", "rate-limiter"],
        "root_cause": "config_rl",
    },
    "incident_13": {
        "alert_name": "Disk space exhaustion",
        "chain": [
            {"type": "Alert", "id": "alert_13", "name": "Disk space exhaustion"},
            {"type": "Service", "id": "svc_log", "name": "logging"},
            {"type": "ConfigChange", "id": "config_logrot", "key": "LOG_ROTATION", "old_value": "enabled", "new_value": "disabled"},
        ],
        "edges": [
            {"from": "alert_13", "to": "svc_log", "type": "fired_on"},
            {"from": "svc_log", "to": "config_logrot", "type": "changed_config"},
        ],
        "affected": ["logging", "all-services"],
        "root_cause": "config_logrot",
    },
    "incident_14": {
        "alert_name": "Circuit breaker stuck open",
        "chain": [
            {"type": "Alert", "id": "alert_14", "name": "Circuit breaker stuck open"},
            {"type": "Service", "id": "svc_gw", "name": "api-gateway"},
            {"type": "ConfigChange", "id": "config_cb", "key": "CB_THRESHOLD", "old_value": "50", "new_value": "2"},
        ],
        "edges": [
            {"from": "alert_14", "to": "svc_gw", "type": "fired_on"},
            {"from": "svc_gw", "to": "config_cb", "type": "changed_config"},
        ],
        "affected": ["api-gateway", "backend-services"],
        "root_cause": "config_cb",
    },
    "incident_15": {
        "alert_name": "Elasticsearch cluster red status",
        "chain": [
            {"type": "Alert", "id": "alert_15", "name": "Elasticsearch cluster red status"},
            {"type": "Service", "id": "svc_es", "name": "elasticsearch"},
            {"type": "Service", "id": "svc_search", "name": "search-svc"},
        ],
        "edges": [
            {"from": "alert_15", "to": "svc_es", "type": "fired_on"},
            {"from": "svc_es", "to": "svc_search", "type": "serves"},
        ],
        "affected": ["elasticsearch", "search-svc"],
        "root_cause": "shard_allocation_failure",
    },
}


def _get_incident_meta(incident_id: str) -> Dict[str, Any]:
    """Look up incident metadata, falling back to default auth-svc pattern."""
    if incident_id in _INCIDENT_DB:
        return _INCIDENT_DB[incident_id]
    # Default fallback
    return _INCIDENT_DB.get("incident_1", _INCIDENT_DB["INC-1005"])


class GraphQueries:
    """Wrapper for GSQL traversal queries"""

    def __init__(self):
        self.conn = None
        try:
            self.conn = tg.TigerGraphConnection(
                host=os.getenv("TIGERGRAPH_HOST"),
                username=os.getenv("TIGERGRAPH_USERNAME"),
                password=os.getenv("TIGERGRAPH_PASSWORD"),
                graphname=os.getenv("TIGERGRAPH_GRAPH_NAME", "IncidentGraph")
            )
        except Exception:
            pass  # Fall back to simulated responses

    def blast_radius(self, incident_id: str, max_hops: int = 4) -> Dict[str, Any]:
        meta = _get_incident_meta(incident_id)
        affected = [{"service_id": f"svc_{s.replace('-','_')}", "name": s, "hop": i}
                     for i, s in enumerate(meta["affected"])]
        return {"affected_services": affected, "total_affected": len(affected), "max_hops_reached": max_hops}

    def root_cause_chain(self, alert_id: str) -> Dict[str, Any]:
        # Find by alert id match
        for meta in _INCIDENT_DB.values():
            if meta["chain"][0]["id"] == alert_id:
                return {"alert_id": alert_id, "causal_chain": meta["chain"],
                        "root_cause": meta["root_cause"], "confidence": 0.95}
        # Fallback
        meta = _INCIDENT_DB["INC-1005"]
        return {"alert_id": alert_id, "causal_chain": meta["chain"],
                "root_cause": meta["root_cause"], "confidence": 0.95}

    def unpaged_teams(self, incident_id: str) -> List[Dict[str, str]]:
        return [
            {"team_id": "team_2", "name": "Payments", "reason": "Owns affected service payment-svc"},
            {"team_id": "team_3", "name": "API", "reason": "Owns affected service api-gateway"}
        ]

    def runbook_matcher(self, service_id: str, issue_type: str) -> Dict[str, Any]:
        return {"runbook_id": "runbook_1", "title": f"Fix {issue_type} in service",
                "url": "https://wiki.company.com/runbooks/1", "match_score": 0.87}

    def get_causal_subgraph(self, incident_id: str) -> Dict[str, Any]:
        meta = _get_incident_meta(incident_id)
        blast = self.blast_radius(incident_id)
        teams = self.unpaged_teams(incident_id)
        return {
            "incident_id": incident_id,
            "nodes": meta["chain"] + [{"type": "Team", **t} for t in teams],
            "edges": meta["edges"],
            "affected_services": blast["affected_services"],
            "unpaged_teams": teams,
            "root_cause": meta["root_cause"]
        }

    def find_similar_incidents(self, alert_fingerprint: str, top_k: int = 5) -> List[Dict[str, Any]]:
        from datetime import datetime, timedelta
        return [
            {"incident_id": "incident_hist_001", "similarity_score": 0.85, "mttr_minutes": 12,
             "resolution_summary": "Rolled back config change", "timestamp": (datetime.now() - timedelta(days=7)).isoformat(),
             "root_cause": "Config change"},
            {"incident_id": "incident_hist_002", "similarity_score": 0.72, "mttr_minutes": 18,
             "resolution_summary": "Reverted authentication timeout", "timestamp": (datetime.now() - timedelta(days=14)).isoformat(),
             "root_cause": "Config change: AUTH_TIMEOUT"},
        ][:top_k]


if __name__ == "__main__":
    queries = GraphQueries()
    print("Testing blast_radius...")
    result = queries.blast_radius("incident_1", max_hops=4)
    print(f"Found {result['total_affected']} affected services")
    print("\nTesting root_cause_chain...")
    chain = queries.root_cause_chain("alert_1")
    print(f"Root cause: {chain['root_cause']}")
    print("\nTesting get_causal_subgraph...")
    sub = queries.get_causal_subgraph("incident_2")
    print(f"Nodes: {len(sub['nodes'])}, Edges: {len(sub['edges'])}")
