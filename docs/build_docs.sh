#!/bin/bash

# DotMac Platform Documentation Build Script

set -e

echo "==================================="
echo "DotMac Documentation Builder"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from docs directory
if [ ! -f "conf.py" ]; then
    echo -e "${RED}Error: Must run from docs directory${NC}"
    exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Install dependencies strategically
echo "Installing documentation dependencies..."

# Option 1: Try full requirements (includes app dependencies)
if pip install -q -r requirements-full.txt; then
    print_status "Full dependencies installed (best quality docs)"
elif pip install -q -r requirements.txt; then
    print_warning "Basic docs dependencies only (some imports will be mocked)"
    echo "To get better documentation, install: pip install -r requirements-full.txt"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Verify critical packages
echo "Verifying critical packages..."
python -c "
import sys
missing = []
for pkg in ['httpx', 'structlog', 'fastapi', 'pydantic']:
    try:
        __import__(pkg)
        print(f'✓ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'✗ {pkg} (will be mocked)')

if missing:
    print(f'\\nNote: {len(missing)} packages will use mocked imports')
    print('For complete documentation, run: pip install -r requirements-full.txt')
else:
    print('\\n✓ All critical packages available for documentation')
"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf _build
print_status "Cleaned _build directory"

# Generate API documentation
echo "Generating API documentation..."
if sphinx-apidoc -o api ../isp-framework/src/dotmac_isp -f -e -M; then
    print_status "API documentation generated"
else
    print_warning "API documentation generation had issues"
fi

# Build HTML documentation
echo "Building HTML documentation..."
if sphinx-build -b html . _build/html; then
    print_status "HTML documentation built successfully"
    echo ""
    echo "Documentation available at: file://$(pwd)/_build/html/index.html"
else
    print_error "HTML build failed"
    exit 1
fi

# Build PDF documentation (optional)
if command -v pdflatex &> /dev/null; then
    echo "Building PDF documentation..."
    if sphinx-build -b latex . _build/latex && make -C _build/latex; then
        print_status "PDF documentation built"
        echo "PDF available at: _build/latex/DotMac.pdf"
    else
        print_warning "PDF build failed (non-critical)"
    fi
else
    print_warning "pdflatex not found, skipping PDF generation"
fi

# Generate coverage report
echo "Generating documentation coverage report..."
if sphinx-build -b coverage . _build/coverage; then
    print_status "Coverage report generated"
    echo "Coverage report: _build/coverage/python.txt"
    echo ""
    echo "Undocumented items:"
    cat _build/coverage/python.txt | head -20
else
    print_warning "Coverage report generation failed"
fi

echo ""
echo "==================================="
echo "Documentation build complete!"
echo "==================================="
echo ""
echo "Quick actions:"
echo "  - View HTML: open _build/html/index.html"
echo "  - Start live server: make livehtml"
echo "  - Clean build: make clean"
echo ""
