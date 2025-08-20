#!/bin/bash
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
    "dotmac_analytics:latest"
    "dotmac_api_gateway:latest"
    "dotmac_billing:latest"
    "dotmac_core_events:latest"
    "dotmac_core_ops:latest"
    "dotmac_devtools:latest"
    "dotmac_identity:latest"
    "dotmac_networking:latest"
    "dotmac_platform:latest"
    "dotmac_services:latest"
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
        critical_file="$SCAN_DIR/${image//[:\/]/_}-critical.json"
        if [ -f "$critical_file" ]; then
            critical_count=$(jq length "$critical_file" 2>/dev/null || echo 0)
            if [ "$critical_count" -gt 0 ]; then
                echo "### $image: $critical_count critical"
                jq -r '.[] | "- \(.VulnerabilityID): \(.Title)"' "$critical_file"
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
