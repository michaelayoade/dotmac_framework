#!/bin/bash

# DotMac Framework Security Audit Script
# Comprehensive security assessment for production deployments

set -e

echo "🔒 DotMac Framework Security Audit"
echo "=================================="
echo "Started at: $(date)"
echo ""

# Configuration
AUDIT_OUTPUT_DIR="${1:-./security-audit-$(date +%Y%m%d-%H%M%S)}"
SEVERITY_THRESHOLD="${SEVERITY_THRESHOLD:-medium}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Audit counters
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0
PASSED_CHECKS=0

# Create audit output directory
mkdir -p "$AUDIT_OUTPUT_DIR"

log_issue() {
    local severity="$1"
    local message="$2"
    local recommendation="$3"
    
    case "$severity" in
        "CRITICAL")
            echo -e "${RED}❌ CRITICAL: $message${NC}"
            echo -e "   💡 Recommendation: $recommendation"
            ((CRITICAL_ISSUES++))
            ;;
        "HIGH")
            echo -e "${RED}⚠️  HIGH: $message${NC}"
            echo -e "   💡 Recommendation: $recommendation"
            ((HIGH_ISSUES++))
            ;;
        "MEDIUM")
            echo -e "${YELLOW}⚠️  MEDIUM: $message${NC}"
            echo -e "   💡 Recommendation: $recommendation"
            ((MEDIUM_ISSUES++))
            ;;
        "LOW")
            echo -e "${BLUE}ℹ️  LOW: $message${NC}"
            echo -e "   💡 Recommendation: $recommendation"
            ((LOW_ISSUES++))
            ;;
        "PASS")
            echo -e "${GREEN}✅ PASSED: $message${NC}"
            ((PASSED_CHECKS++))
            ;;
    esac
    
    # Log to file
    echo "[$severity] $(date): $message | Recommendation: $recommendation" >> "$AUDIT_OUTPUT_DIR/audit-results.log"
}

# ============================================================================
# 1. SECRETS AND CREDENTIALS AUDIT
# ============================================================================

echo "🔐 1. Secrets and Credentials Audit"
echo "------------------------------------"

# Check for hardcoded secrets
echo "Scanning for hardcoded secrets..."
if command -v rg >/dev/null 2>&1; then
    SECRET_PATTERNS="(password|secret|key|token|api_key|private_key|credential)\s*[:=]\s*['\"][^'\"]{8,}"
    
    SECRET_FINDINGS=$(rg -i "$SECRET_PATTERNS" src/ config/ --type py --type yaml --type json --type toml 2>/dev/null || true)
    
    if [ -n "$SECRET_FINDINGS" ]; then
        log_issue "CRITICAL" "Potential hardcoded secrets found in source code" "Move all secrets to OpenBao/environment variables and remove from code"
        echo "$SECRET_FINDINGS" > "$AUDIT_OUTPUT_DIR/hardcoded-secrets.txt"
    else
        log_issue "PASS" "No hardcoded secrets detected in source code"
    fi
else
    log_issue "MEDIUM" "ripgrep not available for secret scanning" "Install ripgrep for comprehensive secret detection"
fi

# Check environment files for example values
if find . -name "*.env*" -type f | head -1 | xargs grep -l "CHANGE_ME\|example\|password123\|secret123" >/dev/null 2>&1; then
    log_issue "HIGH" "Example/placeholder secrets found in environment files" "Replace all placeholder values with production secrets"
else
    log_issue "PASS" "No placeholder secrets in environment files"
fi

# Check for SSH keys in repository
if find . -name "id_rsa*" -o -name "*.pem" -o -name "*.key" | grep -v "/tmp/" | head -1 >/dev/null 2>&1; then
    log_issue "CRITICAL" "Private keys found in repository" "Remove private keys and add to .gitignore"
else
    log_issue "PASS" "No private keys found in repository"
fi

echo ""

# ============================================================================
# 2. DEPENDENCY VULNERABILITY SCAN
# ============================================================================

echo "📦 2. Dependency Vulnerability Scan"
echo "------------------------------------"

