#!/bin/bash
# Build dotmac_api_gateway
set -e

echo "📦 Building dotmac_api_gateway..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-latest}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TARGET=${TARGET:-production}

cd dotmac_api_gateway

# Build with specified target
docker build \
    --target "$TARGET" \
    --tag "dotmac_api_gateway:$VERSION" \
    --tag "dotmac_api_gateway:latest" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg SERVICE_NAME="dotmac_api_gateway" \
    --build-arg SERVICE_DESCRIPTION="DotMac API Gateway Service" \
    .

echo "✅ Built dotmac_api_gateway:$VERSION"

# Optional: Run security scan
if [ "${SECURITY_SCAN:-false}" = "true" ]; then
    echo "🔒 Running security scan..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image "dotmac_api_gateway:$VERSION"
fi

# Optional: Run tests
if [ "${RUN_TESTS:-false}" = "true" ]; then
    echo "🧪 Running tests..."
    docker build --target testing --tag "dotmac_api_gateway:test" .
    docker run --rm "dotmac_api_gateway:test"
fi
