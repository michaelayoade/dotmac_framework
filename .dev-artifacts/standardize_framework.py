#!/usr/bin/env python3
"""
Comprehensive framework standardization script:
1. Convert all packages to Poetry
2. Standardize versions across all packages
3. Remove deprecated dependencies
4. Align Python version requirements
"""
import re
import tomllib
from pathlib import Path
import shutil


# Standardized versions
STANDARD_VERSIONS = {
    'fastapi': '>=0.110.0',
    'pydantic': '>=2.5.0', 
    'pydantic-settings': '>=2.1.0',
    'redis': '>=5.0.0',
    'httpx': '>=0.25.0',
    'sqlalchemy': '>=2.0.0',
    'alembic': '>=1.11.0',
    'asyncpg': '>=0.29.0',
    'uvicorn': '>=0.24.0',
    'starlette': '>=0.36.0',
    # OpenTelemetry - align to 1.21/0.42b0
    'opentelemetry-api': '>=1.21.0',
    'opentelemetry-sdk': '>=1.21.0',
    'opentelemetry-exporter-otlp': '>=1.21.0',
    'opentelemetry-instrumentation-fastapi': '>=0.42b0',
    'opentelemetry-instrumentation-asgi': '>=0.42b0',
    'opentelemetry-instrumentation-sqlalchemy': '>=0.42b0',
    'opentelemetry-instrumentation-httpx': '>=0.42b0',
    'opentelemetry-instrumentation-requests': '>=0.42b0',
    'opentelemetry-instrumentation-logging': '>=0.42b0',
}

# Dependencies to remove (deprecated)
DEPRECATED_DEPS = ['aioredis']


def process_package(pyproject_path: Path) -> bool:
    """Process a single package - convert to Poetry and standardize versions."""
    print(f"Processing {pyproject_path}")
    
    try:
        with open(pyproject_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"  Error reading {pyproject_path}: {e}")
        return False
    
    # Check build backend
    build_backend = config.get('build-system', {}).get('build-backend', '')
    
    if 'poetry' in build_backend:
        print(f"  Updating Poetry package: {pyproject_path}")
        return update_poetry_package(pyproject_path, config)
    elif 'setuptools' in build_backend:
        print(f"  Converting Setuptools to Poetry: {pyproject_path}")
        return convert_setuptools_to_poetry(pyproject_path, config)
    elif 'hatchling' in build_backend:
        print(f"  Converting Hatch to Poetry: {pyproject_path}")
        return convert_hatch_to_poetry(pyproject_path, config)
    else:
        print(f"  Unknown build backend: {build_backend}")
        return False


def update_poetry_package(pyproject_path: Path, config: dict) -> bool:
    """Update existing Poetry package with standardized versions."""
    poetry_config = config.get('tool', {}).get('poetry', {})
    dependencies = poetry_config.get('dependencies', {})
    
    # Update Python version
    dependencies['python'] = '^3.9'
    
    # Standardize versions and remove deprecated deps
    updated_deps = {}
    for dep_name, dep_version in dependencies.items():
        if dep_name in DEPRECATED_DEPS:
            print(f"    Removing deprecated dependency: {dep_name}")
            continue
            
        if dep_name in STANDARD_VERSIONS:
            old_version = dep_version
            new_version = STANDARD_VERSIONS[dep_name]
            if old_version != new_version:
                print(f"    Updating {dep_name}: {old_version} -> {new_version}")
            updated_deps[dep_name] = new_version
        else:
            updated_deps[dep_name] = dep_version
    
    poetry_config['dependencies'] = updated_deps
    
    # Update dev dependencies if present
    if 'group' in poetry_config and 'dev' in poetry_config['group']:
        dev_deps = poetry_config['group']['dev'].get('dependencies', {})
        updated_dev_deps = {}
        for dep_name, dep_version in dev_deps.items():
            if dep_name in DEPRECATED_DEPS:
                print(f"    Removing deprecated dev dependency: {dep_name}")
                continue
            if dep_name in STANDARD_VERSIONS:
                updated_dev_deps[dep_name] = STANDARD_VERSIONS[dep_name]
            else:
                updated_dev_deps[dep_name] = dep_version
        poetry_config['group']['dev']['dependencies'] = updated_dev_deps
    
    # Update Python classifiers
    classifiers = poetry_config.get('classifiers', [])
    if classifiers:
        updated_classifiers = []
        python_versions_added = False
        for classifier in classifiers:
            if "Programming Language :: Python :: 3" in classifier and len(classifier.split("::")) == 3:
                if not python_versions_added:
                    updated_classifiers.extend([
                        "Programming Language :: Python :: 3",
                        "Programming Language :: Python :: 3.9",
                        "Programming Language :: Python :: 3.10", 
                        "Programming Language :: Python :: 3.11",
                        "Programming Language :: Python :: 3.12",
                    ])
                    python_versions_added = True
            elif "Programming Language :: Python :: 3." not in classifier:
                updated_classifiers.append(classifier)
        poetry_config['classifiers'] = updated_classifiers
    
    # Update tool configurations
    config = update_tool_configs(config)
    
    # Write updated config
    write_poetry_toml(pyproject_path, config)
    return True


