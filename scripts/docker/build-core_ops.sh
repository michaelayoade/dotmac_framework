#!/bin/bash
# Build dotmac_core_ops
set -e

echo "📦 Building dotmac_core_ops..."

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-latest}
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TARGET=${TARGET:-production}

cd dotmac_core_ops

# Build with specified target
docker build \
    --target "$TARGET" \
    --tag "dotmac_core_ops:$VERSION" \
    --tag "dotmac_core_ops:latest" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg SERVICE_NAME="dotmac_core_ops" \
    --build-arg SERVICE_DESCRIPTION="DotMac Core Operations Service" \
    .

echo "✅ Built dotmac_core_ops:$VERSION"

# Optional: Run security scan
if [ "${SECURITY_SCAN:-false}" = "true" ]; then
    echo "🔒 Running security scan..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image "dotmac_core_ops:$VERSION"
fi

# Optional: Run tests
if [ "${RUN_TESTS:-false}" = "true" ]; then
    echo "🧪 Running tests..."
    docker build --target testing --tag "dotmac_core_ops:test" .
    docker run --rm "dotmac_core_ops:test"
fi
