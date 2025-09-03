#!/usr/bin/env python3
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

Comprehensive Production Readiness Analysis for DotMac Framework
Analyzes all critical aspects needed for production deployment.
"""

import ast
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionReadinessAnalyzer:
    """Comprehensive production readiness analysis."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.analysis_results = {}

    def analyze_codebase_structure(self) -> Dict[str, Any]:
        """Analyze overall codebase structure and architecture."""
        structure_analysis = {
            "modules": {},
            "architecture_patterns": [],
            "dependency_structure": {},
            "code_quality_metrics": {},
        }

        # Analyze main modules
        src_dir = self.root_dir / "src"
        if src_dir.exists():
            for module_dir in src_dir.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith("."):
                    module_info = self._analyze_module_structure(module_dir)
                    structure_analysis["modules"][module_dir.name] = module_info

        # Check for key architectural files
        key_files = {
            "docker_compose": "docker-compose.yml",
            "main_dockerfile": "Dockerfile",
            "kubernetes_configs": "k8s/",
            "requirements": "requirements.txt",
            "pyproject": "pyproject.toml",
            "makefile": "Makefile",
            "readme": "README.md",
        }

        structure_analysis["key_files"] = {}
        for key, filename in key_files.items():
            file_path = self.root_dir / filename
            structure_analysis["key_files"][key] = {
                "exists": file_path.exists(),
                "path": str(file_path) if file_path.exists() else None,
            }

        return structure_analysis

    def _analyze_module_structure(self, module_dir: Path) -> Dict[str, Any]:
        """Analyze individual module structure."""
        module_info = {
            "python_files": 0,
            "subdirectories": [],
            "has_init": False,
            "has_main": False,
            "has_tests": False,
            "api_endpoints": 0,
            "models": 0,
        }

        for py_file in module_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            module_info["python_files"] += 1

            if py_file.name == "__init__.py":
                module_info["has_init"] = True
            elif py_file.name == "main.py" or py_file.name == "app.py":
                module_info["has_main"] = True
            elif "test" in py_file.name.lower():
                module_info["has_tests"] = True
            elif "router" in py_file.name or "api" in py_file.name:
                module_info["api_endpoints"] += 1
            elif "model" in py_file.name:
                module_info["models"] += 1

        # Get subdirectories
        for subdir in module_dir.iterdir():
            if (
                subdir.is_dir()
                and not subdir.name.startswith(".")
                and subdir.name != "__pycache__"
            ):
                module_info["subdirectories"].append(subdir.name)

        return module_info

    def analyze_security_implementation(self) -> Dict[str, Any]:
        """Analyze security implementation and compliance."""
        security_analysis = {
            "authentication": {},
            "authorization": {},
            "data_protection": {},
            "api_security": {},
            "secrets_management": {},
            "compliance_features": {},
        }

        # Check for authentication implementations
        auth_patterns = ["jwt", "auth", "login", "session", "token", "oauth", "saml"]

        security_files = []
        for pattern in auth_patterns:
            files = list(self.root_dir.rglob(f"*{pattern}*.py"))
            security_files.extend(files)

        security_analysis["authentication"] = {
            "auth_files_count": len(set(security_files)),
            "jwt_implementation": len(list(self.root_dir.rglob("*jwt*.py"))) > 0,
            "session_management": len(list(self.root_dir.rglob("*session*.py"))) > 0,
            "multi_factor": len(list(self.root_dir.rglob("*mfa*.py"))) > 0,
        }

        # Check for security middleware
        security_analysis["api_security"] = {
            "csrf_protection": len(list(self.root_dir.rglob("*csrf*.py"))) > 0,
            "rate_limiting": len(list(self.root_dir.rglob("*rate_limit*.py"))) > 0,
            "input_validation": len(list(self.root_dir.rglob("*validation*.py"))) > 0,
            "security_middleware": len(
                list(self.root_dir.rglob("*security*middleware*.py"))
            )
            > 0,
        }

        # Check secrets management
        secrets_files = list(self.root_dir.rglob("*secret*.py"))
        vault_files = list(self.root_dir.rglob("*vault*.py"))

        security_analysis["secrets_management"] = {
            "secrets_files": len(secrets_files),
            "vault_integration": len(vault_files) > 0,
            "encryption_files": len(list(self.root_dir.rglob("*encrypt*.py"))) > 0,
        }

        return security_analysis

    def analyze_testing_coverage(self) -> Dict[str, Any]:
        """Analyze testing implementation and coverage."""
        testing_analysis = {
            "test_files": {},
            "testing_frameworks": [],
            "coverage_config": False,
            "ci_cd_tests": False,
        }

        # Count test files
        test_patterns = ["test_*.py", "*_test.py", "tests/*.py"]
        total_tests = 0

        for pattern in test_patterns:
            test_files = list(self.root_dir.rglob(pattern))
            total_tests += len(test_files)

        testing_analysis["test_files"]["total_test_files"] = total_tests
        testing_analysis["test_files"]["has_test_directory"] = (
            self.root_dir / "tests"
        ).exists()

        # Check for testing frameworks
        framework_indicators = {
            "pytest": ["pytest", "conftest.py"],
            "unittest": ["unittest"],
            "fastapi_test": ["TestClient", "test_client"],
        }

        for framework, indicators in framework_indicators.items():
            found = False
            for indicator in indicators:
                if list(self.root_dir.rglob(f"*{indicator}*")):
                    found = True
                    break
            if found:
                testing_analysis["testing_frameworks"].append(framework)

        # Check for coverage configuration
        coverage_files = [".coveragerc", "pytest.ini", "pyproject.toml"]
        for coverage_file in coverage_files:
            if (self.root_dir / coverage_file).exists():
                testing_analysis["coverage_config"] = True
                break

        # Check for CI/CD
        ci_dirs = [".github/workflows", ".gitlab-ci.yml", ".travis.yml"]
        for ci_dir in ci_dirs:
            if (self.root_dir / ci_dir).exists():
                testing_analysis["ci_cd_tests"] = True
                break

        return testing_analysis

    def analyze_deployment_readiness(self) -> Dict[str, Any]:
        """Analyze deployment and infrastructure readiness."""
        deployment_analysis = {
            "containerization": {},
            "orchestration": {},
            "configuration_management": {},
            "monitoring": {},
            "scalability": {},
        }

        # Docker analysis
        dockerfile_main = self.root_dir / "Dockerfile"
        docker_compose = self.root_dir / "docker-compose.yml"

        deployment_analysis["containerization"] = {
            "dockerfile_exists": dockerfile_main.exists(),
            "docker_compose_exists": docker_compose.exists(),
            "multi_stage_build": False,
            "dockerignore_exists": (self.root_dir / ".dockerignore").exists(),
        }

        if dockerfile_main.exists():
            try:
                with open(dockerfile_main, "r") as f:
                    dockerfile_content = f.read()
                    deployment_analysis["containerization"]["multi_stage_build"] = (
                        "FROM" in dockerfile_content
                        and dockerfile_content.count("FROM") > 1
                    )
            except Exception:
                pass

        # Kubernetes analysis
        k8s_dir = self.root_dir / "k8s"
        deployment_analysis["orchestration"] = {
            "kubernetes_configs": k8s_dir.exists(),
            "helm_charts": (self.root_dir / "helm").exists()
            or len(list(self.root_dir.rglob("Chart.yaml"))) > 0,
            "deployment_manifests": len(list(self.root_dir.rglob("*deployment*.yaml")))
            > 0,
            "service_manifests": len(list(self.root_dir.rglob("*service*.yaml"))) > 0,
            "ingress_configs": len(list(self.root_dir.rglob("*ingress*.yaml"))) > 0,
        }

        # Configuration management
        config_files = [
            "config.yaml",
            "settings.py",
            ".env.example",
            "alembic.ini",
            "logging.conf",
        ]

        deployment_analysis["configuration_management"] = {}
        for config_file in config_files:
            deployment_analysis["configuration_management"][
                config_file.replace(".", "_")
            ] = (self.root_dir / config_file).exists()

        # Monitoring setup
        monitoring_indicators = ["prometheus", "grafana", "signoz", "opentelemetry"]
        monitoring_files = []

        for indicator in monitoring_indicators:
            files = list(self.root_dir.rglob(f"*{indicator}*"))
            monitoring_files.extend(files)

        deployment_analysis["monitoring"] = {
            "monitoring_files": len(set(monitoring_files)),
            "health_checks": len(list(self.root_dir.rglob("*health*.py"))) > 0,
            "metrics_collection": len(list(self.root_dir.rglob("*metrics*.py"))) > 0,
        }

        return deployment_analysis

    def analyze_documentation(self) -> Dict[str, Any]:
        """Analyze documentation and operational procedures."""
        docs_analysis = {
            "user_documentation": {},
            "developer_documentation": {},
            "operational_documentation": {},
            "api_documentation": {},
        }

        # Check for documentation files
        doc_patterns = {
            "README files": "README*.md",
            "API docs": "*API*.md",
            "deployment docs": "*DEPLOY*.md",
            "configuration docs": "*CONFIG*.md",
            "architecture docs": "*ARCHITECTURE*.md",
        }

        for doc_type, pattern in doc_patterns.items():
            doc_files = list(self.root_dir.rglob(pattern))
            docs_analysis["user_documentation"][doc_type.lower().replace(" ", "_")] = (
                len(doc_files)
            )

        # Check for docs directory
        docs_dir = self.root_dir / "docs"
        docs_analysis["developer_documentation"] = {
            "docs_directory_exists": docs_dir.exists(),
            "total_md_files": len(list(self.root_dir.rglob("*.md"))),
            "sphinx_docs": (
                (docs_dir / "conf.py").exists() if docs_dir.exists() else False
            ),
        }

        # OpenAPI/Swagger documentation
        openapi_files = list(self.root_dir.rglob("*openapi*.json")) + list(
            self.root_dir.rglob("*swagger*.json")
        )
        docs_analysis["api_documentation"] = {
            "openapi_specs": len(openapi_files),
            "fastapi_docs": True,  # FastAPI auto-generates docs
        }

        return docs_analysis

    def calculate_readiness_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall production readiness score."""
        scores = {}

        # Structure score (0-100)
        structure = analysis["structure"]
        structure_score = 0
        if len(structure["modules"]) >= 2:
            structure_score += 20
        if structure["key_files"]["docker_compose"]["exists"]:
            structure_score += 15
        if structure["key_files"]["pyproject"]["exists"]:
            structure_score += 10
        if structure["key_files"]["makefile"]["exists"]:
            structure_score += 10
        if structure["key_files"]["readme"]["exists"]:
            structure_score += 15
        if any(mod["has_main"] for mod in structure["modules"].values()):
            structure_score += 15
        if any(mod["has_tests"] for mod in structure["modules"].values()):
            structure_score += 15

        scores["structure"] = min(structure_score, 100)

        # Security score (0-100)
        security = analysis["security"]
        security_score = 0
        if security["authentication"]["jwt_implementation"]:
            security_score += 20
        if security["authentication"]["session_management"]:
            security_score += 15
        if security["api_security"]["csrf_protection"]:
            security_score += 15
        if security["api_security"]["rate_limiting"]:
            security_score += 15
        if security["secrets_management"]["vault_integration"]:
            security_score += 20
        if security["secrets_management"]["encryption_files"] > 0:
            security_score += 15

        scores["security"] = min(security_score, 100)

        # Testing score (0-100)
        testing = analysis["testing"]
        testing_score = 0
        if testing["test_files"]["total_test_files"] > 0:
            testing_score += 30
        if testing["test_files"]["has_test_directory"]:
            testing_score += 20
        if "pytest" in testing["testing_frameworks"]:
            testing_score += 20
        if testing["coverage_config"]:
            testing_score += 15
        if testing["ci_cd_tests"]:
            testing_score += 15

        scores["testing"] = min(testing_score, 100)

        # Deployment score (0-100)
        deployment = analysis["deployment"]
        deployment_score = 0
        if deployment["containerization"]["dockerfile_exists"]:
            deployment_score += 20
        if deployment["containerization"]["docker_compose_exists"]:
            deployment_score += 20
        if deployment["orchestration"]["kubernetes_configs"]:
            deployment_score += 20
        if deployment["monitoring"]["health_checks"]:
            deployment_score += 20
        if deployment["monitoring"]["metrics_collection"]:
            deployment_score += 20

        scores["deployment"] = min(deployment_score, 100)

        # Documentation score (0-100)
        docs = analysis["documentation"]
        docs_score = 0
        if docs["user_documentation"]["readme_files"] > 0:
            docs_score += 25
        if docs["developer_documentation"]["docs_directory_exists"]:
            docs_score += 25
        if docs["user_documentation"]["api_docs"] > 0:
            docs_score += 25
        if docs["user_documentation"]["deployment_docs"] > 0:
            docs_score += 25

        scores["documentation"] = min(docs_score, 100)

        # Overall score
        overall_score = sum(scores.values()) / len(scores)
        scores["overall"] = round(overall_score, 1)

        return scores

    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive production readiness analysis."""
        logger.info("Starting comprehensive production readiness analysis...")

        analysis = {}

        # Run all analyses
        analysis["structure"] = self.analyze_codebase_structure()
        analysis["security"] = self.analyze_security_implementation()
        analysis["testing"] = self.analyze_testing_coverage()
        analysis["deployment"] = self.analyze_deployment_readiness()
        analysis["documentation"] = self.analyze_documentation()

        # Calculate scores
        analysis["readiness_scores"] = self.calculate_readiness_score(analysis)

        # Add metadata
        analysis["analysis_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "analyzer_version": "1.0.0",
            "framework_version": "production-ready",
        }

        return analysis


def main():
    """Run production readiness analysis."""
    analyzer = ProductionReadinessAnalyzer("/home/dotmac_framework")
    results = analyzer.run_comprehensive_analysis()

    # Save results
    output_file = "/home/dotmac_framework/PRODUCTION_READINESS_ANALYSIS.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    scores = results["readiness_scores"]
    print("\n" + "=" * 60)
    print("DOTMAC FRAMEWORK - PRODUCTION READINESS ANALYSIS")
    print("=" * 60)
    print(f"Overall Readiness Score: {scores['overall']}/100")
    print(f"Structure & Architecture: {scores['structure']}/100")
    print(f"Security Implementation: {scores['security']}/100")
    print(f"Testing Coverage: {scores['testing']}/100")
    print(f"Deployment Readiness: {scores['deployment']}/100")
    print(f"Documentation: {scores['documentation']}/100")
    print("=" * 60)

    # Readiness assessment
    if scores["overall"] >= 80:
        print("✅ PRODUCTION READY - High confidence for production deployment")
    elif scores["overall"] >= 60:
        print("⚠️  MOSTLY READY - Minor improvements needed before production")
    else:
        print("❌ NOT READY - Significant work needed before production deployment")

    print(f"\nDetailed analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
