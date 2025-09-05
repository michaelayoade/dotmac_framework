#!/usr/bin/env python3
"""
Advanced contextual analysis for ruff violations
"""
import ast
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set


def analyze_import_context(filename: str, line_num: int, import_name: str) -> Dict:
    """Deep analysis of import usage context"""
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            content = ''.join(lines)
        
        # Check if it's used in type annotations only
        type_usage = bool(re.search(rf'\b{import_name}\b.*:', content))
        
        # Check if it's used in docstrings/comments
        doc_usage = bool(re.search(rf'{import_name}', ' '.join(
            line.strip() for line in lines 
            if line.strip().startswith(('"""', "'''", '#'))
        )))
        
        # Check if it's used in dynamic/string contexts
        dynamic_usage = bool(re.search(rf'["\'].*{import_name}.*["\']', content))
        
        # Check if file is an __init__.py (likely re-export)
        is_init = filename.endswith('__init__.py')
        
        # Check if it's used in TYPE_CHECKING block
        type_checking = 'TYPE_CHECKING' in content and import_name in content
        
        return {
            'type_usage': type_usage,
            'doc_usage': doc_usage, 
            'dynamic_usage': dynamic_usage,
            'is_init': is_init,
            'type_checking': type_checking,
            'likely_false_positive': any([type_usage, doc_usage, dynamic_usage, is_init, type_checking])
        }
    except:
        return {'likely_false_positive': False}


def analyze_exception_context(filename: str, line_num: int) -> Dict:
    """Analyze context of broad exception handling"""
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        # Get surrounding context
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 5)
        context = ''.join(lines[start:end])
        
        # Check for legitimate broad exception patterns
        patterns = {
            'cleanup': bool(re.search(r'(finally|cleanup|close|disconnect)', context, re.IGNORECASE)),
            'fallback': bool(re.search(r'(fallback|default|graceful)', context, re.IGNORECASE)),
            'logging': bool(re.search(r'(log|logger|print)', context, re.IGNORECASE)),
            'external_api': bool(re.search(r'(request|http|api|client)', context, re.IGNORECASE)),
            'plugin_system': bool(re.search(r'(plugin|module|import|load)', context, re.IGNORECASE)),
            'initialization': bool(re.search(r'(init|setup|configure|start)', context, re.IGNORECASE))
        }
        
        return {
            'patterns': patterns,
            'likely_false_positive': any(patterns.values())
        }
    except:
        return {'likely_false_positive': False}


def analyze_line_complexity(filename: str, line_num: int) -> Dict:
    """Analyze if long line is complex or just data"""
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            
        if line_num > len(lines):
            return {'likely_false_positive': False}
            
        line = lines[line_num - 1]
        
        # Count different complexity indicators
        complexity_indicators = {
            'string_literal': len(re.findall(r'["\'].*?["\']', line)),
            'function_calls': len(re.findall(r'\w+\s*\(', line)),
            'operators': len(re.findall(r'[+\-*/=<>!&|]', line)),
            'parentheses_depth': max((line[:i].count('(') - line[:i].count(')')) for i in range(len(line))),
            'is_url': bool(re.search(r'https?://', line)),
            'is_sql': bool(re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE)\b', line, re.IGNORECASE)),
            'is_format_string': bool(re.search(r'f["\'].*\{.*\}.*["\']', line)),
            'is_comment': line.strip().startswith('#'),
            'is_import': line.strip().startswith(('import ', 'from ')),
        }
        
        # Simple data structures are usually false positives for length
        is_data_structure = any([
            complexity_indicators['is_url'],
            complexity_indicators['is_sql'], 
            complexity_indicators['is_format_string'],
            complexity_indicators['is_comment'],
            complexity_indicators['string_literal'] > complexity_indicators['function_calls']
        ])
        
        return {
            'complexity': complexity_indicators,
            'likely_false_positive': is_data_structure
        }
    except:
        return {'likely_false_positive': False}


def run_advanced_analysis():
    """Run advanced contextual analysis on violations"""
    try:
        result = subprocess.run(
            ["./.venv/bin/ruff", "check", "--output-format=json"],
            capture_output=True, text=True, cwd="/home/dotmac_framework"
        )
        violations = json.loads(result.stdout) if result.stdout.strip() else []
    except:
        print("❌ Could not get violations")
        return
    
    print(f"🔬 Deep analysis of {len(violations)} violations...\n")
    
    # Analyze by type
    analyses = {
        'F401': [],  # Unused imports
        'BLE001': [],  # Broad exceptions
        'E501': []   # Long lines
    }
    
    for violation in violations:
        code = violation.get('code')
        if code not in analyses:
            continue
            
        filename = violation['filename']
        line_num = violation.get('location', {}).get('row', 0)
        
        if code == 'F401':
            import_match = re.search(r'`([^`]+)` imported but unused', violation['message'])
            if import_match:
                import_name = import_match.group(1).split('.')[-1]
                analysis = analyze_import_context(filename, line_num, import_name)
                analyses[code].append({
                    'file': filename,
                    'line': line_num,
                    'analysis': analysis,
                    'message': violation['message']
                })
                
        elif code == 'BLE001':
            analysis = analyze_exception_context(filename, line_num)
            analyses[code].append({
                'file': filename,
                'line': line_num, 
                'analysis': analysis
            })
            
        elif code == 'E501':
            analysis = analyze_line_complexity(filename, line_num)
            analyses[code].append({
                'file': filename,
                'line': line_num,
                'analysis': analysis
            })
    
    # Report results
    for code, items in analyses.items():
        if not items:
            continue
            
        false_positives = [item for item in items if item['analysis']['likely_false_positive']]
        real_issues = [item for item in items if not item['analysis']['likely_false_positive']]
        
        print(f"🔍 {code} Analysis:")
        print(f"   False positives: {len(false_positives)}")
        print(f"   Real issues: {len(real_issues)}")
        
        if false_positives:
            print(f"   Example false positive: {false_positives[0]['file']}:{false_positives[0]['line']}")
        if real_issues:
            print(f"   Example real issue: {real_issues[0]['file']}:{real_issues[0]['line']}")
        print()


if __name__ == "__main__":
    run_advanced_analysis()