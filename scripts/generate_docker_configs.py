#!/usr/bin/env python3
"""
Docker Configuration Generator for DotMac Platform

This script generates service-specific Docker configurations from templates,
ensuring consistency and security across all services.
"""

import argparse
import os
from pathlib import Path
from typing import Dict, List


class DockerConfigGenerator:
    """Generates Docker configurations for DotMac services."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.template_path = self.root_path / "docker"
        self.services = self._discover_services()

        # Service configuration templates
        self.service_configs = {
            "dotmac_platform": {
                "port": 8000,
                "description": "DotMac Platform Core SDK",
                "health_check": 'python -c "import dotmac_platform; print(\'OK\')"',
                "dependencies": ["postgres", "redis"],
                "cpu_limit": "2",
                "memory_limit": "1G"
            },
            "dotmac_api_gateway": {
                "port": 8000,
                "description": "DotMac API Gateway Service",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["redis"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_identity": {
                "port": 8000,
                "description": "DotMac Identity Management Service",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres", "redis"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_services": {
                "port": 8000,
                "description": "DotMac Service Management",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_networking": {
                "port": 8000,
                "description": "DotMac Networking Management",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres", "redis"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_billing": {
                "port": 8000,
                "description": "DotMac Billing Management",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_analytics": {
                "port": 8000,
                "description": "DotMac Analytics Service",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres", "redis"],
                "cpu_limit": "2",
                "memory_limit": "1G"
            },
            "dotmac_core_events": {
                "port": 8000,
                "description": "DotMac Core Events Service",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres", "redis", "kafka"],
                "cpu_limit": "2",
                "memory_limit": "1G"
            },
            "dotmac_core_ops": {
                "port": 8000,
                "description": "DotMac Core Operations Service",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": ["postgres", "redis"],
                "cpu_limit": "1",
                "memory_limit": "512M"
            },
            "dotmac_devtools": {
                "port": 8000,
                "description": "DotMac Development Tools",
                "health_check": "curl -f http://localhost:8000/health",
                "dependencies": [],
                "cpu_limit": "0.5",
                "memory_limit": "256M"
            }
        }

    def _discover_services(self) -> List[str]:
        """Discover all DotMac services."""
        services = []
        for item in self.root_path.iterdir():
            if (item.is_dir() and
                item.name.startswith("dotmac_") and
                not item.name.endswith("_framework")):
                services.append(item.name)
        return sorted(services)

    def generate_dockerfile(self, service: str, target: str = "production") -> bool:
        """Generate service-specific Dockerfile from template."""
        if service not in self.services:
            print(f"❌ Service '{service}' not found")
            return False

        service_path = self.root_path / service
        dockerfile_path = service_path / "Dockerfile"
        template_path = self.template_path / "Dockerfile.template"

        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return False

        # Read template
        with open(template_path) as f:
            template_content = f.read()

        # Get service configuration
        config = self.service_configs.get(service, {})

        # Replace template variables
        dockerfile_content = template_content.replace("${SERVICE_NAME}", service)
        dockerfile_content = dockerfile_content.replace("${SERVICE_DESCRIPTION}",
                                                       config.get("description", f"{service} service"))
        dockerfile_content = dockerfile_content.replace("${SERVICE_PORT}",
                                                       str(config.get("port", 8000)))
        dockerfile_content = dockerfile_content.replace("${HEALTH_CHECK_CMD}",
                                                       config.get("health_check", "curl -f http://localhost:8000/health"))

        # Add service-specific customizations
        dockerfile_content = self._add_service_customizations(dockerfile_content, service, config)

        # Write Dockerfile
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        print(f"✅ Generated Dockerfile for {service}")
        return True

    def _add_service_customizations(self, content: str, service: str, config: Dict) -> str:
        """Add service-specific customizations to Dockerfile."""
        customizations = []

        # Add service-specific environment variables
        if service == "dotmac_api_gateway":
            customizations.append("ENV GATEWAY_MODE=production")
            customizations.append("ENV RATE_LIMIT_ENABLED=true")
        elif service == "dotmac_identity":
            customizations.append("ENV IDENTITY_PROVIDER=local")
            customizations.append("ENV MFA_ENABLED=true")
        elif service == "dotmac_analytics":
            customizations.append("ENV ANALYTICS_BATCH_SIZE=1000")
            customizations.append("ENV METRICS_RETENTION_DAYS=30")

        # Add customizations to the production stage
        if customizations:
            custom_env = "\n".join(customizations)
            content = content.replace(
                "ENV PYTHONFAULTHANDLER=1",
                f"ENV PYTHONFAULTHANDLER=1\n{custom_env}"
            )

        return content

    def generate_docker_compose(self, environment: str = "development") -> bool:
        """Generate environment-specific docker-compose.yml."""
        template_path = self.template_path / "docker-compose.template.yml"
        output_path = self.root_path / f"docker-compose.{environment}.yml"

        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return False

        # Read template
        with open(template_path) as f:
            template_content = f.read()

        # Environment-specific modifications
        if environment == "development":
            compose_content = self._customize_for_development(template_content)
        elif environment == "staging":
            compose_content = self._customize_for_staging(template_content)
        elif environment == "production":
            compose_content = self._customize_for_production(template_content)
        else:
            compose_content = template_content

        # Write docker-compose file
        with open(output_path, "w") as f:
            f.write(compose_content)

        print(f"✅ Generated docker-compose.{environment}.yml")
        return True

    def _customize_for_development(self, content: str) -> str:
        """Customize docker-compose for development environment."""
        # Enable development profiles by default
        content = content.replace(
            "profiles:\n      - development",
            "# profiles:\n      #   - development  # Enabled by default"
        )

        # Add volume mounts for live code reloading
        dev_volumes = """
    volumes:
      - .:/app:ro
      - ./logs:/app/logs"""

        content = content.replace(
            "volumes:\n      - logs_data:/app/logs",
            dev_volumes
        )

        return content

    def _customize_for_staging(self, content: str) -> str:
        """Customize docker-compose for staging environment."""
        # Enable security scanning in staging
        content = content.replace(
            "profiles:\n      - security",
            "# profiles:\n      #   - security  # Enabled in staging"
        )

        return content

    def _customize_for_production(self, content: str) -> str:
        """Customize docker-compose for production environment."""
        # Remove development services
        dev_services = [
            "mailhog:", "swagger-ui:", "test-runner:"
        ]

        lines = content.split("\n")
        filtered_lines = []
        skip_service = False

        for line in lines:
            if any(service in line for service in dev_services):
                skip_service = True
                continue
            if skip_service and line.startswith("  ") and not line.startswith("    "):
                skip_service = False

            if not skip_service:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def generate_build_scripts(self) -> bool:
        """Generate build scripts for all services."""
        scripts_dir = self.root_path / "scripts" / "docker"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Generate build-all script
        build_all_script = self._generate_build_all_script()
        with open(scripts_dir / "build-all.sh", "w") as f:
            f.write(build_all_script)
        os.chmod(scripts_dir / "build-all.sh", 0o755)

        # Generate individual service build scripts
        for service in self.services:
            build_script = self._generate_service_build_script(service)
            script_path = scripts_dir / f"build-{service.replace('dotmac_', '')}.sh"
            with open(script_path, "w") as f:
                f.write(build_script)
            os.chmod(script_path, 0o755)

        print(f"✅ Generated build scripts in {scripts_dir}")
        return True

    def _generate_build_all_script(self) -> str:
        """Generate script to build all services."""
        return f"""#!/bin/bash
