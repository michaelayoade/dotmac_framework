#!/usr/bin/env python3
"""
Module Audit Script - Phase 1 of Module Scaffolding Strategy

This script audits all modules in the DotMac Framework to identify:
1. Existing modules and their components
2. Missing components per module
3. Module completeness levels
4. Priority recommendations for completion

Usage:
    python scripts/module_audit.py
"""

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class ComponentType(Enum):
    """Standard module components."""

    INIT = "__init__.py"
    ROUTER = "router.py"
    SERVICE = "service.py"
    REPOSITORY = "repository.py"
    MODELS = "models.py"
    SCHEMAS = "schemas.py"
    TASKS = "tasks.py"
    DEPENDENCIES = "dependencies.py"
    EXCEPTIONS = "exceptions.py"


class CompletenessLevel(Enum):
    """Module completeness levels."""

    COMPLETE = "complete"  # All required components present
    FUNCTIONAL = "functional"  # Core components present (router, service, models)
    PARTIAL = "partial"  # Some components missing
    MINIMAL = "minimal"  # Only __init__.py or basic files
    EMPTY = "empty"  # No meaningful components


@dataclass
class ModuleAnalysis:
    """Analysis results for a single module."""

    name: str
    path: str
    platform: str  # 'isp' or 'management'
    existing_components: set[ComponentType] = field(default_factory=set)
    missing_components: set[ComponentType] = field(default_factory=set)
    additional_files: list[str] = field(default_factory=list)
    completeness_level: CompletenessLevel = CompletenessLevel.EMPTY
    priority: str = "low"  # low, medium, high, critical
    notes: list[str] = field(default_factory=list)


