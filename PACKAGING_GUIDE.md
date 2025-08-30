# DotMac Framework Packaging Guide

## Overview

The DotMac Framework uses a **single authoritative pyproject.toml** approach for dependency management and packaging. This guide clarifies the packaging structure and installation procedures.

## Authoritative Configuration

**Primary configuration file:** `/home/dotmac_framework/pyproject.toml`

This file contains:

- All runtime dependencies for the entire monorepo
- Development dependencies
- Testing configuration (pytest, ruff, black, mypy)
- Build system configuration

## Package Structure

```
/home/dotmac_framework/
├── pyproject.toml                    # ✅ AUTHORITATIVE - Runtime dependencies
├── src/
│   ├── pyproject.toml               # ❌ DEPRECATED - Legacy shared services config
│   ├── dotmac_shared/               # Core shared framework
│   ├── dotmac_isp/                  # ISP application
│   ├── dotmac_management/           # Management platform
│   ├── dotmac_sdk/                  # SDK packages
│   └── ...
├── docs/pyproject.toml              # ✅ VALID - Documentation-specific deps
├── frontend/                        # Frontend workspace (separate packaging)
└── packages/                        # External utility packages
```

## Installation Methods

### Method 1: Development Installation (Recommended)

```bash
# Install the entire framework in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Install with all optional dependencies
pip install -e ".[dev,docs]"
```

### Method 2: Production Installation

```bash
# Install from source
pip install .

# Install specific components only (if needed)
pip install ./src/dotmac_shared
pip install ./src/dotmac_isp
pip install ./src/dotmac_management
```

## Dependency Management

### Runtime Dependencies

All runtime dependencies are defined in the root `pyproject.toml`:

```toml
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    # ... etc
]
```

### Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.0.280",
    "black>=23.7.0",
    # ... etc
]
```

### Package Inclusion

The framework includes all Python packages from the `src/` directory:

```toml
[tool.poetry]
packages = [
    {include = "dotmac_isp", from = "src"},
    {include = "dotmac_shared", from = "src"},
    {include = "dotmac_management", from = "src"},
    {include = "dotmac_network_visualization", from = "src"},
    {include = "dotmac_sdk", from = "src"},
    {include = "dotmac_sdk_core", from = "src"}
]
```

## Deprecated Configurations

### Files to Ignore

- `src/pyproject.toml` - Legacy Poetry configuration for shared services (superseded by root config)
- `src/dotmac_shared/*/pyproject.toml` - Individual package configs (not needed in monorepo)

### Migration Notes

If you previously used:

```bash
cd src && poetry install
```

Now use:

```bash
pip install -e .
```

## Testing

All testing is configured via the root `pyproject.toml`:

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m e2e
```

## Code Quality Tools

All tools are configured in the root `pyproject.toml`:

```bash
# Format code
black src tests

# Check style
ruff check src tests

# Type checking
mypy src

# All quality checks
pre-commit run --all-files
```

## Docker and Deployment

The unified configuration ensures consistent dependency resolution in containers:

```dockerfile
# Dockerfile example
FROM python:3.11
COPY pyproject.toml .
RUN pip install .
COPY src/ src/
```

## Troubleshooting

### Common Issues

1. **Multiple pyproject.toml files causing conflicts:**
   - Use only the root `pyproject.toml`
   - Ignore deprecated configs in `src/`

2. **Import errors after installation:**
   - Ensure you're using `pip install -e .` for development
   - Check that all required packages are in the root dependencies

3. **Poetry vs pip confusion:**
   - The framework now uses standard pyproject.toml (PEP 518/621)
   - Poetry syntax in root config is for backward compatibility only

### Verification

To verify your installation:

```bash
# Check that all packages can be imported
python -c "import dotmac_shared, dotmac_isp, dotmac_management; print('✅ All packages importable')"

# Run basic health check
python -c "from dotmac_shared.application.config import PlatformConfig; print('✅ Shared framework loaded')"
```

## Summary

- **Single source of truth:** Root `pyproject.toml` only
- **Installation:** `pip install -e .` for development
- **Dependencies:** All managed centrally
- **Testing:** Configured via root pyproject.toml
- **Deprecated:** Individual package pyproject.toml files
