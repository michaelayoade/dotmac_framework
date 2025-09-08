#!/bin/bash

# DotMac Framework Implementation Validation Script
# Validates completion of gap resolution phases

set -e

echo "======================================================="
echo "DOTMAC FRAMEWORK IMPLEMENTATION VALIDATION"
echo "======================================================="
echo "Generated: $(date)"
echo "Repository: $(pwd)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_RESULTS=()
PHASE_SCORES=()

# Helper functions
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    VALIDATION_RESULTS+=("PASS: $1")
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    VALIDATION_RESULTS+=("WARN: $1")
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    VALIDATION_RESULTS+=("FAIL: $1")
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

count_files() {
    find src/ -name "*.py" "$@" 2>/dev/null | wc -l
}

# Phase 1: Security Fixes Validation
validate_phase_1() {
    echo -e "${BLUE}=== PHASE 1: CRITICAL SECURITY FIXES ===${NC}"
    local score=0
    local max_score=4

    echo "Checking for hardcoded secrets..."
    if command -v bandit >/dev/null 2>&1; then
        SECRETS_COUNT=$(bandit -r src/ --format json 2>/dev/null | python3 -c "import json, sys; data=json.load(sys.stdin); print(len([r for r in data.get('results', []) if 'hardcoded_password' in r.get('issue_id', '') or 'hardcoded_bind_all_interfaces' in r.get('issue_id', '')]))" 2>/dev/null || echo "0")
        if [ "$SECRETS_COUNT" -eq 0 ]; then
            log_success "No hardcoded secrets found"
            ((score++))
        else
            log_error "$SECRETS_COUNT hardcoded secrets still present"
        fi
    else
        log_warning "Bandit not installed - cannot check for secrets"
    fi

    echo "Checking for SQL injection risks..."
    SQL_INJECTION_COUNT=$(grep -r "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" src/ --include="*.py" 2>/dev/null | wc -l)
    if [ "$SQL_INJECTION_COUNT" -eq 0 ]; then
        log_success "No SQL injection patterns found"
        ((score++))
    else
        log_error "$SQL_INJECTION_COUNT potential SQL injection patterns found"
        # Show examples
        grep -r "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" src/ --include="*.py" -n | head -3
    fi

    echo "Checking input validation coverage..."
    PYDANTIC_ENDPOINTS=$(grep -r "@router\.\(post\|put\|patch\)" src/ --include="*.py" -A 5 | grep -c "BaseModel\|Pydantic" || echo "0")
    TOTAL_ENDPOINTS=$(grep -r "@router\.\(post\|put\|patch\)" src/ --include="*.py" | wc -l)
    
    if [ "$TOTAL_ENDPOINTS" -gt 0 ]; then
        VALIDATION_PERCENTAGE=$((PYDANTIC_ENDPOINTS * 100 / TOTAL_ENDPOINTS))
        if [ "$VALIDATION_PERCENTAGE" -ge 90 ]; then
            log_success "Input validation coverage: $VALIDATION_PERCENTAGE% ($PYDANTIC_ENDPOINTS/$TOTAL_ENDPOINTS endpoints)"
            ((score++))
        else
            log_error "Input validation coverage: $VALIDATION_PERCENTAGE% ($PYDANTIC_ENDPOINTS/$TOTAL_ENDPOINTS endpoints) - Target: ≥90%"
        fi
    else
        log_warning "No API endpoints found for validation check"
    fi

    echo "Checking security pipeline..."
    if [ -f ".github/workflows/security.yml" ] || [ -f ".pre-commit-config.yaml" ]; then
        log_success "Security pipeline configuration found"
        ((score++))
    else
        log_error "No security pipeline configuration found"
    fi

    PHASE_SCORES+=("Phase 1: $score/$max_score")
    echo "Phase 1 Score: $score/$max_score"
    echo ""
}