class ModuleAuditor:
    """Module audit system."""

    def __init__(self):
        self.framework_root = Path(__file__).parent.parent  # noqa: B008
        self.src_root = self.framework_root / "src"
        self.modules: list[ModuleAnalysis] = []

        # Required components for different completeness levels
        self.REQUIRED_CORE = {
            ComponentType.INIT,
            ComponentType.ROUTER,
            ComponentType.SERVICE,
            ComponentType.MODELS,
        }
        self.REQUIRED_FULL = {
            ComponentType.INIT,
            ComponentType.ROUTER,
            ComponentType.SERVICE,
            ComponentType.REPOSITORY,
            ComponentType.MODELS,
            ComponentType.SCHEMAS,
        }

    def scan_modules(self) -> list[ModuleAnalysis]:
        """Scan all modules in the framework."""
        print("🔍 Scanning modules...")

        # ISP Framework modules
        isp_modules_dir = self.src_root / "dotmac_isp" / "modules"
        if isp_modules_dir.exists():
            self._scan_platform_modules(isp_modules_dir, "isp")

        # Management Platform modules
        mgmt_modules_dir = self.src_root / "dotmac_management" / "modules"
        if mgmt_modules_dir.exists():
            self._scan_platform_modules(mgmt_modules_dir, "management")

        print(f"📊 Found {len(self.modules)} modules total")
        return self.modules

    def _scan_platform_modules(self, modules_dir: Path, platform: str):
        """Scan modules in a specific platform directory."""
        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                analysis = self._analyze_module(module_dir, platform)
                if analysis:
                    self.modules.append(analysis)

    def _analyze_module(self, module_path: Path, platform: str) -> ModuleAnalysis:
        """Analyze a single module."""
        module_name = module_path.name
        analysis = ModuleAnalysis(
            name=module_name,
            path=str(module_path.relative_to(self.framework_root)),
            platform=platform,
        )

        # Check for standard components
        for component in ComponentType:
            component_path = module_path / component.value
            if component_path.exists():
                analysis.existing_components.add(component)
            else:
                analysis.missing_components.add(component)

        # Find additional files
        for file_path in module_path.rglob("*.py"):
            if file_path.is_file():
                rel_path = file_path.relative_to(module_path)
                if str(rel_path) not in [c.value for c in ComponentType]:
                    analysis.additional_files.append(str(rel_path))

        # Determine completeness level
        analysis.completeness_level = self._determine_completeness(analysis)

        # Set priority based on completeness and module importance
        analysis.priority = self._determine_priority(analysis)

        # Add analysis notes
        self._add_analysis_notes(analysis)

        return analysis

    def _determine_completeness(self, analysis: ModuleAnalysis) -> CompletenessLevel:
        """Determine the completeness level of a module."""
        existing = analysis.existing_components

        if not existing or existing == {ComponentType.INIT}:
            return CompletenessLevel.EMPTY

        if self.REQUIRED_FULL.issubset(existing):
            return CompletenessLevel.COMPLETE

        if self.REQUIRED_CORE.issubset(existing):
            return CompletenessLevel.FUNCTIONAL

        core_count = len(existing.intersection(self.REQUIRED_CORE))
        if core_count >= 2:
            return CompletenessLevel.PARTIAL

        return CompletenessLevel.MINIMAL

    def _determine_priority(self, analysis: ModuleAnalysis) -> str:
        """Determine completion priority for a module."""
        # Critical modules that should be complete
        critical_modules = {
            "billing",
            "identity",
            "authentication",
            "auth",
            "tenants",
            "monitoring",
            "analytics",
        }

        # High priority modules
        high_priority_modules = {
            "services",
            "notifications",
            "network_monitoring",
            "support",
            "compliance",
            "licensing",
        }

        module_name = analysis.name.lower()

        if any(critical in module_name for critical in critical_modules):
            if analysis.completeness_level in [
                CompletenessLevel.EMPTY,
                CompletenessLevel.MINIMAL,
            ]:
                return "critical"
            elif analysis.completeness_level == CompletenessLevel.PARTIAL:
                return "high"
            else:
                return "medium"

        if any(high_pri in module_name for high_pri in high_priority_modules):
            if analysis.completeness_level in [
                CompletenessLevel.EMPTY,
                CompletenessLevel.MINIMAL,
            ]:
                return "high"
            else:
                return "medium"

        # Default priority based on completeness
        if analysis.completeness_level == CompletenessLevel.EMPTY:
            return "medium"
        elif analysis.completeness_level == CompletenessLevel.MINIMAL:
            return "low"
        else:
            return "low"

    def _add_analysis_notes(self, analysis: ModuleAnalysis):
        """Add analysis notes for a module."""
        if ComponentType.ROUTER not in analysis.existing_components:
            analysis.notes.append("Missing router.py - no API endpoints")

        if ComponentType.SERVICE not in analysis.existing_components:
            analysis.notes.append("Missing service.py - no business logic layer")

        if ComponentType.MODELS not in analysis.existing_components:
            analysis.notes.append("Missing models.py - no database models")

        if ComponentType.SCHEMAS not in analysis.existing_components:
            analysis.notes.append("Missing schemas.py - no request/response validation")

        if ComponentType.REPOSITORY not in analysis.existing_components:
            analysis.notes.append("Missing repository.py - no data access layer")

        # Check for unusual patterns
        if len(analysis.additional_files) > 10:
            analysis.notes.append(
                f"Large module with {len(analysis.additional_files)} additional files"
            )

        if "services" in [f.lower() for f in analysis.additional_files]:
            analysis.notes.append(
                "Has services subdirectory - may use different organization pattern"
            )

    def categorize_modules(self) -> dict[CompletenessLevel, list[ModuleAnalysis]]:
        """Categorize modules by completeness level."""
        categories = {level: [] for level in CompletenessLevel}
        for module in self.modules:
            categories[module.completeness_level].append(module)
        return categories

    def generate_report(self) -> str:
        """Generate a comprehensive audit report."""
        categories = self.categorize_modules()

        report = []
        report.append("# Module Audit Report - Phase 1")
        report.append("=" * 50)
        report.append("")

        # Summary statistics
        report.append("## Summary Statistics")
        report.append(f"- Total modules found: {len(self.modules)}")
        report.append(
            f"- ISP Framework modules: {len([m for m in self.modules if m.platform == 'isp'])}"
        )
        report.append(
            f"- Management Platform modules: {len([m for m in self.modules if m.platform == 'management'])}"
        )
        report.append("")

        # Completeness breakdown
        report.append("## Completeness Breakdown")
        for level, modules in categories.items():
            if modules:
                report.append(f"- {level.value.title()}: {len(modules)} modules")
        report.append("")

        # Priority breakdown
        priority_counts = {}
        for module in self.modules:
            priority_counts[module.priority] = (
                priority_counts.get(module.priority, 0) + 1
            )

        report.append("## Priority Breakdown")
        for priority in ["critical", "high", "medium", "low"]:
            count = priority_counts.get(priority, 0)
            if count > 0:
                report.append(f"- {priority.title()}: {count} modules")
        report.append("")

        # Detailed analysis by completeness level
        for level, modules in categories.items():
            if modules:
                report.append(f"## {level.value.title()} Modules ({len(modules)})")
                report.append("")

                for module in sorted(modules, key=lambda m: (m.priority, m.name)):
                    report.append(f"### {module.name} ({module.platform})")
                    report.append(f"**Path:** `{module.path}`")
                    report.append(f"**Priority:** {module.priority}")

                    if module.existing_components:
                        components = ", ".join(
                            [
                                c.value
                                for c in sorted(
                                    module.existing_components, key=lambda x: x.value
                                )
                            ]
                        )
                        report.append(f"**Has:** {components}")

                    if module.missing_components:
                        missing = ", ".join(
                            [
                                c.value
                                for c in sorted(
                                    module.missing_components, key=lambda x: x.value
                                )
                                if c != ComponentType.INIT
                            ]
                        )
                        if missing:
                            report.append(f"**Missing:** {missing}")

                    if module.notes:
                        report.append("**Notes:**")
                        for note in module.notes:
                            report.append(f"- {note}")

                    report.append("")

        # Action recommendations
        report.append("## Action Recommendations")
        report.append("")

        critical_modules = [m for m in self.modules if m.priority == "critical"]
        if critical_modules:
            report.append("### 🚨 Critical Actions Required")
            for module in critical_modules:
                report.append(f"- **{module.name}**: Complete missing core components")

        high_priority = [m for m in self.modules if m.priority == "high"]
        if high_priority:
            report.append("### ⚡ High Priority")
            for module in high_priority[:5]:  # Top 5
                missing_core = [
                    c.value
                    for c in self.REQUIRED_CORE
                    if c in module.missing_components
                ]
                if missing_core:
                    report.append(f"- **{module.name}**: Add {', '.join(missing_core)}")

        report.append("")
        report.append("### 📊 Next Steps")
        report.append("1. **Phase 2**: Implement scaffolding framework")
        report.append("2. **Phase 3**: Complete critical and high-priority modules")
        report.append("3. **Phase 4**: Standardize existing modules")
        report.append("4. **Phase 5**: Add comprehensive testing")

        return "\n".join(report)

    def save_json_report(self, output_path: Path):
        """Save detailed analysis as JSON."""
        data = {
            "summary": {
                "total_modules": len(self.modules),
                "isp_modules": len([m for m in self.modules if m.platform == "isp"]),
                "management_modules": len(
                    [m for m in self.modules if m.platform == "management"]
                ),
                "completeness_breakdown": {
                    level.value: len(
                        [m for m in self.modules if m.completeness_level == level]
                    )
                    for level in CompletenessLevel
                },
                "priority_breakdown": {
                    priority: len([m for m in self.modules if m.priority == priority])
                    for priority in ["critical", "high", "medium", "low"]
                },
            },
            "modules": [
                {
                    "name": m.name,
                    "path": m.path,
                    "platform": m.platform,
                    "existing_components": [c.value for c in m.existing_components],
                    "missing_components": [c.value for c in m.missing_components],
                    "additional_files": m.additional_files,
                    "completeness_level": m.completeness_level.value,
                    "priority": m.priority,
                    "notes": m.notes,
                }
                for m in self.modules
            ],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)


