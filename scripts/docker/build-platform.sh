#!/bin/bash
# Build dotmac_platform
set -e

echo "📦 Building dotmac_platform..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-latest}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TARGET=${TARGET:-production}

cd dotmac_platform

# Build with specified target
docker build \
    --target "$TARGET" \
    --tag "dotmac_platform:$VERSION" \
    --tag "dotmac_platform:latest" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg SERVICE_NAME="dotmac_platform" \
    --build-arg SERVICE_DESCRIPTION="DotMac Platform Core SDK" \
    .

echo "✅ Built dotmac_platform:$VERSION"

# Optional: Run security scan
if [ "${SECURITY_SCAN:-false}" = "true" ]; then
    echo "🔒 Running security scan..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image "dotmac_platform:$VERSION"
fi

# Optional: Run tests
if [ "${RUN_TESTS:-false}" = "true" ]; then
    echo "🧪 Running tests..."
    docker build --target testing --tag "dotmac_platform:test" .
    docker run --rm "dotmac_platform:test"
fi
