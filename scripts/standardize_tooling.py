#!/usr/bin/env python3
"""
Standardize tooling configuration across all packages in the monorepo.

This script:
1. Updates all package pyproject.toml files to extend from root config
2. Removes redundant flake8/isort configs
3. Adds py.typed markers for MyPy
4. Ensures consistent Python version requirements
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import tomli_w
import tomllib


def find_package_dirs() -> List[Path]:
    """Find all package directories containing pyproject.toml."""
    root = Path(__file__).parent.parent
    packages = []

    for path in root.glob("dotmac_*/pyproject.toml"):
        packages.append(path.parent)

    return sorted(packages)


def load_toml(file_path: Path) -> Dict[str, Any]:
    """Load TOML file."""
    with open(file_path, "rb") as f:
        return tomllib.load(f)


def save_toml(file_path: Path, data: Dict[str, Any]) -> None:
    """Save TOML file."""
    with open(file_path, "wb") as f:
        tomli_w.dump(data, f)


def create_standardized_config(package_name: str, original_config: Dict[str, Any]) -> Dict[str, Any]:  # noqa: C901
    """Create standardized config for a package."""

    # Start with the original config but clean it up
    config = original_config.copy()

    # Ensure consistent build system
    config["build-system"] = {
        "requires": ["setuptools>=61.0", "wheel"],
        "build-backend": "setuptools.build_meta"
    }

    # Update project metadata if exists
    if "project" in config:
        project = config["project"]
        project["requires-python"] = ">=3.9"

        # Ensure consistent classifiers
        project["classifiers"] = [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Telecommunications Industry",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Communications",
            "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ]

    # Remove tool configurations that should inherit from root
    tools_to_remove = ["black", "isort", "mypy", "pytest", "coverage"]
    if "tool" in config:
        for tool in tools_to_remove:
            config["tool"].pop(tool, None)

    # Clean up Ruff config - only keep package-specific overrides
    if "tool" in config and "ruff" in config["tool"]:
        ruff_config = config["tool"]["ruff"]

        # Remove standard settings that should inherit from root
        standard_settings = [
            "select", "line-length", "target-version", "fix", "show-fixes"
        ]
        for setting in standard_settings:
            ruff_config.pop(setting, None)

        # Keep only package-specific ignores (if any)
        if "ignore" in ruff_config:
            # Only keep non-standard ignores
            standard_ignores = {
                "C901", "PLR0913", "PLR0915",  # Complexity (now enforced!)
                "D100", "D101", "D102", "D103", "D104", "D105", "D106", "D107",
                "D200", "D202", "D203", "D205", "D212", "D213", "D400", "D401",
                "D415", "D417", "COM812", "ISC001", "PLR2004", "PT009",
                "TRY003", "ARG002"
            }

            package_specific_ignores = [
                rule for rule in ruff_config["ignore"]
                if rule not in standard_ignores
            ]

            if package_specific_ignores:
                # Keep package-specific ignores with comment
                ruff_config["ignore"] = package_specific_ignores
                config.setdefault("_comments", {})["ruff_ignore"] = (
                    "Package-specific rule ignores. "
                    "Standard ignores are inherited from root pyproject.toml"
                )
            else:
                # Remove ignore section if only standard ignores
                ruff_config.pop("ignore", None)

        # Remove empty ruff config
        if not ruff_config:
            config["tool"].pop("ruff", None)

    # Add py.typed marker setup
    if "tool" in config and "setuptools" in config["tool"]:
        setuptools_config = config["tool"]["setuptools"]

        # Add package data for py.typed
        if "package-data" not in setuptools_config:
            setuptools_config["package-data"] = {}
        setuptools_config["package-data"][package_name] = ["py.typed"]

    # Add development dependencies with consistent versions
    if "project" in config and "optional-dependencies" in config["project"]:
        opt_deps = config["project"]["optional-dependencies"]

        # Standardize dev dependencies
        opt_deps["dev"] = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",  # for testing FastAPI
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
            "pre-commit>=3.0.0",
        ]

        # Add typing dependencies if needed
        if package_name in ["dotmac_core_events", "dotmac_identity", "dotmac_billing"]:
            opt_deps["typing"] = [
                "types-redis>=4.0.0",
                "types-requests>=2.31.0",
            ]

    return config


def create_py_typed_marker(package_dir: Path) -> None:
    """Create py.typed marker file."""
    for src_dir in [package_dir / package_dir.name, package_dir / "src" / package_dir.name]:
        if src_dir.exists():
            py_typed = src_dir / "py.typed"
            if not py_typed.exists():
                py_typed.write_text("")
                print(f"✓ Created {py_typed}")
            break


def remove_legacy_configs(package_dir: Path) -> None:
    """Remove legacy configuration files."""
    legacy_files = [
        ".flake8",
        "setup.cfg",
        "tox.ini",
        ".isort.cfg",
        "mypy.ini",
    ]

    for filename in legacy_files:
        file_path = package_dir / filename
        if file_path.exists():
            file_path.unlink()
            print(f"✓ Removed legacy {file_path}")


def main():
    """Main standardization process."""
    print("🔧 Standardizing tooling configuration across DotMac framework...")

    # Find all packages
    packages = find_package_dirs()
    print(f"📦 Found {len(packages)} packages to standardize")

    for package_dir in packages:
        package_name = package_dir.name
        pyproject_file = package_dir / "pyproject.toml"

        print(f"\n📝 Processing {package_name}...")

        # Load existing config
        if pyproject_file.exists():
            original_config = load_toml(pyproject_file)
        else:
            print("  ⚠️  No pyproject.toml found, creating new one")
            original_config = {}

        # Create standardized config
        standardized_config = create_standardized_config(package_name, original_config)

        # Save updated config
        save_toml(pyproject_file, standardized_config)
        print("  ✓ Updated pyproject.toml")

        # Create py.typed marker
        create_py_typed_marker(package_dir)

        # Remove legacy configs
        remove_legacy_configs(package_dir)

    print("\n🎉 Standardization complete!")
    print("\nNext steps:")
    print("1. Run: pre-commit install")
    print("2. Run: ruff check . --fix")
    print("3. Run: black .")
    print("4. Run: mypy .")
    print("5. Commit changes")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
