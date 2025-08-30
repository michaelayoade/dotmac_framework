#!/usr/bin/env python3
"""
Developer Environment Setup Script for DotMac Framework

This script automates the setup of a complete development environment
including all dependencies, tools, and configurations.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class Colors:
    """Terminal color constants."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


class DevSetup:
    """Development environment setup manager."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.system = platform.system().lower()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # Required tools and versions
        self.required_tools = {
            "python": "3.9",
            "docker": "20.0",
            "docker-compose": "2.0",
            "git": "2.30",
            "node": "18.0",
            "pnpm": "8.0",
        }

    def print_banner(self):
        """Print setup banner."""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    DotMac Framework                          ║
║                Development Setup Script                      ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}

🚀 Setting up your development environment...
📍 Project root: {self.project_root}
🖥️  System: {self.system}
🐍 Python: {self.python_version}
"""

    def run_setup(self):
        """Run complete development setup."""
        try:
            self.print_banner()

            # Step 1: Check system requirements
            self.log_step("Checking system requirements")
            self.check_system_requirements()

            # Step 2: Set up Python environment
            self.log_step("Setting up Python environment")
            self.setup_python_environment()

            # Step 3: Install dependencies
            self.log_step("Installing dependencies")
            self.install_dependencies()

            # Step 4: Set up Git hooks
            self.log_step("Setting up Git hooks")
            self.setup_git_hooks()

            # Step 5: Set up Docker environment
            self.log_step("Setting up Docker environment")
            self.setup_docker_environment()

            # Step 6: Initialize databases
            self.log_step("Initializing databases")
            self.initialize_databases()

            # Step 7: Set up frontend environment
            self.log_step("Setting up frontend environment")
            self.setup_frontend()

            # Step 8: Configure development tools
            self.log_step("Configuring development tools")
            self.configure_dev_tools()

            # Step 9: Run initial tests
            self.log_step("Running initial tests")
            self.run_initial_tests()

            # Step 10: Generate development documentation
            self.log_step("Generating documentation")
            self.generate_documentation()

            self.print_success_message()

        except Exception as e:
            self.log_error(f"Setup failed: {e}")
            sys.exit(1)

    def log_step(self, message: str):
        """Log a setup step."""

    def log_success(self, message: str):
        """Log a success message."""

    def log_warning(self, message: str):
        """Log a warning message."""

    def log_error(self, message: str):
        """Log an error message."""

    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> bool:
        """Run a command and return success status."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"Command failed: {' '.join(command)}")
            self.log_error(f"Error: {e.stderr}")
            return False

    def check_tool_version(self, tool: str, required_version: str) -> bool:
        """Check if a tool meets version requirements."""
        try:
            if tool == "python":
                current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
                return current_version >= required_version

            # Get version for other tools
            version_commands = {
                "docker": ["docker", "--version"],
                "docker-compose": ["docker-compose", "--version"],
                "git": ["git", "--version"],
                "node": ["node", "--version"],
                "pnpm": ["pnpm", "--version"],
            }

            if tool not in version_commands:
                return False

            result = subprocess.run(
                version_commands[tool], capture_output=True, text=True, check=True
            )

            # Simple version check (could be more sophisticated)
            return result.returncode == 0

        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def check_system_requirements(self):
        """Check system requirements and dependencies."""
        missing_tools = []

        for tool, required_version in self.required_tools.items():
            if self.check_tool_version(tool, required_version):
                self.log_success(f"{tool} is available")
            else:
                missing_tools.append(tool)
                self.log_warning(
                    f"{tool} is missing or outdated (requires {required_version}+)"
                )

        if missing_tools:
            self.log_error("Please install missing tools before continuing:")
            for tool in missing_tools:
                self.print_installation_instructions(tool)
            return False

        self.log_success("All system requirements met")
        return True

    def print_installation_instructions(self, tool: str):
        """Print installation instructions for a tool."""
        instructions = {
            "docker": "Install Docker Desktop from https://docker.com",
            "docker-compose": "Docker Compose comes with Docker Desktop",
            "git": "Install Git from https://git-scm.com",
            "node": "Install Node.js from https://nodejs.org (LTS version)",
            "pnpm": "Install pnpm: npm install -g pnpm",
            "python": "Install Python 3.9+ from https://python.org",
        }

        instruction = instructions.get(tool, f"Please install {tool}")

    def setup_python_environment(self):
        """Set up Python virtual environment and tools."""
        # Check if we're already in a virtual environment
        if sys.prefix == sys.base_prefix:
            self.log_warning("Not running in a virtual environment")

            # Try to create one
            venv_path = self.project_root / "venv"
            if not venv_path.exists():
                self.log_step("Creating virtual environment")
                if self.run_command([sys.executable, "-m", "venv", "venv"]):
                    self.log_success("Virtual environment created")
                    self.log_warning(
                        "Please activate it with: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
                    )
                else:
                    self.log_error("Failed to create virtual environment")
        else:
            self.log_success("Running in virtual environment")

        # Upgrade pip
        if self.run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
        ):
            self.log_success("pip upgraded")

        # Install pip-tools
        if self.run_command([sys.executable, "-m", "pip", "install", "pip-tools"]):
            self.log_success("pip-tools installed")

    def install_dependencies(self):
        """Install Python dependencies."""
        # Compile dependencies if lockfiles don't exist
        if not (self.project_root / "requirements-dev.lock").exists():
            self.log_step("Compiling dependencies")
            if self.run_command(["make", "deps-compile"]):
                self.log_success("Dependencies compiled")
            else:
                self.log_error("Failed to compile dependencies")
                return False

        # Install development dependencies
        if self.run_command(["make", "install-dev"]):
            self.log_success("Development dependencies installed")
        else:
            self.log_error("Failed to install dependencies")
            return False

        return True

    def setup_git_hooks(self):
        """Set up Git pre-commit hooks."""
        if self.run_command(["pre-commit", "install"]):
            self.log_success("Pre-commit hooks installed")
        else:
            self.log_error("Failed to install pre-commit hooks")
            return False

        # Install additional hook types
        hook_types = ["pre-push", "commit-msg"]
        for hook_type in hook_types:
            if self.run_command(["pre-commit", "install", "--hook-type", hook_type]):
                self.log_success(f"{hook_type} hook installed")

        return True

    def setup_docker_environment(self):
        """Set up Docker development environment."""
        # Check if Docker is running
        if not self.run_command(["docker", "info"]):
            self.log_error("Docker is not running. Please start Docker Desktop.")
            return False

        # Build test images
        if self.run_command(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile.test",
                "-t",
                "dotmac-framework:test",
                ".",
            ]
        ):
            self.log_success("Test Docker image built")
        else:
            self.log_warning("Failed to build test image")

        # Pull required images
        images = [
            "postgres:16-alpine",
            "redis:7-alpine",
            "timescale/timescaledb:2.11.2-pg16",
        ]

        for image in images:
            if self.run_command(["docker", "pull", image]):
                self.log_success(f"Pulled {image}")
            else:
                self.log_warning(f"Failed to pull {image}")

        return True

    def initialize_databases(self):
        """Initialize development databases."""
        self.log_step("Starting database services")

        # Start only database services
        if self.run_command(
            [
                "docker-compose",
                "-f",
                "docker-compose.test.yml",
                "up",
                "-d",
                "postgres-test",
                "redis-test",
                "timescaledb-test",
            ]
        ):
            self.log_success("Database services started")
        else:
            self.log_error("Failed to start database services")
            return False

        # Wait for databases to be ready
        import time

        self.log_step("Waiting for databases to be ready")
        time.sleep(10)

        # Run database initialization
        if self.run_command(
            [
                "docker-compose",
                "-f",
                "docker-compose.test.yml",
                "exec",
                "-T",
                "postgres-test",
                "psql",
                "-U",
                "dotmac_test",
                "-d",
                "dotmac_test",
                "-c",
                "SELECT 1;",
            ]
        ):
            self.log_success("Databases are ready")
        else:
            self.log_warning("Database connectivity check failed")

        return True

    def setup_frontend(self):
        """Set up frontend development environment."""
        frontend_dir = self.project_root / "frontend"

        if not frontend_dir.exists():
            self.log_warning("Frontend directory not found, skipping")
            return True

        # Install frontend dependencies
        if self.run_command(["pnpm", "install"], cwd=frontend_dir):
            self.log_success("Frontend dependencies installed")
        else:
            self.log_error("Failed to install frontend dependencies")
            return False

        return True

    def configure_dev_tools(self):
        """Configure development tools and IDE settings."""
        # Create .vscode directory and settings
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)

        # VS Code settings
        vscode_settings = {
            "python.defaultInterpreterPath": "./venv/bin/python",
            "python.linting.enabled": True,
            "python.linting.ruffEnabled": True,
            "python.formatting.provider": "black",
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {"source.organizeImports": True},
            "files.exclude": {
                "**/__pycache__": True,
                "**/*.pyc": True,
                "**/node_modules": True,
                "**/.pytest_cache": True,
                "**/.mypy_cache": True,
                "**/.ruff_cache": True,
            },
        }

        import json

        with open(vscode_dir / "settings.json", "w") as f:
            json.dump(vscode_settings, f, indent=2)

        self.log_success("VS Code settings configured")

        # Create launch configuration
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: Debug Tests",
                    "type": "python",
                    "request": "launch",
                    "module": "pytest",
                    "args": ["-v", "--tb=short"],
                    "console": "integratedTerminal",
                    "justMyCode": False,
                },
                {
                    "name": "Python: Run Quality Checks",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/scripts/quality-gate-check.py",
                    "console": "integratedTerminal",
                    "args": ["--environment", "development"],
                },
            ],
        }

        with open(vscode_dir / "launch.json", "w") as f:
            json.dump(launch_config, f, indent=2)

        self.log_success("VS Code launch configuration created")
        return True

    def run_initial_tests(self):
        """Run initial tests to verify setup."""
        # Run a quick test to verify everything works
        if self.run_command(["python", "-m", "pytest", "--version"]):
            self.log_success("pytest is working")
        else:
            self.log_error("pytest is not working")
            return False

        # Run a simple test if any exist
        if self.run_command(
            [
                "python",
                "-m",
                "pytest",
                "-m",
                "unit and fast",
                "--tb=short",
                "-x",  # Stop on first failure
            ]
        ):
            self.log_success("Initial tests passed")
        else:
            self.log_warning("Some tests failed (this might be expected for new setup)")

        return True

    def generate_documentation(self):
        """Generate development documentation."""
        docs_dir = self.project_root / "docs" / "development"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Generate developer quickstart guide
        quickstart_content = self.generate_quickstart_guide()
        with open(docs_dir / "QUICKSTART.md", "w") as f:
            f.write(quickstart_content)

        # Generate testing guide
        testing_guide = self.generate_testing_guide()
        with open(docs_dir / "TESTING.md", "w") as f:
            f.write(testing_guide)

        self.log_success("Development documentation generated")
        return True

    def generate_quickstart_guide(self) -> str:
        """Generate quickstart guide content."""
        return """# DotMac Framework - Developer Quickstart