# Python dependencies
if [ -f "requirements.txt" ] && command -v safety >/dev/null 2>&1; then
    echo "Scanning Python dependencies with safety..."
    if ! safety check -r requirements.txt --json > "$AUDIT_OUTPUT_DIR/python-vulnerabilities.json" 2>/dev/null; then
        VULN_COUNT=$(jq '. | length' "$AUDIT_OUTPUT_DIR/python-vulnerabilities.json" 2>/dev/null || echo "0")
        if [ "$VULN_COUNT" -gt 0 ]; then
            log_issue "HIGH" "$VULN_COUNT Python dependency vulnerabilities found" "Review and update vulnerable packages in requirements.txt"
        fi
    else
        log_issue "PASS" "No known Python dependency vulnerabilities"
    fi
else
    log_issue "MEDIUM" "Python dependency scanning not available" "Install safety: pip install safety"
fi

# Node.js dependencies (if present)
if [ -f "frontend/package.json" ] && [ -f "frontend/pnpm-lock.yaml" ]; then
    echo "Scanning Node.js dependencies..."
    cd frontend
    if command -v pnpm >/dev/null 2>&1; then
        if ! pnpm audit --json > "../$AUDIT_OUTPUT_DIR/nodejs-vulnerabilities.json" 2>/dev/null; then
            VULN_COUNT=$(jq '.metadata.vulnerabilities.total' "../$AUDIT_OUTPUT_DIR/nodejs-vulnerabilities.json" 2>/dev/null || echo "0")
            if [ "$VULN_COUNT" -gt 0 ]; then
                log_issue "HIGH" "$VULN_COUNT Node.js dependency vulnerabilities found" "Run 'pnpm audit --fix' to resolve vulnerabilities"
            fi
        else
            log_issue "PASS" "No known Node.js dependency vulnerabilities"
        fi
    fi
    cd ..
fi

echo ""

# ============================================================================
# 3. DOCKER SECURITY SCAN
# ============================================================================

echo "🐳 3. Docker Security Scan"
echo "---------------------------"

if [ -f "Dockerfile" ] && command -v docker >/dev/null 2>&1; then
    # Check Dockerfile best practices
    echo "Analyzing Dockerfile security..."
    
    # Check for USER instruction
    if ! grep -q "^USER " Dockerfile; then
        log_issue "HIGH" "Dockerfile runs as root user" "Add 'USER <non-root-user>' instruction to Dockerfile"
    else
        log_issue "PASS" "Dockerfile uses non-root user"
    fi
    
    # Check for COPY/ADD with correct permissions
    if grep -q "COPY.*--chown=" Dockerfile || grep -q "ADD.*--chown=" Dockerfile; then
        log_issue "PASS" "Dockerfile uses proper file ownership"
    else
        log_issue "MEDIUM" "Dockerfile doesn't specify file ownership" "Use COPY --chown=user:group for better security"
    fi
    
    # Check for secrets in Dockerfile
    if grep -qi "password\|secret\|key" Dockerfile; then
        log_issue "CRITICAL" "Potential secrets found in Dockerfile" "Remove secrets from Dockerfile and use build-time secrets"
    else
        log_issue "PASS" "No secrets detected in Dockerfile"
    fi
    
    # Container image scanning (if available)
    if command -v trivy >/dev/null 2>&1; then
        echo "Scanning container images with Trivy..."
        trivy image --format json --output "$AUDIT_OUTPUT_DIR/container-vulnerabilities.json" \
               ghcr.io/dotmac/dotmac-framework:latest 2>/dev/null || true
        
        if [ -f "$AUDIT_OUTPUT_DIR/container-vulnerabilities.json" ]; then
            CRITICAL_VULNS=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' \
                           "$AUDIT_OUTPUT_DIR/container-vulnerabilities.json" 2>/dev/null || echo "0")
            HIGH_VULNS=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' \
                        "$AUDIT_OUTPUT_DIR/container-vulnerabilities.json" 2>/dev/null || echo "0")
            
            if [ "$CRITICAL_VULNS" -gt 0 ]; then
                log_issue "CRITICAL" "$CRITICAL_VULNS critical vulnerabilities in container image" "Update base image and rebuild container"
            elif [ "$HIGH_VULNS" -gt 0 ]; then
                log_issue "HIGH" "$HIGH_VULNS high-severity vulnerabilities in container image" "Update base image and rebuild container"
            else
                log_issue "PASS" "No critical or high-severity vulnerabilities in container image"
            fi
        fi
    else
        log_issue "MEDIUM" "Container vulnerability scanning not available" "Install Trivy for container security scanning"
    fi
