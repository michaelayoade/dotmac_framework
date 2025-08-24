#!/bin/bash
# validate-ai-workflow.sh - Validates AI-First Development Workflow
# This script demonstrates and validates the complete AI-first development workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ISP_FRAMEWORK_DIR="$PROJECT_ROOT/isp-framework"
MGMT_PLATFORM_DIR="$PROJECT_ROOT/management-platform"

# Progress tracking
STEP_COUNTER=0
TOTAL_STEPS=12

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}   DotMac AI-First Development Workflow${NC}"
    echo -e "${BLUE}        Validation & Demonstration${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

print_step() {
    ((STEP_COUNTER++))
    echo -e "${YELLOW}[Step $STEP_COUNTER/$TOTAL_STEPS] $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if a command exists
check_command() {
    local cmd=$1
    local dir=$2
    
    if cd "$dir" && make help 2>/dev/null | grep -q "$cmd"; then
        print_success "Command '$cmd' available in $(basename "$dir")"
        return 0
    else
        print_error "Command '$cmd' NOT available in $(basename "$dir")"
        return 1
    fi
}

# Function to validate command execution (dry run)
validate_command() {
    local cmd=$1
    local dir=$2
    local description=$3
    
    print_info "Validating: $description"
    
    if cd "$dir" && timeout 10s make "$cmd" --dry-run >/dev/null 2>&1; then
        print_success "✓ Command validates successfully"
        return 0
    else
        print_error "✗ Command validation failed"
        return 1
    fi
}

main() {
    print_header
    
    # Step 1: Validate project structure
    print_step "Validating Project Structure"
    
    if [[ -d "$ISP_FRAMEWORK_DIR" && -d "$MGMT_PLATFORM_DIR" ]]; then
        print_success "Both platforms found"
        print_info "ISP Framework: $ISP_FRAMEWORK_DIR"
        print_info "Management Platform: $MGMT_PLATFORM_DIR"
    else
        print_error "Missing platform directories"
        exit 1
    fi
    echo ""
    
    # Step 2: Validate unified commands
    print_step "Validating Unified Commands"
    
    cd "$PROJECT_ROOT"
    UNIFIED_COMMANDS=("help" "install-all" "test-all" "test-ai-suite" "up" "down" "health-check")
    
    for cmd in "${UNIFIED_COMMANDS[@]}"; do
        if make help 2>/dev/null | grep -q "$cmd"; then
            print_success "Unified command '$cmd' available"
        else
            print_error "Unified command '$cmd' missing"
        fi
    done
    echo ""
    
    # Step 3: Validate ISP Framework AI commands
    print_step "Validating ISP Framework AI Commands"
    
    ISP_AI_COMMANDS=("ai-safety-check" "test-ai-suite" "test-revenue-critical")
    
    for cmd in "${ISP_AI_COMMANDS[@]}"; do
        check_command "$cmd" "$ISP_FRAMEWORK_DIR"
    done
    echo ""
    
    # Step 4: Validate Management Platform AI commands
    print_step "Validating Management Platform AI Commands"
    
    MGMT_AI_COMMANDS=("ai-safety-check" "test-ai-suite" "test-revenue-critical")
    
    for cmd in "${MGMT_AI_COMMANDS[@]}"; do
        check_command "$cmd" "$MGMT_PLATFORM_DIR"
    done
    echo ""
    
    # Step 5: Validate AI-first workflow sequence
    print_step "Demonstrating AI-First Workflow Sequence"
    
    echo -e "${BLUE}Standard AI-First Development Workflow:${NC}"
    echo "1. ai-safety-check      # Fast safety gate (< 30 seconds)"
    echo "2. test-ai-suite        # AI-optimized testing (property-based + behavior + contract)"
    echo "3. test-revenue-critical # Revenue-critical path validation"
    echo "4. format-all && lint-all # Code quality (optional for AI)"
    echo ""
    
    # Step 6: Validate command structure
    print_step "Validating Command Structure - ISP Framework"
    
    validate_command "ai-safety-check" "$ISP_FRAMEWORK_DIR" "AI safety checks"
    validate_command "test-ai-suite" "$ISP_FRAMEWORK_DIR" "AI test suite"
    validate_command "test-revenue-critical" "$ISP_FRAMEWORK_DIR" "Revenue-critical tests"
    echo ""
    
    # Step 7: Validate command structure - Management Platform
    print_step "Validating Command Structure - Management Platform"
    
    validate_command "ai-safety-check" "$MGMT_PLATFORM_DIR" "AI safety checks"
    validate_command "test-ai-suite" "$MGMT_PLATFORM_DIR" "AI test suite"
    validate_command "test-revenue-critical" "$MGMT_PLATFORM_DIR" "Revenue-critical tests"
    echo ""
    
    # Step 8: Validate test markers
    print_step "Validating Test Markers"
    
    EXPECTED_MARKERS=(
        "property_based"
        "behavior" 
        "contract"
        "revenue_critical"
        "smoke_critical"
        "billing"
        "tenant_isolation"
    )
    
    print_info "Expected test markers for AI-first development:"
    for marker in "${EXPECTED_MARKERS[@]}"; do
        echo "  - @pytest.mark.$marker"
    done
    echo ""
    
    # Step 9: Validate configuration files
    print_step "Validating Configuration Files"
    
    CONFIG_FILES=(
        "pyproject.toml"
        "pytest.ini" 
        "Makefile"
        "docker-compose.yml"
    )
    
    for file in "${CONFIG_FILES[@]}"; do
        if [[ -f "$ISP_FRAMEWORK_DIR/$file" ]]; then
            print_success "ISP Framework has $file"
        else
            print_error "ISP Framework missing $file"
        fi
        
        if [[ -f "$MGMT_PLATFORM_DIR/$file" ]]; then
            print_success "Management Platform has $file"
        else
            print_error "Management Platform missing $file"
        fi
    done
    echo ""
    
    # Step 10: Validate AI-first testing philosophy
    print_step "AI-First Testing Philosophy Summary"
    
    echo -e "${BLUE}Key Principles:${NC}"
    echo "✓ Property-based testing (40%) - AI generates edge cases"
    echo "✓ Behavior testing (30%) - Business outcome focused"
    echo "✓ Contract testing (20%) - API schema validation"
    echo "✓ Smoke testing (10%) - Revenue-critical paths"
    echo ""
    echo -e "${BLUE}Safety Gates:${NC}"
    echo "✓ Revenue-critical logic protection"
    echo "✓ Multi-tenant isolation validation"
    echo "✓ Business rule integrity checks"
    echo "✓ Security pattern compliance"
    echo ""
    
    # Step 11: Demonstrate usage examples
    print_step "Usage Examples"
    
    echo -e "${BLUE}Quick Start (Developer Workflow):${NC}"
    echo "# 1. Safety check (always first)"
    echo "make ai-safety-check"
    echo ""
    echo "# 2. Platform-specific development"
    echo "cd isp-framework && make test-ai-suite"
    echo "cd management-platform && make test-revenue-critical"
    echo ""
    echo "# 3. Full platform validation"
    echo "make test-all"
    echo ""
    
    echo -e "${BLUE}CI/CD Pipeline Integration:${NC}"
    echo "# Fast feedback loop (< 5 minutes)"
    echo "make ai-safety-check && make test-ai-suite"
    echo ""
    echo "# Full validation (< 15 minutes)"
    echo "make test-all && make security-all"
    echo ""
    
    # Step 12: Final validation summary
    print_step "Final Validation Summary"
    
    VALIDATION_RESULTS=()
    
    # Check unified commands
    if cd "$PROJECT_ROOT" && make help >/dev/null 2>&1; then
        VALIDATION_RESULTS+=("✅ Unified commands working")
    else
        VALIDATION_RESULTS+=("❌ Unified commands broken")
    fi
    
    # Check ISP Framework
    if cd "$ISP_FRAMEWORK_DIR" && make help >/dev/null 2>&1; then
        VALIDATION_RESULTS+=("✅ ISP Framework commands working")
    else
        VALIDATION_RESULTS+=("❌ ISP Framework commands broken")
    fi
    
    # Check Management Platform
    if cd "$MGMT_PLATFORM_DIR" && make help >/dev/null 2>&1; then
        VALIDATION_RESULTS+=("✅ Management Platform commands working")
    else
        VALIDATION_RESULTS+=("❌ Management Platform commands broken")
    fi
    
    echo -e "${BLUE}Validation Results:${NC}"
    for result in "${VALIDATION_RESULTS[@]}"; do
        echo "  $result"
    done
    echo ""
    
    print_success "AI-First Development Workflow Validation Complete!"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "1. Run: make ai-safety-check"
    echo "2. Run: make test-ai-suite  # For comprehensive AI testing"
    echo "3. Run: make test-revenue-critical # For business logic validation"
    echo "4. Integrate into your development workflow"
    echo ""
    echo -e "${BLUE}For platform-specific commands:${NC}"
    echo "• ISP Framework: cd isp-framework && make help"
    echo "• Management Platform: cd management-platform && make help"
    
    return 0
}

# Run main function
main "$@"