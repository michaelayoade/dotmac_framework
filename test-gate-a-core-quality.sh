#!/bin/bash
# Gate A: Core Quality - Python Packages, Types, Lint, Security
# Purpose: Validate code quality and build artifacts for all Python packages

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO") echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" ;;
        "WARNING") echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" ;;
    esac
}

# Track results
declare -a PASSED_TESTS=()
declare -a FAILED_TESTS=()
declare -a WARNINGS=()

# Function to run test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local required="${3:-true}"
    
    log "INFO" "Running $test_name..."
    
    if eval "$test_command" >/tmp/gate_a_${test_name//[^a-zA-Z0-9]/_}.log 2>&1; then
        log "SUCCESS" "$test_name passed"
        PASSED_TESTS+=("$test_name")
        return 0
    else
        if [ "$required" = "true" ]; then
            log "ERROR" "$test_name failed (REQUIRED)"
            FAILED_TESTS+=("$test_name")
            echo "Last 20 lines of output:"
            tail -20 "/tmp/gate_a_${test_name//[^a-zA-Z0-9]/_}.log" | sed 's/^/  /'
        else
            log "WARNING" "$test_name failed (OPTIONAL)"
            WARNINGS+=("$test_name")
        fi
        return 1
    fi
}

# Function to test Python package
test_python_package() {
    local package_path="$1"
    local package_name="$(basename "$package_path")"
    
    if [ ! -f "$package_path/pyproject.toml" ]; then
        log "INFO" "Skipping $package_name (no pyproject.toml)"
        return 0
    fi
    
    log "INFO" "Testing Python package: $package_name"
    cd "$package_path"
    
    # Check if package has tests
    local has_tests=false
    if [ -d "tests" ] || find . -name "*test*.py" -not -path "./build/*" | grep -q .; then
        has_tests=true
    fi
    
    # Unit Tests (if present)
    if [ "$has_tests" = true ]; then
        run_test "${package_name}_unit_tests" \
            "/root/.local/share/pypoetry/venv/bin/python -m pytest -q --tb=short" \
            true
    else
        log "WARNING" "$package_name has no tests"
        WARNINGS+=("${package_name}_no_tests")
    fi
    
    # Type Checking (if mypy config exists)
    if [ -f "pyproject.toml" ] && grep -q "mypy" "pyproject.toml"; then
        run_test "${package_name}_mypy" \
            "/root/.local/share/pypoetry/venv/bin/python -m mypy ." \
            true
    elif command -v /root/.local/share/pypoetry/venv/bin/mypy >/dev/null 2>&1 && [ -d "src" ]; then
        run_test "${package_name}_mypy" \
            "/root/.local/share/pypoetry/venv/bin/python -m mypy src/" \
            false
    fi
    
    # Linting
    if command -v /root/.local/share/pypoetry/venv/bin/ruff >/dev/null 2>&1; then
        run_test "${package_name}_ruff_check" \
            "/root/.local/share/pypoetry/venv/bin/ruff check ." \
            true
        
        run_test "${package_name}_ruff_format" \
            "/root/.local/share/pypoetry/venv/bin/ruff format --check ." \
            false
    fi
    
    # Build package
    if command -v build >/dev/null 2>&1; then
        run_test "${package_name}_build" \
            "python -m build --wheel --sdist" \
            true
    elif command -v poetry >/dev/null 2>&1 && [ -f "poetry.lock" ]; then
        run_test "${package_name}_poetry_build" \
            "poetry build" \
            true
    fi
    
    # Security scan (if bandit available)
    if command -v bandit >/dev/null 2>&1; then
        run_test "${package_name}_bandit" \
            "python -m bandit -r . -f json -o /tmp/bandit_${package_name}.json || python -m bandit -r . --severity-level medium" \
            false
    fi
    
    cd "$SCRIPT_DIR"
}