def main():
    """Run the module audit."""
    print("🚀 Starting Module Audit - Phase 1")
    print("=" * 50)

    auditor = ModuleAuditor()

    # Phase 1.1: Scan all modules
    print("\n📋 Phase 1.1: Scanning all existing modules")
    modules = auditor.scan_modules()

    # Phase 1.2: Categorize modules
    print("\n📊 Phase 1.2: Categorizing modules by completeness")
    categories = auditor.categorize_modules()

    # Phase 1.3: Generate reports
    print("\n📄 Phase 1.3: Generating audit report")
    report = auditor.generate_report()

    # Save reports
    output_dir = Path(__file__).parent.parent / "reports"  # noqa: B008
    output_dir.mkdir(exist_ok=True)

    # Text report
    report_path = output_dir / "module_audit_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    # JSON report
    json_path = output_dir / "module_audit_data.json"
    auditor.save_json_report(json_path)

    print("\n✅ Audit complete!")
    print(f"📄 Report saved to: {report_path}")
    print(f"📊 JSON data saved to: {json_path}")

    # Print summary
    print("\n📈 Quick Summary:")
    print(f"- Total modules: {len(modules)}")
    print(f"- Complete: {len(categories[CompletenessLevel.COMPLETE])}")
    print(f"- Functional: {len(categories[CompletenessLevel.FUNCTIONAL])}")
    print(f"- Partial: {len(categories[CompletenessLevel.PARTIAL])}")
    print(f"- Minimal: {len(categories[CompletenessLevel.MINIMAL])}")
    print(f"- Empty: {len(categories[CompletenessLevel.EMPTY])}")

    critical_count = len([m for m in modules if m.priority == "critical"])
    if critical_count > 0:
        print(f"\n🚨 {critical_count} critical modules need immediate attention!")


if __name__ == "__main__":
    main()