## 🚀 Getting Started

Your development environment has been set up successfully! Here's what you need to know:

### Daily Development Workflow

1. **Start your day:**
   ```bash
   # Pull latest changes
   git pull origin main

   # Update dependencies if needed
   make deps-update

   # Run quality checks
   make check
   ```

2. **Before committing:**
   ```bash
   # Run tests
   make test

   # Check code quality
   make lint

   # Run security checks
   make security
   ```

3. **Before pushing:**
   ```bash
   # Run comprehensive checks
   make ci-test
   ```

### Quick Commands

- `make test` - Run all tests
- `make test-unit` - Run unit tests only (fast)
- `make lint` - Run linting with complexity checks
- `make format` - Format code
- `make security` - Run security scans
- `make check` - Run all quality checks

### Development Environment

- **Python virtual environment**: `venv/`
- **Test databases**: Available via Docker Compose
- **Frontend**: Available in `frontend/` directory
- **Pre-commit hooks**: Automatically check code quality

### IDE Configuration

VS Code settings have been configured with:
- Python interpreter path
- Linting and formatting settings
- Test configuration
- Debug configurations

### Troubleshooting

If you encounter issues:

1. **Dependency problems**: Run `make clean && make install-dev`
2. **Test failures**: Check database connectivity with `docker-compose -f docker-compose.test.yml ps`
3. **Import errors**: Ensure virtual environment is activated
4. **Pre-commit issues**: Run `pre-commit install --install-hooks`