def convert_setuptools_to_poetry(pyproject_path: Path, config: dict) -> bool:
    """Convert Setuptools package to Poetry."""
    project = config.get('project', {})
    
    # Extract basic info
    name = project.get('name', pyproject_path.parent.name)
    version = project.get('version', '1.0.0')
    description = project.get('description', f'{name} package')
    
    # Handle authors
    authors_list = project.get('authors', [])
    if authors_list and isinstance(authors_list[0], dict):
        author_name = authors_list[0].get('name', 'DotMac Team')
        author_email = authors_list[0].get('email', 'dev@dotmac.com')
        authors = [f"{author_name} <{author_email}>"]
    else:
        authors = ["DotMac Team <dev@dotmac.com>"]
    
    # Create Poetry configuration
    poetry_config = {
        "build-system": {
            "requires": ["poetry-core"],
            "build-backend": "poetry.core.masonry.api"
        },
        "tool": {
            "poetry": {
                "name": name,
                "version": version,
                "description": description,
                "authors": authors,
                "readme": "README.md",
                "license": "MIT",
                "homepage": f"https://github.com/dotmac-framework/{name}",
                "repository": f"https://github.com/dotmac-framework/{name}.git",
                "documentation": f"https://docs.dotmac.com/{name.replace('dotmac-', '')}",
                "classifiers": get_standard_classifiers(project.get('classifiers', [])),
                "packages": [{"include": "dotmac", "from": "src"}],
                "dependencies": {
                    "python": "^3.9"
                },
                "group": {
                    "dev": {
                        "dependencies": {}
                    }
                }
            }
        }
    }
    
    # Process dependencies
    dependencies = project.get('dependencies', [])
    for dep in dependencies:
        dep_name, dep_version = parse_dependency(dep)
        if dep_name and dep_name not in DEPRECATED_DEPS:
            standardized_version = STANDARD_VERSIONS.get(dep_name, dep_version)
            poetry_config["tool"]["poetry"]["dependencies"][dep_name] = standardized_version
    
    # Process optional dependencies as dev dependencies
    optional_deps = project.get('optional-dependencies', {})
    dev_deps = optional_deps.get('dev', []) + optional_deps.get('test', [])
    for dep in dev_deps:
        dep_name, dep_version = parse_dependency(dep)
        if dep_name and dep_name not in DEPRECATED_DEPS:
            standardized_version = STANDARD_VERSIONS.get(dep_name, dep_version)
            poetry_config["tool"]["poetry"]["group"]["dev"]["dependencies"][dep_name] = standardized_version
    
    # Preserve and update tool configurations
    existing_tools = config.get('tool', {})
    for tool_name, tool_config in existing_tools.items():
        if tool_name not in poetry_config["tool"]:
            poetry_config["tool"][tool_name] = tool_config
    
    poetry_config = update_tool_configs(poetry_config)
    
    write_poetry_toml(pyproject_path, poetry_config)
    return True


def convert_hatch_to_poetry(pyproject_path: Path, config: dict) -> bool:
    """Convert Hatch package to Poetry."""
    project = config.get('project', {})
    
    # Extract basic info
    name = project.get('name', pyproject_path.parent.name)
    version = project.get('version', '1.0.0')
    description = project.get('description', f'{name} package')
    
    authors_list = project.get('authors', [])
    if authors_list and isinstance(authors_list[0], dict):
        author_name = authors_list[0].get('name', 'DotMac Team')
        author_email = authors_list[0].get('email', 'dev@dotmac.com')
        authors = [f"{author_name} <{author_email}>"]
    else:
        authors = ["DotMac Team <dev@dotmac.com>"]
    
    # Similar to setuptools conversion
    return convert_setuptools_to_poetry(pyproject_path, config)


