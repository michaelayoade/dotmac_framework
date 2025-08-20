"""
Service Generator SDK - Automated service scaffolding and project generation.
"""

import os
import shutil
import subprocess
from datetime import datetime
from dotmac_devtools.core.datetime_utils import utc_now, utc_now_iso
from pathlib import Path
from typing import Any
from uuid import uuid4

import git
from cookiecutter.main import cookiecutter
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..core.config import DevToolsConfig, get_template_path
from ..core.exceptions import ServiceScaffoldingError, ValidationError


class ServiceGeneratorService:
    """Core service for generating DotMac services."""

    def __init__(self, config: DevToolsConfig):
        self.config = config
        self._template_env = None

    @property
    def template_env(self) -> Environment:
        """Get Jinja2 template environment."""
        if self._template_env is None:
            template_path = self.config.templates.custom_path
            self._template_env = Environment(
                loader=FileSystemLoader([
                    str(template_path),
                    str(Path(__file__).parent.parent / "templates")
                ]),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        return self._template_env

    async def generate_service(self, **kwargs) -> dict[str, Any]:
        """Generate a new DotMac service."""

        # Validate required parameters
        service_name = kwargs.get('name')
        if not service_name:
            raise ValidationError("Service name is required")

        service_type = kwargs.get('type', 'rest-api')
        template = kwargs.get('template')
        output_dir = kwargs.get('output_dir', self.config.workspace_path)

        # Prepare service configuration
        service_config = {
            'service_name': service_name,
            'service_type': service_type,
            'service_id': str(uuid4()),
            'author': kwargs.get('author', self.config.defaults.author),
            'license': kwargs.get('license', self.config.defaults.license),
            'python_version': kwargs.get('python_version', self.config.defaults.python_version),
            'docker_registry': kwargs.get('docker_registry', self.config.defaults.docker_registry),
            'description': kwargs.get('description', f"DotMac {service_type} service"),
            'version': kwargs.get('version', '1.0.0'),
            'database': kwargs.get('database', 'postgresql'),
            'cache': kwargs.get('cache', 'redis'),
            'queue': kwargs.get('queue', 'rabbitmq'),
            'enable_auth': kwargs.get('enable_auth', True),
            'enable_monitoring': kwargs.get('enable_monitoring', True),
            'enable_testing': kwargs.get('enable_testing', True),
            'enable_docs': kwargs.get('enable_docs', True),
            'created_at': utc_now().isoformat(),
            'dotmac_framework_version': '1.0.0',
        }

        # Get template path
        try:
            if template:
                # Use specific template if provided
                template_path = get_template_path(template, self.config)
            else:
                # Use type-based template
                template_path = get_template_path(f"service-{service_type}", self.config)
        except FileNotFoundError:
            # Fall back to generic service template
            template_path = get_template_path("service-generic", self.config)

        # Generate service
        service_path = Path(output_dir) / f"dotmac_{service_name}"

        try:
            # Check if template is a yaml file (microservice template)
            if template and template_path.suffix == '.yaml':
                # Handle microservice template generation
                project_path = await self._generate_from_yaml_template(template_path, service_config, output_dir)
            else:
                # Use cookiecutter for initial generation
                project_path = cookiecutter(
                    str(template_path),
                    extra_context=service_config,
                    output_dir=str(output_dir),
                    no_input=True,
                    overwrite_if_exists=kwargs.get('overwrite', False)
                )

            service_path = Path(project_path)

            # Post-generation processing
            await self._post_process_service(service_path, service_config)

            return {
                'service_name': service_name,
                'service_path': str(service_path),
                'service_type': service_type,
                'config': service_config,
                'generated_files': await self._list_generated_files(service_path),
                'next_steps': self._get_next_steps(service_config)
            }

        except Exception as e:
            raise ServiceScaffoldingError(f"Failed to generate service: {str(e)}")

    async def generate_microservice(self, **kwargs) -> dict[str, Any]:
        """Generate a microservice with event-driven architecture."""
        kwargs['type'] = 'microservice'
        kwargs.setdefault('queue', 'rabbitmq')
        kwargs.setdefault('enable_events', True)
        return await self.generate_service(**kwargs)

    async def generate_rest_api(self, **kwargs) -> dict[str, Any]:
        """Generate a REST API service with OpenAPI documentation."""
        kwargs['type'] = 'rest-api'
        kwargs.setdefault('enable_openapi', True)
        kwargs.setdefault('enable_cors', True)
        return await self.generate_service(**kwargs)

    async def generate_graphql_service(self, **kwargs) -> dict[str, Any]:
        """Generate a GraphQL service with schema-first development."""
        kwargs['type'] = 'graphql'
        kwargs.setdefault('enable_playground', True)
        kwargs.setdefault('enable_introspection', True)
        return await self.generate_service(**kwargs)

    async def generate_background_worker(self, **kwargs) -> dict[str, Any]:
        """Generate a background worker service."""
        kwargs['type'] = 'background-worker'
        kwargs.setdefault('queue', 'celery')
        kwargs.setdefault('enable_scheduling', True)
        return await self.generate_service(**kwargs)

    async def generate_data_pipeline(self, **kwargs) -> dict[str, Any]:
        """Generate a data pipeline service."""
        kwargs['type'] = 'data-pipeline'
        kwargs.setdefault('framework', 'airflow')
        kwargs.setdefault('enable_monitoring', True)
        return await self.generate_service(**kwargs)

    async def _post_process_service(self, service_path: Path, config: dict[str, Any]):  # noqa: C901
        """Post-process generated service."""

        # Initialize Git repository
        if self.config.generator.git_init:
            try:
                repo = git.Repo.init(service_path)

                # Create initial commit
                repo.git.add(A=True)
                repo.git.commit('-m', 'Initial commit: Generated DotMac service')

            except Exception as e:
                print(f"Warning: Failed to initialize Git repository: {e}")

        # Create virtual environment
        if self.config.generator.create_venv:
            try:
                venv_path = service_path / "venv"
                subprocess.run([
                    "python", "-m", "venv", str(venv_path)
                ], check=True, cwd=service_path)

            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to create virtual environment: {e}")

        # Install dependencies
        if self.config.generator.install_deps:
            try:
                subprocess.run([
                    "pip", "install", "-e", "."
                ], check=True, cwd=service_path)

            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to install dependencies: {e}")

        # Format code
        if self.config.generator.auto_format:
            try:
                subprocess.run([
                    "black", "."
                ], check=True, cwd=service_path)

                subprocess.run([
                    "isort", "."
                ], check=True, cwd=service_path)

            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to format code: {e}")

        # Run tests
        if self.config.generator.run_tests:
            try:
                subprocess.run([
                    "pytest", "--tb=short"
                ], check=True, cwd=service_path)

            except subprocess.CalledProcessError as e:
                print(f"Warning: Tests failed: {e}")

    async def _list_generated_files(self, service_path: Path) -> list[str]:
        """List all generated files."""
        files = []
        for root, dirs, filenames in os.walk(service_path):
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(service_path)
                files.append(str(relative_path))
        return sorted(files)

    def _get_next_steps(self, config: dict[str, Any]) -> list[str]:
        """Get next steps for the generated service."""
        steps = [
            f"cd {config['service_name']}",
            "Review the generated code structure",
        ]

        if config.get('enable_testing'):
            steps.append("Run tests: pytest")

        if config.get('service_type') == 'rest-api':
            steps.append("Start development server: python -m uvicorn main:app --reload")
            steps.append("View API docs: http://localhost:8000/docs")

        if config.get('database'):
            steps.append("Configure database connection in .env file")
            steps.append("Run database migrations: alembic upgrade head")

        steps.extend([
            "Configure environment variables in .env file",
            "Update README.md with service-specific information",
            "Commit initial changes: git add . && git commit -m 'Initial service setup'"
        ])

        return steps

    async def list_available_templates(self) -> dict[str, Any]:
        """List all available service templates."""
        templates = {}

        # Built-in templates
        builtin_path = Path(__file__).parent.parent / "templates"
        if builtin_path.exists():
            for template_dir in builtin_path.iterdir():
                if template_dir.is_dir() and template_dir.name.startswith('service-'):
                    template_name = template_dir.name.replace('service-', '')
                    templates[template_name] = {
                        'name': template_name,
                        'path': str(template_dir),
                        'type': 'builtin',
                        'description': self._get_template_description(template_dir)
                    }

        # Custom templates
        custom_path = self.config.templates.custom_path
        if custom_path.exists():
            for template_dir in custom_path.iterdir():
                if template_dir.is_dir() and template_dir.name.startswith('service-'):
                    template_name = template_dir.name.replace('service-', '')
                    templates[template_name] = {
                        'name': template_name,
                        'path': str(template_dir),
                        'type': 'custom',
                        'description': self._get_template_description(template_dir)
                    }

        return templates

    def _get_template_description(self, template_path: Path) -> str:
        """Get template description from metadata."""
        metadata_file = template_path / "template.yaml"
        if metadata_file.exists():
            import yaml
            try:
                with open(metadata_file) as f:
                    metadata = yaml.safe_load(f)
                return metadata.get('description', 'No description available')
            except Exception:
                pass

        return "No description available"

    async def _generate_from_yaml_template(self, template_path: Path, service_config: dict[str, Any], output_dir: str) -> str:
        """Generate service from YAML template definition."""
        import yaml

        # Load template definition
        with open(template_path) as f:
            template_def = yaml.safe_load(f)

        service_name = service_config['service_name']
        project_path = Path(output_dir) / service_name
        project_path.mkdir(parents=True, exist_ok=True)

        # Copy template files from template directory
        template_dir = template_path.parent / template_def['name']
        if template_dir.exists():
            for item in template_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, project_path)
                elif item.is_dir():
                    shutil.copytree(item, project_path / item.name, dirs_exist_ok=True)

        # Process environment variables
        env_file = project_path / '.env'
        if not env_file.exists() and template_def.get('env'):
            env_content = "\n".join([f"{env_var}=" for env_var in template_def['env']])
            env_file.write_text(env_content)

        return str(project_path)


