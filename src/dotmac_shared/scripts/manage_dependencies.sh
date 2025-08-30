#!/bin/bash
# DotMac Framework - Dependency Management Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if pip-tools is installed
check_pip_tools() {
    if ! command -v pip-compile &> /dev/null; then
        log_error "pip-tools not found. Installing..."
        pip install pip-tools
    fi
}

# Compile dependencies with hashes for security
compile_dependencies() {
    log_info "Compiling dependencies with security hashes..."

    cd "$ROOT_DIR"

    # Compile main requirements
    pip-compile requirements.in \
        --generate-hashes \
        --resolver=backtracking \
        --output-file=requirements.lock \
        --verbose

    log_info "Dependencies compiled to requirements.lock"
}

# Compile development dependencies
compile_dev_dependencies() {
    log_info "Compiling development dependencies..."

    cd "$ROOT_DIR"

    # Create dev requirements if not exists
    if [[ ! -f "requirements-dev.in" ]]; then
        cat > requirements-dev.in << 'EOF'
# Development Dependencies
-r requirements.in

# Testing
pytest-xdist>=3.5.0,<4.0.0
pytest-mock>=3.12.0,<4.0.0
factory-boy>=3.3.0,<4.0.0
freezegun>=1.2.0,<2.0.0

# Code Quality
pre-commit>=3.6.0,<4.0.0
bandit>=1.7.5,<2.0.0
safety>=2.3.0,<3.0.0

# Documentation
mkdocstrings[python]>=0.24.0,<1.0.0
mike>=2.0.0,<3.0.0

# Profiling & Debugging
py-spy>=0.3.14,<1.0.0
memory-profiler>=0.61.0,<1.0.0

# Database Tools
pgcli>=4.0.1,<5.0.0
redis-cli>=2.5.0,<3.0.0
EOF
    fi

    pip-compile requirements-dev.in \
        --generate-hashes \
        --resolver=backtracking \
        --output-file=requirements-dev.lock \
        --verbose

    log_info "Development dependencies compiled to requirements-dev.lock"
}

# Sync dependencies across all packages
sync_package_dependencies() {
    log_info "Syncing dependencies across all packages..."

    for package_dir in "$ROOT_DIR"/dotmac_*; do
        if [[ -d "$package_dir" && -f "$package_dir/pyproject.toml" ]]; then
            package_name=$(basename "$package_dir")
            log_info "Processing $package_name..."

            # Update package pyproject.toml to reference locked versions
            python3 - << EOF
import tomllib
import tomli_w
from pathlib import Path

package_file = Path("$package_dir/pyproject.toml")
if package_file.exists():
    with open(package_file, 'rb') as f:
        config = tomllib.load(f)

    # Add reference to root lockfile
    if 'project' not in config:
        config['project'] = {}

    # Add note about dependency management
    config.setdefault('_dependency_management', {
        'lockfile': '../requirements.lock',
        'dev_lockfile': '../requirements-dev.lock',
        'update_command': '../scripts/manage_dependencies.sh compile'
    })

    with open(package_file, 'wb') as f:
        tomli_w.dump(config, f)

    print(f"Updated {package_file}")
EOF
        fi
    done
}

# Check for dependency vulnerabilities
check_vulnerabilities() {
    log_info "Checking for known vulnerabilities..."

    cd "$ROOT_DIR"

    # Install safety if not available
    if ! command -v safety &> /dev/null; then
        pip install safety
    fi

    # Check main dependencies
    safety check --file requirements.lock --json --output vulnerability-report.json || {
        log_error "Vulnerabilities found! Check vulnerability-report.json"
        return 1
    }

    # Check dev dependencies if they exist
    if [[ -f "requirements-dev.lock" ]]; then
        safety check --file requirements-dev.lock --short-report
    fi

    log_info "No known vulnerabilities found"
}

# Update all dependencies
update_dependencies() {
    log_info "Updating all dependencies..."

    cd "$ROOT_DIR"

    # Remove old lockfiles
    rm -f requirements.lock requirements-dev.lock

    # Recompile with latest versions
    compile_dependencies
    compile_dev_dependencies
    sync_package_dependencies

    log_info "Dependencies updated. Please test and commit the changes."
}

# Install dependencies in a clean environment
install_locked() {
    log_info "Installing locked dependencies..."

    cd "$ROOT_DIR"

    if [[ ! -f "requirements.lock" ]]; then
        log_error "requirements.lock not found. Run 'compile' first."
        exit 1
    fi

    # Install with hash verification
    pip install --require-hashes -r requirements.lock

    log_info "Locked dependencies installed successfully"
}

# Show dependency tree
show_tree() {
    log_info "Showing dependency tree..."

    if ! command -v pipdeptree &> /dev/null; then
        log_warn "pipdeptree not found. Installing..."
        pip install pipdeptree
    fi

    pipdeptree --packages "$(grep -E '^[a-zA-Z]' requirements.lock | cut -d'=' -f1 | tr '\n' ',' | sed 's/,$//')"
}

# Audit dependencies for compliance
audit_dependencies() {
    log_info "Auditing dependencies for compliance..."

    cd "$ROOT_DIR"

    # Check licenses
    if ! command -v pip-licenses &> /dev/null; then
        pip install pip-licenses
    fi

    pip-licenses \
        --format=json \
        --output-file=license-report.json \
        --packages "$(grep -E '^[a-zA-Z]' requirements.lock | cut -d'=' -f1)"

    # Check for problematic licenses
    python3 - << 'EOF'
import json

with open('license-report.json') as f:
    licenses = json.load(f)

problematic = ['GPL', 'AGPL', 'SSPL', 'Commons Clause']
issues = []

for pkg in licenses:
    license_name = pkg.get('License', 'UNKNOWN')
    if any(prob in license_name for prob in problematic):
        issues.append(f"{pkg['Name']}: {license_name}")

if issues:
    print("⚠️  Potentially problematic licenses found:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("✅ All licenses appear compatible")
EOF

    log_info "License audit complete. Check license-report.json for details."
}

# Main command dispatcher
main() {
    case "${1:-help}" in
        "compile")
            check_pip_tools
            compile_dependencies
            compile_dev_dependencies
            sync_package_dependencies
            ;;
        "update")
            check_pip_tools
            update_dependencies
            ;;
        "install")
            install_locked
            ;;
        "check")
            check_vulnerabilities
            ;;
        "tree")
            show_tree
            ;;
        "audit")
            audit_dependencies
            ;;
        "sync")
            sync_package_dependencies
            ;;
        "help"|*)
            cat << 'EOF'
DotMac Framework - Dependency Management

Usage: ./scripts/manage_dependencies.sh <command>

Commands:
  compile   Compile requirements.in to locked requirements with hashes
  update    Update all dependencies to latest compatible versions
  install   Install locked dependencies with hash verification
  check     Check for known security vulnerabilities
  tree      Show dependency tree
  audit     Audit licenses and compliance
  sync      Sync dependency config across all packages
  help      Show this help message

Examples:
  ./scripts/manage_dependencies.sh compile
  ./scripts/manage_dependencies.sh check
  ./scripts/manage_dependencies.sh update

Lockfile Workflow:
1. Edit requirements.in with version constraints
2. Run 'compile' to generate requirements.lock with exact versions and hashes
3. Commit both files to version control
4. Use 'install' in production for reproducible builds
5. Run 'check' regularly for security updates
EOF
            ;;
    esac
}

main "$@"