# Build all DotMac services
set -e

echo "🚀 Building all DotMac services..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${{VERSION:-latest}}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Build services in dependency order
SERVICES=("{'" "'.join(self.services)}")

for SERVICE in "${{SERVICES[@]}}"; do
    echo "📦 Building $SERVICE..."

    if [ -d "$SERVICE" ]; then
        cd "$SERVICE"

        # Build with security scanning
        docker build \\
            --target security-scanner \\
            --tag "$SERVICE:security-scan" \\
            --build-arg BUILD_DATE="$BUILD_DATE" \\
            --build-arg VERSION="$VERSION" \\
            --build-arg VCS_REF="$VCS_REF" \\
            . || echo "⚠️  Security scan failed for $SERVICE"

        # Build production image
        docker build \\
            --target production \\
            --tag "$SERVICE:$VERSION" \\
            --tag "$SERVICE:latest" \\
            --build-arg BUILD_DATE="$BUILD_DATE" \\
            --build-arg VERSION="$VERSION" \\
            --build-arg VCS_REF="$VCS_REF" \\
            .

        cd ..
        echo "✅ Built $SERVICE"
    else
        echo "⚠️  Directory $SERVICE not found"
    fi
done

echo "🎉 All services built successfully!"
"""

    def _generate_service_build_script(self, service: str) -> str:
        """Generate build script for individual service."""
        config = self.service_configs.get(service, {})

        return f"""#!/bin/bash
