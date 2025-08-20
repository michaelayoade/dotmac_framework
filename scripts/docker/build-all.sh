#!/bin/bash
# Build all DotMac services
set -e

echo "🚀 Building all DotMac services..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-latest}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Build services in dependency order
SERVICES=("dotmac_analytics" "dotmac_api_gateway" "dotmac_billing" "dotmac_core_events" "dotmac_core_ops" "dotmac_devtools" "dotmac_identity" "dotmac_networking" "dotmac_platform" "dotmac_services")

for SERVICE in "${SERVICES[@]}"; do
    echo "📦 Building $SERVICE..."
    
    if [ -d "$SERVICE" ]; then
        cd "$SERVICE"
        
        # Build with security scanning
        docker build \
            --target security-scanner \
            --tag "$SERVICE:security-scan" \
            --build-arg BUILD_DATE="$BUILD_DATE" \
            --build-arg VERSION="$VERSION" \
            --build-arg VCS_REF="$VCS_REF" \
            . || echo "⚠️  Security scan failed for $SERVICE"
        
        # Build production image
        docker build \
            --target production \
            --tag "$SERVICE:$VERSION" \
            --tag "$SERVICE:latest" \
            --build-arg BUILD_DATE="$BUILD_DATE" \
            --build-arg VERSION="$VERSION" \
            --build-arg VCS_REF="$VCS_REF" \
            .
        
        cd ..
        echo "✅ Built $SERVICE"
    else
        echo "⚠️  Directory $SERVICE not found"
    fi
done

echo "🎉 All services built successfully!"