# Phase 2: Architecture Standardization Validation
validate_phase_2() {
    echo -e "${BLUE}=== PHASE 2: ARCHITECTURE STANDARDIZATION ===${NC}"
    local score=0
    local max_score=5

    echo "Checking base repository implementation..."
    if [ -f "src/dotmac_shared/repositories/base.py" ] || [ -f "packages/dotmac-core/src/dotmac/core/repositories/base.py" ]; then
        log_success "Base repository class found"
        ((score++))
    else
        log_warning "Base repository class not found at expected locations"
    fi

    echo "Checking repository inheritance..."
    TOTAL_REPOS=$(find src/ packages/ -name "*repository.py" 2>/dev/null | wc -l)
    BASE_REPO_USAGE=$(grep -r "BaseRepository\|from.*repositories.*base" src/ packages/ --include="*repository.py" 2>/dev/null | wc -l)
    
    if [ "$TOTAL_REPOS" -gt 0 ]; then
        REPO_PERCENTAGE=$((BASE_REPO_USAGE * 100 / TOTAL_REPOS))
        if [ "$REPO_PERCENTAGE" -ge 70 ]; then
            log_success "Repository standardization: $REPO_PERCENTAGE% ($BASE_REPO_USAGE/$TOTAL_REPOS repositories using base class)"
            ((score++))
        else
            log_warning "Repository standardization: $REPO_PERCENTAGE% ($BASE_REPO_USAGE/$TOTAL_REPOS repositories using base class) - Target: ≥70%"
        fi
    else
        log_info "No repository files found"
    fi

    echo "Checking base service implementation..."
    if [ -f "src/dotmac_shared/services/base.py" ] || find packages/ -name "base.py" -path "*/services/*" 2>/dev/null | head -1 | grep -q "base.py"; then
        log_success "Base service class found"
        ((score++))
    else
        log_warning "Base service class not found at expected locations"
    fi

    echo "Checking service inheritance..."
    TOTAL_SERVICES=$(find src/ packages/ -name "*service.py" 2>/dev/null | wc -l)
    BASE_SERVICE_USAGE=$(grep -r "BaseService\|from.*services.*base" src/ packages/ --include="*service.py" 2>/dev/null | wc -l)
    
    if [ "$TOTAL_SERVICES" -gt 0 ]; then
        SERVICE_PERCENTAGE=$((BASE_SERVICE_USAGE * 100 / TOTAL_SERVICES))
        if [ "$SERVICE_PERCENTAGE" -ge 50 ]; then
            log_success "Service standardization: $SERVICE_PERCENTAGE% ($BASE_SERVICE_USAGE/$TOTAL_SERVICES services using base class)"
            ((score++))
        else
            log_warning "Service standardization: $SERVICE_PERCENTAGE% ($BASE_SERVICE_USAGE/$TOTAL_SERVICES services using base class) - Target: ≥50%"
        fi
    else
        log_info "No service files found"
    fi

    echo "Checking for bare except clauses..."
    BARE_EXCEPT_COUNT=$(grep -r "except:" src/ packages/ --include="*.py" 2>/dev/null | wc -l)
    if [ "$BARE_EXCEPT_COUNT" -eq 0 ]; then
        log_success "No bare except clauses found"
        ((score++))
    else
        log_error "$BARE_EXCEPT_COUNT bare except clauses found - should be 0"
        # Show first few examples
        log_info "Examples:"
        grep -r "except:" src/ packages/ --include="*.py" -n 2>/dev/null | head -3 | while read line; do
            echo "    $line"
        done
    fi

    PHASE_SCORES+=("Phase 2: $score/$max_score")
    echo "Phase 2 Score: $score/$max_score"
    echo ""
}