### Next Steps

1. Read the [Testing Guide](./TESTING.md)
2. Explore the codebase structure
3. Run your first test: `make test-unit`
4. Create your first feature branch: `git checkout -b feature/your-feature-name`

Happy coding! 🎉
"""

    def generate_testing_guide(self) -> str:
        """Generate testing guide content."""
        return """# DotMac Framework - Testing Guide

## 🧪 Testing Overview

This project uses a comprehensive testing strategy with multiple test types and quality gates.

### Test Types

#### Unit Tests
```bash
# Run all unit tests
make test-unit

# Run specific unit tests
pytest tests/examples/unit/ -v

# Run with coverage
pytest -m "unit" --cov --cov-report=html
```

#### Integration Tests
```bash
# Run integration tests (requires databases)
make test-integration

# Run with Docker
make test-docker-integration
```

#### End-to-End Tests
```bash
# Run E2E tests
pytest -m "e2e" -v

# Run in Docker environment
make test-docker
```

#### Performance Tests
```bash
# Run performance benchmarks
pytest -m "performance" --benchmark-json=results.json

# Run load tests with Locust
locust -f tests/examples/performance/locustfile.py --host=http://localhost:8000
```

#### Security Tests
```bash
# Run security tests
pytest -m "security" -v

# Run security scanning
make security
```

