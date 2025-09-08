#!/usr/bin/env python3
"""
Convert packages from Setuptools to Poetry and standardize versions.
"""
import re
import tomllib
from pathlib import Path


def convert_setuptools_to_poetry(pyproject_path: Path) -> bool:
    """Convert a Setuptools pyproject.toml to Poetry format."""
    print(f"Converting {pyproject_path}")
    
    try:
        with open(pyproject_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Error reading {pyproject_path}: {e}")
        return False
    
    # Check if already Poetry
    build_backend = config.get('build-system', {}).get('build-backend', '')
    if 'poetry' in build_backend:
        print(f"  Already Poetry: {pyproject_path}")
        return True
        
    # Check if Setuptools
    if 'setuptools' not in build_backend:
        print(f"  Not Setuptools: {pyproject_path}")
        return False
    
    # Extract project info
    project = config.get('project', {})
    name = project.get('name', pyproject_path.parent.name)
    version = project.get('version', '1.0.0')
    description = project.get('description', '')
    
    # Handle authors
    authors_list = project.get('authors', [])
    if authors_list and isinstance(authors_list[0], dict):
        author_name = authors_list[0].get('name', 'DotMac Team')
        author_email = authors_list[0].get('email', 'dev@dotmac.com')
        authors = [f"{author_name} <{author_email}>"]
    else:
        authors = ["DotMac Team <dev@dotmac.com>"]
    
    # Extract dependencies
    dependencies = project.get('dependencies', [])
    optional_deps = project.get('optional-dependencies', {})
    
    # Create Poetry config
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
                "classifiers": project.get('classifiers', []),
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
    
    # Add Python 3.9 classifier if missing
    classifiers = poetry_config["tool"]["poetry"]["classifiers"]
    python_classifiers = [c for c in classifiers if "Programming Language :: Python :: 3.9" in c]
    if not python_classifiers and "Programming Language :: Python :: 3" in classifiers:
        idx = next(i for i, c in enumerate(classifiers) if "Programming Language :: Python :: 3" in c and len(c.split("::")) == 3)
        classifiers.insert(idx + 1, "Programming Language :: Python :: 3.9")
    
    # Process dependencies with standardized versions
    for dep in dependencies:
        dep_name, dep_version = parse_dependency(dep)
        if dep_name:
            poetry_config["tool"]["poetry"]["dependencies"][dep_name] = standardize_version(dep_name, dep_version)
    
    # Process dev dependencies
    dev_deps = optional_deps.get('dev', []) + optional_deps.get('test', [])
    for dep in dev_deps:
        dep_name, dep_version = parse_dependency(dep)
        if dep_name:
            poetry_config["tool"]["poetry"]["group"]["dev"]["dependencies"][dep_name] = dep_version or ">=1.0.0"
    
    # Preserve existing tool configurations
    existing_tools = config.get('tool', {})
    for tool_name, tool_config in existing_tools.items():
        if tool_name not in poetry_config["tool"]:
            poetry_config["tool"][tool_name] = tool_config
    
    # Update tool configurations for Poetry
    if "mypy" in poetry_config["tool"]:
        poetry_config["tool"]["mypy"]["python_version"] = "3.9"
    if "ruff" in poetry_config["tool"]:
        poetry_config["tool"]["ruff"]["target-version"] = "py39"
    if "black" in poetry_config["tool"]:
        poetry_config["tool"]["black"]["target-version"] = ['py39', 'py310', 'py311', 'py312']
        poetry_config["tool"]["black"]["line-length"] = 100
    if "pytest" in poetry_config["tool"]:
        if "ini_options" in poetry_config["tool"]["pytest"]:
            poetry_config["tool"]["pytest"]["ini_options"]["asyncio_mode"] = "auto"
    
    # Write new Poetry config
    write_poetry_toml(pyproject_path, poetry_config)
    print(f"  Converted: {pyproject_path}")
    return True


def parse_dependency(dep_string: str) -> tuple[str, str]:
    """Parse dependency string into name and version."""
    if ">=" in dep_string:
        name, version = dep_string.split(">=", 1)
        return name.strip(), f">={version.strip()}"
    elif "==" in dep_string:
        name, version = dep_string.split("==", 1)
        return name.strip(), f"=={version.strip()}"
    elif "~=" in dep_string:
        name, version = dep_string.split("~=", 1)
        return name.strip(), f"~={version.strip()}"
    else:
        return dep_string.strip(), ">=1.0.0"


def standardize_version(package_name: str, current_version: str) -> str:
    """Standardize versions according to recommendations."""
    # Standardized versions
    standards = {
        'fastapi': '>=0.110.0',
        'pydantic': '>=2.0.0',
        'redis': '>=5.0.0',
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
    
    return standards.get(package_name, current_version)


def write_poetry_toml(path: Path, config: dict) -> None:
    """Write Poetry configuration to TOML file."""
    lines = []
    
    # Build system
    lines.append("[build-system]")
    lines.append('requires = ["poetry-core"]')
    lines.append('build-backend = "poetry.core.masonry.api"')
    lines.append("")
    
    # Poetry configuration
    poetry = config["tool"]["poetry"]
    lines.append("[tool.poetry]")
    lines.append(f'name = "{poetry["name"]}"')
    lines.append(f'version = "{poetry["version"]}"')
    lines.append(f'description = "{poetry["description"]}"')
    lines.append(f'authors = {poetry["authors"]}')
    lines.append(f'readme = "{poetry["readme"]}"')
    lines.append(f'license = "{poetry["license"]}"')
    lines.append(f'homepage = "{poetry["homepage"]}"')
    lines.append(f'repository = "{poetry["repository"]}"')
    lines.append(f'documentation = "{poetry["documentation"]}"')
    
    if "classifiers" in poetry:
        lines.append("classifiers = [")
        for classifier in poetry["classifiers"]:
            lines.append(f'    "{classifier}",')
        lines.append("]")
    
    lines.append('packages = [{include = "dotmac", from = "src"}]')
    lines.append("")
    
    # Dependencies
    lines.append("[tool.poetry.dependencies]")
    for name, version in poetry["dependencies"].items():
        if isinstance(version, str):
            lines.append(f'{name} = "{version}"')
        else:
            lines.append(f'{name} = {version}')
    lines.append("")
    
    # Dev dependencies
    if "group" in poetry and "dev" in poetry["group"]:
        lines.append("[tool.poetry.group.dev.dependencies]")
        for name, version in poetry["group"]["dev"]["dependencies"].items():
            lines.append(f'{name} = "{version}"')
        lines.append("")
    
    # Other tool configurations
    for tool_name, tool_config in config["tool"].items():
        if tool_name != "poetry":
            write_tool_section(lines, tool_name, tool_config)
    
    # Write file
    with open(path, 'w') as f:
        f.write("\\n".join(lines))


def write_tool_section(lines: list, tool_name: str, config: dict, prefix: str = "") -> None:
    """Write a tool configuration section."""
    section_name = f"[tool.{tool_name}]" if not prefix else f"[{prefix}.{tool_name}]"
    lines.append(section_name)
    
    for key, value in config.items():
        if isinstance(value, dict):
            lines.append("")
            write_tool_section(lines, key, value, f"tool.{tool_name}" if not prefix else f"{prefix}.{tool_name}")
        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                lines.append(f'{key} = {value}')
            else:
                lines.append(f'{key} = [')
                for item in value:
                    if isinstance(item, str):
                        lines.append(f'    "{item}",')
                    else:
                        lines.append(f'    {item},')
                lines.append(']')
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f'{key} = {value}')
    
    lines.append("")


def main():
    """Main conversion function."""
    print("Converting Setuptools packages to Poetry...")
    
    # Find all pyproject.toml files
    packages_dir = Path("packages")
    pyproject_files = list(packages_dir.rglob("pyproject.toml"))
    
    converted_count = 0
    for pyproject_path in pyproject_files:
        if convert_setuptools_to_poetry(pyproject_path):
            converted_count += 1
    
    print(f"\\nConversion complete: {converted_count} packages processed")


if __name__ == "__main__":
    main()