else
    log_issue "LOW" "Docker security scan skipped" "Dockerfile not found or Docker not available"
fi

echo ""

# ============================================================================
# 4. KUBERNETES SECURITY SCAN
# ============================================================================

echo "☸️  4. Kubernetes Security Scan"
echo "--------------------------------"

if [ -d "k8s/" ] && command -v kubectl >/dev/null 2>&1; then
    echo "Analyzing Kubernetes configurations..."
    
    # Check for security contexts
    DEPLOYMENTS_WITHOUT_SECURITY_CONTEXT=$(find k8s/ -name "*.yaml" -exec grep -l "kind: Deployment" {} \; | \
        xargs grep -L "securityContext" | wc -l)
    
    if [ "$DEPLOYMENTS_WITHOUT_SECURITY_CONTEXT" -gt 0 ]; then
        log_issue "HIGH" "$DEPLOYMENTS_WITHOUT_SECURITY_CONTEXT deployments without security context" "Add securityContext with runAsNonRoot: true"
    else
        log_issue "PASS" "All deployments have security context configured"
    fi
    
    # Check for resource limits
    DEPLOYMENTS_WITHOUT_LIMITS=$(find k8s/ -name "*.yaml" -exec grep -l "kind: Deployment" {} \; | \
        xargs grep -L "resources:" | wc -l)
    
    if [ "$DEPLOYMENTS_WITHOUT_LIMITS" -gt 0 ]; then
        log_issue "MEDIUM" "$DEPLOYMENTS_WITHOUT_LIMITS deployments without resource limits" "Add CPU and memory limits to prevent resource exhaustion"
    else
        log_issue "PASS" "All deployments have resource limits"
    fi
    
    # Check for NetworkPolicies
    if find k8s/ -name "*.yaml" -exec grep -l "kind: NetworkPolicy" {} \; | head -1 >/dev/null; then
        log_issue "PASS" "NetworkPolicies configured for network isolation"
    else
        log_issue "HIGH" "No NetworkPolicies found" "Implement NetworkPolicies to isolate services"
    fi
    
    # Check for PodDisruptionBudgets
    if find k8s/ -name "*.yaml" -exec grep -l "kind: PodDisruptionBudget" {} \; | head -1 >/dev/null; then
        log_issue "PASS" "PodDisruptionBudgets configured for availability"
    else
        log_issue "MEDIUM" "No PodDisruptionBudgets found" "Add PodDisruptionBudgets for high availability"
    fi
    
    # Scan with kubesec if available
    if command -v kubesec >/dev/null 2>&1; then
        echo "Scanning with kubesec..."
        for file in $(find k8s/ -name "*.yaml" -exec grep -l "kind: Deployment" {} \;); do
            kubesec scan "$file" > "$AUDIT_OUTPUT_DIR/kubesec-$(basename $file).json" 2>/dev/null || true
        done
        log_issue "PASS" "Kubesec analysis completed"
    else
        log_issue "LOW" "Kubesec scanning not available" "Install kubesec for Kubernetes security analysis"
    fi
    
else
    log_issue "LOW" "Kubernetes security scan skipped" "Kubernetes configurations not found or kubectl not available"
fi

echo ""

# ============================================================================
# 5. TLS/SSL CONFIGURATION AUDIT
# ============================================================================

echo "🔒 5. TLS/SSL Configuration Audit"
echo "----------------------------------"

# Check TLS configuration files
if find config/ -name "*.hcl" -o -name "*.conf" | xargs grep -l "tls_disable.*0" >/dev/null 2>&1; then
    log_issue "PASS" "TLS enabled in configuration files"
else
    if find config/ -name "*.hcl" -o -name "*.conf" | xargs grep -l "tls_disable.*1" >/dev/null 2>&1; then
        log_issue "CRITICAL" "TLS disabled in configuration files" "Enable TLS for production deployment"
    fi
fi

