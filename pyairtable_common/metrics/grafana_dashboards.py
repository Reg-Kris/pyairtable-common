"""
Grafana dashboard configurations for PyAirtable microservices.

This module provides pre-configured Grafana dashboard JSON definitions
for monitoring the PyAirtable ecosystem.
"""
import json
from typing import Dict, List, Any


def create_overview_dashboard() -> Dict[str, Any]:
    """Create the main overview dashboard for PyAirtable ecosystem."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "PyAirtable Microservices Overview",
            "tags": ["pyairtable", "overview", "microservices"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Service Health Status",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "up{job=~\"pyairtable-.*\"}",
                            "legendFormat": "{{service}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {"displayMode": "list", "orientation": "horizontal"},
                            "mappings": [
                                {"options": {"0": {"text": "Down", "color": "red"}}},
                                {"options": {"1": {"text": "Up", "color": "green"}}}
                            ]
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Request Rate (per service)",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{job=~\"pyairtable-.*\"}[5m])",
                            "legendFormat": "{{service}} - {{method}} {{endpoint}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {"drawStyle": "line", "lineInterpolation": "linear"}
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Response Time P95",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=~\"pyairtable-.*\"}[5m]))",
                            "legendFormat": "{{service}} P95",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "unit": "s"
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Error Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{status_code=~\"5..\",job=~\"pyairtable-.*\"}[5m])",
                            "legendFormat": "{{service}} 5xx errors",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {"drawStyle": "line", "lineInterpolation": "linear"}
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }
    
    return dashboard


def create_airtable_gateway_dashboard() -> Dict[str, Any]:
    """Create dashboard for airtable-gateway-py service."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "Airtable Gateway Service",
            "tags": ["pyairtable", "airtable-gateway"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Airtable API Requests",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(airtable_api_requests_total[5m])",
                            "legendFormat": "{{base_id}} - {{operation}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Cache Hit Ratio",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "cache_hit_ratio",
                            "legendFormat": "Hit Ratio",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0,
                            "max": 1,
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 0.7},
                                    {"color": "green", "value": 0.9}
                                ]
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Rate Limit Hits",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(airtable_rate_limit_hits_total[5m])",
                            "legendFormat": "{{base_id}} - {{limit_type}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                },
                {
                    "id": 4,
                    "title": "API Quota Usage",
                    "type": "gauge",
                    "targets": [
                        {
                            "expr": "airtable_api_quota_usage",
                            "legendFormat": "{{base_id}} - {{quota_type}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "min": 0,
                            "max": 100,
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 70},
                                    {"color": "red", "value": 90}
                                ]
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 5,
                    "title": "Request Queue Size",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "airtable_request_queue_size",
                            "legendFormat": "{{base_id}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }
    
    return dashboard


def create_mcp_server_dashboard() -> Dict[str, Any]:
    """Create dashboard for mcp-server-py service."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "MCP Server Service",
            "tags": ["pyairtable", "mcp-server"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Active Subprocesses",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "mcp_subprocess_count",
                            "legendFormat": "{{process_type}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Subprocess Creation Rate",
                    "type": "timeseries", 
                    "targets": [
                        {
                            "expr": "rate(mcp_subprocess_creation_total[5m])",
                            "legendFormat": "{{process_type}} - {{status}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Tool Execution Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(mcp_tool_executions_total[5m])",
                            "legendFormat": "{{tool_name}} - {{status}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Tool Execution Duration P95",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(mcp_tool_execution_duration_seconds_bucket[5m]))",
                            "legendFormat": "{{tool_name}} P95",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {"unit": "s"}
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                },
                {
                    "id": 5,
                    "title": "Protocol Message Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(mcp_protocol_messages_total[5m])",
                            "legendFormat": "{{message_type}} - {{direction}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }
    
    return dashboard


def create_llm_orchestrator_dashboard() -> Dict[str, Any]:
    """Create dashboard for llm-orchestrator-py service."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "LLM Orchestrator Service",
            "tags": ["pyairtable", "llm-orchestrator"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Active Sessions",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "llm_active_sessions",
                            "legendFormat": "Active Sessions",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Gemini API Request Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(gemini_requests_total[5m])",
                            "legendFormat": "{{model}} - {{operation}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 18, "x": 6, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Token Usage Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(gemini_token_usage_total[5m])",
                            "legendFormat": "{{model}} - {{token_type}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Gemini API Latency P95",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(gemini_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "{{model}} P95",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {"unit": "s"}
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                },
                {
                    "id": 5,
                    "title": "Conversation Turns",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(llm_conversation_turns_total[5m])",
                            "legendFormat": "{{session_type}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
                },
                {
                    "id": 6,
                    "title": "Session Duration P95",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(llm_session_duration_seconds_bucket[5m]))",
                            "legendFormat": "Session Duration P95",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {"unit": "s"}
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }
    
    return dashboard


def create_infrastructure_dashboard() -> Dict[str, Any]:
    """Create infrastructure monitoring dashboard."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "PyAirtable Infrastructure",
            "tags": ["pyairtable", "infrastructure"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Redis Operations Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(redis_operations_total[5m])",
                            "legendFormat": "{{operation}} - {{result}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Redis Connection Pool Size",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "redis_connection_pool_size",
                            "legendFormat": "{{pool_type}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Circuit Breaker States",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "circuit_breaker_state",
                            "legendFormat": "{{circuit_name}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {"options": {"0": {"text": "Closed", "color": "green"}}},
                                {"options": {"1": {"text": "Open", "color": "red"}}},
                                {"options": {"2": {"text": "Half-Open", "color": "yellow"}}}
                            ]
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Circuit Breaker Failures",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(circuit_breaker_failures_total[5m])",
                            "legendFormat": "{{circuit_name}}",
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }
    
    return dashboard


def create_sla_dashboard() -> Dict[str, Any]:
    """Create SLA monitoring dashboard."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "PyAirtable SLA Monitoring",
            "tags": ["pyairtable", "sla", "monitoring"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Service Availability (99.9% SLA)",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "avg_over_time(up{job=~\"pyairtable-.*\"}[24h])",
                            "legendFormat": "{{service}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0.99,
                            "max": 1,
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 0.995},
                                    {"color": "green", "value": 0.999}
                                ]
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Error Budget Burn Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
                            "legendFormat": "{{service}} Error Rate",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "custom": {
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 0.001},
                                        {"color": "red", "value": 0.01}
                                    ]
                                }
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Response Time SLA (P95 < 2s)",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "{{service}} P95",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s",
                            "custom": {
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 1.5},
                                        {"color": "red", "value": 2.0}
                                    ]
                                }
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
                }
            ],
            "time": {"from": "now-24h", "to": "now"},
            "refresh": "5m"
        }
    }
    
    return dashboard


