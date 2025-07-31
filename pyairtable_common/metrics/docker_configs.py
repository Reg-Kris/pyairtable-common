"""
Docker Compose configurations for Prometheus and Grafana integration.

This module provides Docker Compose configurations and deployment templates
for monitoring the PyAirtable microservices ecosystem.
"""
import yaml
from typing import Dict, List, Any


def create_prometheus_config() -> Dict[str, Any]:
    """Create Prometheus configuration for PyAirtable services."""
    
    config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "rule_files": [],
        "scrape_configs": [
            {
                "job_name": "prometheus",
                "static_configs": [
                    {"targets": ["localhost:9090"]}
                ]
            },
            {
                "job_name": "pyairtable-airtable-gateway",
                "static_configs": [
                    {"targets": ["airtable-gateway-py:8000"]}
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "15s"
            },
            {
                "job_name": "pyairtable-mcp-server",
                "static_configs": [
                    {"targets": ["mcp-server-py:8001"]}
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "15s"
            },
            {
                "job_name": "pyairtable-llm-orchestrator",
                "static_configs": [
                    {"targets": ["llm-orchestrator-py:8002"]}
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "15s"
            },
            {
                "job_name": "pyairtable-api-gateway",
                "static_configs": [
                    {"targets": ["pyairtable-api-gateway:8003"]}
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "15s"
            },
            {
                "job_name": "redis-exporter",
                "static_configs": [
                    {"targets": ["redis-exporter:9121"]}
                ],
                "scrape_interval": "15s"
            }
        ],
        "alerting": {
            "alertmanagers": [
                {
                    "static_configs": [
                        {"targets": ["alertmanager:9093"]}
                    ]
                }
            ]
        }
    }
    
    return config


def create_docker_compose_monitoring() -> Dict[str, Any]:
    """Create Docker Compose configuration for monitoring stack."""
    
    compose = {
        "version": "3.8",
        "services": {
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "pyairtable-prometheus",
                "ports": ["9090:9090"],
                "volumes": [
                    "./prometheus.yml:/etc/prometheus/prometheus.yml",
                    "prometheus_data:/prometheus"
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--storage.tsdb.retention.time=200h",
                    "--web.enable-lifecycle"
                ],
                "networks": ["pyairtable-network"]
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "pyairtable-grafana",
                "ports": ["3000:3000"],
                "environment": {
                    "GF_SECURITY_ADMIN_PASSWORD": "admin",
                    "GF_USERS_ALLOW_SIGN_UP": "false",
                    "GF_INSTALL_PLUGINS": "grafana-piechart-panel,grafana-worldmap-panel"
                },
                "volumes": [
                    "grafana_data:/var/lib/grafana",
                    "./grafana/provisioning:/etc/grafana/provisioning",
                    "./grafana/dashboards:/var/lib/grafana/dashboards"
                ],
                "networks": ["pyairtable-network"],
                "depends_on": ["prometheus"]
            },
            "redis-exporter": {
                "image": "oliver006/redis_exporter:latest",
                "container_name": "pyairtable-redis-exporter",
                "ports": ["9121:9121"],
                "environment": {
                    "REDIS_ADDR": "redis:6379"
                },
                "networks": ["pyairtable-network"],
                "depends_on": ["redis"]
            },
            "alertmanager": {
                "image": "prom/alertmanager:latest",
                "container_name": "pyairtable-alertmanager",
                "ports": ["9093:9093"],
                "volumes": [
                    "./alertmanager.yml:/etc/alertmanager/alertmanager.yml"
                ],
                "networks": ["pyairtable-network"]
            }
        },
        "volumes": {
            "prometheus_data": {},
            "grafana_data": {}
        },
        "networks": {
            "pyairtable-network": {
                "external": True
            }
        }
    }
    
    return compose


def create_grafana_provisioning_config() -> Dict[str, Any]:
    """Create Grafana provisioning configuration."""
    
    # Datasource configuration
    datasource_config = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "access": "proxy",
                "url": "http://prometheus:9090",
                "isDefault": True,
                "editable": True
            }
        ]
    }
    
    # Dashboard provider configuration
    dashboard_config = {
        "apiVersion": 1,
        "providers": [
            {
                "name": "PyAirtable Dashboards",
                "orgId": 1,
                "folder": "",
                "type": "file",
                "disableDeletion": False,
                "updateIntervalSeconds": 10,
                "allowUiUpdates": True,
                "options": {
                    "path": "/var/lib/grafana/dashboards"
                }
            }
        ]
    }
    
    return {
        "datasources": datasource_config,
        "dashboards": dashboard_config
    }