# Build {service}
set -e

echo "📦 Building {service}..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${{VERSION:-latest}}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TARGET=${{TARGET:-production}}

cd {service}

# Build with specified target
docker build \\
    --target "$TARGET" \\
    --tag "{service}:$VERSION" \\
    --tag "{service}:latest" \\
    --build-arg BUILD_DATE="$BUILD_DATE" \\
    --build-arg VERSION="$VERSION" \\
    --build-arg VCS_REF="$VCS_REF" \\
    --build-arg SERVICE_NAME="{service}" \\
    --build-arg SERVICE_DESCRIPTION="{config.get('description', f'{service} service')}" \\
    .

echo "✅ Built {service}:$VERSION"

# Optional: Run security scan
if [ "${{SECURITY_SCAN:-false}}" = "true" ]; then
    echo "🔒 Running security scan..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \\
        aquasec/trivy:latest image "{service}:$VERSION"
fi

# Optional: Run tests
if [ "${{RUN_TESTS:-false}}" = "true" ]; then
    echo "🧪 Running tests..."
    docker build --target testing --tag "{service}:test" .
    docker run --rm "{service}:test"
fi
"""

    def generate_security_configs(self) -> bool:
        """Generate security scanning and hardening configurations."""
        security_dir = self.root_path / "docker" / "security"
        security_dir.mkdir(parents=True, exist_ok=True)

        # Generate .dockerignore
        dockerignore_content = self._generate_dockerignore()
        with open(self.root_path / ".dockerignore", "w") as f:
            f.write(dockerignore_content)

        # Generate security scanning script
        security_script = self._generate_security_script()
        with open(security_dir / "scan-all.sh", "w") as f:
            f.write(security_script)
        os.chmod(security_dir / "scan-all.sh", 0o755)

        # Generate hardening checklist
        hardening_checklist = self._generate_hardening_checklist()
        with open(security_dir / "hardening-checklist.md", "w") as f:
            f.write(hardening_checklist)

        print(f"✅ Generated security configurations in {security_dir}")
        return True

    def _generate_dockerignore(self) -> str:
        """Generate comprehensive .dockerignore file."""
        return """# DotMac Platform .dockerignore
# Exclude unnecessary files from Docker build context

# Git
.git
.gitignore
.gitattributes

# Documentation
*.md
docs/
README*
CHANGELOG*
LICENSE*

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Testing
.tox/
.coverage
.pytest_cache/
htmlcov/
.coverage.*
coverage.xml
*.cover
.hypothesis/

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Cache
.cache/
.mypy_cache/
.pytest_cache/

# Temporary files
tmp/
temp/
*.tmp
*.temp

# Security sensitive files
*.key
*.pem
*.crt
secrets/
.env.local
.env.production

# Docker
Dockerfile*
docker-compose*
.dockerignore

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile

# Dependencies
node_modules/
"""

    def _generate_security_script(self) -> str:
        """Generate comprehensive security scanning script."""
        return r"""#!/bin/bash
# Comprehensive security scanning for DotMac services
set -e

echo "🔒 DotMac Security Scanner"
echo "=========================="

SCAN_DIR="./security"
mkdir -p "$SCAN_DIR"

# Function to scan image
scan_image() {
    local image=$1
    local output_file="$SCAN_DIR/${image//[:\/]/_}-scan.json"

    echo "🔍 Scanning $image..."

    # Trivy vulnerability scan
    trivy image --format json --output "$output_file" "$image" || true

    # Extract critical vulnerabilities
    jq '.Results[]? | select(.Vulnerabilities) | .Vulnerabilities[]? | select(.Severity == "CRITICAL")' "$output_file" > "$SCAN_DIR/${image//[:\/]/_}-critical.json" 2>/dev/null || true

    # Generate summary
    critical_count=$(jq length "$SCAN_DIR/${image//[:\/]/_}-critical.json" 2>/dev/null || echo 0)

    if [ "$critical_count" -gt 0 ]; then
        echo "❌ $image: $critical_count critical vulnerabilities found"
        return 1
    else
        echo "✅ $image: No critical vulnerabilities"
        return 0
    fi
}

# Scan all DotMac images
IMAGES=(
""" + "\n".join([f'    "{service}:latest"' for service in self.services]) + """
)

failed_scans=0

for image in "${IMAGES[@]}"; do
    if ! scan_image "$image"; then
        ((failed_scans++))
    fi
done