# Check for weak TLS configuration
if find config/ -name "*.hcl" -o -name "*.conf" | xargs grep -l "tls_min_version.*tls10\|tls_min_version.*tls11" >/dev/null 2>&1; then
    log_issue "HIGH" "Weak TLS version configured" "Use TLS 1.2 or higher (tls_min_version = \"tls12\")"
else
    log_issue "PASS" "Strong TLS version configured"
fi

# Test live endpoints (if in production environment)
if [ "$ENVIRONMENT" = "production" ]; then
    DOMAINS=("api.dotmac.com" "admin.dotmac.com" "customer.dotmac.com")
    
    for domain in "${DOMAINS[@]}"; do
        if command -v openssl >/dev/null 2>&1; then
            echo "Testing TLS configuration for $domain..."
            
            # Check if site is accessible and using TLS
            if openssl s_client -connect "$domain:443" -servername "$domain" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
                log_issue "PASS" "Valid TLS certificate for $domain"
                
                # Check TLS version
                TLS_VERSION=$(openssl s_client -connect "$domain:443" -servername "$domain" </dev/null 2>&1 | grep "Protocol" | awk '{print $3}')
                if echo "$TLS_VERSION" | grep -q "TLSv1.[23]"; then
                    log_issue "PASS" "Strong TLS version ($TLS_VERSION) for $domain"
                else
                    log_issue "HIGH" "Weak TLS version ($TLS_VERSION) for $domain" "Configure server to use TLS 1.2 or higher"
                fi
                
            else
                log_issue "CRITICAL" "TLS certificate validation failed for $domain" "Fix certificate configuration"
            fi
        fi
    done
fi

echo ""

# ============================================================================
# 6. FILE PERMISSIONS AND SYSTEM SECURITY
# ============================================================================

echo "📁 6. File Permissions and System Security"
echo "-------------------------------------------"

# Check file permissions on sensitive files
SENSITIVE_FILES=("config/shared/openbao.hcl" "docker-compose.prod*.yml" "k8s/base/secrets.yaml")

for file in "${SENSITIVE_FILES[@]}"; do
    if [ -f "$file" ]; then
        PERMS=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null)
        if [ "$PERMS" = "600" ] || [ "$PERMS" = "640" ]; then
            log_issue "PASS" "Secure file permissions for $file ($PERMS)"
        else
            log_issue "MEDIUM" "Insecure file permissions for $file ($PERMS)" "chmod 600 $file"
        fi
    fi
done

# Check for world-writable files
WORLD_WRITABLE=$(find . -type f -perm -002 2>/dev/null | grep -v ".git" | head -5)
if [ -n "$WORLD_WRITABLE" ]; then
    log_issue "MEDIUM" "World-writable files found" "Remove world-write permissions from sensitive files"
    echo "$WORLD_WRITABLE" >> "$AUDIT_OUTPUT_DIR/world-writable-files.txt"
else
    log_issue "PASS" "No world-writable files detected"
fi

echo ""

# ============================================================================
# 7. CODE SECURITY ANALYSIS
# ============================================================================

echo "🔍 7. Code Security Analysis"
echo "-----------------------------"

# Check for SQL injection patterns
if command -v rg >/dev/null 2>&1; then
    SQL_INJECTION_PATTERNS="(execute|query)\s*\(\s*['\"].*%.*['\"]"
    
    if rg -i "$SQL_INJECTION_PATTERNS" src/ --type py >/dev/null 2>&1; then
        log_issue "HIGH" "Potential SQL injection vulnerabilities found" "Use parameterized queries and avoid string concatenation"
    else
        log_issue "PASS" "No obvious SQL injection patterns detected"
    fi
    
    # Check for command injection patterns
    COMMAND_INJECTION_PATTERNS="(subprocess|os\.system|exec|eval)\s*\("
    
    if rg -i "$COMMAND_INJECTION_PATTERNS" src/ --type py >/dev/null 2>&1; then
        log_issue "MEDIUM" "Potential command injection vulnerabilities found" "Validate and sanitize all external inputs"
    else
        log_issue "PASS" "No obvious command injection patterns detected"
    fi
fi