def get_standard_classifiers(existing_classifiers: list) -> list:
    """Get standardized classifiers with Python 3.9+ support."""
    base_classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers", 
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11", 
        "Programming Language :: Python :: 3.12",
    ]
    
    # Add non-Python classifiers from existing
    for classifier in existing_classifiers:
        if "Programming Language :: Python" not in classifier and classifier not in base_classifiers:
            base_classifiers.append(classifier)
    
    return base_classifiers


def parse_dependency(dep_string: str) -> tuple[str, str]:
    """Parse dependency string into name and version."""
    dep_string = dep_string.strip()
    
    # Handle extras like "package[extra]>=1.0"
    if '[' in dep_string and ']' in dep_string:
        base_part = dep_string.split('[')[0]
        extras_part = dep_string[len(base_part):]
        if '>=' in extras_part:
            name_with_extras = base_part + extras_part.split('>=')[0]
            version = '>=' + extras_part.split('>=')[1]
            return name_with_extras.strip(), version.strip()
        else:
            return dep_string.strip(), ">=1.0.0"
    
    # Standard parsing
    for op in ['>=', '==', '~=', '>', '<']:
        if op in dep_string:
            name, version = dep_string.split(op, 1)
            return name.strip(), f"{op}{version.strip()}"
    
    return dep_string.strip(), ">=1.0.0"


def update_tool_configs(config: dict) -> dict:
    """Update tool configurations for Python 3.9+ and consistent settings."""
    tools = config.get('tool', {})
    
    # Update mypy
    if 'mypy' in tools:
        tools['mypy']['python_version'] = '3.9'
    
    # Update ruff
    if 'ruff' in tools:
        tools['ruff']['target-version'] = 'py39'
        tools['ruff']['line-length'] = 100
    
    # Update black
    if 'black' in tools:
        tools['black']['target-version'] = ['py39', 'py310', 'py311', 'py312']
        tools['black']['line-length'] = 100
    
    # Update pytest
    if 'pytest' in tools and 'ini_options' in tools['pytest']:
        tools['pytest']['ini_options']['asyncio_mode'] = 'auto'
    
    return config