#### Contract Tests
```bash
# Run API contract tests
pytest -m "contract" -v
```

### Test Organization

```
tests/
├── examples/           # Example tests for each type
│   ├── unit/          # Unit test examples
│   ├── integration/   # Integration test examples
│   ├── e2e/          # End-to-end test examples
│   ├── contract/     # Contract test examples
│   ├── performance/  # Performance test examples
│   └── security/     # Security test examples
├── conftest.py       # Global test configuration
└── test_contracts.py # API contract definitions
```

### Test Configuration

Tests are configured via `pyproject.toml` with:
- Async support
- Parallel execution
- Coverage reporting
- Custom markers
- Timeout handling

### Writing Tests

#### Unit Test Example
```python
import pytest
from mymodule import MyClass

@pytest.mark.unit
@pytest.mark.fast
def test_my_function():
    # Arrange
    instance = MyClass()

    # Act
    result = instance.my_method("test")

    # Assert
    assert result == "expected"
```

#### Async Test Example
```python
import pytest

@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

#### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.database
async def test_database_integration(db_connection):
    # Test requires real database
    result = await create_user(db_connection, user_data)
    assert result.id is not None
```

### Test Data and Fixtures

#### Using Factories
```python
from factory import Factory, Faker

class CustomerFactory(Factory):
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
```

#### Database Fixtures
```python
@pytest_asyncio.fixture
async def db_connection():
    # Set up test database connection
    conn = await create_test_connection()
    yield conn
    await conn.close()
```

### Quality Gates

Tests must meet quality gates:
- **Coverage**: Minimum 80% overall
- **Performance**: Response times within limits
- **Security**: No security violations
- **Complexity**: Functions under complexity limits

### CI/CD Integration

Tests run automatically in GitHub Actions:
- Unit tests on every PR
- Integration tests on every PR
- Performance tests on schedule
- Security tests on schedule

### Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Test Organization**: Group related tests in classes
3. **Fixtures**: Use fixtures for common setup
4. **Markers**: Use markers to categorize tests
5. **Isolation**: Ensure tests are independent
6. **Data**: Use factories for test data generation
7. **Mocking**: Mock external dependencies
8. **Assertions**: Use specific assertions with clear messages

### Troubleshooting

#### Common Issues

1. **Database connection failures**:
   ```bash
   docker-compose -f docker-compose.test.yml up -d postgres-test
   ```

2. **Import errors**:
   ```bash
   pip install -e .
   ```

3. **Async test failures**:
   - Ensure `pytest-asyncio` is installed
   - Use `@pytest.mark.asyncio` decorator

4. **Flaky tests**:
   - Add appropriate waits
   - Use proper test isolation
   - Check for race conditions

### Useful Commands

```bash
# Run specific test file
pytest tests/test_example.py -v

# Run tests matching pattern
pytest -k "test_user" -v

# Run tests and generate coverage report
pytest --cov --cov-report=html

# Run tests with specific markers
pytest -m "unit and not slow"

# Debug test failures
pytest --pdb -x

# Run tests in parallel
pytest -n auto

# Generate test report
python scripts/generate-test-report.py
```
"""

    def print_success_message(self):
        """Print setup completion message."""
        success_message = f"""
{Colors.GREEN}{Colors.BOLD}
🎉 Development environment setup completed successfully!

Next steps:
{Colors.END}{Colors.GREEN}
1. Activate your virtual environment (if not already activated)
2. Run your first test: make test-unit
3. Start developing: git checkout -b feature/your-feature-name
4. Read the documentation in docs/development/

Useful commands:
• make test          - Run all tests
• make lint          - Check code quality
• make security      - Run security scans
• make check         - Run all quality checks
• make dev           - Start development environment

Happy coding! 🚀
{Colors.END}

{Colors.CYAN}📚 Documentation generated in docs/development/
🔧 VS Code configuration created in .vscode/
🐳 Docker test environment ready
🧪 Test examples available in tests/examples/
{Colors.END}
"""


def main():
    """Main entry point."""
    setup = DevSetup()
    setup.run_setup()


if __name__ == "__main__":
    main()
