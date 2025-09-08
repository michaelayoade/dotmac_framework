#!/usr/bin/env python3
"""
Comprehensive Observability Analysis Tool
Analyzes all aspects of the DotMac observability stack to identify issues
"""

import os
import sys
import json
import subprocess
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConfigIssue:
    component: str
    severity: str  # critical, major, minor, warning
    issue_type: str
    description: str
    location: str
    recommended_fix: str

@dataclass
class ServiceStatus:
    name: str
    running: bool
    healthy: bool
    ports: List[str]
    image: str
    error_details: Optional[str] = None

@dataclass
class ConnectivityTest:
    source: str
    target: str
    port: int
    protocol: str
    success: bool
    response_time_ms: Optional[float] = None
    error: Optional[str] = None

class ObservabilityAnalyzer:
    def __init__(self):
        self.issues: List[ConfigIssue] = []
        self.service_status: List[ServiceStatus] = []
        self.connectivity_tests: List[ConnectivityTest] = []
        self.project_root = Path("/home/dotmac_framework")
        
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run all analysis checks"""
        logger.info("Starting comprehensive observability analysis...")
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_sections": {}
        }
        
        # 1. Configuration Analysis
        logger.info("1. Analyzing configuration files...")
        config_results = self.analyze_configurations()
        results["analysis_sections"]["configuration"] = config_results
        
        # 2. Docker Service Analysis
        logger.info("2. Analyzing Docker services...")
        docker_results = self.analyze_docker_services()
        results["analysis_sections"]["docker_services"] = docker_results
        
        # 3. Network Connectivity Analysis
        logger.info("3. Testing network connectivity...")
        network_results = self.analyze_network_connectivity()
        results["analysis_sections"]["network_connectivity"] = network_results
        
        # 4. Application Integration Analysis
        logger.info("4. Analyzing application integration...")
        app_results = self.analyze_application_integration()
        results["analysis_sections"]["application_integration"] = app_results
        
        # 5. Environment Variable Analysis
        logger.info("5. Analyzing environment configuration...")
        env_results = self.analyze_environment_variables()
        results["analysis_sections"]["environment_variables"] = env_results
        
        # 6. File System Analysis
        logger.info("6. Analyzing file system and volumes...")
        fs_results = self.analyze_file_system()
        results["analysis_sections"]["file_system"] = fs_results
        
        # Generate summary
        results["summary"] = self.generate_summary()
        
        return results
    
    def analyze_configurations(self) -> Dict[str, Any]:
        """Analyze configuration files for inconsistencies"""
        
        # Check for missing imports/classes
        self.check_missing_config_classes()
        
        # Check docker-compose configurations
        self.check_docker_compose_configs()
        
        # Check OTEL configurations
        self.check_otel_configs()
        
        # Check platform service configs
        self.check_platform_service_configs()
        
        return {
            "issues_found": len([i for i in self.issues if i.component.startswith("config")]),
            "critical_issues": len([i for i in self.issues if i.severity == "critical"]),
            "major_issues": len([i for i in self.issues if i.severity == "major"]),
            "issues": [
                {
                    "component": issue.component,
                    "severity": issue.severity,
                    "type": issue.issue_type,
                    "description": issue.description,
                    "location": issue.location,
                    "fix": issue.recommended_fix
                }
                for issue in self.issues if issue.component.startswith("config")
            ]
        }
    
    def check_missing_config_classes(self):
        """Check for missing configuration classes"""
        bootstrap_file = self.project_root / "packages/dotmac-platform-services/src/dotmac/platform/observability/bootstrap.py"
        config_file = self.project_root / "packages/dotmac-platform-services/src/dotmac/platform/observability/config.py"
        
        if bootstrap_file.exists():
            bootstrap_content = bootstrap_file.read_text()
            
            # Check for missing imports
            missing_imports = []
            if "from .config import ExporterConfig" in bootstrap_content:
                if config_file.exists():
                    config_content = config_file.read_text()
                    if "class ExporterConfig" not in config_content:
                        missing_imports.append("ExporterConfig")
                        
            if "from .config import ExporterType" in bootstrap_content:
                if config_file.exists():
                    config_content = config_file.read_text()
                    if "class ExporterType" not in config_content and "ExporterType" not in config_content:
                        missing_imports.append("ExporterType")
            
            for missing in missing_imports:
                self.issues.append(ConfigIssue(
                    component="config_classes",
                    severity="critical",
                    issue_type="missing_class",
                    description=f"Missing {missing} class in config.py but imported in bootstrap.py",
                    location=str(config_file),
                    recommended_fix=f"Add {missing} class definition to config.py or update import in bootstrap.py"
                ))
    
    def check_docker_compose_configs(self):
        """Check Docker Compose configurations"""
        main_compose = self.project_root / "docker-compose.yml"
        gate_compose = self.project_root / ".dev-artifacts/gate-e-0c/docker-compose.gate-e-0c.yml"
        
        if main_compose.exists():
            # Check for service definitions
            compose_content = main_compose.read_text()
            
            # Check observability services
            observability_services = ["clickhouse", "signoz-collector", "signoz-query", "signoz-frontend"]
            
            for service in observability_services:
                if service in compose_content:
                    # Check if ports are conflicting
                    if service == "clickhouse":
                        if "9000:9000" in compose_content and gate_compose.exists():
                            gate_content = gate_compose.read_text()
                            if "9001:9000" in gate_content:
                                self.issues.append(ConfigIssue(
                                    component="config_docker",
                                    severity="major",
                                    issue_type="port_conflict",
                                    description="Port conflict between main docker-compose.yml (9000:9000) and gate-e docker-compose (9001:9000)",
                                    location=str(main_compose),
                                    recommended_fix="Use consistent port mappings across all compose files"
                                ))
    
    def check_otel_configs(self):
        """Check OpenTelemetry configurations"""
        main_otel_config = self.project_root / "config/signoz/otel-collector-config.yaml"
        gate_otel_config = self.project_root / ".dev-artifacts/gate-e-0c/otel-collector-config.yaml"
        
        configs_to_check = [
            (main_otel_config, "main"),
            (gate_otel_config, "gate-e")
        ]
        
        for config_path, config_type in configs_to_check:
            if config_path.exists():
                try:
                    import yaml
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    
                    # Check for required sections
                    required_sections = ["receivers", "processors", "exporters", "service"]
                    for section in required_sections:
                        if section not in config:
                            self.issues.append(ConfigIssue(
                                component="config_otel",
                                severity="critical",
                                issue_type="missing_section",
                                description=f"Missing required section '{section}' in OTEL config",
                                location=str(config_path),
                                recommended_fix=f"Add {section} section to OTEL configuration"
                            ))
                    
                    # Check exporters
                    if "exporters" in config:
                        exporters = config["exporters"]
                        if config_type == "main":
                            # Check for clickhouse exporter
                            if "clickhouse" in exporters:
                                endpoint = exporters["clickhouse"].get("endpoint", "")
                                if "localhost" in endpoint:
                                    self.issues.append(ConfigIssue(
                                        component="config_otel",
                                        severity="major",
                                        issue_type="incorrect_endpoint",
                                        description="OTEL exporter using localhost instead of service name",
                                        location=str(config_path),
                                        recommended_fix="Change endpoint from localhost to service name (e.g., clickhouse)"
                                    ))
                        
                except ImportError:
                    self.issues.append(ConfigIssue(
                        component="config_otel",
                        severity="warning",
                        issue_type="parse_error",
                        description="Cannot parse YAML config - PyYAML not available",
                        location=str(config_path),
                        recommended_fix="Install PyYAML to validate YAML configurations"
                    ))
                except Exception as e:
                    self.issues.append(ConfigIssue(
                        component="config_otel",
                        severity="major",
                        issue_type="parse_error",
                        description=f"Failed to parse OTEL config: {e}",
                        location=str(config_path),
                        recommended_fix="Fix YAML syntax errors in configuration file"
                    ))
    
    def check_platform_service_configs(self):
        """Check platform service configurations"""
        # Check if applications are configured to use observability
        isp_app = self.project_root / "src/dotmac_isp/app.py"
        mgmt_app = self.project_root / "src/dotmac_management/main.py"
        
        apps_to_check = [
            (isp_app, "ISP"),
            (mgmt_app, "Management")
        ]
        
        for app_path, app_name in apps_to_check:
            if app_path.exists():
                app_content = app_path.read_text()
                
                # Check for observability imports
                obs_imports = [
                    "observability",
                    "opentelemetry", 
                    "tracing",
                    "metrics"
                ]
                
                has_obs_imports = any(imp in app_content for imp in obs_imports)
                
                if not has_obs_imports:
                    self.issues.append(ConfigIssue(
                        component="config_app_integration",
                        severity="major",
                        issue_type="missing_integration",
                        description=f"{app_name} application missing observability integration",
                        location=str(app_path),
                        recommended_fix="Add observability bootstrap and initialization to application startup"
                    ))
    
    def analyze_docker_services(self) -> Dict[str, Any]:
        """Analyze Docker service status"""
        try:
            # Get running containers
            result = subprocess.run([
                "docker", "ps", "--format", 
                "{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            name = parts[0]
                            status = parts[1]
                            ports = parts[2].split(', ') if parts[2] else []
                            image = parts[3]
                            
                            # Check if it's an observability service
                            obs_keywords = ['signoz', 'clickhouse', 'otel', 'collector']
                            if any(keyword in name.lower() for keyword in obs_keywords):
                                is_running = 'Up' in status
                                is_healthy = 'healthy' in status
                                
                                self.service_status.append(ServiceStatus(
                                    name=name,
                                    running=is_running,
                                    healthy=is_healthy,
                                    ports=ports,
                                    image=image,
                                    error_details=status if not is_healthy and is_running else None
                                ))
            
            # Get all containers (including stopped)
            result_all = subprocess.run([
                "docker", "ps", "-a", "--format",
                "{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
            ], capture_output=True, text=True)
            
            # Check for expected but not running services
            expected_services = [
                'dotmac-clickhouse',
                'dotmac-signoz-collector', 
                'dotmac-signoz-query',
                'dotmac-signoz-frontend'
            ]
            
            running_services = [s.name for s in self.service_status]
            
            for expected in expected_services:
                if expected not in running_services:
                    # Check if it exists but is stopped
                    if result_all.returncode == 0:
                        all_lines = result_all.stdout.strip().split('\n')
                        found_stopped = False
                        for line in all_lines:
                            if expected in line and 'Exited' in line:
                                parts = line.split('\t')
                                self.service_status.append(ServiceStatus(
                                    name=expected,
                                    running=False,
                                    healthy=False,
                                    ports=[],
                                    image=parts[3] if len(parts) > 3 else "unknown",
                                    error_details=parts[1] if len(parts) > 1 else "Stopped"
                                ))
                                found_stopped = True
                                break
                        
                        if not found_stopped:
                            self.service_status.append(ServiceStatus(
                                name=expected,
                                running=False,
                                healthy=False,
                                ports=[],
                                image="unknown",
                                error_details="Service not found"
                            ))
        
        except Exception as e:
            logger.error(f"Error analyzing docker services: {e}")
        
        return {
            "total_services": len(self.service_status),
            "running_services": len([s for s in self.service_status if s.running]),
            "healthy_services": len([s for s in self.service_status if s.healthy]),
            "services": [
                {
                    "name": s.name,
                    "running": s.running,
                    "healthy": s.healthy,
                    "ports": s.ports,
                    "image": s.image,
                    "error": s.error_details
                }
                for s in self.service_status
            ]
        }
    
    def analyze_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity between services"""
        
        # Test endpoints
        endpoints_to_test = [
            ("localhost", 3301, "http", "SigNoz Frontend"),
            ("localhost", 8080, "http", "SigNoz Query"),
            ("localhost", 9000, "tcp", "ClickHouse Native"),
            ("localhost", 8123, "http", "ClickHouse HTTP"),
            ("localhost", 4317, "tcp", "OTEL gRPC"),
            ("localhost", 4318, "http", "OTEL HTTP"),
        ]
        
        for host, port, protocol, description in endpoints_to_test:
            success = False
            response_time = None
            error = None
            
            try:
                if protocol == "http":
                    start_time = time.time()
                    response = requests.get(f"http://{host}:{port}/health", timeout=5)
                    response_time = (time.time() - start_time) * 1000
                    success = response.status_code < 500
                    if not success:
                        error = f"HTTP {response.status_code}"
                elif protocol == "tcp":
                    import socket
                    start_time = time.time()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    response_time = (time.time() - start_time) * 1000
                    success = result == 0
                    if not success:
                        error = f"Connection refused (code: {result})"
                    sock.close()
            except Exception as e:
                error = str(e)
            
            self.connectivity_tests.append(ConnectivityTest(
                source="localhost",
                target=f"{host}:{port}",
                port=port,
                protocol=protocol,
                success=success,
                response_time_ms=response_time,
                error=error
            ))
        
        return {
            "total_tests": len(self.connectivity_tests),
            "successful_tests": len([t for t in self.connectivity_tests if t.success]),
            "failed_tests": len([t for t in self.connectivity_tests if not t.success]),
            "tests": [
                {
                    "target": t.target,
                    "protocol": t.protocol,
                    "success": t.success,
                    "response_time_ms": t.response_time_ms,
                    "error": t.error
                }
                for t in self.connectivity_tests
            ]
        }
    
    def analyze_application_integration(self) -> Dict[str, Any]:
        """Analyze how applications integrate with observability"""
        
        integration_status = {}
        
        # Check main applications
        apps_to_check = [
            ("ISP Framework", "src/dotmac_isp"),
            ("Management Platform", "src/dotmac_management"),
        ]
        
        for app_name, app_path in apps_to_check:
            app_dir = self.project_root / app_path
            
            integration_status[app_name] = {
                "observability_imports": False,
                "bootstrap_initialization": False,
                "metrics_endpoints": False,
                "tracing_middleware": False,
                "environment_variables": False
            }
            
            if app_dir.exists():
                # Check for observability-related files
                python_files = list(app_dir.rglob("*.py"))
                
                obs_patterns = [
                    ("observability_imports", ["from.*observability", "import.*opentelemetry", "import.*metrics", "import.*tracing"]),
                    ("bootstrap_initialization", ["initialize_otel", "bootstrap", "setup_observability"]),
                    ("metrics_endpoints", ["/metrics", "prometheus", "metrics_endpoint"]),
                    ("tracing_middleware", ["tracing_middleware", "trace_middleware", "TraceMiddleware"])
                ]
                
                for pattern_name, patterns in obs_patterns:
                    for py_file in python_files:
                        try:
                            content = py_file.read_text()
                            if any(pattern in content for pattern in patterns):
                                integration_status[app_name][pattern_name] = True
                                break
                        except:
                            continue
        
        return integration_status
    
    def analyze_environment_variables(self) -> Dict[str, Any]:
        """Analyze environment variable configuration"""
        
        # Check docker-compose environment variables
        main_compose = self.project_root / "docker-compose.yml"
        env_issues = []
        
        if main_compose.exists():
            compose_content = main_compose.read_text()
            
            # Check for required environment variables
            required_env_vars = [
                "SIGNOZ_ENDPOINT",
                "CLICKHOUSE_PASSWORD",
                "OTEL_RESOURCE_ATTRIBUTES"
            ]
            
            for var in required_env_vars:
                if var not in compose_content:
                    env_issues.append(f"Missing {var} in docker-compose.yml")
                elif f"{var}:" in compose_content and "${" not in compose_content.split(f"{var}:")[1].split('\n')[0]:
                    # Static value, not from environment
                    env_issues.append(f"{var} has static value, should use environment variable")
        
        return {
            "issues": env_issues,
            "total_issues": len(env_issues)
        }
    
    def analyze_file_system(self) -> Dict[str, Any]:
        """Analyze file system and volume configurations"""
        
        fs_issues = []
        
        # Check for required directories
        required_dirs = [
            "config/signoz",
            "signoz/dashboards",
            ".dev-artifacts/gate-e-0c"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                fs_issues.append(f"Missing directory: {dir_path}")
            elif not full_path.is_dir():
                fs_issues.append(f"Path exists but is not a directory: {dir_path}")
        
        # Check for required config files
        required_files = [
            "config/signoz/otel-collector-config.yaml",
            ".dev-artifacts/gate-e-0c/otel-collector-config.yaml",
            ".dev-artifacts/gate-e-0c/query-service-config.yaml"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                fs_issues.append(f"Missing config file: {file_path}")
            elif not full_path.is_file():
                fs_issues.append(f"Path exists but is not a file: {file_path}")
        
        return {
            "issues": fs_issues,
            "total_issues": len(fs_issues)
        }
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary"""
        
        total_issues = len(self.issues)
        critical_issues = len([i for i in self.issues if i.severity == "critical"])
        major_issues = len([i for i in self.issues if i.severity == "major"])
        minor_issues = len([i for i in self.issues if i.severity == "minor"])
        
        running_services = len([s for s in self.service_status if s.running])
        healthy_services = len([s for s in self.service_status if s.healthy])
        
        successful_connectivity = len([t for t in self.connectivity_tests if t.success])
        total_connectivity = len(self.connectivity_tests)
        
        # Determine overall health
        health_score = 0
        if total_issues > 0:
            health_score -= (critical_issues * 25 + major_issues * 10 + minor_issues * 5)
        
        if len(self.service_status) > 0:
            health_score += (healthy_services / len(self.service_status)) * 50
        
        if total_connectivity > 0:
            health_score += (successful_connectivity / total_connectivity) * 25
        
        health_score = max(0, min(100, health_score + 50))  # Normalize to 0-100
        
        return {
            "overall_health_score": round(health_score, 2),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "major_issues": major_issues,
            "minor_issues": minor_issues,
            "services": {
                "total": len(self.service_status),
                "running": running_services,
                "healthy": healthy_services
            },
            "connectivity": {
                "total_tests": total_connectivity,
                "successful": successful_connectivity,
                "failed": total_connectivity - successful_connectivity
            },
            "recommendations": self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate fix recommendations based on analysis"""
        recommendations = []
        
        # Critical issues first
        critical_issues = [i for i in self.issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append("CRITICAL: Fix missing configuration classes (ExporterConfig, ExporterType)")
            
        # Service issues
        unhealthy_services = [s for s in self.service_status if s.running and not s.healthy]
        if unhealthy_services:
            recommendations.append(f"Fix {len(unhealthy_services)} unhealthy services")
            
        stopped_services = [s for s in self.service_status if not s.running]
        if stopped_services:
            recommendations.append(f"Start {len(stopped_services)} stopped observability services")
        
        # Connectivity issues
        failed_tests = [t for t in self.connectivity_tests if not t.success]
        if failed_tests:
            recommendations.append(f"Fix {len(failed_tests)} connectivity issues")
        
        return recommendations

def main():
    """Main analysis execution"""
    analyzer = ObservabilityAnalyzer()
    results = analyzer.run_comprehensive_analysis()
    
    # Save results
    output_file = Path(".dev-artifacts/observability-analysis/detailed_analysis_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    summary = results["summary"]
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE OBSERVABILITY ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"Overall Health Score: {summary['overall_health_score']}/100")
    print(f"\nIssues Found:")
    print(f"  Critical: {summary['critical_issues']}")
    print(f"  Major: {summary['major_issues']}")
    print(f"  Minor: {summary['minor_issues']}")
    print(f"  Total: {summary['total_issues']}")
    
    print(f"\nServices:")
    print(f"  Running: {summary['services']['running']}/{summary['services']['total']}")
    print(f"  Healthy: {summary['services']['healthy']}/{summary['services']['total']}")
    
    print(f"\nConnectivity:")
    print(f"  Successful: {summary['connectivity']['successful']}/{summary['connectivity']['total_tests']}")
    
    print(f"\nTop Recommendations:")
    for i, rec in enumerate(summary['recommendations'][:5], 1):
        print(f"  {i}. {rec}")
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    main()