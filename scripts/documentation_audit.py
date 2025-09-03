#!/usr/bin/env python3
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

Documentation Audit Tool for DotMac Framework
Validates code-documentation alignment and implements DRY principles
"""

import ast
import importlib.util
import inspect
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class APIEndpoint:
    """API endpoint information"""

    method: str
    path: str
    function_name: str
    docstring: Optional[str]
    parameters: List[str]
    response_model: Optional[str]
    file_path: str
    line_number: int


@dataclass
class ClassInfo:
    """Python class information"""

    name: str
    docstring: Optional[str]
    methods: List[str]
    properties: List[str]
    file_path: str
    line_number: int
    base_classes: List[str]


@dataclass
class ModuleInfo:
    """Python module information"""

    name: str
    file_path: str
    docstring: Optional[str]
    classes: List[ClassInfo]
    functions: List[str]
    imports: List[str]


@dataclass
class DocumentationGap:
    """Represents a gap between code and documentation"""

    type: str  # 'missing', 'outdated', 'incorrect'
    category: str  # 'class', 'function', 'endpoint', 'module'
    item_name: str
    file_path: str
    description: str
    current_doc: Optional[str]
    expected_doc: Optional[str]


class CodeAnalyzer:
    """Analyzes Python source code for documentation audit"""

    def __init__(self, source_root: str):
        self.source_root = Path(source_root)
        self.modules: Dict[str, ModuleInfo] = {}
        self.api_endpoints: Dict[str, List[APIEndpoint]] = {}
        self.gaps: List[DocumentationGap] = []

    def analyze_file(self, file_path: Path) -> Optional[ModuleInfo]:
        """Analyze a single Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            # Extract module docstring
            module_docstring = ast.get_docstring(tree)

            # Get module name relative to source root
            module_name = (
                str(file_path.relative_to(self.source_root))
                .replace("/", ".")
                .replace(".py", "")
            )

            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(self._analyze_class(node, file_path))
                elif isinstance(node, ast.FunctionDef):
                    if not any(
                        isinstance(parent, ast.ClassDef)
                        for parent in ast.walk(tree)
                        if hasattr(parent, "body")
                        and node in getattr(parent, "body", [])
                    ):
                        functions.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))

            return ModuleInfo(
                name=module_name,
                file_path=str(file_path),
                docstring=module_docstring,
                classes=classes,
                functions=functions,
                imports=imports,
            )

        except Exception as e:
            logging.warning(f"Failed to analyze {file_path}: {e}")
            return None

    def _analyze_class(self, class_node: ast.ClassDef, file_path: Path) -> ClassInfo:
        """Analyze a class definition"""
        methods = []
        properties = []
        base_classes = [ast.unparse(base) for base in class_node.bases]

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue  # Skip private methods
                methods.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                methods.append(f"async {node.name}")

        return ClassInfo(
            name=class_node.name,
            docstring=ast.get_docstring(class_node),
            methods=methods,
            properties=properties,
            file_path=str(file_path),
            line_number=class_node.lineno,
            base_classes=base_classes,
        )

    def analyze_api_routes(self, file_path: Path) -> List[APIEndpoint]:
        """Analyze FastAPI routes in a file"""
        endpoints = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for FastAPI route decorators
                    for decorator in node.decorator_list:
                        if self._is_fastapi_route_decorator(decorator):
                            endpoint = self._extract_endpoint_info(
                                node, decorator, file_path
                            )
                            if endpoint:
                                endpoints.append(endpoint)

        except Exception as e:
            logging.warning(f"Failed to analyze API routes in {file_path}: {e}")

        return endpoints

    def _is_fastapi_route_decorator(self, decorator: ast.AST) -> bool:
        """Check if decorator is a FastAPI route decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in ["get", "post", "put", "delete", "patch"]
        return False

    def _extract_endpoint_info(
        self, func_node: ast.FunctionDef, decorator: ast.Call, file_path: Path
    ) -> Optional[APIEndpoint]:
        """Extract endpoint information from function and decorator"""
        try:
            method = decorator.func.attr.upper()
            path = None

            # Extract path from decorator arguments
            if decorator.args:
                path = ast.literal_eval(decorator.args[0])

            # Extract parameters
            parameters = [arg.arg for arg in func_node.args.args if arg.arg != "self"]

            # Extract response model from type hints
            response_model = None
            if func_node.returns:
                response_model = ast.unparse(func_node.returns)

            return APIEndpoint(
                method=method,
                path=path or f"/{func_node.name}",
                function_name=func_node.name,
                docstring=ast.get_docstring(func_node),
                parameters=parameters,
                response_model=response_model,
                file_path=str(file_path),
                line_number=func_node.lineno,
            )
        except Exception as e:
            logging.warning(f"Failed to extract endpoint info: {e}")
            return None

    def analyze_all(self) -> None:
        """Analyze all Python files in source directory"""
        python_files = list(self.source_root.rglob("*.py"))

        for file_path in python_files:
            # Skip test files and __pycache__
            if "__pycache__" in str(file_path) or "/tests/" in str(file_path):
                continue

            # Analyze module
            module_info = self.analyze_file(file_path)
            if module_info:
                self.modules[module_info.name] = module_info

            # Analyze API routes
            if any(
                keyword in str(file_path) for keyword in ["router", "api", "endpoints"]
            ):
                endpoints = self.analyze_api_routes(file_path)
                if endpoints:
                    self.api_endpoints[str(file_path)] = endpoints


class DocumentationValidator:
    """Validates existing documentation against code"""

    def __init__(self, project_root: str, code_analyzer: CodeAnalyzer):
        self.project_root = Path(project_root)
        self.code_analyzer = code_analyzer
        self.documentation_files: Dict[str, str] = {}
        self.gaps: List[DocumentationGap] = []

    def scan_documentation(self) -> None:
        """Scan all documentation files"""
        doc_extensions = [".md", ".rst", ".txt"]

        for ext in doc_extensions:
            for doc_file in self.project_root.rglob(f"*{ext}"):
                # Skip node_modules and other irrelevant directories
                if any(
                    skip in str(doc_file)
                    for skip in ["node_modules", "test_env", "__pycache__", ".git"]
                ):
                    continue

                try:
                    with open(doc_file, "r", encoding="utf-8") as f:
                        self.documentation_files[str(doc_file)] = f.read()
                except Exception as e:
                    logging.warning(
                        f"Failed to read documentation file {doc_file}: {e}"
                    )

    def validate_api_documentation(self) -> None:
        """Validate API documentation against actual endpoints"""
        # Find API documentation files
        api_doc_files = [
            f
            for f in self.documentation_files.keys()
            if any(
                keyword in f.lower()
                for keyword in ["api", "endpoint", "swagger", "openapi"]
            )
        ]

        # Get all actual endpoints
        all_endpoints = []
        for endpoints in self.code_analyzer.api_endpoints.values():
            all_endpoints.extend(endpoints)

        # Check for documented endpoints that don't exist
        for doc_file, content in self.documentation_files.items():
            if "api" in doc_file.lower():
                self._validate_api_doc_file(doc_file, content, all_endpoints)

    def _validate_api_doc_file(
        self, doc_file: str, content: str, actual_endpoints: List[APIEndpoint]
    ) -> None:
        """Validate a single API documentation file"""
        # This is a simplified check - in practice, you'd parse the doc format
        actual_paths = {ep.path for ep in actual_endpoints}

        # Look for path-like patterns in documentation
        import re

        documented_paths = set(re.findall(r"/[a-zA-Z0-9_/-]+", content))

        # Find gaps
        for doc_path in documented_paths:
            if doc_path not in actual_paths:
                self.gaps.append(
                    DocumentationGap(
                        type="outdated",
                        category="endpoint",
                        item_name=doc_path,
                        file_path=doc_file,
                        description=f"Documented endpoint {doc_path} not found in code",
                        current_doc=doc_path,
                        expected_doc=None,
                    )
                )

    def validate_class_documentation(self) -> None:
        """Validate class documentation"""
        for module_name, module_info in self.code_analyzer.modules.items():
            for class_info in module_info.classes:
                if not class_info.docstring:
                    self.gaps.append(
                        DocumentationGap(
                            type="missing",
                            category="class",
                            item_name=f"{module_name}.{class_info.name}",
                            file_path=class_info.file_path,
                            description=f"Class {class_info.name} has no docstring",
                            current_doc=None,
                            expected_doc=f"Docstring for {class_info.name} class",
                        )
                    )


class DRYDocumentationGenerator:
    """Generates DRY (Don't Repeat Yourself) documentation"""

    def __init__(self, project_root: str, code_analyzer: CodeAnalyzer):
        self.project_root = Path(project_root)
        self.code_analyzer = code_analyzer

    def generate_api_reference(self) -> str:
        """Generate API reference from code"""
        content = ["# API Reference", ""]
        content.append("Auto-generated from source code analysis")
        content.append("")

        for file_path, endpoints in self.code_analyzer.api_endpoints.items():
            if not endpoints:
                continue

            content.append(f"## {Path(file_path).stem}")
            content.append("")

            for endpoint in endpoints:
                content.append(f"### {endpoint.method} {endpoint.path}")
                content.append("")

                if endpoint.docstring:
                    content.append(endpoint.docstring)
                    content.append("")

                if endpoint.parameters:
                    content.append("**Parameters:**")
                    for param in endpoint.parameters:
                        content.append(f"- `{param}`")
                    content.append("")

                if endpoint.response_model:
                    content.append(f"**Response Model:** `{endpoint.response_model}`")
                    content.append("")

                content.append(f"*Source: {endpoint.file_path}:{endpoint.line_number}*")
                content.append("")

        return "\n".join(content)

    def generate_module_reference(self) -> str:
        """Generate module reference from code"""
        content = ["# Module Reference", ""]
        content.append("Auto-generated from source code analysis")
        content.append("")

        for module_name, module_info in sorted(self.code_analyzer.modules.items()):
            content.append(f"## {module_name}")
            content.append("")

            if module_info.docstring:
                content.append(module_info.docstring)
                content.append("")

            if module_info.classes:
                content.append("### Classes")
                content.append("")
                for class_info in module_info.classes:
                    content.append(f"#### {class_info.name}")
                    if class_info.docstring:
                        content.append(class_info.docstring)
                    content.append("")

                    if class_info.methods:
                        content.append("**Methods:**")
                        for method in class_info.methods:
                            content.append(f"- `{method}()`")
                        content.append("")

            content.append(f"*Source: {module_info.file_path}*")
            content.append("")

        return "\n".join(content)


def main():
    """Main function for documentation audit"""
    logging.basicConfig(level=logging.INFO)
    project_root = "/home/dotmac_framework"
    source_root = f"{project_root}/src"

    print("🔍 Starting Documentation Audit...")

    # Analyze source code
    print("📊 Analyzing source code...")
    code_analyzer = CodeAnalyzer(source_root)
    code_analyzer.analyze_all()

    print(f"✅ Analyzed {len(code_analyzer.modules)} modules")
    print(
        f"✅ Found {sum(len(eps) for eps in code_analyzer.api_endpoints.values())} API endpoints"
    )

    # Validate documentation
    print("📋 Validating documentation...")
    validator = DocumentationValidator(project_root, code_analyzer)
    validator.scan_documentation()
    validator.validate_api_documentation()
    validator.validate_class_documentation()

    print(f"⚠️  Found {len(validator.gaps)} documentation gaps")

    # Generate DRY documentation
    print("📝 Generating DRY documentation...")
    generator = DRYDocumentationGenerator(project_root, code_analyzer)

    # Create reports directory
    reports_dir = Path(project_root) / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Save audit results
    audit_report = {
        "modules_analyzed": len(code_analyzer.modules),
        "api_endpoints_found": sum(
            len(eps) for eps in code_analyzer.api_endpoints.values()
        ),
        "documentation_files": len(validator.documentation_files),
        "gaps_found": len(validator.gaps),
        "gaps": [asdict(gap) for gap in validator.gaps[:50]],  # Limit for readability
        "modules": {
            name: asdict(info)
            for name, info in list(code_analyzer.modules.items())[:20]
        },  # Sample
        "api_endpoints": {
            file: [asdict(ep) for ep in eps]
            for file, eps in list(code_analyzer.api_endpoints.items())[:10]
        },  # Sample
    }

    with open(reports_dir / "documentation_audit_report.json", "w") as f:
        json.dump(audit_report, f, indent=2)

    # Generate markdown report
    with open(reports_dir / "documentation_audit_report.md", "w") as f:
        f.write("# Documentation Audit Report\n\n")
        f.write(
            f"**Generated on:** {subprocess.check_output(['date']).decode().strip()}\n\n"
        )
        f.write("## Summary\n\n")
        f.write(f"- **Modules Analyzed:** {len(code_analyzer.modules)}\n")
        f.write(
            f"- **API Endpoints Found:** {sum(len(eps) for eps in code_analyzer.api_endpoints.values())}\n"
        )
        f.write(f"- **Documentation Files:** {len(validator.documentation_files)}\n")
        f.write(f"- **Gaps Found:** {len(validator.gaps)}\n\n")

        if validator.gaps:
            f.write("## Critical Gaps\n\n")
            for gap in validator.gaps[:20]:  # Top 20 gaps
                f.write(f"### {gap.category.title()}: {gap.item_name}\n")
                f.write(f"**Type:** {gap.type}\n\n")
                f.write(f"**Description:** {gap.description}\n\n")
                f.write(f"**File:** `{gap.file_path}`\n\n")
                if gap.current_doc:
                    f.write(f"**Current:** {gap.current_doc[:100]}...\n\n")
                f.write("---\n\n")

    # Generate auto-documentation
    api_ref = generator.generate_api_reference()
    with open(reports_dir / "auto_generated_api_reference.md", "w") as f:
        f.write(api_ref)

    module_ref = generator.generate_module_reference()
    with open(reports_dir / "auto_generated_module_reference.md", "w") as f:
        f.write(module_ref)

    print("✅ Documentation audit completed!")
    print(f"📊 Reports saved to {reports_dir}/")
    print(f"🔍 Found {len(validator.gaps)} gaps requiring attention")

    # Print top issues
    if validator.gaps:
        print("\n🚨 Top Issues:")
        for i, gap in enumerate(validator.gaps[:5], 1):
            print(f"{i}. {gap.category.title()} '{gap.item_name}' - {gap.type}")


if __name__ == "__main__":
    main()
