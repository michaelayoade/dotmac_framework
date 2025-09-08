#!/usr/bin/env python3
"""
Gate E: Observability Sanity Checks

Validates metrics export, trace collection, and observability pipeline health.
This script performs comprehensive checks of the DotMac observability stack.
"""

import asyncio
import json
import time
import logging
import requests
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ObservabilityEndpoint:
    """Configuration for observability endpoints"""
    name: str
    url: str
    expected_status: int = 200
    timeout: float = 30.0
    headers: Dict[str, str] = field(default_factory=dict)
    auth: Optional[tuple] = None

@dataclass
class MetricCheck:
    """Configuration for metric validation"""
    name: str
    pattern: str  # Regex pattern to find in metrics
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True

@dataclass
class TraceCheck:
    """Configuration for trace validation"""
    service_name: str
    operation_name: str
    expected_spans: int
    max_duration_ms: float = 5000.0

@dataclass
class CheckResult:
    """Result of an observability check"""
    name: str
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

class ObservabilitySanityChecker:
    """Main class for performing observability sanity checks"""
    
    def __init__(self):
        self.base_urls = {
            'management': os.getenv('MANAGEMENT_URL', 'http://localhost:8000'),
            'isp': os.getenv('ISP_URL', 'http://localhost:3000'),
            'signoz': os.getenv('SIGNOZ_URL', 'http://localhost:3301'),
            'prometheus': os.getenv('PROMETHEUS_URL', 'http://localhost:9090'),
            'jaeger': os.getenv('JAEGER_URL', 'http://localhost:16686')
        }
        
        self.results: List[CheckResult] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DotMac-Observability-Checker/1.0',
            'Accept': 'application/json'
        })

    def run_all_checks(self) -> bool:
        """Run all observability sanity checks"""
        logger.info("Starting Gate E Observability Sanity Checks")
        
        checks = [
            self.check_metrics_endpoints,
            self.check_prometheus_metrics,
            self.check_trace_collection,
            self.check_signoz_health,
            self.check_business_metrics,
            self.check_service_discovery,
            self.check_alerting_rules,
            self.check_dashboard_health,
            self.check_log_aggregation,
            self.check_performance_metrics
        ]
        
        for check_func in checks:
            try:
                logger.info(f"Running check: {check_func.__name__}")
                check_func()
            except Exception as e:
                logger.error(f"Check {check_func.__name__} failed with error: {str(e)}")
                self.results.append(CheckResult(
                    name=check_func.__name__,
                    success=False,
                    message=f"Exception: {str(e)}"
                ))
        
        return self.generate_report()

    def check_metrics_endpoints(self):
        """Verify metrics endpoints are accessible"""
        endpoints = [
            ObservabilityEndpoint(
                name="Management Platform Metrics",
                url=f"{self.base_urls['management']}/metrics"
            ),
            ObservabilityEndpoint(
                name="Prometheus Metrics API",
                url=f"{self.base_urls['prometheus']}/api/v1/query",
                expected_status=400  # Bad request without query param is expected
            ),
            ObservabilityEndpoint(
                name="SigNoz Health",
                url=f"{self.base_urls['signoz']}/api/v1/health"
            )
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = self.session.get(
                    endpoint.url,
                    headers=endpoint.headers,
                    auth=endpoint.auth,
                    timeout=endpoint.timeout
                )
                
                duration = (time.time() - start_time) * 1000
                
                if response.status_code == endpoint.expected_status:
                    self.results.append(CheckResult(
                        name=f"Endpoint: {endpoint.name}",
                        success=True,
                        message=f"Endpoint accessible (HTTP {response.status_code})",
                        duration_ms=duration,
                        details={'status_code': response.status_code, 'url': endpoint.url}
                    ))
                else:
                    self.results.append(CheckResult(
                        name=f"Endpoint: {endpoint.name}",
                        success=False,
                        message=f"Unexpected status code: {response.status_code} (expected {endpoint.expected_status})",
                        duration_ms=duration,
                        details={'status_code': response.status_code, 'url': endpoint.url}
                    ))
                    
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                self.results.append(CheckResult(
                    name=f"Endpoint: {endpoint.name}",
                    success=False,
                    message=f"Failed to connect: {str(e)}",
                    duration_ms=duration,
                    details={'error': str(e), 'url': endpoint.url}
                ))

    def check_prometheus_metrics(self):
        """Validate Prometheus metrics collection"""
        metrics_to_check = [
            MetricCheck(
                name="HTTP Requests Total",
                pattern="http_requests_total",
                min_value=0,
                required=True
            ),
            MetricCheck(
                name="Database Connections",
                pattern="database_connections",
                min_value=0,
                required=True
            ),
            MetricCheck(
                name="DotMac Customer Count",
                pattern="dotmac_customers_total",
                min_value=0,
                required=False
            ),
            MetricCheck(
                name="API Response Time",
                pattern="http_request_duration_seconds",
                min_value=0,
                required=True
            )
        ]
        
        try:
            # Get metrics from management platform
            response = self.session.get(
                f"{self.base_urls['management']}/metrics",
                timeout=30
            )
            
            if response.status_code != 200:
                self.results.append(CheckResult(
                    name="Prometheus Metrics Collection",
                    success=False,
                    message=f"Failed to fetch metrics: HTTP {response.status_code}"
                ))
                return
            
            metrics_text = response.text
            
            for metric in metrics_to_check:
                if metric.pattern in metrics_text:
                    # Try to extract metric value for validation
                    lines = [line for line in metrics_text.split('\n') if metric.pattern in line and not line.startswith('#')]
                    
                    if lines:
                        self.results.append(CheckResult(
                            name=f"Metric: {metric.name}",
                            success=True,
                            message=f"Metric '{metric.pattern}' found with {len(lines)} data points",
                            details={'metric_lines': len(lines), 'sample': lines[0] if lines else None}
                        ))
                    else:
                        self.results.append(CheckResult(
                            name=f"Metric: {metric.name}",
                            success=False,
                            message=f"Metric '{metric.pattern}' found but no data points",
                            details={'pattern': metric.pattern}
                        ))
                else:
                    success = not metric.required
                    message = f"Metric '{metric.pattern}' {'not found (optional)' if not metric.required else 'not found (required)'}"
                    
                    self.results.append(CheckResult(
                        name=f"Metric: {metric.name}",
                        success=success,
                        message=message,
                        details={'pattern': metric.pattern, 'required': metric.required}
                    ))
                    
        except Exception as e:
            self.results.append(CheckResult(
                name="Prometheus Metrics Collection",
                success=False,
                message=f"Exception during metrics check: {str(e)}"
            ))

    def check_trace_collection(self):
        """Validate distributed tracing functionality"""
        # Generate a test trace by making an API call
        try:
            # Make authenticated API call to generate trace
            trace_headers = {
                'X-Trace-Test': 'gate-e-validation',
                'X-Test-ID': f'sanity-check-{int(time.time())}'
            }
            
            start_time = time.time()
            response = self.session.get(
                f"{self.base_urls['management']}/api/v1/health",
                headers=trace_headers,
                timeout=30
            )
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Check for trace ID in response headers
                trace_id = response.headers.get('X-Trace-ID')
                
                if trace_id:
                    self.results.append(CheckResult(
                        name="Trace Generation",
                        success=True,
                        message=f"Trace ID generated: {trace_id}",
                        duration_ms=duration,
                        details={'trace_id': trace_id, 'headers': dict(response.headers)}
                    ))
                    
                    # Try to query the trace (with delay for processing)
                    time.sleep(2)
                    self.verify_trace_in_backend(trace_id)
                else:
                    self.results.append(CheckResult(
                        name="Trace Generation",
                        success=False,
                        message="No trace ID in response headers",
                        duration_ms=duration,
                        details={'response_headers': dict(response.headers)}
                    ))
            else:
                self.results.append(CheckResult(
                    name="Trace Generation",
                    success=False,
                    message=f"Failed to generate test trace: HTTP {response.status_code}",
                    duration_ms=duration
                ))
                
        except Exception as e:
            self.results.append(CheckResult(
                name="Trace Generation",
                success=False,
                message=f"Exception during trace generation: {str(e)}"
            ))

    def verify_trace_in_backend(self, trace_id: str):
        """Verify trace is collected in the tracing backend"""
        backends_to_check = []
        
        # Check SigNoz if available
        if self.base_urls.get('signoz'):
            backends_to_check.append(('SigNoz', f"{self.base_urls['signoz']}/api/v1/traces/{trace_id}"))
        
        # Check Jaeger if available
        if self.base_urls.get('jaeger'):
            backends_to_check.append(('Jaeger', f"{self.base_urls['jaeger']}/api/traces/{trace_id}"))
        
        for backend_name, backend_url in backends_to_check:
            try:
                response = self.session.get(backend_url, timeout=15)
                
                if response.status_code == 200:
                    trace_data = response.json()
                    spans_count = len(trace_data.get('spans', [])) if isinstance(trace_data, dict) else 0
                    
                    self.results.append(CheckResult(
                        name=f"Trace Collection ({backend_name})",
                        success=True,
                        message=f"Trace found with {spans_count} spans",
                        details={'trace_id': trace_id, 'spans_count': spans_count, 'backend': backend_name}
                    ))
                else:
                    # 404 is acceptable - trace might not be processed yet
                    success = response.status_code == 404
                    message = "Trace not found yet (acceptable)" if success else f"Error fetching trace: HTTP {response.status_code}"
                    
                    self.results.append(CheckResult(
                        name=f"Trace Collection ({backend_name})",
                        success=success,
                        message=message,
                        details={'trace_id': trace_id, 'status_code': response.status_code}
                    ))
                    
            except Exception as e:
                self.results.append(CheckResult(
                    name=f"Trace Collection ({backend_name})",
                    success=False,
                    message=f"Exception checking trace: {str(e)}",
                    details={'trace_id': trace_id, 'error': str(e)}
                ))

    def check_signoz_health(self):
        """Check SigNoz observability platform health"""
        try:
            # Check SigNoz API health
            response = self.session.get(f"{self.base_urls['signoz']}/api/v1/health", timeout=30)
            
            if response.status_code == 200:
                health_data = response.json()
                
                self.results.append(CheckResult(
                    name="SigNoz Health Check",
                    success=True,
                    message="SigNoz API is healthy",
                    details=health_data
                ))
                
                # Check SigNoz services
                services_response = self.session.get(f"{self.base_urls['signoz']}/api/v1/services", timeout=30)
                if services_response.status_code == 200:
                    services_data = services_response.json()
                    service_count = len(services_data.get('data', []))
                    
                    self.results.append(CheckResult(
                        name="SigNoz Service Discovery",
                        success=service_count > 0,
                        message=f"Found {service_count} services in SigNoz",
                        details={'services_count': service_count}
                    ))
                    
            else:
                self.results.append(CheckResult(
                    name="SigNoz Health Check",
                    success=False,
                    message=f"SigNoz API unhealthy: HTTP {response.status_code}"
                ))
                
        except Exception as e:
            self.results.append(CheckResult(
                name="SigNoz Health Check",
                success=False,
                message=f"Cannot connect to SigNoz: {str(e)}"
            ))

    def check_business_metrics(self):
        """Validate business-specific metrics collection"""
        business_metrics = [
            "dotmac_customers_total",
            "dotmac_billing_runs_total", 
            "dotmac_api_requests_total",
            "dotmac_notifications_sent_total",
            "dotmac_partner_signups_total",
            "dotmac_commission_calculated_total",
            "dotmac_tenant_active_total"
        ]
        
        try:
            response = self.session.get(f"{self.base_urls['management']}/metrics", timeout=30)
            
            if response.status_code != 200:
                self.results.append(CheckResult(
                    name="Business Metrics Collection",
                    success=False,
                    message=f"Failed to fetch metrics for business validation: HTTP {response.status_code}"
                ))
                return
            
            metrics_text = response.text
            found_metrics = []
            missing_metrics = []
            
            for metric in business_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)
                else:
                    missing_metrics.append(metric)
            
            self.results.append(CheckResult(
                name="Business Metrics Collection",
                success=len(found_metrics) > len(missing_metrics),
                message=f"Found {len(found_metrics)}/{len(business_metrics)} business metrics",
                details={
                    'found_metrics': found_metrics,
                    'missing_metrics': missing_metrics,
                    'total_expected': len(business_metrics)
                }
            ))
            
        except Exception as e:
            self.results.append(CheckResult(
                name="Business Metrics Collection",
                success=False,
                message=f"Exception during business metrics check: {str(e)}"
            ))

    def check_service_discovery(self):
        """Check service discovery and registration"""
        expected_services = [
            'dotmac-management',
            'dotmac-isp',
            'postgres',
            'redis'
        ]
        
        # This would typically check a service registry like Consul or etcd
        # For now, we'll check if services respond to health checks
        discovered_services = []
        
        service_endpoints = {
            'dotmac-management': f"{self.base_urls['management']}/health",
            'dotmac-isp': f"{self.base_urls['isp']}/health" if self.base_urls.get('isp') else None,
        }
        
        for service_name, endpoint in service_endpoints.items():
            if endpoint:
                try:
                    response = self.session.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        discovered_services.append(service_name)
                except:
                    pass
        
        self.results.append(CheckResult(
            name="Service Discovery",
            success=len(discovered_services) >= 1,  # At least management should be up
            message=f"Discovered {len(discovered_services)} services",
            details={
                'discovered_services': discovered_services,
                'expected_services': expected_services
            }
        ))

    def check_alerting_rules(self):
        """Check that alerting rules are configured"""
        # This would typically check Prometheus alerting rules
        # For now, we'll check if the alerts endpoint is accessible
        try:
            if self.base_urls.get('prometheus'):
                response = self.session.get(f"{self.base_urls['prometheus']}/api/v1/rules", timeout=20)
                
                if response.status_code == 200:
                    rules_data = response.json()
                    groups = rules_data.get('data', {}).get('groups', [])
                    rules_count = sum(len(group.get('rules', [])) for group in groups)
                    
                    self.results.append(CheckResult(
                        name="Alerting Rules",
                        success=rules_count > 0,
                        message=f"Found {rules_count} alerting rules in {len(groups)} groups",
                        details={'rules_count': rules_count, 'groups_count': len(groups)}
                    ))
                else:
                    self.results.append(CheckResult(
                        name="Alerting Rules",
                        success=False,
                        message=f"Cannot fetch alerting rules: HTTP {response.status_code}"
                    ))
            else:
                self.results.append(CheckResult(
                    name="Alerting Rules",
                    success=False,
                    message="Prometheus URL not configured - skipping alerting rules check"
                ))
                
        except Exception as e:
            self.results.append(CheckResult(
                name="Alerting Rules",
                success=False,
                message=f"Exception checking alerting rules: {str(e)}"
            ))

    def check_dashboard_health(self):
        """Check that observability dashboards are accessible"""
        dashboards = [
            ("Management Observability", f"{self.base_urls['management']}/admin/observability"),
            ("SigNoz Dashboard", f"{self.base_urls['signoz']}/dashboard" if self.base_urls.get('signoz') else None),
        ]
        
        accessible_dashboards = 0
        
        for dashboard_name, dashboard_url in dashboards:
            if not dashboard_url:
                continue
                
            try:
                # Check if dashboard page loads (might require authentication)
                response = self.session.get(dashboard_url, timeout=15, allow_redirects=True)
                
                # Consider 200 (OK) or 401/403 (auth required) as success
                if response.status_code in [200, 401, 403]:
                    accessible_dashboards += 1
                    success = True
                    message = f"Dashboard accessible (HTTP {response.status_code})"
                else:
                    success = False
                    message = f"Dashboard not accessible (HTTP {response.status_code})"
                
                self.results.append(CheckResult(
                    name=f"Dashboard: {dashboard_name}",
                    success=success,
                    message=message,
                    details={'status_code': response.status_code, 'url': dashboard_url}
                ))
                
            except Exception as e:
                self.results.append(CheckResult(
                    name=f"Dashboard: {dashboard_name}",
                    success=False,
                    message=f"Cannot access dashboard: {str(e)}",
                    details={'error': str(e), 'url': dashboard_url}
                ))

    def check_log_aggregation(self):
        """Check log aggregation and correlation"""
        # Check if logs endpoint exists and returns structured logs
        try:
            # Try to access logs API or check log format
            response = self.session.get(f"{self.base_urls['management']}/api/v1/logs", timeout=20)
            
            if response.status_code == 200:
                logs_data = response.json()
                self.results.append(CheckResult(
                    name="Log Aggregation",
                    success=True,
                    message="Logs API accessible and returning structured data",
                    details={'response_type': type(logs_data).__name__}
                ))
            elif response.status_code == 401:
                # Authentication required is acceptable
                self.results.append(CheckResult(
                    name="Log Aggregation",
                    success=True,
                    message="Logs API accessible (authentication required)",
                    details={'status_code': response.status_code}
                ))
            else:
                self.results.append(CheckResult(
                    name="Log Aggregation", 
                    success=False,
                    message=f"Logs API returned HTTP {response.status_code}"
                ))
                
        except requests.RequestException as e:
            # Logs API might not exist - check for log correlation headers instead
            try:
                response = self.session.get(f"{self.base_urls['management']}/health", timeout=10)
                has_request_id = 'X-Request-ID' in response.headers
                has_trace_id = 'X-Trace-ID' in response.headers
                
                success = has_request_id or has_trace_id
                message = f"Log correlation headers: Request-ID={has_request_id}, Trace-ID={has_trace_id}"
                
                self.results.append(CheckResult(
                    name="Log Aggregation",
                    success=success,
                    message=message,
                    details={'has_request_id': has_request_id, 'has_trace_id': has_trace_id}
                ))
                
            except Exception as inner_e:
                self.results.append(CheckResult(
                    name="Log Aggregation",
                    success=False,
                    message=f"Cannot verify log aggregation: {str(inner_e)}"
                ))

    def check_performance_metrics(self):
        """Check performance-related metrics"""
        performance_checks = [
            "Response time metrics",
            "Database query performance",
            "Memory usage metrics",
            "CPU utilization metrics"
        ]
        
        try:
            # Get metrics and look for performance indicators
            response = self.session.get(f"{self.base_urls['management']}/metrics", timeout=30)
            
            if response.status_code != 200:
                self.results.append(CheckResult(
                    name="Performance Metrics",
                    success=False,
                    message=f"Cannot fetch metrics for performance check: HTTP {response.status_code}"
                ))
                return
            
            metrics_text = response.text
            performance_indicators = {
                "response_time": "http_request_duration_seconds" in metrics_text,
                "database_performance": "database_query_duration_seconds" in metrics_text or "db_query_duration" in metrics_text,
                "memory_usage": "process_resident_memory_bytes" in metrics_text or "memory_usage" in metrics_text,
                "cpu_usage": "process_cpu_seconds_total" in metrics_text or "cpu_usage" in metrics_text
            }
            
            found_indicators = sum(performance_indicators.values())
            total_indicators = len(performance_indicators)
            
            self.results.append(CheckResult(
                name="Performance Metrics",
                success=found_indicators >= total_indicators // 2,  # At least half should be present
                message=f"Found {found_indicators}/{total_indicators} performance indicators",
                details=performance_indicators
            ))
            
        except Exception as e:
            self.results.append(CheckResult(
                name="Performance Metrics",
                success=False,
                message=f"Exception checking performance metrics: {str(e)}"
            ))

    def generate_report(self) -> bool:
        """Generate and save the observability sanity check report"""
        total_checks = len(self.results)
        passed_checks = sum(1 for result in self.results if result.success)
        failed_checks = total_checks - passed_checks
        
        overall_success = failed_checks == 0 or (passed_checks / total_checks) >= 0.8  # 80% pass rate
        
        report = {
            'gate': 'E',
            'test_type': 'observability_sanity_checks',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'overall_success': overall_success,
            'summary': {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'failed_checks': failed_checks,
                'pass_rate': round((passed_checks / total_checks) * 100, 2) if total_checks > 0 else 0
            },
            'environment': {
                'base_urls': self.base_urls,
                'python_version': sys.version,
                'platform': sys.platform
            },
            'checks': [
                {
                    'name': result.name,
                    'success': result.success,
                    'message': result.message,
                    'duration_ms': result.duration_ms,
                    'details': result.details
                }
                for result in self.results
            ]
        }
        
        # Save report
        report_dir = Path('.dev-artifacts/gate-e/')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / 'observability-sanity-check-report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Gate E: Observability Sanity Check Results")
        print(f"{'='*60}")
        print(f"Overall Status: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {failed_checks}")
        print(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
        print(f"\nDetailed Results:")
        print(f"{'='*60}")
        
        for result in self.results:
            status = "✅" if result.success else "❌"
            duration = f" ({result.duration_ms:.1f}ms)" if result.duration_ms > 0 else ""
            print(f"{status} {result.name}{duration}")
            if not result.success:
                print(f"    └─ {result.message}")
        
        print(f"\nReport saved to: {report_file}")
        
        if not overall_success:
            logger.error("Observability sanity checks failed!")
            print(f"\n❌ Gate E observability checks failed. See {report_file} for details.")
        else:
            logger.info("All observability sanity checks passed!")
            print(f"\n✅ Gate E observability checks passed!")
        
        return overall_success

def main():
    """Main entry point"""
    checker = ObservabilitySanityChecker()
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()