class ServiceGeneratorSDK:
    """SDK for DotMac service generation."""

    def __init__(self, config: DevToolsConfig | None = None):
        self.config = config or DevToolsConfig()
        self._service = ServiceGeneratorService(self.config)

    async def generate_service(
        self,
        name: str,
        service_type: str = "rest-api",
        template: str | None = None,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a new DotMac service."""
        return await self._service.generate_service(
            name=name,
            type=service_type,
            template=template,
            output_dir=output_dir,
            **kwargs
        )

    async def generate_microservice(
        self,
        name: str,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a microservice."""
        return await self._service.generate_microservice(
            name=name,
            output_dir=output_dir,
            **kwargs
        )

    async def generate_rest_api(
        self,
        name: str,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a REST API service."""
        return await self._service.generate_rest_api(
            name=name,
            output_dir=output_dir,
            **kwargs
        )

    async def generate_graphql_service(
        self,
        name: str,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a GraphQL service."""
        return await self._service.generate_graphql_service(
            name=name,
            output_dir=output_dir,
            **kwargs
        )

    async def generate_background_worker(
        self,
        name: str,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a background worker service."""
        return await self._service.generate_background_worker(
            name=name,
            output_dir=output_dir,
            **kwargs
        )

    async def generate_data_pipeline(
        self,
        name: str,
        output_dir: str | Path | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate a data pipeline service."""
        return await self._service.generate_data_pipeline(
            name=name,
            output_dir=output_dir,
            **kwargs
        )

    async def list_templates(self) -> dict[str, Any]:
        """List available service templates."""
        return await self._service.list_available_templates()
