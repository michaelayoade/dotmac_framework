#!/usr/bin/env python3
"""
Production Readiness Validator for Workflow Orchestration
Phase 4: Production Readiness

This module validates that all Phase 4 components are ready for production deployment.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import requests
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    details: str
    critical: bool = True
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class ProductionReadinessValidator:
    """Validates production readiness for workflow orchestration."""
    
    def __init__(self, base_path: str = "/home/dotmac_framework"):
        self.base_path = Path(base_path)
        self.results = []
        
    def run_all_validations(self) -> List[ValidationResult]:
        """Run all production readiness validations."""
        print("🔍 Starting Production Readiness Validation")
        print("Phase 4: Production Readiness")
        print()
        
        # Configuration validations
        self.validate_production_configuration()
        self.validate_environment_variables()
        self.validate_security_configuration()
        
        # Infrastructure validations
        self.validate_monitoring_setup()
        self.validate_backup_configuration()
        self.validate_database_configuration()
        
        # Application validations
        self.validate_workflow_orchestration()
        self.validate_performance_configuration()
        self.validate_scaling_readiness()
        
        # Documentation validations
        self.validate_runbooks()
        self.validate_deployment_scripts()
        
        # Final checks
        self.validate_health_endpoints()
        self.validate_logging_configuration()
        
        return self.results
    
    def validate_production_configuration(self) -> None:
        """Validate production configuration files."""
        print("1. Validating production configuration...")
        
        config_files = [
            ".dev-artifacts/production-config/docker-compose.production.yml",
            ".dev-artifacts/production-config/.env.production",
            ".dev-artifacts/production-config/nginx.conf",
            ".dev-artifacts/production-config/app-config/production.yaml"
        ]
        
        missing_files = []
        for config_file in config_files:
            file_path = self.base_path / config_file
            if not file_path.exists():
                missing_files.append(config_file)
        
        if missing_files:
            self.results.append(ValidationResult(
                check_name="Production Configuration Files",
                passed=False,
                details=f"Missing configuration files: {', '.join(missing_files)}",
                recommendations=[
                    "Run production configuration generator to create missing files",
                    "Verify all configuration templates are properly generated"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Production Configuration Files",
                passed=True,
                details="All production configuration files present",
                critical=True
            ))
    
    def validate_environment_variables(self) -> None:
        """Validate environment variable configuration."""
        print("2. Validating environment variables...")
        
        required_env_vars = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "BUSINESS_LOGIC_WORKFLOWS_ENABLED"
        ]
        
        env_file = self.base_path / ".dev-artifacts/production-config/.env.production"
        if not env_file.exists():
            self.results.append(ValidationResult(
                check_name="Environment Variables",
                passed=False,
                details="Production environment file not found",
                recommendations=["Create .env.production file with required variables"]
            ))
            return
        
        env_content = env_file.read_text()
        missing_vars = []
        insecure_vars = []
        
        for var in required_env_vars:
            if f"{var}=" not in env_content:
                missing_vars.append(var)
            elif f"{var}=change_this" in env_content:
                insecure_vars.append(var)
        
        if missing_vars or insecure_vars:
            details = ""
            if missing_vars:
                details += f"Missing variables: {', '.join(missing_vars)}. "
            if insecure_vars:
                details += f"Default values detected: {', '.join(insecure_vars)}"
                
            self.results.append(ValidationResult(
                check_name="Environment Variables",
                passed=False,
                details=details,
                recommendations=[
                    "Set all required environment variables",
                    "Replace default values with secure secrets",
                    "Use strong passwords and random keys"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Environment Variables",
                passed=True,
                details="All required environment variables configured",
                critical=True
            ))
    
    def validate_security_configuration(self) -> None:
        """Validate security configuration."""
        print("3. Validating security configuration...")
        
        security_checks = []
        
        # Check if SSL/TLS is configured
        nginx_config = self.base_path / ".dev-artifacts/production-config/nginx.conf"
        if nginx_config.exists():
            nginx_content = nginx_config.read_text()
            if "ssl_certificate" in nginx_content and "listen 443 ssl" in nginx_content:
                security_checks.append("SSL/TLS configuration present")
            else:
                security_checks.append("SSL/TLS configuration missing or incomplete")
        else:
            security_checks.append("Nginx configuration file not found")
        
        # Check security headers
        if nginx_config.exists():
            nginx_content = nginx_config.read_text()
            security_headers = [
                "X-Frame-Options",
                "X-XSS-Protection", 
                "X-Content-Type-Options",
                "Strict-Transport-Security"
            ]
            
            missing_headers = [header for header in security_headers 
                             if header not in nginx_content]
            
            if missing_headers:
                security_checks.append(f"Missing security headers: {', '.join(missing_headers)}")
            else:
                security_checks.append("Security headers configured")
        
        # Check for security runbook
        security_runbook = self.base_path / ".dev-artifacts/runbooks/security_runbook.md"
        if security_runbook.exists():
            security_checks.append("Security runbook available")
        else:
            security_checks.append("Security runbook missing")
        
        # Evaluate overall security
        critical_issues = [check for check in security_checks 
                          if "missing" in check.lower() or "not found" in check.lower()]
        
        if critical_issues:
            self.results.append(ValidationResult(
                check_name="Security Configuration",
                passed=False,
                details=f"Security issues found: {'; '.join(critical_issues)}",
                recommendations=[
                    "Configure SSL/TLS certificates",
                    "Add security headers to Nginx configuration",
                    "Review security runbook for additional hardening"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Security Configuration",
                passed=True,
                details="Basic security configuration validated",
                critical=True
            ))
    
    def validate_monitoring_setup(self) -> None:
        """Validate monitoring and alerting setup."""
        print("4. Validating monitoring setup...")
        
        monitoring_files = [
            ".dev-artifacts/workflow_monitoring_setup.py",
            ".dev-artifacts/runbooks/monitoring_runbook.md"
        ]
        
        missing_files = []
        for monitoring_file in monitoring_files:
            if not (self.base_path / monitoring_file).exists():
                missing_files.append(monitoring_file)
        
        # Check if monitoring configuration was generated
        monitoring_setup = self.base_path / ".dev-artifacts/workflow_monitoring_setup.py"
        metrics_configured = False
        alerts_configured = False
        
        if monitoring_setup.exists():
            setup_content = monitoring_setup.read_text()
            if "workflow_saga_executions_total" in setup_content:
                metrics_configured = True
            if "alert:" in setup_content:
                alerts_configured = True
        
        issues = []
        if missing_files:
            issues.append(f"Missing monitoring files: {', '.join(missing_files)}")
        if not metrics_configured:
            issues.append("Workflow metrics not configured")
        if not alerts_configured:
            issues.append("Alert rules not configured")
        
        if issues:
            self.results.append(ValidationResult(
                check_name="Monitoring Setup",
                passed=False,
                details="; ".join(issues),
                recommendations=[
                    "Run monitoring setup generator",
                    "Configure Prometheus metrics collection",
                    "Set up Grafana dashboards",
                    "Define alert rules for critical metrics"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Monitoring Setup",
                passed=True,
                details="Monitoring and alerting configuration ready",
                critical=True
            ))
    
    def validate_backup_configuration(self) -> None:
        """Validate backup and recovery configuration."""
        print("5. Validating backup configuration...")
        
        backup_files = [
            ".dev-artifacts/runbooks/backup_recovery_runbook.md"
        ]
        
        backup_ready = True
        issues = []
        
        # Check if backup runbook exists
        backup_runbook = self.base_path / ".dev-artifacts/runbooks/backup_recovery_runbook.md"
        if not backup_runbook.exists():
            backup_ready = False
            issues.append("Backup and recovery runbook missing")
        else:
            # Check if runbook contains essential procedures
            runbook_content = backup_runbook.read_text()
            required_procedures = [
                "Database Backup",
                "Configuration Backup", 
                "Recovery Procedures"
            ]
            
            missing_procedures = [proc for proc in required_procedures 
                                if proc not in runbook_content]
            
            if missing_procedures:
                backup_ready = False
                issues.append(f"Missing backup procedures: {', '.join(missing_procedures)}")
        
        # Check if backup directory structure is documented
        if backup_runbook.exists():
            runbook_content = backup_runbook.read_text()
            if "/opt/dotmac/backups" not in runbook_content:
                issues.append("Backup directory not documented")
        
        if not backup_ready or issues:
            self.results.append(ValidationResult(
                check_name="Backup Configuration",
                passed=False,
                details="; ".join(issues) if issues else "Backup configuration incomplete",
                recommendations=[
                    "Complete backup and recovery runbook",
                    "Set up automated backup scripts",
                    "Test backup and recovery procedures",
                    "Configure backup retention policies"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Backup Configuration",
                passed=True,
                details="Backup and recovery procedures documented",
                critical=True
            ))
    
    def validate_database_configuration(self) -> None:
        """Validate database configuration."""
        print("6. Validating database configuration...")
        
        # Check if database migration files exist
        migrations_dir = self.base_path / "alembic/versions"
        workflow_migration = None
        
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob("*workflow_orchestration*.py"):
                workflow_migration = migration_file
                break
        
        # Check alembic configuration
        alembic_ini = self.base_path / "alembic.ini"
        env_py = self.base_path / "alembic/env.py"
        
        db_issues = []
        
        if not workflow_migration:
            db_issues.append("Workflow orchestration migration not found")
        
        if not alembic_ini.exists():
            db_issues.append("Alembic configuration missing")
        
        if not env_py.exists():
            db_issues.append("Alembic env.py missing")
        
        # Check if env.py includes workflow models
        if env_py.exists():
            env_content = env_py.read_text()
            if "dotmac_shared.business_logic" not in env_content:
                db_issues.append("Workflow models not included in migrations")
        
        if db_issues:
            self.results.append(ValidationResult(
                check_name="Database Configuration",
                passed=False,
                details="; ".join(db_issues),
                recommendations=[
                    "Create workflow orchestration database migrations",
                    "Update alembic env.py to include workflow models",
                    "Test database migration procedures"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Database Configuration", 
                passed=True,
                details="Database migration configuration ready",
                critical=True
            ))
    
    def validate_workflow_orchestration(self) -> None:
        """Validate workflow orchestration implementation."""
        print("7. Validating workflow orchestration...")
        
        # Check core workflow files
        workflow_files = [
            "src/dotmac_shared/business_logic/sagas.py",
            "src/dotmac_shared/business_logic/idempotency.py",
            "src/dotmac_management/use_cases/tenant/provision_tenant.py",
            "src/dotmac_management/use_cases/billing/process_billing.py"
        ]
        
        missing_files = []
        implementation_issues = []
        
        for workflow_file in workflow_files:
            file_path = self.base_path / workflow_file
            if not file_path.exists():
                missing_files.append(workflow_file)
            else:
                # Check for key implementations
                content = file_path.read_text()
                
                if "sagas.py" in workflow_file:
                    if "SagaCoordinator" not in content:
                        implementation_issues.append("SagaCoordinator not implemented")
                elif "idempotency.py" in workflow_file:
                    if "IdempotencyManager" not in content:
                        implementation_issues.append("IdempotencyManager not implemented")
                elif "provision_tenant.py" in workflow_file:
                    if "saga_coordinator" not in content:
                        implementation_issues.append("Saga integration missing in tenant provisioning")
                elif "process_billing.py" in workflow_file:
                    if "idempotency" not in content:
                        implementation_issues.append("Idempotency integration missing in billing")
        
        issues = missing_files + implementation_issues
        
        if issues:
            self.results.append(ValidationResult(
                check_name="Workflow Orchestration",
                passed=False,
                details="; ".join(issues),
                recommendations=[
                    "Implement missing workflow orchestration components",
                    "Complete saga coordinator integration",
                    "Add idempotency management to use cases",
                    "Test workflow execution end-to-end"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Workflow Orchestration",
                passed=True,
                details="Workflow orchestration implementation complete",
                critical=True
            ))
    
    def validate_performance_configuration(self) -> None:
        """Validate performance testing and optimization."""
        print("8. Validating performance configuration...")
        
        performance_files = [
            ".dev-artifacts/performance_testing_mock.py",
            ".dev-artifacts/runbooks/performance_optimization_guide.md"
        ]
        
        performance_ready = True
        issues = []
        
        for perf_file in performance_files:
            if not (self.base_path / perf_file).exists():
                performance_ready = False
                issues.append(f"Missing: {perf_file}")
        
        # Check if performance testing was executed
        results_dir = self.base_path / ".dev-artifacts/performance-results"
        if not results_dir.exists():
            issues.append("Performance test results not found")
        else:
            result_files = list(results_dir.glob("*.json"))
            if not result_files:
                issues.append("No performance test results available")
        
        if not performance_ready or issues:
            self.results.append(ValidationResult(
                check_name="Performance Configuration",
                passed=False,
                details="; ".join(issues),
                recommendations=[
                    "Run performance testing suite",
                    "Generate performance optimization guide",
                    "Analyze performance test results",
                    "Implement recommended optimizations"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Performance Configuration",
                passed=True,
                details="Performance testing and optimization ready",
                critical=False
            ))
    
    def validate_scaling_readiness(self) -> None:
        """Validate scaling configuration."""
        print("9. Validating scaling readiness...")
        
        scaling_files = [
            ".dev-artifacts/runbooks/scaling_runbook.md",
            ".dev-artifacts/production-config/docker-compose.production.yml"
        ]
        
        scaling_ready = True
        issues = []
        
        # Check scaling documentation
        scaling_runbook = self.base_path / ".dev-artifacts/runbooks/scaling_runbook.md"
        if not scaling_runbook.exists():
            scaling_ready = False
            issues.append("Scaling runbook missing")
        
        # Check docker-compose for scaling configuration
        compose_file = self.base_path / ".dev-artifacts/production-config/docker-compose.production.yml"
        if compose_file.exists():
            compose_content = compose_file.read_text()
            if "deploy:" not in compose_content:
                issues.append("Resource limits not configured in docker-compose")
        else:
            scaling_ready = False
            issues.append("Production docker-compose file missing")
        
        if not scaling_ready or issues:
            self.results.append(ValidationResult(
                check_name="Scaling Readiness",
                passed=False,
                details="; ".join(issues),
                critical=False,
                recommendations=[
                    "Create scaling runbook with procedures",
                    "Configure resource limits in docker-compose",
                    "Set up horizontal scaling procedures",
                    "Document auto-scaling strategies"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Scaling Readiness",
                passed=True,
                details="Scaling procedures documented and configured",
                critical=False
            ))
    
    def validate_runbooks(self) -> None:
        """Validate operational runbooks."""
        print("10. Validating operational runbooks...")
        
        required_runbooks = [
            "deployment_runbook.md",
            "troubleshooting_runbook.md", 
            "monitoring_runbook.md",
            "maintenance_runbook.md",
            "backup_recovery_runbook.md",
            "security_runbook.md"
        ]
        
        runbooks_dir = self.base_path / ".dev-artifacts/runbooks"
        missing_runbooks = []
        
        if not runbooks_dir.exists():
            missing_runbooks = required_runbooks
        else:
            for runbook in required_runbooks:
                if not (runbooks_dir / runbook).exists():
                    missing_runbooks.append(runbook)
        
        if missing_runbooks:
            self.results.append(ValidationResult(
                check_name="Operational Runbooks",
                passed=False,
                details=f"Missing runbooks: {', '.join(missing_runbooks)}",
                recommendations=[
                    "Generate all required operational runbooks",
                    "Review runbook content for completeness",
                    "Ensure runbooks are accessible to operations team"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Operational Runbooks",
                passed=True,
                details="All operational runbooks available",
                critical=True
            ))
    
    def validate_deployment_scripts(self) -> None:
        """Validate deployment scripts."""
        print("11. Validating deployment scripts...")
        
        deployment_files = [
            ".dev-artifacts/production-config/deploy.sh"
        ]
        
        deployment_ready = True
        issues = []
        
        for deploy_file in deployment_files:
            file_path = self.base_path / deploy_file
            if not file_path.exists():
                deployment_ready = False
                issues.append(f"Missing: {deploy_file}")
            else:
                # Check if deployment script is executable
                if not os.access(file_path, os.X_OK):
                    issues.append(f"Deployment script not executable: {deploy_file}")
        
        if not deployment_ready or issues:
            self.results.append(ValidationResult(
                check_name="Deployment Scripts",
                passed=False,
                details="; ".join(issues),
                recommendations=[
                    "Create deployment automation scripts",
                    "Make deployment scripts executable",
                    "Test deployment scripts in staging environment"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Deployment Scripts",
                passed=True,
                details="Deployment automation scripts ready",
                critical=True
            ))
    
    def validate_health_endpoints(self) -> None:
        """Validate health check endpoints."""
        print("12. Validating health endpoints...")
        
        # Check if health endpoints are implemented
        main_py = self.base_path / "src/dotmac_management/main.py"
        health_implemented = False
        
        if main_py.exists():
            main_content = main_py.read_text()
            if "/api/workflows/health" in main_content:
                health_implemented = True
        
        if not health_implemented:
            self.results.append(ValidationResult(
                check_name="Health Endpoints",
                passed=False,
                details="Workflow health endpoints not implemented",
                recommendations=[
                    "Implement /api/workflows/health endpoint",
                    "Add health checks for all workflow components",
                    "Test health endpoints respond correctly"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Health Endpoints",
                passed=True,
                details="Health endpoints implemented",
                critical=True
            ))
    
    def validate_logging_configuration(self) -> None:
        """Validate logging configuration."""
        print("13. Validating logging configuration...")
        
        logging_issues = []
        
        # Check if structured logging is configured
        app_config = self.base_path / ".dev-artifacts/production-config/app-config/production.yaml"
        if app_config.exists():
            try:
                import yaml
                with open(app_config, 'r') as f:
                    config = yaml.safe_load(f)
                
                if 'logging' not in config:
                    logging_issues.append("Logging configuration missing from app config")
                elif config.get('logging', {}).get('format') != 'json':
                    logging_issues.append("Structured logging (JSON) not configured")
            except Exception as e:
                logging_issues.append(f"Error reading app config: {e}")
        else:
            logging_issues.append("Application configuration file missing")
        
        # Check if log directories are configured
        env_file = self.base_path / ".dev-artifacts/production-config/.env.production"
        if env_file.exists():
            env_content = env_file.read_text()
            if "LOG_LEVEL" not in env_content:
                logging_issues.append("LOG_LEVEL not configured in environment")
        
        if logging_issues:
            self.results.append(ValidationResult(
                check_name="Logging Configuration",
                passed=False,
                details="; ".join(logging_issues),
                critical=False,
                recommendations=[
                    "Configure structured logging (JSON format)",
                    "Set appropriate log levels for production",
                    "Set up log rotation and retention policies",
                    "Configure log aggregation and monitoring"
                ]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Logging Configuration",
                passed=True,
                details="Logging configuration ready for production",
                critical=False
            ))
    
    def generate_readiness_report(self) -> Dict[str, Any]:
        """Generate comprehensive production readiness report."""
        critical_passed = sum(1 for r in self.results if r.critical and r.passed)
        critical_total = sum(1 for r in self.results if r.critical)
        total_passed = sum(1 for r in self.results if r.passed)
        total_checks = len(self.results)
        
        # Calculate readiness score
        critical_score = (critical_passed / critical_total * 100) if critical_total > 0 else 0
        overall_score = (total_passed / total_checks * 100) if total_checks > 0 else 0
        
        # Determine readiness status
        if critical_score == 100:
            readiness_status = "READY FOR PRODUCTION"
        elif critical_score >= 80:
            readiness_status = "MOSTLY READY - Minor issues to resolve"
        elif critical_score >= 60:
            readiness_status = "NEEDS WORK - Several critical issues"
        else:
            readiness_status = "NOT READY - Major issues must be resolved"
        
        # Collect failed checks and recommendations
        failed_checks = [r for r in self.results if not r.passed]
        critical_issues = [r for r in failed_checks if r.critical]
        
        all_recommendations = []
        for result in failed_checks:
            all_recommendations.extend(result.recommendations)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "readiness_status": readiness_status,
            "critical_score": critical_score,
            "overall_score": overall_score,
            "total_checks": total_checks,
            "passed_checks": total_passed,
            "failed_checks": len(failed_checks),
            "critical_issues": len(critical_issues),
            "summary": {
                "critical_passed": critical_passed,
                "critical_total": critical_total,
                "non_critical_passed": total_passed - critical_passed,
                "non_critical_total": total_checks - critical_total
            },
            "failed_validations": [
                {
                    "check": r.check_name,
                    "critical": r.critical,
                    "details": r.details,
                    "recommendations": r.recommendations
                } for r in failed_checks
            ],
            "recommendations": list(set(all_recommendations)),
            "next_steps": self._generate_next_steps(readiness_status, critical_issues)
        }
    
    def _generate_next_steps(self, status: str, critical_issues: List[ValidationResult]) -> List[str]:
        """Generate next steps based on readiness status."""
        if status == "READY FOR PRODUCTION":
            return [
                "Review final deployment checklist",
                "Schedule production deployment window",
                "Notify stakeholders of go-live timeline",
                "Prepare rollback procedures"
            ]
        elif "MOSTLY READY" in status:
            return [
                "Resolve remaining critical issues",
                "Perform final validation checks", 
                "Plan deployment timeline",
                "Prepare contingency plans"
            ]
        elif "NEEDS WORK" in status:
            return [
                "Focus on critical issues first",
                "Assign owners to failed validations",
                "Set target completion dates",
                "Re-run validation after fixes"
            ]
        else:
            return [
                "Address all critical failures immediately",
                "Review Phase 4 implementation requirements",
                "Consider extending timeline for proper completion",
                "Seek additional resources if needed"
            ]
    
    def print_validation_summary(self) -> None:
        """Print validation results summary."""
        report = self.generate_readiness_report()
        
        print(f"\n{'='*60}")
        print("PRODUCTION READINESS VALIDATION REPORT")
        print(f"{'='*60}")
        
        print(f"\n📊 Overall Results:")
        print(f"  Status: {report['readiness_status']}")
        print(f"  Critical Score: {report['critical_score']:.1f}% ({report['summary']['critical_passed']}/{report['summary']['critical_total']})")
        print(f"  Overall Score: {report['overall_score']:.1f}% ({report['passed_checks']}/{report['total_checks']})")
        
        # Print passed checks
        passed_checks = [r for r in self.results if r.passed]
        print(f"\n✅ Passed Validations ({len(passed_checks)}):")
        for result in passed_checks:
            status = "🔥 CRITICAL" if result.critical else "📋 INFO"
            print(f"  {status} {result.check_name}")
        
        # Print failed checks
        failed_checks = [r for r in self.results if not r.passed]
        if failed_checks:
            print(f"\n❌ Failed Validations ({len(failed_checks)}):")
            for result in failed_checks:
                status = "🚨 CRITICAL" if result.critical else "⚠️ WARNING"
                print(f"  {status} {result.check_name}")
                print(f"    Issue: {result.details}")
                if result.recommendations:
                    print(f"    Recommendations: {'; '.join(result.recommendations[:2])}")
                print()
        
        # Print next steps
        print(f"🎯 Next Steps:")
        for i, step in enumerate(report['next_steps'], 1):
            print(f"  {i}. {step}")
        
        print(f"\n📁 Full report available at: .dev-artifacts/production-readiness-report.json")
        print(f"{'='*60}\n")


def main():
    """Run production readiness validation."""
    validator = ProductionReadinessValidator()
    
    try:
        # Run all validations
        results = validator.run_all_validations()
        
        # Generate and save report
        report = validator.generate_readiness_report()
        
        report_path = Path("/home/dotmac_framework/.dev-artifacts/production-readiness-report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        validator.print_validation_summary()
        
        # Return appropriate exit code
        critical_issues = sum(1 for r in results if r.critical and not r.passed)
        return 0 if critical_issues == 0 else 1
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())