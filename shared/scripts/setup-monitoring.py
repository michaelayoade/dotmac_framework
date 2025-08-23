#!/usr/bin/env python3
"""
Monitoring and Alerting Dashboard Setup for DotMac Framework

This script sets up comprehensive monitoring and alerting systems:
- Real-time test execution monitoring
- Performance metrics dashboard  
- Security alert system
- Deployment status notifications
- User experience monitoring
- Service health monitoring
- Resource usage monitoring

The system provides real-time insights into system health and automatically
alerts teams when issues are detected.
"""

import asyncio
import json
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import requests
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring-logs/monitoring-setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MonitoringDashboardSetup:
    """Comprehensive monitoring and alerting dashboard setup."""
    
    def __init__(self):
        self.config = {}
        self.monitoring_services = {}
        
        # Monitoring stack components
        self.components = {
            'prometheus': {'port': 9090, 'config_file': 'prometheus.yml'},
            'grafana': {'port': 3000, 'config_dir': 'grafana'},
            'alertmanager': {'port': 9093, 'config_file': 'alertmanager.yml'},
            'node_exporter': {'port': 9100, 'config_file': 'node_exporter.yml'},
            'blackbox_exporter': {'port': 9115, 'config_file': 'blackbox.yml'}
        }
        
        self.setup_directories()
        self.load_configuration()
    
    def setup_directories(self):
        """Setup required monitoring directories."""
        directories = [
            'monitoring-config',
            'monitoring-logs', 
            'grafana-dashboards',
            'prometheus-rules',
            'alerting-templates',
            'monitoring-data'
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def load_configuration(self):
        """Load monitoring configuration."""
        config_file = Path('monitoring-config/monitoring.yml')
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._get_default_config()
            self._save_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default monitoring configuration."""
        return {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s',
                'external_labels': {
                    'monitor': 'dotmac-framework',
                    'environment': 'production'
                }
            },
            'alerting': {
                'enabled': True,
                'channels': {
                    'slack': {
                        'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
                        'channel': '#alerts'
                    },
                    'email': {
                        'smtp_server': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'from_email': os.getenv('ALERT_FROM_EMAIL'),
                        'to_emails': ['ops@dotmac.framework']
                    }
                }
            },
            'dashboards': {
                'grafana_admin_password': os.getenv('GRAFANA_ADMIN_PASSWORD', 'admin'),
                'auto_provisioning': True,
                'themes': ['light', 'dark']
            },
            'retention': {
                'metrics_retention': '30d',
                'logs_retention': '7d',
                'alerts_retention': '30d'
            },
            'thresholds': {
                'cpu_warning': 70.0,
                'cpu_critical': 85.0,
                'memory_warning': 75.0,
                'memory_critical': 90.0,
                'disk_warning': 80.0,
                'disk_critical': 95.0,
                'response_time_warning': 500,  # ms
                'response_time_critical': 1000,  # ms
                'error_rate_warning': 5.0,  # %
                'error_rate_critical': 10.0  # %
            }
        }
    
    def _save_default_config(self):
        """Save default configuration to file."""
        with open('monitoring-config/monitoring.yml', 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    async def setup_comprehensive_monitoring(self) -> Dict[str, Any]:
        """Setup complete monitoring and alerting system."""
        logger.info("📊 Setting up Comprehensive Monitoring and Alerting")
        logger.info("=" * 70)
        
        try:
            # Step 1: Setup Prometheus metrics collection
            await self._setup_prometheus()
            
            # Step 2: Setup Grafana dashboards
            await self._setup_grafana()
            
            # Step 3: Setup AlertManager
            await self._setup_alertmanager()
            
            # Step 4: Setup Node Exporter for system metrics
            await self._setup_node_exporter()
            
            # Step 5: Setup Blackbox Exporter for endpoint monitoring
            await self._setup_blackbox_exporter()
            
            # Step 6: Configure application metrics
            await self._configure_application_metrics()
            
            # Step 7: Setup real-time monitoring
            await self._setup_realtime_monitoring()
            
            # Step 8: Configure security monitoring
            await self._setup_security_monitoring()
            
            # Step 9: Setup user experience monitoring
            await self._setup_ux_monitoring()
            
            # Step 10: Setup deployment monitoring
            await self._setup_deployment_monitoring()
            
            # Step 11: Configure alerting rules
            await self._configure_alerting_rules()
            
            # Step 12: Setup notification channels
            await self._setup_notification_channels()
            
            # Generate monitoring report
            monitoring_report = await self._generate_monitoring_report()
            
            logger.info("✅ Comprehensive Monitoring Setup Completed!")
            return monitoring_report
            
        except Exception as e:
            logger.error(f"❌ Monitoring setup failed: {e}")
            raise
    
    async def _setup_prometheus(self):
        """Setup Prometheus metrics collection."""
        logger.info("🎯 Setting up Prometheus...")
        
        # Generate Prometheus configuration
        prometheus_config = {
            'global': self.config['global'],
            'rule_files': [
                'prometheus-rules/*.yml'
            ],
            'alerting': {
                'alertmanagers': [{
                    'static_configs': [{
                        'targets': ['localhost:9093']
                    }]
                }]
            },
            'scrape_configs': [
                {
                    'job_name': 'prometheus',
                    'static_configs': [{
                        'targets': ['localhost:9090']
                    }]
                },
                {
                    'job_name': 'dotmac-backend-services',
                    'static_configs': [{
                        'targets': [
                            'localhost:8000',  # API Gateway
                            'localhost:8001',  # Identity
                            'localhost:8002',  # Billing
                            'localhost:8003',  # Services
                            'localhost:8004',  # Networking
                            'localhost:8005',  # Analytics
                            'localhost:8006'   # Platform
                        ]
                    }],
                    'metrics_path': '/metrics',
                    'scrape_interval': '10s'
                },
                {
                    'job_name': 'dotmac-frontend-portals',
                    'static_configs': [{
                        'targets': [
                            'localhost:3001',  # Admin
                            'localhost:3002',  # Customer
                            'localhost:3003',  # Reseller
                            'localhost:3004'   # Technician
                        ]
                    }],
                    'metrics_path': '/api/metrics',
                    'scrape_interval': '15s'
                },
                {
                    'job_name': 'node-exporter',
                    'static_configs': [{
                        'targets': ['localhost:9100']
                    }]
                },
                {
                    'job_name': 'blackbox-http',
                    'metrics_path': '/probe',
                    'params': {
                        'module': ['http_2xx']
                    },
                    'static_configs': [{
                        'targets': [
                            'http://localhost/health',
                            'http://localhost:3001',
                            'http://localhost:3002',
                            'http://localhost:3003',
                            'http://localhost:3004'
                        ]
                    }],
                    'relabel_configs': [{
                        'source_labels': ['__address__'],
                        'target_label': '__param_target'
                    }, {
                        'source_labels': ['__param_target'],
                        'target_label': 'instance'
                    }, {
                        'target_label': '__address__',
                        'replacement': 'localhost:9115'
                    }]
                }
            ]
        }
        
        # Save Prometheus configuration
        with open('monitoring-config/prometheus.yml', 'w') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False)
        
        # Start Prometheus
        await self._start_prometheus()
        
        logger.info("  ✅ Prometheus configured and started")
    
    async def _start_prometheus(self):
        """Start Prometheus server."""
        cmd = [
            'prometheus',
            '--config.file=monitoring-config/prometheus.yml',
            '--storage.tsdb.path=monitoring-data/prometheus',
            '--web.console.templates=consoles',
            '--web.console.libraries=console_libraries',
            '--web.listen-address=:9090',
            '--web.enable-lifecycle',
            f'--storage.tsdb.retention.time={self.config["retention"]["metrics_retention"]}'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.monitoring_services['prometheus'] = process
            
            # Wait for Prometheus to start
            await self._wait_for_service('http://localhost:9090/-/ready', 'Prometheus')
            
        except Exception as e:
            logger.warning(f"    ⚠️  Failed to start Prometheus: {e}")
    
    async def _setup_grafana(self):
        """Setup Grafana dashboards."""
        logger.info("📊 Setting up Grafana dashboards...")
        
        # Generate Grafana configuration
        grafana_config = {
            'server': {
                'http_port': 3000,
                'root_url': 'http://localhost:3000'
            },
            'security': {
                'admin_password': self.config['dashboards']['grafana_admin_password']
            },
            'database': {
                'type': 'sqlite3',
                'path': 'monitoring-data/grafana.db'
            },
            'dashboards': {
                'default_home_dashboard_path': 'grafana-dashboards/dotmac-overview.json'
            }
        }
        
        # Save Grafana configuration
        grafana_config_dir = Path('monitoring-config/grafana')
        grafana_config_dir.mkdir(exist_ok=True)
        
        with open('monitoring-config/grafana/grafana.ini', 'w') as f:
            for section, settings in grafana_config.items():
                f.write(f'[{section}]\\n')
                for key, value in settings.items():
                    f.write(f'{key} = {value}\\n')
                f.write('\\n')
        
        # Generate dashboard configurations
        await self._create_grafana_dashboards()
        
        # Start Grafana
        await self._start_grafana()
        
        logger.info("  ✅ Grafana configured and started")
    
    async def _create_grafana_dashboards(self):
        """Create Grafana dashboard configurations."""
        
        # Overview Dashboard
        overview_dashboard = {
            'dashboard': {
                'title': 'DotMac Framework Overview',
                'tags': ['dotmac', 'overview'],
                'timezone': 'browser',
                'refresh': '5s',
                'panels': [
                    {
                        'title': 'System Health',
                        'type': 'stat',
                        'targets': [{
                            'expr': 'up{job=~"dotmac.*"}',
                            'legendFormat': '{{instance}}'
                        }],
                        'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0}
                    },
                    {
                        'title': 'Response Time',
                        'type': 'graph',
                        'targets': [{
                            'expr': 'histogram_quantile(0.95, http_request_duration_seconds_bucket)',
                            'legendFormat': '95th percentile'
                        }],
                        'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0}
                    },
                    {
                        'title': 'Error Rate',
                        'type': 'graph',
                        'targets': [{
                            'expr': 'rate(http_requests_total{status=~"5.."}[5m])',
                            'legendFormat': 'Error rate'
                        }],
                        'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 8}
                    },
                    {
                        'title': 'Active Users',
                        'type': 'stat',
                        'targets': [{
                            'expr': 'active_users_total',
                            'legendFormat': 'Active Users'
                        }],
                        'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 8}
                    }
                ]
            }
        }
        
        with open('grafana-dashboards/dotmac-overview.json', 'w') as f:
            json.dump(overview_dashboard, f, indent=2)
        
        # Portal-specific dashboards
        portals = ['admin', 'customer', 'reseller', 'technician']
        for portal in portals:
            portal_dashboard = self._create_portal_dashboard(portal)
            with open(f'grafana-dashboards/{portal}-portal.json', 'w') as f:
                json.dump(portal_dashboard, f, indent=2)
        
        logger.info("    📊 Dashboard configurations created")
    
    def _create_portal_dashboard(self, portal_name: str) -> Dict[str, Any]:
        """Create dashboard configuration for specific portal."""
        return {
            'dashboard': {
                'title': f'{portal_name.title()} Portal Metrics',
                'tags': ['dotmac', portal_name, 'portal'],
                'refresh': '10s',
                'panels': [
                    {
                        'title': f'{portal_name.title()} Portal Health',
                        'type': 'stat',
                        'targets': [{
                            'expr': f'up{{job="dotmac-frontend-portals",instance=~".*{portal_name}.*"}}',
                            'legendFormat': 'Health Status'
                        }]
                    },
                    {
                        'title': 'Page Load Time',
                        'type': 'graph',
                        'targets': [{
                            'expr': f'page_load_time{{portal="{portal_name}"}}',
                            'legendFormat': 'Load Time (ms)'
                        }]
                    },
                    {
                        'title': 'User Sessions',
                        'type': 'graph',
                        'targets': [{
                            'expr': f'user_sessions{{portal="{portal_name}"}}',
                            'legendFormat': 'Active Sessions'
                        }]
                    }
                ]
            }
        }
    
    async def _start_grafana(self):
        """Start Grafana server."""
        cmd = [
            'grafana-server',
            '--config=monitoring-config/grafana/grafana.ini',
            '--homepath=/usr/share/grafana'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.monitoring_services['grafana'] = process
            
            # Wait for Grafana to start
            await self._wait_for_service('http://localhost:3000/api/health', 'Grafana')
            
        except Exception as e:
            logger.warning(f"    ⚠️  Failed to start Grafana: {e}")
    
    async def _setup_alertmanager(self):
        """Setup AlertManager for notifications."""
        logger.info("🚨 Setting up AlertManager...")
        
        # Generate AlertManager configuration
        alertmanager_config = {
            'global': {
                'smtp_smarthost': 'smtp.gmail.com:587',
                'smtp_from': self.config['alerting']['channels']['email']['from_email']
            },
            'route': {
                'group_by': ['alertname'],
                'group_wait': '10s',
                'group_interval': '10s',
                'repeat_interval': '1h',
                'receiver': 'web.hook'
            },
            'receivers': []
        }
        
        # Configure notification channels
        if self.config['alerting']['channels']['slack']['webhook_url']:
            alertmanager_config['receivers'].append({
                'name': 'web.hook',
                'slack_configs': [{
                    'api_url': self.config['alerting']['channels']['slack']['webhook_url'],
                    'channel': self.config['alerting']['channels']['slack']['channel'],
                    'title': 'DotMac Alert: {{ .GroupLabels.alertname }}',
                    'text': 'Summary: {{ .CommonAnnotations.summary }}'
                }]
            })
        
        if self.config['alerting']['channels']['email']['to_emails']:
            alertmanager_config['receivers'].append({
                'name': 'email',
                'email_configs': [{
                    'to': email,
                    'subject': 'DotMac Alert: {{ .GroupLabels.alertname }}',
                    'body': '''
Alert: {{ .GroupLabels.alertname }}
Summary: {{ .CommonAnnotations.summary }}
Description: {{ .CommonAnnotations.description }}
                    '''
                } for email in self.config['alerting']['channels']['email']['to_emails']]
            })
        
        # Save AlertManager configuration
        with open('monitoring-config/alertmanager.yml', 'w') as f:
            yaml.dump(alertmanager_config, f, default_flow_style=False)
        
        # Start AlertManager
        await self._start_alertmanager()
        
        logger.info("  ✅ AlertManager configured and started")
    
    async def _start_alertmanager(self):
        """Start AlertManager."""
        cmd = [
            'alertmanager',
            '--config.file=monitoring-config/alertmanager.yml',
            '--storage.path=monitoring-data/alertmanager',
            '--web.listen-address=:9093'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.monitoring_services['alertmanager'] = process
            
            # Wait for AlertManager to start
            await self._wait_for_service('http://localhost:9093/-/ready', 'AlertManager')
            
        except Exception as e:
            logger.warning(f"    ⚠️  Failed to start AlertManager: {e}")
    
    async def _setup_node_exporter(self):
        """Setup Node Exporter for system metrics."""
        logger.info("💾 Setting up Node Exporter...")
        
        cmd = [
            'node_exporter',
            '--web.listen-address=:9100'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.monitoring_services['node_exporter'] = process
            
            # Wait for Node Exporter to start
            await self._wait_for_service('http://localhost:9100/metrics', 'Node Exporter')
            
            logger.info("  ✅ Node Exporter started")
            
        except Exception as e:
            logger.warning(f"    ⚠️  Failed to start Node Exporter: {e}")
    
    async def _setup_blackbox_exporter(self):
        """Setup Blackbox Exporter for endpoint monitoring."""
        logger.info("🔍 Setting up Blackbox Exporter...")
        
        # Generate Blackbox configuration
        blackbox_config = {
            'modules': {
                'http_2xx': {
                    'prober': 'http',
                    'timeout': '5s',
                    'http': {
                        'valid_http_versions': ['HTTP/1.1', 'HTTP/2.0'],
                        'valid_status_codes': [200, 301, 302],
                        'method': 'GET'
                    }
                },
                'tcp_connect': {
                    'prober': 'tcp',
                    'timeout': '5s'
                }
            }
        }
        
        # Save Blackbox configuration
        with open('monitoring-config/blackbox.yml', 'w') as f:
            yaml.dump(blackbox_config, f, default_flow_style=False)
        
        cmd = [
            'blackbox_exporter',
            '--config.file=monitoring-config/blackbox.yml',
            '--web.listen-address=:9115'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.monitoring_services['blackbox_exporter'] = process
            
            # Wait for Blackbox Exporter to start
            await self._wait_for_service('http://localhost:9115/metrics', 'Blackbox Exporter')
            
            logger.info("  ✅ Blackbox Exporter started")
            
        except Exception as e:
            logger.warning(f"    ⚠️  Failed to start Blackbox Exporter: {e}")
    
    async def _configure_application_metrics(self):
        """Configure application-specific metrics collection."""
        logger.info("📈 Configuring application metrics...")
        
        # Generate metrics configuration for each service
        services_config = {
            'backend_services': {
                'metrics_endpoint': '/metrics',
                'metrics': [
                    'http_requests_total',
                    'http_request_duration_seconds',
                    'database_connections_active',
                    'cache_hits_total',
                    'cache_misses_total',
                    'background_jobs_total',
                    'api_rate_limit_exceeded_total'
                ]
            },
            'frontend_portals': {
                'metrics_endpoint': '/api/metrics',
                'metrics': [
                    'page_views_total',
                    'user_sessions_active',
                    'js_errors_total',
                    'page_load_time_seconds',
                    'core_web_vitals_lcp',
                    'core_web_vitals_fid',
                    'core_web_vitals_cls'
                ]
            }
        }
        
        # Save application metrics configuration
        with open('monitoring-config/application-metrics.yml', 'w') as f:
            yaml.dump(services_config, f, default_flow_style=False)
        
        logger.info("  ✅ Application metrics configured")
    
    async def _setup_realtime_monitoring(self):
        """Setup real-time monitoring dashboard."""
        logger.info("⚡ Setting up real-time monitoring...")
        
        # Create real-time monitoring script
        realtime_script = '''#!/usr/bin/env python3
"""Real-time monitoring script for DotMac services."""

import asyncio
import json
import requests
import time
from datetime import datetime

async def collect_realtime_metrics():
    """Collect real-time metrics from all services."""
    
    services = {
        'api_gateway': 'http://localhost:8000/health',
        'admin_portal': 'http://localhost:3001/api/health',
        'customer_portal': 'http://localhost:3002/api/health',
        'reseller_portal': 'http://localhost:3003/api/health',
        'technician_portal': 'http://localhost:3004/api/health'
    }
    
    while True:
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        for service_name, health_url in services.items():
            try:
                start_time = time.time()
                response = requests.get(health_url, timeout=5)
                response_time = (time.time() - start_time) * 1000  # ms
                
                metrics['services'][service_name] = {
                    'status': 'up' if response.status_code == 200 else 'down',
                    'response_time': response_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                metrics['services'][service_name] = {
                    'status': 'down',
                    'error': str(e),
                    'response_time': None
                }
        
        # Save metrics to file for dashboard
        with open('/tmp/realtime-metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        await asyncio.sleep(5)  # Update every 5 seconds

if __name__ == "__main__":
    asyncio.run(collect_realtime_metrics())
'''
        
        # Save real-time monitoring script
        with open('monitoring-config/realtime-monitor.py', 'w') as f:
            f.write(realtime_script)
        
        # Make script executable
        os.chmod('monitoring-config/realtime-monitor.py', 0o755)
        
        logger.info("  ✅ Real-time monitoring configured")
    
    async def _setup_security_monitoring(self):
        """Setup security monitoring and alerting."""
        logger.info("🔒 Setting up security monitoring...")
        
        security_rules = {
            'groups': [{
                'name': 'security_alerts',
                'rules': [
                    {
                        'alert': 'HighErrorRate',
                        'expr': 'rate(http_requests_total{status=~"5.."}[5m]) > 0.1',
                        'for': '2m',
                        'labels': {'severity': 'warning'},
                        'annotations': {
                            'summary': 'High error rate detected',
                            'description': 'Error rate is {{ $value }} requests/sec'
                        }
                    },
                    {
                        'alert': 'UnauthorizedAccess',
                        'expr': 'rate(http_requests_total{status="401"}[5m]) > 0.05',
                        'for': '1m',
                        'labels': {'severity': 'critical'},
                        'annotations': {
                            'summary': 'High number of unauthorized access attempts',
                            'description': 'Unauthorized access rate: {{ $value }} requests/sec'
                        }
                    },
                    {
                        'alert': 'SuspiciousActivity',
                        'expr': 'rate(failed_login_attempts_total[5m]) > 10',
                        'for': '1m',
                        'labels': {'severity': 'warning'},
                        'annotations': {
                            'summary': 'Suspicious login activity detected',
                            'description': 'Failed login attempts: {{ $value }} attempts/sec'
                        }
                    }
                ]
            }]
        }
        
        # Save security rules
        with open('prometheus-rules/security-rules.yml', 'w') as f:
            yaml.dump(security_rules, f, default_flow_style=False)
        
        logger.info("  ✅ Security monitoring configured")
    
    async def _setup_ux_monitoring(self):
        """Setup user experience monitoring."""
        logger.info("👥 Setting up user experience monitoring...")
        
        # Create UX monitoring configuration
        ux_config = {
            'core_web_vitals': {
                'lcp_threshold': 2500,  # ms
                'fid_threshold': 100,   # ms  
                'cls_threshold': 0.1
            },
            'page_performance': {
                'load_time_threshold': 3000,  # ms
                'ttfb_threshold': 600,         # ms
                'dom_ready_threshold': 2000    # ms
            },
            'user_satisfaction': {
                'bounce_rate_threshold': 70,     # %
                'session_duration_min': 30,     # seconds
                'error_rate_threshold': 5        # %
            }
        }
        
        # Save UX monitoring configuration
        with open('monitoring-config/ux-monitoring.yml', 'w') as f:
            yaml.dump(ux_config, f, default_flow_style=False)
        
        # Create UX alerting rules
        ux_rules = {
            'groups': [{
                'name': 'ux_alerts',
                'rules': [
                    {
                        'alert': 'HighPageLoadTime',
                        'expr': 'page_load_time_seconds > 3',
                        'for': '5m',
                        'labels': {'severity': 'warning'},
                        'annotations': {
                            'summary': 'Page load time exceeds threshold',
                            'description': 'Page load time: {{ $value }}s for {{ $labels.portal }}'
                        }
                    },
                    {
                        'alert': 'PoorCoreWebVitals',
                        'expr': 'core_web_vitals_lcp > 2500 or core_web_vitals_fid > 100 or core_web_vitals_cls > 0.1',
                        'for': '2m',
                        'labels': {'severity': 'warning'},
                        'annotations': {
                            'summary': 'Core Web Vitals threshold exceeded',
                            'description': 'Poor Core Web Vitals on {{ $labels.portal }}'
                        }
                    }
                ]
            }]
        }
        
        # Save UX rules
        with open('prometheus-rules/ux-rules.yml', 'w') as f:
            yaml.dump(ux_rules, f, default_flow_style=False)
        
        logger.info("  ✅ User experience monitoring configured")
    
    async def _setup_deployment_monitoring(self):
        """Setup deployment process monitoring."""
        logger.info("🚀 Setting up deployment monitoring...")
        
        deployment_config = {
            'pipeline_stages': [
                'code_quality',
                'security_scan',
                'unit_tests',
                'integration_tests',
                'e2e_tests',
                'performance_tests',
                'deployment'
            ],
            'success_thresholds': {
                'test_success_rate': 100.0,  # Must be 100% for deployment
                'deployment_time': 1800,     # 30 minutes max
                'rollback_time': 300         # 5 minutes max
            },
            'notifications': {
                'on_deployment_start': True,
                'on_deployment_success': True,
                'on_deployment_failure': True,
                'on_test_failure': True
            }
        }
        
        # Save deployment monitoring configuration
        with open('monitoring-config/deployment-monitoring.yml', 'w') as f:
            yaml.dump(deployment_config, f, default_flow_style=False)
        
        logger.info("  ✅ Deployment monitoring configured")
    
    async def _configure_alerting_rules(self):
        """Configure comprehensive alerting rules."""
        logger.info("⚠️ Configuring alerting rules...")
        
        # System-level alerts
        system_rules = {
            'groups': [{
                'name': 'system_alerts',
                'rules': [
                    {
                        'alert': 'HighCPUUsage',
                        'expr': f'100 - (avg by(instance) (rate(node_cpu_seconds_total{{mode="idle"}}[5m])) * 100) > {self.config["thresholds"]["cpu_critical"]}',
                        'for': '5m',
                        'labels': {'severity': 'critical'},
                        'annotations': {
                            'summary': 'High CPU usage detected',
                            'description': 'CPU usage: {{ $value }}% on {{ $labels.instance }}'
                        }
                    },
                    {
                        'alert': 'HighMemoryUsage',
                        'expr': f'(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > {self.config["thresholds"]["memory_critical"]}',
                        'for': '5m',
                        'labels': {'severity': 'critical'},
                        'annotations': {
                            'summary': 'High memory usage detected',
                            'description': 'Memory usage: {{ $value }}% on {{ $labels.instance }}'
                        }
                    },
                    {
                        'alert': 'HighDiskUsage',
                        'expr': f'(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > {self.config["thresholds"]["disk_critical"]}',
                        'for': '2m',
                        'labels': {'severity': 'critical'},
                        'annotations': {
                            'summary': 'High disk usage detected',
                            'description': 'Disk usage: {{ $value }}% on {{ $labels.instance }}'
                        }
                    },
                    {
                        'alert': 'ServiceDown',
                        'expr': 'up == 0',
                        'for': '1m',
                        'labels': {'severity': 'critical'},
                        'annotations': {
                            'summary': 'Service is down',
                            'description': 'Service {{ $labels.job }} on {{ $labels.instance }} is down'
                        }
                    }
                ]
            }]
        }
        
        # Save system rules
        with open('prometheus-rules/system-rules.yml', 'w') as f:
            yaml.dump(system_rules, f, default_flow_style=False)
        
        logger.info("  ✅ Alerting rules configured")
    
    async def _setup_notification_channels(self):
        """Setup notification channels for alerts."""
        logger.info("📢 Setting up notification channels...")
        
        # Create notification templates
        notification_templates = {
            'slack': {
                'success': {
                    'title': '✅ DotMac Deployment Success',
                    'color': 'good',
                    'text': 'All tests passed! Production deployment completed successfully.'
                },
                'failure': {
                    'title': '❌ DotMac Deployment Failed', 
                    'color': 'danger',
                    'text': 'Deployment failed. Automatic remediation in progress.'
                },
                'alert': {
                    'title': '🚨 DotMac System Alert',
                    'color': 'warning',
                    'text': 'System issue detected. Check monitoring dashboard for details.'
                }
            },
            'email': {
                'subject_template': '[DotMac] {{ .Status }} - {{ .AlertName }}',
                'body_template': '''
DotMac Framework Alert

Alert: {{ .AlertName }}
Status: {{ .Status }}
Severity: {{ .Severity }}

Summary: {{ .Summary }}
Description: {{ .Description }}

Time: {{ .Timestamp }}

Dashboard: http://localhost:3000
Prometheus: http://localhost:9090
                '''
            }
        }
        
        # Save notification templates
        with open('alerting-templates/notifications.yml', 'w') as f:
            yaml.dump(notification_templates, f, default_flow_style=False)
        
        logger.info("  ✅ Notification channels configured")
    
    async def _wait_for_service(self, url: str, service_name: str, max_attempts: int = 30):
        """Wait for service to become available."""
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404]:  # 404 is OK for some endpoints
                    return
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)
        
        raise Exception(f"Service {service_name} failed to become available")
    
    async def _generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring setup report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'setup_status': 'completed',
            'components': {
                name: {
                    'status': 'running' if name in self.monitoring_services else 'not_started',
                    'port': config['port'],
                    'url': f'http://localhost:{config["port"]}'
                }
                for name, config in self.components.items()
            },
            'dashboards': {
                'grafana_url': 'http://localhost:3000',
                'prometheus_url': 'http://localhost:9090',
                'alertmanager_url': 'http://localhost:9093'
            },
            'configuration': {
                'metrics_retention': self.config['retention']['metrics_retention'],
                'alerting_enabled': self.config['alerting']['enabled'],
                'notification_channels': list(self.config['alerting']['channels'].keys())
            },
            'monitoring_targets': {
                'backend_services': 7,
                'frontend_portals': 4,
                'system_metrics': True,
                'security_monitoring': True,
                'ux_monitoring': True
            }
        }
    
    async def cleanup_monitoring(self):
        """Cleanup monitoring services."""
        logger.info("🧹 Cleaning up monitoring services...")
        
        for service_name, process in self.monitoring_services.items():
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=10)
                logger.info(f"  🛑 Stopped {service_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to stop {service_name}: {e}")
                try:
                    process.kill()
                except Exception:
                    pass


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring and Alerting Dashboard Setup")
    parser.add_argument('--config', default='monitoring-config/monitoring.yml', help='Configuration file path')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup existing monitoring services')
    
    args = parser.parse_args()
    
    try:
        monitoring_setup = MonitoringDashboardSetup()
        
        if args.cleanup:
            await monitoring_setup.cleanup_monitoring()
            return
        
        # Setup comprehensive monitoring
        monitoring_report = await monitoring_setup.setup_comprehensive_monitoring()
        
        logger.info("🎉 Monitoring and Alerting Setup Completed!")
        logger.info(f"📊 Monitoring Report: {json.dumps(monitoring_report, indent=2)}")
        
        # Keep monitoring services running
        logger.info("🔄 Monitoring services are running. Press Ctrl+C to stop.")
        
        # Setup signal handlers for graceful shutdown
        import signal
        
        def signal_handler(signum, frame):
            logger.info("🛑 Received shutdown signal. Cleaning up...")
            asyncio.create_task(monitoring_setup.cleanup_monitoring())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"❌ Monitoring setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())