# Generate combined report
echo "📊 Generating security report..."
{
    echo "# DotMac Security Scan Report"
    echo "Generated on: $(date)"
    echo ""
    echo "## Summary"
    echo "- Images scanned: ${#IMAGES[@]}"
    echo "- Failed scans: $failed_scans"
    echo ""
    echo "## Critical Vulnerabilities"

    for image in "${IMAGES[@]}"; do
        critical_file="$SCAN_DIR/${image//[:\\/]/_}-critical.json"
        if [ -f "$critical_file" ]; then
            critical_count=$(jq length "$critical_file" 2>/dev/null || echo 0)
            if [ "$critical_count" -gt 0 ]; then
                echo "### $image: $critical_count critical"
                jq -r '.[] | "- \\(.VulnerabilityID): \\(.Title)"' "$critical_file"
                echo ""
            fi
        fi
    done
} > "$SCAN_DIR/security-report.md"

echo "📄 Security report saved to $SCAN_DIR/security-report.md"

if [ "$failed_scans" -gt 0 ]; then
    echo "⚠️  $failed_scans images have critical vulnerabilities"
    exit 1
else
    echo "🎉 All images passed security scan"
    exit 0
fi
"""

    def _generate_hardening_checklist(self) -> str:
        """Generate Docker security hardening checklist."""
        return """# Docker Security Hardening Checklist

## Base Image Security
- [ ] Use official, minimal base images (alpine, distroless)
- [ ] Regularly update base images
- [ ] Scan base images for vulnerabilities
- [ ] Use specific image tags, not 'latest'

## User Security
- [ ] Run containers as non-root user
- [ ] Use numeric user IDs in USER instruction
- [ ] Set appropriate file permissions
- [ ] Remove shell access where possible

## Network Security
- [ ] Use custom networks instead of default bridge
- [ ] Implement network segmentation
- [ ] Expose only necessary ports
- [ ] Use internal networks for service communication

## File System Security
- [ ] Use read-only file systems where possible
- [ ] Mount sensitive directories as read-only
- [ ] Use tmpfs for temporary data
- [ ] Implement proper volume permissions

## Secret Management
- [ ] Use Docker secrets or external secret management
- [ ] Never embed secrets in images
- [ ] Use .dockerignore to exclude sensitive files
- [ ] Rotate secrets regularly

## Runtime Security
- [ ] Use security profiles (AppArmor, SELinux)
- [ ] Implement resource limits
- [ ] Use health checks
- [ ] Enable logging and monitoring

## Build Security
- [ ] Use multi-stage builds
- [ ] Minimize attack surface
- [ ] Verify package signatures
- [ ] Use dependency scanning

## Compliance
- [ ] Follow CIS Docker Benchmark
- [ ] Implement vulnerability scanning
- [ ] Regular security assessments
- [ ] Document security measures
"""

    def generate_all_configs(self, environments: List[str] = None) -> bool:
        """Generate all Docker configurations."""
        if environments is None:
            environments = ["development", "staging", "production"]

        success = True

        print("🚀 Generating Docker configurations for DotMac Platform...")

        # Generate Dockerfiles for all services
        for service in self.services:
            if not self.generate_dockerfile(service):
                success = False

        # Generate Docker Compose files for all environments
        for env in environments:
            if not self.generate_docker_compose(env):
                success = False

        # Generate build scripts
        if not self.generate_build_scripts():
            success = False

        # Generate security configurations
        if not self.generate_security_configs():
            success = False

        if success:
            print("🎉 All Docker configurations generated successfully!")
        else:
            print("❌ Some configurations failed to generate")

        return success


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Generate Docker configurations for DotMac Platform")

    parser.add_argument("--service", help="Generate Dockerfile for specific service")
    parser.add_argument("--environment", choices=["development", "staging", "production"],
                       help="Generate docker-compose for specific environment")
    parser.add_argument("--all", action="store_true", help="Generate all configurations")
    parser.add_argument("--build-scripts", action="store_true", help="Generate build scripts")
    parser.add_argument("--security", action="store_true", help="Generate security configurations")
    parser.add_argument("--root", default=".", help="Root directory of DotMac framework")

    args = parser.parse_args()

    generator = DockerConfigGenerator(args.root)

    if args.all:
        success = generator.generate_all_configs()
    elif args.service:
        success = generator.generate_dockerfile(args.service)
    elif args.environment:
        success = generator.generate_docker_compose(args.environment)
    elif args.build_scripts:
        success = generator.generate_build_scripts()
    elif args.security:
        success = generator.generate_security_configs()
    else:
        print("Please specify what to generate. Use --help for options.")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
