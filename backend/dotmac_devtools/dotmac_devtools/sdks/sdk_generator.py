"""
SDK Generator SDK - Multi-language SDK generation from OpenAPI specifications.
"""

import json
import subprocess
from datetime import datetime
from dotmac_devtools.core.datetime_utils import utc_now, utc_now_iso
from pathlib import Path
from typing import Any

import httpx
import yaml
from jinja2 import Environment, FileSystemLoader
from openapi_spec_validator import validate_spec

from ..core.config import DevToolsConfig
from ..core.exceptions import SDKGenerationError, ValidationError


class SDKGeneratorService:
    """Core service for generating multi-language SDKs."""

    SUPPORTED_LANGUAGES = {
        'python': {
            'name': 'Python',
            'file_extensions': ['.py'],
            'package_manager': 'pip',
            'framework_options': ['requests', 'httpx', 'aiohttp'],
            'features': ['async', 'sync', 'typing', 'pydantic']
        },
        'typescript': {
            'name': 'TypeScript',
            'file_extensions': ['.ts', '.js'],
            'package_manager': 'npm',
            'framework_options': ['axios', 'fetch', 'node-fetch'],
            'features': ['async', 'types', 'decorators', 'rxjs']
        },
        'go': {
            'name': 'Go',
            'file_extensions': ['.go'],
            'package_manager': 'go mod',
            'framework_options': ['net/http', 'resty', 'fasthttp'],
            'features': ['context', 'generics', 'interfaces']
        },
        'java': {
            'name': 'Java',
            'file_extensions': ['.java'],
            'package_manager': 'maven',
            'framework_options': ['okhttp', 'retrofit', 'spring'],
            'features': ['annotations', 'generics', 'async']
        },
        'csharp': {
            'name': 'C#',
            'file_extensions': ['.cs'],
            'package_manager': 'nuget',
            'framework_options': ['httpclient', 'restsharp'],
            'features': ['async', 'attributes', 'generics']
        }
    }

    def __init__(self, config: DevToolsConfig):
        self.config = config
        self._template_env = None

    @property
    def template_env(self) -> Environment:
        """Get Jinja2 template environment."""
        if self._template_env is None:
            template_path = Path(__file__).parent.parent / "templates" / "sdk"
            self._template_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        return self._template_env

    async def generate_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate SDK for specified language."""

        # Validate required parameters
        language = kwargs.get('language')
        if not language:
            raise ValidationError("Programming language is required")

        if language not in self.SUPPORTED_LANGUAGES:
            raise ValidationError(f"Unsupported language: {language}")

        # Get API specification
        api_spec = await self._load_api_spec(kwargs)

        # Validate OpenAPI spec
        try:
            validate_spec(api_spec)
        except Exception as e:
            raise ValidationError(f"Invalid OpenAPI specification: {str(e)}")

        # Generate SDK
        sdk_config = {
            'language': language,
            'language_info': self.SUPPORTED_LANGUAGES[language],
            'api_spec': api_spec,
            'package_name': kwargs.get('package_name', self._generate_package_name(api_spec, language)),
            'package_version': kwargs.get('package_version', '1.0.0'),
            'output_dir': kwargs.get('output_dir', self.config.sdk.default_output_dir),
            'framework': kwargs.get('framework', self._get_default_framework(language)),
            'async_support': kwargs.get('async_support', self.config.sdk.async_by_default),
            'include_examples': kwargs.get('include_examples', self.config.sdk.include_examples),
            'include_tests': kwargs.get('include_tests', self.config.sdk.include_tests),
            'author': kwargs.get('author', self.config.defaults.author),
            'license': kwargs.get('license', self.config.defaults.license),
            'generated_at': utc_now().isoformat(),
        }

        # Generate SDK files
        generated_files = await self._generate_sdk_files(sdk_config)

        # Post-process SDK
        await self._post_process_sdk(sdk_config, generated_files)

        return {
            'language': language,
            'package_name': sdk_config['package_name'],
            'output_dir': sdk_config['output_dir'],
            'generated_files': generated_files,
            'config': sdk_config,
            'next_steps': self._get_sdk_next_steps(sdk_config)
        }

    async def generate_python_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate Python SDK with async support."""
        kwargs['language'] = 'python'
        kwargs.setdefault('framework', 'httpx')
        kwargs.setdefault('async_support', True)
        return await self.generate_sdk(**kwargs)

    async def generate_typescript_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate TypeScript SDK with type definitions."""
        kwargs['language'] = 'typescript'
        kwargs.setdefault('framework', 'axios')
        kwargs.setdefault('include_types', True)
        return await self.generate_sdk(**kwargs)

    async def generate_go_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate Go SDK with context support."""
        kwargs['language'] = 'go'
        kwargs.setdefault('framework', 'net/http')
        kwargs.setdefault('context_support', True)
        return await self.generate_sdk(**kwargs)

    async def _load_api_spec(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Load OpenAPI specification from various sources."""

        # From file path
        if 'api_spec_file' in kwargs:
            spec_path = Path(kwargs['api_spec_file'])
            if not spec_path.exists():
                raise ValidationError(f"API spec file not found: {spec_path}")

            with open(spec_path) as f:
                if spec_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    return json.load(f)

        # From URL
        if 'api_spec_url' in kwargs:
            async with httpx.AsyncClient() as client:
                response = await client.get(kwargs['api_spec_url'])
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')
                if 'yaml' in content_type or 'yml' in content_type:
                    return yaml.safe_load(response.text)
                else:
                    return response.json()

        # From dict
        if 'api_spec' in kwargs:
            return kwargs['api_spec']

        # From service discovery
        if 'service_name' in kwargs:
            return await self._discover_service_spec(kwargs['service_name'])

        raise ValidationError("No API specification source provided")

    async def _discover_service_spec(self, service_name: str) -> dict[str, Any]:
        """Discover API specification from service registry."""
        # This would integrate with service discovery
        # For now, try common endpoints
        common_endpoints = [
            f"http://{service_name}:8000/openapi.json",
            f"http://{service_name}/openapi.json",
            "http://localhost:8000/openapi.json",
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in common_endpoints:
                try:
                    response = await client.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        return response.json()
                except Exception:
                    continue

        raise ValidationError(f"Could not discover API spec for service: {service_name}")

    def _generate_package_name(self, api_spec: dict[str, Any], language: str) -> str:
        """Generate appropriate package name for the language."""

        # Get API title
        title = api_spec.get('info', {}).get('title', 'API Client')

        # Convert to appropriate format for language
        if language == 'python':
            # Convert to snake_case
            package_name = title.lower().replace(' ', '_').replace('-', '_')
            package_name = ''.join(c for c in package_name if c.isalnum() or c == '_')
            return f"{package_name}_client"

        elif language == 'typescript':
            # Convert to kebab-case
            package_name = title.lower().replace(' ', '-').replace('_', '-')
            package_name = ''.join(c for c in package_name if c.isalnum() or c == '-')
            return f"{package_name}-client"

        elif language == 'go':
            # Convert to lowercase
            package_name = title.lower().replace(' ', '').replace('-', '').replace('_', '')
            package_name = ''.join(c for c in package_name if c.isalnum())
            return f"{package_name}client"

        elif language == 'java':
            # Convert to camelCase
            words = title.lower().replace('-', ' ').replace('_', ' ').split()
            package_name = words[0] + ''.join(word.capitalize() for word in words[1:])
            return f"{package_name}Client"

        elif language == 'csharp':
            # Convert to PascalCase
            words = title.replace('-', ' ').replace('_', ' ').split()
            package_name = ''.join(word.capitalize() for word in words)
            return f"{package_name}Client"

        return "ApiClient"

    def _get_default_framework(self, language: str) -> str:
        """Get default framework for language."""
        frameworks = self.SUPPORTED_LANGUAGES[language]['framework_options']
        return frameworks[0] if frameworks else 'default'

    async def _generate_sdk_files(self, config: dict[str, Any]) -> list[str]:
        """Generate SDK files based on configuration."""

        language = config['language']
        output_dir = Path(config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Get language-specific generator
        generator_method = getattr(self, f"_generate_{language}_files", None)
        if generator_method:
            files = await generator_method(config, output_dir)
            generated_files.extend(files)
        else:
            raise SDKGenerationError(f"No generator available for language: {language}")

        return generated_files

    async def _generate_python_files(self, config: dict[str, Any], output_dir: Path) -> list[str]:
        """Generate Python SDK files."""

        package_name = config['package_name']
        package_dir = output_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)

        files = []

        # Generate setup.py
        setup_content = self.template_env.get_template('python/setup.py.j2').render(config)
        setup_file = output_dir / "setup.py"
        setup_file.write_text(setup_content)
        files.append(str(setup_file))

        # Generate pyproject.toml
        pyproject_content = self.template_env.get_template('python/pyproject.toml.j2').render(config)
        pyproject_file = output_dir / "pyproject.toml"
        pyproject_file.write_text(pyproject_content)
        files.append(str(pyproject_file))

        # Generate main client
        client_content = self.template_env.get_template('python/client.py.j2').render(config)
        client_file = package_dir / "client.py"
        client_file.write_text(client_content)
        files.append(str(client_file))

        # Generate models
        models_content = self.template_env.get_template('python/models.py.j2').render(config)
        models_file = package_dir / "models.py"
        models_file.write_text(models_content)
        files.append(str(models_file))

        # Generate API classes
        api_content = self.template_env.get_template('python/api.py.j2').render(config)
        api_file = package_dir / "api.py"
        api_file.write_text(api_content)
        files.append(str(api_file))

        # Generate __init__.py
        init_content = self.template_env.get_template('python/__init__.py.j2').render(config)
        init_file = package_dir / "__init__.py"
        init_file.write_text(init_content)
        files.append(str(init_file))

        # Generate examples if requested
        if config['include_examples']:
            examples_dir = output_dir / "examples"
            examples_dir.mkdir(exist_ok=True)

            example_content = self.template_env.get_template('python/example.py.j2').render(config)
            example_file = examples_dir / "basic_usage.py"
            example_file.write_text(example_content)
            files.append(str(example_file))

        # Generate tests if requested
        if config['include_tests']:
            tests_dir = output_dir / "tests"
            tests_dir.mkdir(exist_ok=True)

            test_content = self.template_env.get_template('python/test_client.py.j2').render(config)
            test_file = tests_dir / "test_client.py"
            test_file.write_text(test_content)
            files.append(str(test_file))

        return files

    async def _generate_typescript_files(self, config: dict[str, Any], output_dir: Path) -> list[str]:
        """Generate TypeScript SDK files."""

        files = []

        # Generate package.json
        package_content = self.template_env.get_template('typescript/package.json.j2').render(config)
        package_file = output_dir / "package.json"
        package_file.write_text(package_content)
        files.append(str(package_file))

        # Generate tsconfig.json
        tsconfig_content = self.template_env.get_template('typescript/tsconfig.json.j2').render(config)
        tsconfig_file = output_dir / "tsconfig.json"
        tsconfig_file.write_text(tsconfig_content)
        files.append(str(tsconfig_file))

        # Generate source files
        src_dir = output_dir / "src"
        src_dir.mkdir(exist_ok=True)

        # Main client
        client_content = self.template_env.get_template('typescript/client.ts.j2').render(config)
        client_file = src_dir / "client.ts"
        client_file.write_text(client_content)
        files.append(str(client_file))

        # Types
        types_content = self.template_env.get_template('typescript/types.ts.j2').render(config)
        types_file = src_dir / "types.ts"
        types_file.write_text(types_content)
        files.append(str(types_file))

        # Index
        index_content = self.template_env.get_template('typescript/index.ts.j2').render(config)
        index_file = src_dir / "index.ts"
        index_file.write_text(index_content)
        files.append(str(index_file))

        return files

    async def _post_process_sdk(self, config: dict[str, Any], generated_files: list[str]):  # noqa: C901
        """Post-process generated SDK."""

        output_dir = Path(config['output_dir'])
        language = config['language']

        # Format code
        if self.config.generator.auto_format:
            try:
                if language == 'python':
                    subprocess.run(['black', '.'], cwd=output_dir, check=False)
                    subprocess.run(['isort', '.'], cwd=output_dir, check=False)
                elif language == 'typescript':
                    subprocess.run(['npx', 'prettier', '--write', '.'], cwd=output_dir, check=False)
                elif language == 'go':
                    subprocess.run(['go', 'fmt', './...'], cwd=output_dir, check=False)
            except Exception as e:
                print(f"Warning: Failed to format {language} code: {e}")

        # Install dependencies
        if self.config.generator.install_deps:
            try:
                if language == 'python':
                    subprocess.run(['pip', 'install', '-e', '.'], cwd=output_dir, check=False)
                elif language == 'typescript':
                    subprocess.run(['npm', 'install'], cwd=output_dir, check=False)
                elif language == 'go':
                    subprocess.run(['go', 'mod', 'tidy'], cwd=output_dir, check=False)
            except Exception as e:
                print(f"Warning: Failed to install {language} dependencies: {e}")

    def _get_sdk_next_steps(self, config: dict[str, Any]) -> list[str]:
        """Get next steps for the generated SDK."""

        language = config['language']
        package_name = config['package_name']

        steps = [
            f"cd {config['output_dir']}",
            "Review the generated SDK structure",
        ]

        if language == 'python':
            steps.extend([
                "Install the SDK: pip install -e .",
                "Import in your code: from {package_name} import Client",
                "Run tests: pytest" if config['include_tests'] else None,
            ])
        elif language == 'typescript':
            steps.extend([
                "Install dependencies: npm install",
                "Build the SDK: npm run build",
                "Import in your code: import { Client } from './{package_name}'",
                "Run tests: npm test" if config['include_tests'] else None,
            ])
        elif language == 'go':
            steps.extend([
                "Initialize go module: go mod init",
                "Install dependencies: go mod tidy",
                "Import in your code: import \"./{package_name}\"",
                "Run tests: go test ./..." if config['include_tests'] else None,
            ])

        # Remove None values
        steps = [step for step in steps if step is not None]

        steps.extend([
            "Check examples/ directory for usage examples" if config['include_examples'] else None,
            "Update README.md with SDK-specific documentation",
            "Publish to package registry when ready",
        ])

        return [step for step in steps if step is not None]


class SDKGeneratorSDK:
    """SDK for multi-language SDK generation."""

    def __init__(self, config: DevToolsConfig | None = None):
        self.config = config or DevToolsConfig()
        self._service = SDKGeneratorService(self.config)

    async def generate_sdk(
        self,
        language: str,
        api_spec_file: str | None = None,
        api_spec_url: str | None = None,
        service_name: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate SDK for specified language."""
        return await self._service.generate_sdk(
            language=language,
            api_spec_file=api_spec_file,
            api_spec_url=api_spec_url,
            service_name=service_name,
            **kwargs
        )

    async def generate_python_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate Python SDK with async support."""
        return await self._service.generate_python_sdk(**kwargs)

    async def generate_typescript_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate TypeScript SDK with types."""
        return await self._service.generate_typescript_sdk(**kwargs)

    async def generate_go_sdk(self, **kwargs) -> dict[str, Any]:
        """Generate Go SDK with context support."""
        return await self._service.generate_go_sdk(**kwargs)

    def get_supported_languages(self) -> dict[str, Any]:
        """Get list of supported programming languages."""
        return self._service.SUPPORTED_LANGUAGES.copy()