# Static analysis with bandit (if available)
if command -v bandit >/dev/null 2>&1 && [ -d "src/" ]; then
    echo "Running Bandit security analysis..."
    if bandit -r src/ -f json -o "$AUDIT_OUTPUT_DIR/bandit-results.json" -ll 2>/dev/null; then
        HIGH_ISSUES_BANDIT=$(jq '[.results[] | select(.issue_severity == "HIGH")] | length' "$AUDIT_OUTPUT_DIR/bandit-results.json" 2>/dev/null || echo "0")
        MEDIUM_ISSUES_BANDIT=$(jq '[.results[] | select(.issue_severity == "MEDIUM")] | length' "$AUDIT_OUTPUT_DIR/bandit-results.json" 2>/dev/null || echo "0")
        
        if [ "$HIGH_ISSUES_BANDIT" -gt 0 ]; then
            log_issue "HIGH" "$HIGH_ISSUES_BANDIT high-severity security issues found by Bandit" "Review and fix issues in bandit-results.json"
        elif [ "$MEDIUM_ISSUES_BANDIT" -gt 0 ]; then
            log_issue "MEDIUM" "$MEDIUM_ISSUES_BANDIT medium-severity security issues found by Bandit" "Review and fix issues in bandit-results.json"
        else
            log_issue "PASS" "No high or medium-severity issues found by Bandit"
        fi
    fi
else
    log_issue "LOW" "Static security analysis not available" "Install bandit: pip install bandit"
fi

echo ""

# ============================================================================
# AUDIT SUMMARY
# ============================================================================

echo "📊 Security Audit Summary"
echo "========================="
echo "Audit completed at: $(date)"
echo "Output directory: $AUDIT_OUTPUT_DIR"
echo ""
echo "Results:"
echo -e "  ${GREEN}✅ Passed checks: $PASSED_CHECKS${NC}"
echo -e "  ${BLUE}ℹ️  Low issues: $LOW_ISSUES${NC}"
echo -e "  ${YELLOW}⚠️  Medium issues: $MEDIUM_ISSUES${NC}"
echo -e "  ${RED}⚠️  High issues: $HIGH_ISSUES${NC}"
echo -e "  ${RED}❌ Critical issues: $CRITICAL_ISSUES${NC}"
echo ""

# Generate audit report
cat > "$AUDIT_OUTPUT_DIR/audit-summary.json" <<EOF
{
  "audit_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "severity_threshold": "$SEVERITY_THRESHOLD",
  "results": {
    "passed": $PASSED_CHECKS,
    "low": $LOW_ISSUES,
    "medium": $MEDIUM_ISSUES,
    "high": $HIGH_ISSUES,
    "critical": $CRITICAL_ISSUES
  },
  "audit_directory": "$AUDIT_OUTPUT_DIR"
}
EOF

# Determine exit code based on severity threshold
EXIT_CODE=0

case "$SEVERITY_THRESHOLD" in
    "critical")
        if [ $CRITICAL_ISSUES -gt 0 ]; then EXIT_CODE=1; fi
        ;;
    "high")
        if [ $CRITICAL_ISSUES -gt 0 ] || [ $HIGH_ISSUES -gt 0 ]; then EXIT_CODE=1; fi
        ;;
    "medium")
        if [ $CRITICAL_ISSUES -gt 0 ] || [ $HIGH_ISSUES -gt 0 ] || [ $MEDIUM_ISSUES -gt 0 ]; then EXIT_CODE=1; fi
        ;;
    "low")
        if [ $CRITICAL_ISSUES -gt 0 ] || [ $HIGH_ISSUES -gt 0 ] || [ $MEDIUM_ISSUES -gt 0 ] || [ $LOW_ISSUES -gt 0 ]; then EXIT_CODE=1; fi
        ;;
esac

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}🎉 Security audit passed with severity threshold: $SEVERITY_THRESHOLD${NC}"
else
    echo -e "${RED}🚨 Security audit failed with severity threshold: $SEVERITY_THRESHOLD${NC}"
    echo -e "Review issues above and in $AUDIT_OUTPUT_DIR/audit-results.log"
fi

echo ""
echo "Next steps:"
echo "1. Review detailed results in $AUDIT_OUTPUT_DIR/"
echo "2. Address critical and high-severity issues immediately"
echo "3. Plan remediation for medium and low-severity issues"
echo "4. Schedule regular security audits (monthly recommended)"
echo "5. Update security documentation based on findings"

exit $EXIT_CODE