def create_alerting_rules() -> Dict[str, Any]:
    """Create Prometheus alerting rules."""
    
    rules = {
        "groups": [
            {
                "name": "pyairtable.rules",
                "rules": [
                    {
                        "alert": "ServiceDown",
                        "expr": "up{job=~\"pyairtable-.*\"} == 0",
                        "for": "1m",
                        "labels": {
                            "severity": "critical"
                        },
                        "annotations": {
                            "summary": "PyAirtable service {{ $labels.job }} is down",
                            "description": "Service {{ $labels.job }} has been down for more than 1 minute."
                        }
                    },
                    {
                        "alert": "HighErrorRate",
                        "expr": "rate(http_requests_total{status_code=~\"5..\",job=~\"pyairtable-.*\"}[5m]) / rate(http_requests_total{job=~\"pyairtable-.*\"}[5m]) > 0.1",
                        "for": "5m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "High error rate on {{ $labels.service }}",
                            "description": "Error rate is {{ $value | humanizePercentage }} on {{ $labels.service }}"
                        }
                    },
                    {
                        "alert": "HighLatency",
                        "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=~\"pyairtable-.*\"}[5m])) > 2",
                        "for": "5m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "High latency on {{ $labels.service }}",
                            "description": "95th percentile latency is {{ $value }}s on {{ $labels.service }}"
                        }
                    },
                    {
                        "alert": "AirtableRateLimitHit",
                        "expr": "rate(airtable_rate_limit_hits_total[5m]) > 0",
                        "for": "1m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "Airtable rate limit hit for {{ $labels.base_id }}",
                            "description": "Rate limit hit for base {{ $labels.base_id }} with limit type {{ $labels.limit_type }}"
                        }
                    },
                    {
                        "alert": "CircuitBreakerOpen",
                        "expr": "circuit_breaker_state == 1",
                        "for": "1m",
                        "labels": {
                            "severity": "critical"
                        },
                        "annotations": {
                            "summary": "Circuit breaker {{ $labels.circuit_name }} is open",
                            "description": "Circuit breaker {{ $labels.circuit_name }} has been open for more than 1 minute"
                        }
                    },
                    {
                        "alert": "LowCacheHitRatio",
                        "expr": "cache_hit_ratio < 0.7",
                        "for": "10m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "Low cache hit ratio",
                            "description": "Cache hit ratio is {{ $value | humanizePercentage }} which is below 70%"
                        }
                    }
                ]
            }
        ]
    }
    
    return rules


def create_alertmanager_config() -> Dict[str, Any]:
    """Create Alertmanager configuration."""
    
    config = {
        "global": {
            "smtp_smarthost": "localhost:587",
            "smtp_from": "alerts@pyairtable.example.com"
        },
        "route": {
            "group_by": ["alertname"],
            "group_wait": "10s",
            "group_interval": "10s",
            "repeat_interval": "1h",
            "receiver": "web.hook"
        },
        "receivers": [
            {
                "name": "web.hook",
                "slack_configs": [
                    {
                        "api_url": "YOUR_SLACK_WEBHOOK_URL",
                        "channel": "#alerts",
                        "title": "PyAirtable Alert",
                        "text": "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}"
                    }
                ]
            }
        ],
        "inhibit_rules": [
            {
                "source_match": {
                    "severity": "critical"
                },
                "target_match": {
                    "severity": "warning"
                },
                "equal": ["alertname", "service"]
            }
        ]
    }
    
    return config