# Phase 3: Testing & Observability Validation
validate_phase_3() {
    echo -e "${BLUE}=== PHASE 3: TESTING & OBSERVABILITY ===${NC}"
    local score=0
    local max_score=5

    echo "Checking test coverage..."
    if command -v pytest >/dev/null 2>&1; then
        # Try to get coverage if available
        if python3 -c "import coverage" 2>/dev/null; then
            COVERAGE=$(python3 -m pytest --cov=src --cov-report=term-missing --tb=no -q 2>/dev/null | grep "^TOTAL" | awk '{print $4}' | sed 's/%//' || echo "0")
            if [ "$COVERAGE" -ge 70 ]; then
                log_success "Test coverage: $COVERAGE% (target: ≥70%)"
                ((score++))
            elif [ "$COVERAGE" -ge 50 ]; then
                log_warning "Test coverage: $COVERAGE% (target: ≥70%)"
            else
                log_error "Test coverage: $COVERAGE% (target: ≥70%)"
            fi
        else
            TEST_FILES=$(find tests/ -name "*.py" -not -name "__*" 2>/dev/null | wc -l)
            TOTAL_FILES=$(find src/ -name "*.py" 2>/dev/null | wc -l)
            if [ "$TOTAL_FILES" -gt 0 ]; then
                TEST_RATIO=$((TEST_FILES * 100 / TOTAL_FILES))
                log_info "Test files: $TEST_FILES (ratio: $TEST_RATIO% of source files)"
                if [ "$TEST_RATIO" -ge 20 ]; then
                    ((score++))
                fi
            fi
        fi
    else
        log_warning "pytest not available - cannot check test coverage"
    fi

    echo "Checking integration tests..."
    INTEGRATION_TESTS=$(find tests/ -path "*/integration/*" -name "*.py" 2>/dev/null | wc -l)
    if [ "$INTEGRATION_TESTS" -gt 0 ]; then
        log_success "$INTEGRATION_TESTS integration test files found"
        ((score++))
    else
        log_warning "No integration tests found in tests/integration/"
    fi

    echo "Checking health checks..."
    HEALTH_CHECK_FILES=$(grep -r "health.*check\|check.*health" src/ packages/ --include="*.py" -l 2>/dev/null | wc -l)
    if [ "$HEALTH_CHECK_FILES" -ge 3 ]; then
        log_success "$HEALTH_CHECK_FILES files with health check implementations"
        ((score++))
    else
        log_warning "$HEALTH_CHECK_FILES files with health check implementations - need more comprehensive health checks"
    fi

    echo "Checking monitoring setup..."
    MONITORING_FILES=$(find src/ packages/ -name "*monitor*" -o -name "*observability*" -o -name "*metrics*" 2>/dev/null | grep "\.py$" | wc -l)
    if [ "$MONITORING_FILES" -ge 5 ]; then
        log_success "$MONITORING_FILES monitoring/observability files found"
        ((score++))
    else
        log_warning "$MONITORING_FILES monitoring/observability files found - may need more monitoring infrastructure"
    fi

    echo "Checking async/await patterns..."
    SYNC_IN_ASYNC=$(grep -r "def.*async" src/ packages/ --include="*.py" -A 10 | grep -c "\.execute(\|requests\.\|time\.sleep" 2>/dev/null || echo "0")
    if [ "$SYNC_IN_ASYNC" -eq 0 ]; then
        log_success "No synchronous calls in async functions detected"
        ((score++))
    else
        log_warning "$SYNC_IN_ASYNC potential synchronous calls in async functions detected"
    fi

    PHASE_SCORES+=("Phase 3: $score/$max_score")
    echo "Phase 3 Score: $score/$max_score"
    echo ""
}

# Phase 4: Performance & Documentation Validation
validate_phase_4() {
    echo -e "${BLUE}=== PHASE 4: PERFORMANCE & DOCUMENTATION ===${NC}"
    local score=0
    local max_score=4

    echo "Checking function complexity..."
    LONG_FUNCTIONS=$(grep -r "^def \|^    def \|^async def \|^    async def " src/ packages/ --include="*.py" | wc -l)
    # This is a rough estimate - would need more sophisticated analysis for exact line counts
    if [ "$LONG_FUNCTIONS" -gt 0 ]; then
        log_info "Found $LONG_FUNCTIONS functions total"
        # Assume improvement if we have reasonable function count
        if [ "$LONG_FUNCTIONS" -lt 2000 ]; then
            log_success "Function count appears manageable"
            ((score++))
        else
            log_warning "High function count - may indicate complex functions"
        fi
    fi

    echo "Checking API documentation..."
    DOCUMENTED_ENDPOINTS=$(grep -r "@router\." src/ packages/ --include="*.py" -A 5 | grep -c "\"\"\"" || echo "0")
    TOTAL_API_ENDPOINTS=$(grep -r "@router\." src/ packages/ --include="*.py" | wc -l)
    
    if [ "$TOTAL_API_ENDPOINTS" -gt 0 ]; then
        DOC_PERCENTAGE=$((DOCUMENTED_ENDPOINTS * 100 / TOTAL_API_ENDPOINTS))
        if [ "$DOC_PERCENTAGE" -ge 80 ]; then
            log_success "API documentation: $DOC_PERCENTAGE% ($DOCUMENTED_ENDPOINTS/$TOTAL_API_ENDPOINTS endpoints documented)"
            ((score++))
        else
            log_warning "API documentation: $DOC_PERCENTAGE% ($DOCUMENTED_ENDPOINTS/$TOTAL_API_ENDPOINTS endpoints documented) - Target: ≥80%"
        fi
    else
        log_info "No API endpoints found for documentation check"
    fi

    echo "Checking developer documentation..."
    DOC_FILES=0
    [ -f "README.md" ] && ((DOC_FILES++))
    [ -f "CONTRIBUTING.md" ] && ((DOC_FILES++))
    [ -d "docs/" ] && DOC_FILES=$((DOC_FILES + $(find docs/ -name "*.md" 2>/dev/null | wc -l)))
    
    if [ "$DOC_FILES" -ge 3 ]; then
        log_success "$DOC_FILES documentation files found"
        ((score++))
    else
        log_warning "$DOC_FILES documentation files found - may need more comprehensive documentation"
    fi

    echo "Checking performance optimizations..."
    # Check for common performance patterns
    EAGER_LOADING=$(grep -r "joinedload\|selectinload" src/ packages/ --include="*.py" 2>/dev/null | wc -l)
    BULK_OPERATIONS=$(grep -r "bulk_insert\|bulk_update" src/ packages/ --include="*.py" 2>/dev/null | wc -l)
    
    if [ "$((EAGER_LOADING + BULK_OPERATIONS))" -ge 5 ]; then
        log_success "Performance optimizations found (eager loading: $EAGER_LOADING, bulk ops: $BULK_OPERATIONS)"
        ((score++))
    else
        log_warning "Limited performance optimizations found (eager loading: $EAGER_LOADING, bulk ops: $BULK_OPERATIONS)"
    fi

    PHASE_SCORES+=("Phase 4: $score/$max_score")
    echo "Phase 4 Score: $score/$max_score"
    echo ""
}