# Dashboard registry
DASHBOARD_CONFIGS = {
    "overview": create_overview_dashboard,
    "airtable-gateway": create_airtable_gateway_dashboard,
    "mcp-server": create_mcp_server_dashboard,
    "llm-orchestrator": create_llm_orchestrator_dashboard,
    "infrastructure": create_infrastructure_dashboard,
    "sla": create_sla_dashboard,
}


def export_dashboard_json(dashboard_name: str, output_file: str = None) -> str:
    """Export dashboard configuration as JSON."""
    if dashboard_name not in DASHBOARD_CONFIGS:
        raise ValueError(f"Unknown dashboard: {dashboard_name}")
    
    dashboard_config = DASHBOARD_CONFIGS[dashboard_name]()
    json_content = json.dumps(dashboard_config, indent=2)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(json_content)
    
    return json_content


def export_all_dashboards(output_dir: str = "./dashboards"):
    """Export all dashboard configurations to JSON files."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    for dashboard_name in DASHBOARD_CONFIGS:
        output_file = os.path.join(output_dir, f"{dashboard_name}-dashboard.json")
        export_dashboard_json(dashboard_name, output_file)
        print(f"Exported {dashboard_name} dashboard to {output_file}")


def get_dashboard_summary() -> Dict[str, str]:
    """Get summary of available dashboards."""
    return {
        "overview": "Main PyAirtable ecosystem overview with health, requests, latency, and errors",
        "airtable-gateway": "Airtable Gateway service metrics including API usage, caching, and rate limits",
        "mcp-server": "MCP Server metrics including subprocess management and tool execution",
        "llm-orchestrator": "LLM Orchestrator metrics including Gemini API usage and session management",
        "infrastructure": "Infrastructure metrics for Redis, circuit breakers, and system health",
        "sla": "SLA monitoring dashboard with availability, error budgets, and performance targets"
    }