# Function to run shared code tests
test_shared_code() {
    log "INFO" "Testing shared code in src/dotmac_shared"
    
    if [ -d "src/dotmac_shared" ]; then
        cd "src/dotmac_shared"
        
        # Python compilation test
        run_test "shared_code_compile" \
            "python -m py_compile \$(find . -name '*.py')" \
            true
        
        # Ruff on shared code
        if command -v ruff >/dev/null 2>&1; then
            run_test "shared_code_ruff" \
                "python -m ruff check ." \
                true
        fi
        
        cd "$SCRIPT_DIR"
    else
        log "WARNING" "No src/dotmac_shared directory found"
        WARNINGS+=("no_shared_code")
    fi
}

# Function to check dependencies
check_dependencies() {
    log "INFO" "Checking Python dependencies for security issues"
    
    # Safety check (if available)
    if command -v safety >/dev/null 2>&1; then
        run_test "dependency_safety" \
            "safety check --json --output /tmp/safety_report.json || safety check" \
            false
    fi
    
    # pip-audit (if available)
    if command -v pip-audit >/dev/null 2>&1; then
        run_test "dependency_audit" \
            "pip-audit --format=json --output=/tmp/pip_audit.json || pip-audit" \
            false
    fi
}

# Function to validate project structure
validate_project_structure() {
    log "INFO" "Validating project structure"
    
    local required_files=(
        "pyproject.toml"
        "requirements.txt"
        ".gitignore"
        "README.md"
    )
    
    local structure_valid=true
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "WARNING" "Missing recommended file: $file"
            WARNINGS+=("missing_$file")
            structure_valid=false
        fi
    done
    
    if [ "$structure_valid" = true ]; then
        PASSED_TESTS+=("project_structure")
    fi
}

# Main execution
main() {
    echo "🔍 Gate A: Core Quality Testing"
    echo "==============================="
    echo "Testing Python packages, types, lint, security, and build artifacts"
    echo ""
    
    # Validate project structure
    validate_project_structure
    
    # Test all packages in packages/
    if [ -d "packages" ]; then
        for package_dir in packages/*/; do
            if [ -d "$package_dir" ]; then
                test_python_package "$package_dir"
            fi
        done
    else
        log "WARNING" "No packages/ directory found"
        WARNINGS+=("no_packages_dir")
    fi
    
    # Test shared code
    test_shared_code
    
    # Check dependencies
    check_dependencies
    
    # Test root Python code if present
    if [ -d "src" ] && [ -f "pyproject.toml" ]; then
        log "INFO" "Testing root Python package"
        test_python_package "."
    fi
    
    # Generate summary
    echo ""
    echo "📊 Gate A Results Summary"
    echo "========================="
    echo "✅ Passed Tests: ${#PASSED_TESTS[@]}"
    for test in "${PASSED_TESTS[@]}"; do
        echo "   - $test"
    done
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  Warnings: ${#WARNINGS[@]}"
        for warning in "${WARNINGS[@]}"; do
            echo "   - $warning"
        done
    fi
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo ""
        echo "❌ Failed Tests: ${#FAILED_TESTS[@]}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "   - $test"
        done
        
        echo ""
        log "ERROR" "Gate A FAILED - ${#FAILED_TESTS[@]} required tests failed"
        echo ""
        echo "🔧 Logs available in /tmp/gate_a_*.log"
        echo "🔧 Fix failing tests and retry"
        return 1
    else
        echo ""
        log "SUCCESS" "Gate A PASSED - All required tests passed"
        
        if [ ${#WARNINGS[@]} -gt 0 ]; then
            echo ""
            echo "💡 Consider addressing warnings for improved code quality"
        fi
        
        echo ""
        echo "🎉 Ready to proceed to Gate B (DB + Integration)"
        return 0
    fi
}

# Handle interruption
trap 'log "WARNING" "Gate A testing interrupted"; exit 1' INT TERM

# Execute
main "$@"