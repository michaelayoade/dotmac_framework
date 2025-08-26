#!/usr/bin/env python3
"""
Async/Sync Pattern Analysis

Analyzes mixed async/sync patterns in the codebase and provides standardization recommendations.
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass

@dataclass
class PatternAnalysis:
    """Analysis result for a file."""
    file_path: str
    async_functions: List[str]
    sync_functions: List[str]
    asyncio_run_calls: List[str]
    mixed_patterns: List[str]
    recommendations: List[str]

class AsyncSyncAnalyzer:
    """Analyzes async/sync patterns in Python code."""
    
    def __init__(self):
        self.results: Dict[str, PatternAnalysis] = {}
        
    def analyze_file(self, file_path: str) -> PatternAnalysis:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            async_functions = []
            sync_functions = []
            asyncio_run_calls = []
            mixed_patterns = []
            recommendations = []
            
            # Analyze function definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    async_functions.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    sync_functions.append(node.name)
                    
                    # Check if sync function contains asyncio.run calls
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if self._is_asyncio_run(child):
                                call_str = f"{node.name}() contains asyncio.run()"
                                asyncio_run_calls.append(call_str)
                                mixed_patterns.append(f"Sync function '{node.name}' calls async code via asyncio.run()")
            
            # Generate recommendations
            if mixed_patterns:
                recommendations.append("Consider standardizing on async/await pattern throughout")
                if "Celery" in content or "celery" in content.lower():
                    recommendations.append("Celery tasks using asyncio.run() are acceptable for gradual migration")
                else:
                    recommendations.append("Convert to full async pattern or use sync-only approach")
            
            return PatternAnalysis(
                file_path=file_path,
                async_functions=async_functions,
                sync_functions=sync_functions,
                asyncio_run_calls=asyncio_run_calls,
                mixed_patterns=mixed_patterns,
                recommendations=recommendations
            )
            
        except Exception as e:
            return PatternAnalysis(
                file_path=file_path,
                async_functions=[],
                sync_functions=[],
                asyncio_run_calls=[],
                mixed_patterns=[f"Analysis error: {e}"],
                recommendations=["Fix syntax errors before analyzing patterns"]
            )
    
    def _is_asyncio_run(self, node: ast.Call) -> bool:
        """Check if a call is asyncio.run()."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'asyncio':
                return node.func.attr == 'run'
        return False
    
    def analyze_directory(self, directory: str, patterns: List[str] = None) -> Dict[str, PatternAnalysis]:
        """Analyze all Python files in a directory."""
        if patterns is None:
            patterns = ["**/*.py"]
            
        results = {}
        
        for pattern in patterns:
            for file_path in Path(directory).rglob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    file_str = str(file_path)
                    analysis = self.analyze_file(file_str)
                    results[file_str] = analysis
                    
        return results
    
    def generate_report(self, results: Dict[str, PatternAnalysis]) -> str:
        """Generate a comprehensive analysis report."""
        report = []
        report.append("# Async/Sync Pattern Analysis Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary statistics
        total_files = len(results)
        files_with_mixed_patterns = sum(1 for r in results.values() if r.mixed_patterns)
        total_async_functions = sum(len(r.async_functions) for r in results.values())
        total_sync_functions = sum(len(r.sync_functions) for r in results.values())
        total_asyncio_run_calls = sum(len(r.asyncio_run_calls) for r in results.values())
        
        report.append(f"## Summary Statistics")
        report.append(f"- Total files analyzed: {total_files}")
        report.append(f"- Files with mixed patterns: {files_with_mixed_patterns}")
        report.append(f"- Total async functions: {total_async_functions}")
        report.append(f"- Total sync functions: {total_sync_functions}")
        report.append(f"- Total asyncio.run() calls: {total_asyncio_run_calls}")
        report.append("")
        
        # Pattern categories
        celery_files = []
        service_files = []
        other_mixed_files = []
        
        for file_path, analysis in results.items():
            if analysis.mixed_patterns:
                content = ""
                try:
                    with open(file_path, 'r') as f:
                        content = f.read().lower()
                except:
                    pass
                    
                if "celery" in content:
                    celery_files.append((file_path, analysis))
                elif "service" in file_path.lower():
                    service_files.append((file_path, analysis))
                else:
                    other_mixed_files.append((file_path, analysis))
        
        # Celery task patterns (acceptable)
        if celery_files:
            report.append("## Celery Task Patterns (Acceptable for Migration)")
            report.append("These files use sync Celery task definitions with asyncio.run() - acceptable pattern.")
            report.append("")
            for file_path, analysis in celery_files:
                report.append(f"### {file_path}")
                for pattern in analysis.mixed_patterns:
                    report.append(f"- {pattern}")
                report.append("")
        
        # Service layer patterns
        if service_files:
            report.append("## Service Layer Patterns")
            report.append("Service files with mixed async/sync patterns:")
            report.append("")
            for file_path, analysis in service_files:
                report.append(f"### {file_path}")
                for pattern in analysis.mixed_patterns:
                    report.append(f"- {pattern}")
                for rec in analysis.recommendations:
                    report.append(f"  → Recommendation: {rec}")
                report.append("")
        
        # Other mixed patterns
        if other_mixed_files:
            report.append("## Other Mixed Patterns")
            report.append("Files with mixed patterns that may need attention:")
            report.append("")
            for file_path, analysis in other_mixed_files:
                report.append(f"### {file_path}")
                for pattern in analysis.mixed_patterns:
                    report.append(f"- {pattern}")
                for rec in analysis.recommendations:
                    report.append(f"  → Recommendation: {rec}")
                report.append("")
        
        # Overall recommendations
        report.append("## Overall Recommendations")
        report.append("")
        report.append("1. **Celery Tasks**: Current pattern (sync def + asyncio.run) is acceptable for gradual migration")
        report.append("2. **Service Layer**: Standardize on async/await throughout for consistency")
        report.append("3. **New Code**: Use consistent async/await pattern for all new code")
        report.append("4. **Migration Strategy**: Migrate sync code to async gradually, module by module")
        report.append("5. **Testing**: Ensure proper async test patterns are used")
        report.append("")
        
        return "\n".join(report)

def main():
    """Main analysis function."""
    print("🔍 Analyzing async/sync patterns...")
    
    analyzer = AsyncSyncAnalyzer()
    
    # Analyze key directories
    directories = [
        "isp-framework/src/dotmac_isp",
        "management-platform/app",
    ]
    
    all_results = {}
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"📁 Analyzing {directory}...")
            results = analyzer.analyze_directory(directory)
            all_results.update(results)
        else:
            print(f"⚠️  Directory not found: {directory}")
    
    # Generate report
    report = analyzer.generate_report(all_results)
    
    # Save report
    with open("async_pattern_analysis.md", "w") as f:
        f.write(report)
    
    print(f"📊 Analysis complete! Report saved to async_pattern_analysis.md")
    print(f"📈 Analyzed {len(all_results)} files")
    
    # Print summary
    files_with_mixed = sum(1 for r in all_results.values() if r.mixed_patterns)
    print(f"📋 Files with mixed patterns: {files_with_mixed}")
    
    return len(all_results)

if __name__ == "__main__":
    main()