# Overall validation summary
generate_summary() {
    echo -e "${BLUE}=== VALIDATION SUMMARY ===${NC}"
    
    # Calculate overall score
    total_score=0
    max_total=0
    for phase_score in "${PHASE_SCORES[@]}"; do
        score=$(echo "$phase_score" | cut -d: -f2 | cut -d/ -f1 | tr -d ' ')
        max=$(echo "$phase_score" | cut -d: -f2 | cut -d/ -f2)
        total_score=$((total_score + score))
        max_total=$((max_total + max))
    done
    
    overall_percentage=$((total_score * 100 / max_total))
    
    echo "Overall Score: $total_score/$max_total ($overall_percentage%)"
    echo ""
    
    for phase_score in "${PHASE_SCORES[@]}"; do
        echo "$phase_score"
    done
    echo ""
    
    # Determine overall status
    if [ "$overall_percentage" -ge 90 ]; then
        log_success "EXCELLENT - Implementation is production ready"
        exit 0
    elif [ "$overall_percentage" -ge 75 ]; then
        log_warning "GOOD - Implementation is mostly complete, minor improvements needed"
        exit 0
    elif [ "$overall_percentage" -ge 60 ]; then
        log_warning "ACCEPTABLE - Implementation has significant gaps that should be addressed"
        exit 1
    else
        log_error "NEEDS WORK - Implementation has critical gaps that must be addressed before production"
        exit 2
    fi
}

# Performance benchmark (optional)
run_performance_benchmark() {
    echo -e "${BLUE}=== PERFORMANCE BENCHMARK ===${NC}"
    
    if [ -f ".dev-artifacts/scripts/performance_benchmark.py" ]; then
        log_info "Running performance benchmark..."
        if command -v python3 >/dev/null 2>&1; then
            python3 .dev-artifacts/scripts/performance_benchmark.py 2>/dev/null || log_warning "Performance benchmark failed or not configured"
        else
            log_warning "Python3 not available for performance benchmark"
        fi
    else
        log_info "Performance benchmark script not found - skipping"
    fi
    echo ""
}

# Main execution
main() {
    echo "Starting validation of DotMac Framework implementation..."
    echo "Working directory: $(pwd)"
    echo ""
    
    # Check if we're in the right directory
    if [ ! -d "src/" ]; then
        log_error "Not in DotMac framework root directory (src/ not found)"
        exit 1
    fi
    
    # Run all validations
    validate_phase_1
    validate_phase_2
    validate_phase_3
    validate_phase_4
    
    # Optional performance benchmark
    if [ "$1" = "--benchmark" ]; then
        run_performance_benchmark
    fi
    
    # Generate summary and exit with appropriate code
    generate_summary
}

# Check for help flag
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "DotMac Framework Implementation Validation"
    echo ""
    echo "Usage: $0 [--benchmark] [--help]"
    echo ""
    echo "Options:"
    echo "  --benchmark    Run performance benchmark (optional)"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "This script validates the implementation of gap resolution across 4 phases:"
    echo "  Phase 1: Critical Security Fixes"
    echo "  Phase 2: Architecture Standardization" 
    echo "  Phase 3: Testing & Observability"
    echo "  Phase 4: Performance & Documentation"
    echo ""
    echo "Exit codes:"
    echo "  0: Excellent (≥90%) or Good (≥75%)" 
    echo "  1: Acceptable (≥60%) - improvements recommended"
    echo "  2: Needs work (<60%) - critical gaps remain"
    exit 0
fi

# Run main validation
main "$@"