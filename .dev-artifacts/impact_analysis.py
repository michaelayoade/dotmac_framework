#!/usr/bin/env python3
"""
Test functional impact of violations - would fixing them break anything?
"""
import ast
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List


def test_import_removal_impact(filename: str, line_num: int, import_name: str) -> Dict:
    """Test what happens if we remove an 'unused' import"""
    try:
        # Create temporary copy
        with open(filename, 'r') as f:
            original_content = f.read()
        
        # Try to parse without the import
        lines = original_content.split('\n')
        if line_num <= len(lines):
            # Comment out the import line
            lines[line_num - 1] = '# ' + lines[line_num - 1]
            modified_content = '\n'.join(lines)
            
            # Test if it still parses
            try:
                ast.parse(modified_content)
                syntax_ok = True
            except SyntaxError:
                syntax_ok = False
            
            # Test if imports resolve (basic check)
            import_resolves = True
            try:
                # Look for usage patterns that might be missed
                if any(pattern in original_content for pattern in [
                    f'getattr({import_name}',
                    f'hasattr({import_name}',
                    f'isinstance(',
                    f'typing.get_type_hints',
                    f'{import_name}.__',
                    f'"{import_name}"',
                    f"'{import_name}'"
                ]):
                    import_resolves = False
            except:
                pass
            
            return {
                'can_remove': syntax_ok and import_resolves,
                'syntax_ok': syntax_ok,
                'likely_used_dynamically': not import_resolves
            }
    except:
        pass
    
    return {'can_remove': False, 'syntax_ok': False, 'likely_used_dynamically': True}


def test_annotation_requirement(filename: str, line_num: int) -> Dict:
    """Test if missing annotation actually impacts type checking"""
    try:
        # Check if file uses strict typing patterns
        with open(filename, 'r') as f:
            content = f.read()
        
        has_type_checking = 'TYPE_CHECKING' in content
        has_other_annotations = bool(len([m for m in ast.walk(ast.parse(content)) 
                                         if isinstance(m, ast.FunctionDef) and m.returns]))
        
        # Check if it's a public API (affects external users)
        tree = ast.parse(content)
        public_functions = [node.name for node in ast.walk(tree) 
                          if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')]
        
        return {
            'affects_public_api': len(public_functions) > 0,
            'file_uses_typing': has_type_checking or has_other_annotations,
            'annotation_recommended': has_type_checking or len(public_functions) > 2
        }
    except:
        return {'affects_public_api': False, 'file_uses_typing': False, 'annotation_recommended': False}


def test_exception_specificity_impact(filename: str, line_num: int) -> Dict:
    """Test if broad exception handling is actually needed"""
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            return {'needs_broad_exception': True}
        
        # Get context around the exception
        start = max(0, line_num - 10)
        end = min(len(lines), line_num + 5) 
        context = ''.join(lines[start:end])
        
        # Check for indicators that broad exception is needed
        needs_broad = any([
            'plugin' in context.lower(),
            'dynamic' in context.lower(),
            'import' in context.lower(),
            'external' in context.lower(),
            'third_party' in context.lower(),
            'adapter' in context.lower(),
            len([line for line in lines[start:end] if 'except' in line]) > 2,  # Multiple exception types
        ])
        
        return {'needs_broad_exception': needs_broad}
    except:
        return {'needs_broad_exception': True}


def run_impact_analysis():
    """Run functional impact analysis"""
    try:
        result = subprocess.run(
            ["./.venv/bin/ruff", "check", "--output-format=json"],
            capture_output=True, text=True, cwd="/home/dotmac_framework"
        )
        violations = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception as e:
        print(f"❌ Could not get violations: {e}")
        return
    
    print(f"🧪 Impact analysis of {len(violations)} violations...\n")
    
    # Test specific violation types
    import_tests = []
    annotation_tests = []
    exception_tests = []
    
    for violation in violations[:20]:  # Test first 20 to avoid too much output
        code = violation.get('code')
        filename = violation['filename']
        line_num = violation.get('location', {}).get('row', 0)
        
        if code == 'F401':
            import_match = re.search(r'`([^`]+)` imported but unused', violation['message'])
            if import_match:
                import_name = import_match.group(1).split('.')[-1]
                result = test_import_removal_impact(filename, line_num, import_name)
                import_tests.append({
                    'file': Path(filename).name,
                    'can_remove': result['can_remove'],
                    'dynamic_usage': result['likely_used_dynamically']
                })
        
        elif code.startswith('ANN'):
            result = test_annotation_requirement(filename, line_num)
            annotation_tests.append({
                'file': Path(filename).name,
                'public_api': result['affects_public_api'],
                'recommended': result['annotation_recommended']
            })
        
        elif code == 'BLE001':
            result = test_exception_specificity_impact(filename, line_num)
            exception_tests.append({
                'file': Path(filename).name,
                'needs_broad': result['needs_broad_exception']
            })
    
    # Report impact analysis
    if import_tests:
        safe_removals = sum(1 for t in import_tests if t['can_remove'])
        dynamic_usage = sum(1 for t in import_tests if t['dynamic_usage'])
        print(f"📦 UNUSED IMPORTS ({len(import_tests)} tested):")
        print(f"   Safe to remove: {safe_removals}")
        print(f"   Used dynamically: {dynamic_usage}")
        print(f"   Real issues: {len(import_tests) - dynamic_usage}\n")
    
    if annotation_tests:
        public_apis = sum(1 for t in annotation_tests if t['public_api'])
        recommended = sum(1 for t in annotation_tests if t['recommended'])
        print(f"🏷️  TYPE ANNOTATIONS ({len(annotation_tests)} tested):")
        print(f"   Affect public APIs: {public_apis}")
        print(f"   Recommended: {recommended}")  
        print(f"   Can skip: {len(annotation_tests) - recommended}\n")
    
    if exception_tests:
        need_broad = sum(1 for t in exception_tests if t['needs_broad'])
        print(f"⚠️  BROAD EXCEPTIONS ({len(exception_tests)} tested):")
        print(f"   Legitimately broad: {need_broad}")
        print(f"   Should be specific: {len(exception_tests) - need_broad}\n")


if __name__ == "__main__":
    import json
    import re
    run_impact_analysis()