def export_monitoring_configs(output_dir: str = "./monitoring"):
    """Export all monitoring configurations to files."""
    import os
    import json
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/grafana/provisioning/datasources", exist_ok=True)
    os.makedirs(f"{output_dir}/grafana/provisioning/dashboards", exist_ok=True)
    os.makedirs(f"{output_dir}/grafana/dashboards", exist_ok=True)
    
    # Export Prometheus config
    prometheus_config = create_prometheus_config()
    with open(f"{output_dir}/prometheus.yml", 'w') as f:
        yaml.dump(prometheus_config, f, default_flow_style=False)
    
    # Export Docker Compose
    compose_config = create_docker_compose_monitoring()
    with open(f"{output_dir}/docker-compose.monitoring.yml", 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False)
    
    # Export Grafana provisioning
    provisioning = create_grafana_provisioning_config()
    
    with open(f"{output_dir}/grafana/provisioning/datasources/datasources.yml", 'w') as f:
        yaml.dump(provisioning["datasources"], f, default_flow_style=False)
    
    with open(f"{output_dir}/grafana/provisioning/dashboards/dashboards.yml", 'w') as f:
        yaml.dump(provisioning["dashboards"], f, default_flow_style=False)
    
    # Export alerting rules
    alerting_rules = create_alerting_rules()
    with open(f"{output_dir}/alerts.yml", 'w') as f:
        yaml.dump(alerting_rules, f, default_flow_style=False)
    
    # Export Alertmanager config
    alertmanager_config = create_alertmanager_config()
    with open(f"{output_dir}/alertmanager.yml", 'w') as f:
        yaml.dump(alertmanager_config, f, default_flow_style=False)
    
    # Export Grafana dashboards
    from .grafana_dashboards import DASHBOARD_CONFIGS
    
    for dashboard_name, dashboard_func in DASHBOARD_CONFIGS.items():
        dashboard_config = dashboard_func()
        with open(f"{output_dir}/grafana/dashboards/{dashboard_name}.json", 'w') as f:
            json.dump(dashboard_config, f, indent=2)
    
    print(f"Exported monitoring configurations to {output_dir}")


def create_deployment_instructions() -> str:
    """Create deployment instructions for the monitoring stack."""
    
    instructions = '''
# PyAirtable Monitoring Stack Deployment

## Prerequisites
- Docker and Docker Compose installed
- PyAirtable services configured with metrics endpoints

## Deployment Steps

1. Export monitoring configurations:
```bash
python -c "
from pyairtable_common.metrics.docker_configs import export_monitoring_configs
export_monitoring_configs('./monitoring')
"
```

2. Create Docker network:
```bash
docker network create pyairtable-network
```

3. Start monitoring stack:
```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

4. Verify services:
```bash
# Check Prometheus
curl http://localhost:9090/-/healthy

# Check Grafana
curl http://localhost:3000/api/health
```

5. Access dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Alertmanager: http://localhost:9093

## Configuration

### Grafana
- Login: admin/admin (change on first login)
- Dashboards are automatically provisioned
- Data source (Prometheus) is pre-configured

### Prometheus
- Scrapes all PyAirtable services on /metrics endpoint
- Retention: 200 hours
- Alerting rules included

### Alertmanager
- Configure Slack webhook in alertmanager.yml
- Alerts sent to #alerts channel

## Service Integration

Ensure your PyAirtable services expose metrics:

```python
from pyairtable_common.metrics.examples import create_service_with_full_metrics

app = create_service_with_full_metrics(
    service_name="my-service-py",
    version="1.0.0"
)
```

## Monitoring

Key metrics to monitor:
- Service availability (up metric)
- Request rate and latency
- Error rates
- Airtable API usage and rate limits
- Cache hit ratios
- Circuit breaker states

## Troubleshooting

1. Services not appearing in Prometheus:
   - Check service health endpoints
   - Verify Docker network connectivity
   - Check Prometheus targets page

2. Grafana dashboards empty:
   - Verify Prometheus data source
   - Check time range settings
   - Ensure services are generating metrics

3. Alerts not firing:
   - Check alert rules in Prometheus
   - Verify Alertmanager configuration
   - Check webhook URLs
'''
    
    return instructions


def get_monitoring_summary() -> Dict[str, str]:
    """Get summary of monitoring components."""
    return {
        "prometheus": "Metrics collection and alerting - Port 9090",
        "grafana": "Dashboards and visualization - Port 3000",
        "redis-exporter": "Redis metrics exporter - Port 9121", 
        "alertmanager": "Alert routing and notification - Port 9093",
        "dashboards": "6 pre-configured dashboards for different views",
        "alerts": "6 alerting rules for key SLAs and issues",
        "network": "All services connected via pyairtable-network"
    }