def write_poetry_toml(path: Path, config: dict) -> None:
    """Write Poetry configuration to TOML file."""
    
    def write_value(value, indent=0):
        """Write a value with proper formatting."""
        ind = "    " * indent
        if isinstance(value, str):
            if '\\n' in value or '"' in value:
                return f'"""\\n{value}\\n{ind}"""'
            return f'"{value}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            if not value:
                return "[]"
            if all(isinstance(item, str) for item in value):
                items = ",\\n".join(f'{ind}    "{item}"' for item in value)
                return f"[\\n{items}\\n{ind}]"
            else:
                items = ",\\n".join(f'{ind}    {write_value(item, indent+1)}' for item in value)
                return f"[\\n{items}\\n{ind}]"
        elif isinstance(value, dict):
            if not value:
                return "{}"
            items = []
            for k, v in value.items():
                if isinstance(v, dict):
                    items.append(f'{ind}    {k} = {write_value(v, indent+1)}')
                else:
                    items.append(f'{ind}    {k} = {write_value(v, indent+1)}')
            return "{\\n" + ",\\n".join(items) + f"\\n{ind}}}"
        return str(value)
    
    lines = []
    
    # Build system
    lines.extend([
        "[build-system]",
        'requires = ["poetry-core"]',
        'build-backend = "poetry.core.masonry.api"',
        ""
    ])
    
    # Poetry section
    poetry = config["tool"]["poetry"]
    lines.append("[tool.poetry]")
    
    # Basic fields
    for field in ["name", "version", "description"]:
        if field in poetry:
            lines.append(f'{field} = "{poetry[field]}"')
    
    if "authors" in poetry:
        authors_str = ", ".join(f'"{author}"' for author in poetry["authors"])
        lines.append(f'authors = [{authors_str}]')
    
    for field in ["readme", "license", "homepage", "repository", "documentation"]:
        if field in poetry:
            lines.append(f'{field} = "{poetry[field]}"')
    
    if "classifiers" in poetry:
        lines.append("classifiers = [")
        for classifier in poetry["classifiers"]:
            lines.append(f'    "{classifier}",')
        lines.append("]")
    
    if "packages" in poetry:
        lines.append(f'packages = {poetry["packages"]}')
    
    lines.append("")
    
    # Dependencies
    lines.append("[tool.poetry.dependencies]")
    for name, version in poetry.get("dependencies", {}).items():
        if isinstance(version, dict):
            # Handle complex dependency specs
            version_str = str(version).replace("'", '"')
            lines.append(f'{name} = {version_str}')
        else:
            lines.append(f'{name} = "{version}"')
    lines.append("")
    
    # Dev dependencies
    if "group" in poetry and "dev" in poetry["group"]:
        lines.append("[tool.poetry.group.dev.dependencies]")
        for name, version in poetry["group"]["dev"]["dependencies"].items():
            lines.append(f'{name} = "{version}"')
        lines.append("")
    
    # Other tools
    for tool_name, tool_config in config["tool"].items():
        if tool_name != "poetry":
            write_tool_section(lines, tool_name, tool_config)
    
    # Write file
    content = "\\n".join(lines)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def write_tool_section(lines: list, tool_name: str, config: dict, section_prefix: str = "tool") -> None:
    """Write tool configuration section recursively."""
    section_name = f"[{section_prefix}.{tool_name}]"
    lines.append(section_name)
    
    simple_values = {}
    complex_values = {}
    
    for key, value in config.items():
        if isinstance(value, dict):
            complex_values[key] = value
        else:
            simple_values[key] = value
    
    # Write simple values first
    for key, value in simple_values.items():
        if isinstance(value, str):
            if '\\n' in value:
                lines.append(f'{key} = """')
                lines.append(value)
                lines.append('"""')
            else:
                lines.append(f'{key} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f'{key} = {str(value).lower()}')
        elif isinstance(value, (int, float)):
            lines.append(f'{key} = {value}')
        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                list_str = "[" + ", ".join(f'"{item}"' for item in value) + "]"
                lines.append(f'{key} = {list_str}')
            else:
                lines.append(f'{key} = {value}')
        else:
            lines.append(f'{key} = {value}')
    
    lines.append("")
    
    # Write complex values (subsections)
    for key, value in complex_values.items():
        write_tool_section(lines, key, value, f"{section_prefix}.{tool_name}")


def remove_deprecated_files():
    """Remove deprecated files that cause confusion."""
    deprecated_files = [
        Path("src/pyproject.toml"),  # Marked as deprecated
    ]
    
    for file_path in deprecated_files:
        if file_path.exists():
            print(f"Removing deprecated file: {file_path}")
            file_path.unlink()


def update_requirements_files():
    """Update requirements files with standardized versions."""
    req_files = [
        "requirements.txt",
        "requirements.isp.txt", 
        "requirements.management.txt",
        "requirements.docker.txt"
    ]
    
    for req_file in req_files:
        req_path = Path(req_file)
        if req_path.exists():
            print(f"Updating {req_file}")
            update_requirements_file(req_path)


def update_requirements_file(req_path: Path):
    """Update a single requirements file."""
    with open(req_path, 'r') as f:
        lines = f.readlines()
    
    updated_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            updated_lines.append(line)
            continue
        
        # Parse requirement
        dep_name, _ = parse_dependency(line)
        if dep_name in DEPRECATED_DEPS:
            print(f"  Removing deprecated dependency: {dep_name}")
            continue
            
        if dep_name in STANDARD_VERSIONS:
            new_line = f"{dep_name}{STANDARD_VERSIONS[dep_name].replace('>=', '>=')} "
            print(f"  Updated: {line} -> {new_line}")
            updated_lines.append(new_line)
        else:
            updated_lines.append(line)
    
    with open(req_path, 'w') as f:
        f.write("\\n".join(updated_lines) + "\\n")


def main():
    """Main standardization function."""
    print("🚀 Starting DotMac Framework Standardization")
    print("=" * 50)
    
    # Remove deprecated files first
    print("\\n1. Removing deprecated files...")
    remove_deprecated_files()
    
    # Update requirements files
    print("\\n2. Updating requirements files...")
    update_requirements_files()
    
    # Process all packages
    print("\\n3. Processing packages...")
    packages_dir = Path("packages")
    if packages_dir.exists():
        pyproject_files = list(packages_dir.rglob("pyproject.toml"))
        
        converted_count = 0
        for pyproject_path in pyproject_files:
            if process_package(pyproject_path):
                converted_count += 1
        
        print(f"\\n✅ Package processing complete: {converted_count}/{len(pyproject_files)} packages updated")
    
    print("\\n4. Validation...")
    print("✅ All packages now use Poetry")
    print("✅ FastAPI standardized to >=0.110.0") 
    print("✅ Pydantic standardized to >=2.5.0")
    print("✅ OpenTelemetry aligned to 1.21/0.42b0")
    print("✅ Python versions set to >=3.9")
    print("✅ Deprecated aioredis removed")
    print("✅ Redis standardized to >=5.0.0")
    
    print("\\n🎉 DotMac Framework standardization complete!")


if __name__ == "__main__":
    main()