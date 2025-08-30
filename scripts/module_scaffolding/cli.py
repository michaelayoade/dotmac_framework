"""
CLI tools for module scaffolding operations.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_audit import ModuleAuditor

from .discovery import ModuleDiscovery, ModuleRegistry
from .templates import ModuleTemplate, Platform
from .validation import ModuleValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScaffoldingCLI:
    """Command-line interface for module scaffolding operations."""

    def __init__(self):
        self.framework_root = Path(__file__).parent.parent.parent
        self.template_system = ModuleTemplate()
        self.validator = ModuleValidator()
        self.auditor = ModuleAuditor()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="DotMac Module Scaffolding CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate a new module
  python -m module_scaffolding scaffold billing --platform isp --components all

  # Validate existing modules
  python -m module_scaffolding validate --module analytics

  # Run full audit
  python -m module_scaffolding audit

  # Discover and register modules
  python -m module_scaffolding discover

  # Repair incomplete modules
  python -m module_scaffolding repair billing --missing service,schemas
            """,
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Scaffold command
        scaffold_parser = subparsers.add_parser("scaffold", help="Generate new module")
        scaffold_parser.add_argument("module_name", help="Name of the module to create")
        scaffold_parser.add_argument(
            "--platform",
            choices=["isp", "management"],
            required=True,
            help="Platform to create module for",
        )
        scaffold_parser.add_argument(
            "--components",
            default="core",
            help="Components to generate (core, all, or comma-separated list)",
        )
        scaffold_parser.add_argument(
            "--force", action="store_true", help="Overwrite existing module"
        )
        scaffold_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without creating",
        )

        # Validate command
        validate_parser = subparsers.add_parser("validate", help="Validate modules")
        validate_parser.add_argument("--module", help="Specific module to validate")
        validate_parser.add_argument(
            "--platform", choices=["isp", "management"], help="Platform to validate"
        )
        validate_parser.add_argument(
            "--output",
            choices=["console", "json", "report"],
            default="console",
            help="Output format",
        )
        validate_parser.add_argument(
            "--save-report", help="Save detailed report to file"
        )

        # Audit command
        audit_parser = subparsers.add_parser("audit", help="Run full module audit")
        audit_parser.add_argument(
            "--output",
            choices=["console", "json"],
            default="console",
            help="Output format",
        )
        audit_parser.add_argument("--save", help="Save results to file")

        # Discover command
        discover_parser = subparsers.add_parser(
            "discover", help="Discover and register modules"
        )
        discover_parser.add_argument(
            "--platform", choices=["isp", "management"], help="Platform to discover"
        )
        discover_parser.add_argument(
            "--health-check",
            action="store_true",
            help="Run health checks after discovery",
        )

        # Repair command
        repair_parser = subparsers.add_parser(
            "repair", help="Repair incomplete modules"
        )
        repair_parser.add_argument("module_name", help="Name of the module to repair")
        repair_parser.add_argument(
            "--missing",
            required=True,
            help="Comma-separated list of missing components",
        )
        repair_parser.add_argument(
            "--platform",
            choices=["isp", "management"],
            required=True,
            help="Platform the module belongs to",
        )
        repair_parser.add_argument(
            "--backup", action="store_true", help="Create backup before repair"
        )

        # Status command
        status_parser = subparsers.add_parser(
            "status", help="Show module registry status"
        )
        status_parser.add_argument(
            "--detailed", action="store_true", help="Show detailed status information"
        )

        return parser

    async def run(self, args: List[str]):
        """Run the CLI with given arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        if not parsed_args.command:
            parser.print_help()
            return

        try:
            if parsed_args.command == "scaffold":
                await self.scaffold_module(parsed_args)
            elif parsed_args.command == "validate":
                await self.validate_modules(parsed_args)
            elif parsed_args.command == "audit":
                await self.audit_modules(parsed_args)
            elif parsed_args.command == "discover":
                await self.discover_modules(parsed_args)
            elif parsed_args.command == "repair":
                await self.repair_module(parsed_args)
            elif parsed_args.command == "status":
                await self.show_status(parsed_args)

        except KeyboardInterrupt:
            print("\n🛑 Operation cancelled by user")
        except Exception as e:
            logger.error(f"Command failed: {e}")
            sys.exit(1)

    async def scaffold_module(self, args):
        """Scaffold a new module."""
        print(f"🏗️  Scaffolding module: {args.module_name} ({args.platform})")

        platform = Platform.ISP if args.platform == "isp" else Platform.MANAGEMENT

        # Determine target directory
        if platform == Platform.ISP:
            target_dir = (
                self.framework_root
                / "src"
                / "dotmac_isp"
                / "modules"
                / args.module_name
            )
        else:
            target_dir = (
                self.framework_root
                / "src"
                / "dotmac_management"
                / "modules"
                / args.module_name
            )

        # Check if module exists
        if target_dir.exists() and not args.force:
            print(
                f"❌ Module {args.module_name} already exists. Use --force to overwrite."
            )
            return

        # Determine components to generate
        if args.components == "core":
            components = [
                "init",
                "router",
                "service",
                "models",
                "schemas",
                "repository",
            ]
        elif args.components == "all":
            components = self.template_system.get_all_components()
        else:
            components = [c.strip() for c in args.components.split(",")]

        # Generate template variables
        variables = self.template_system.generate_module_variables(
            args.module_name, platform
        )

        if args.dry_run:
            print("🔍 Dry run - would create:")
            for component in components:
                filename = self.template_system.component_templates[component].filename
                print(f"  - {target_dir / filename}")
            return

        # Create module directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate components
        created_files = []
        for component in components:
            try:
                content = self.template_system.generate_component(component, variables)
                component_config = self.template_system.component_templates[component]
                file_path = target_dir / component_config.filename

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                created_files.append(str(file_path))
                print(f"  ✅ Created {component_config.filename}")

            except Exception as e:
                print(f"  ❌ Failed to create {component}: {e}")

        print(f"\n🎉 Module {args.module_name} scaffolded successfully!")
        print(f"📁 Location: {target_dir}")
        print(f"📄 Created {len(created_files)} files")

        # Run validation on created module
        print("\n🔍 Running validation on new module...")
        result = await self.validator.validate_module(target_dir, args.module_name)
        print(f"📊 Validation score: {result.score:.1f}/100")

        if result.issues:
            print("⚠️  Issues found:")
            for issue in result.issues[:3]:
                print(f"  - {issue.message}")
            if len(result.issues) > 3:
                print(f"  ... and {len(result.issues) - 3} more issues")

    async def validate_modules(self, args):
        """Validate modules."""
        print("🔍 Running module validation...")

        if args.module:
            # Validate specific module
            if args.platform:
                platform_dir = (
                    "dotmac_isp" if args.platform == "isp" else "dotmac_management"
                )
                module_path = (
                    self.framework_root / "src" / platform_dir / "modules" / args.module
                )
            else:
                # Try both platforms
                isp_path = (
                    self.framework_root / "src" / "dotmac_isp" / "modules" / args.module
                )
                mgmt_path = (
                    self.framework_root
                    / "src"
                    / "dotmac_management"
                    / "modules"
                    / args.module
                )

                if isp_path.exists():
                    module_path = isp_path
                elif mgmt_path.exists():
                    module_path = mgmt_path
                else:
                    print(f"❌ Module {args.module} not found")
                    return

            if not module_path.exists():
                print(f"❌ Module {args.module} not found at {module_path}")
                return

            result = await self.validator.validate_module(module_path, args.module)
            results = {args.module: result}
        else:
            # Validate all modules
            discovery = ModuleDiscovery()
            modules = await discovery.discover_all_modules()

            # Filter by platform if specified
            if args.platform:
                modules = {
                    k: v for k, v in modules.items() if v.platform == args.platform
                }

            # Convert to validation format
            validation_modules = {}
            for name, info in modules.items():
                validation_modules[name] = self.framework_root / info.path

            results = await self.validator.validate_multiple_modules(validation_modules)

        # Output results
        if args.output == "json":
            output = {}
            for name, result in results.items():
                output[name] = {
                    "is_valid": result.is_valid,
                    "score": result.score,
                    "issues_count": len(result.issues),
                    "critical_count": result.critical_count,
                    "errors_count": result.errors_count,
                    "warnings_count": result.warnings_count,
                    "missing_components": result.missing_components,
                    "issues": [
                        {
                            "level": issue.level.value,
                            "category": issue.category.value,
                            "message": issue.message,
                            "file_path": issue.file_path,
                            "line_number": issue.line_number,
                            "rule_id": issue.rule_id,
                        }
                        for issue in result.issues
                    ],
                }
            print(json.dumps(output, indent=2))
        elif args.output == "report":
            report = self.validator.generate_validation_report(results)
            print(report)
        else:
            # Console output
            total = len(results)
            valid = len([r for r in results.values() if r.is_valid])
            avg_score = (
                sum(r.score for r in results.values()) / total if total > 0 else 0
            )

            print(f"\n📊 Validation Results:")
            print(f"  Total modules: {total}")
            print(f"  Valid modules: {valid} ({valid/total*100:.1f}%)")
            print(f"  Average score: {avg_score:.1f}/100")

            # Show worst modules
            sorted_results = sorted(results.items(), key=lambda x: x[1].score)
            if sorted_results:
                print(f"\n⚠️  Modules needing attention:")
                for name, result in sorted_results[:5]:
                    status = "✅" if result.is_valid else "❌"
                    print(
                        f"  {status} {name}: {result.score:.1f}/100 ({result.errors_count}E, {result.warnings_count}W)"
                    )

        # Save report if requested
        if args.save_report:
            report = self.validator.generate_validation_report(results)
            with open(args.save_report, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"📄 Detailed report saved to {args.save_report}")

    async def audit_modules(self, args):
        """Run full module audit."""
        print("📋 Running comprehensive module audit...")

        # Run the audit
        modules = self.auditor.scan_modules()
        categories = self.auditor.categorize_modules()

        if args.output == "json":
            # Generate JSON output
            output = {
                "summary": {
                    "total_modules": len(modules),
                    "completeness_breakdown": {
                        level.value: len(module_list)
                        for level, module_list in categories.items()
                    },
                },
                "modules": [
                    {
                        "name": m.name,
                        "platform": m.platform,
                        "completeness_level": m.completeness_level.value,
                        "priority": m.priority,
                        "existing_components": [c.value for c in m.existing_components],
                        "missing_components": [c.value for c in m.missing_components],
                        "notes": m.notes,
                    }
                    for m in modules
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            # Console output
            report = self.auditor.generate_report()
            print(report)

        # Save if requested
        if args.save:
            report = self.auditor.generate_report()
            with open(args.save, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n📄 Audit report saved to {args.save}")

    async def discover_modules(self, args):
        """Discover and register modules."""
        print("🔍 Discovering modules...")

        registry = ModuleRegistry()
        await registry.initialize()

        modules = registry.modules

        if args.platform:
            modules = {k: v for k, v in modules.items() if v.platform == args.platform}

        print(f"\n📊 Discovery Results:")
        print(f"  Total modules: {len(modules)}")

        # Group by status
        status_groups = {}
        for module in modules.values():
            status = module.status.value
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(module)

        for status, module_list in status_groups.items():
            print(f"  {status.title()}: {len(module_list)} modules")

        # Show module details
        print(f"\n📋 Module Details:")
        for name, module in sorted(modules.items()):
            status_icon = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unavailable": "❌",
                "loading": "🔄",
                "error": "🚨",
            }
            icon = status_icon.get(module.status.value, "❓")

            components = []
            if module.router_available:
                components.append("R")
            if module.service_available:
                components.append("S")
            if module.models_available:
                components.append("M")
            if module.schemas_available:
                components.append("Sch")
            if module.repository_available:
                components.append("Rep")

            components_str = ",".join(components) if components else "None"
            print(f"  {icon} {name} ({module.platform}): [{components_str}]")

            if module.error_message:
                print(f"      Error: {module.error_message}")

        if args.health_check:
            print(f"\n🏥 Running health checks...")
            await registry.run_health_checks()
            print("✅ Health checks completed")

        # Cleanup
        await registry.shutdown()

    async def repair_module(self, args):
        """Repair incomplete module."""
        print(f"🔧 Repairing module: {args.module_name}")

        platform = Platform.ISP if args.platform == "isp" else Platform.MANAGEMENT

        # Find module directory
        if platform == Platform.ISP:
            module_dir = (
                self.framework_root
                / "src"
                / "dotmac_isp"
                / "modules"
                / args.module_name
            )
        else:
            module_dir = (
                self.framework_root
                / "src"
                / "dotmac_management"
                / "modules"
                / args.module_name
            )

        if not module_dir.exists():
            print(f"❌ Module {args.module_name} not found at {module_dir}")
            return

        # Backup if requested
        if args.backup:
            import shutil

            from dotmac_shared.api.exception_handlers import standard_exception_handler

            backup_dir = module_dir.parent / f"{args.module_name}_backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(module_dir, backup_dir)
            print(f"💾 Backup created at {backup_dir}")

        # Parse missing components
        missing_components = [c.strip() for c in args.missing.split(",")]

        # Generate template variables
        variables = self.template_system.generate_module_variables(
            args.module_name, platform
        )

        # Create missing components
        created_files = []
        for component in missing_components:
            if component not in self.template_system.component_templates:
                print(f"⚠️  Unknown component: {component}")
                continue

            try:
                component_config = self.template_system.component_templates[component]
                file_path = module_dir / component_config.filename

                if file_path.exists():
                    print(f"⚠️  {component_config.filename} already exists, skipping")
                    continue

                content = self.template_system.generate_component(component, variables)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                created_files.append(str(file_path))
                print(f"  ✅ Created {component_config.filename}")

            except Exception as e:
                print(f"  ❌ Failed to create {component}: {e}")

        print(f"\n🎉 Module {args.module_name} repaired successfully!")
        print(f"📄 Created {len(created_files)} files")

        # Run validation
        print("\n🔍 Running validation...")
        result = await self.validator.validate_module(module_dir, args.module_name)
        print(f"📊 Validation score: {result.score:.1f}/100")

    async def show_status(self, args):
        """Show module registry status."""
        print("📊 Module Registry Status")
        print("=" * 40)

        try:
            registry = ModuleRegistry()
            await registry.initialize()

            stats = registry.get_registry_stats()

            print(f"Total modules: {stats['total_modules']}")
            print(f"Healthy routers: {stats['healthy_routers']}")

            print(f"\nBy Platform:")
            for platform, count in stats["by_platform"].items():
                print(f"  {platform}: {count} modules")

            print(f"\nBy Status:")
            for status, count in stats["by_status"].items():
                print(f"  {status}: {count} modules")

            if args.detailed:
                print(f"\nComponent Availability:")
                for component, count in stats["component_availability"].items():
                    percentage = (
                        (count / stats["total_modules"]) * 100
                        if stats["total_modules"] > 0
                        else 0
                    )
                    print(f"  {component}: {count} modules ({percentage:.1f}%)")

            await registry.shutdown()

        except Exception as e:
            print(f"❌ Error getting status: {e}")


def main():
    """Main CLI entry point."""
    cli = ScaffoldingCLI()
    asyncio.run(cli.run(sys.argv[1:]))


if __name__ == "__main__":
    main()
