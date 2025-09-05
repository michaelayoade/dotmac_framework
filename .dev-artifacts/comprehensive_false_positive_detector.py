#!/usr/bin/env python3
"""
Comprehensive false positive detector for ruff violations
Combines multiple analysis techniques to determine legitimacy
"""
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM" 
    LOW = "LOW"


@dataclass
class ViolationAnalysis:
    code: str
    filename: str
    line_num: int
    message: str
    is_false_positive: bool
    confidence: Confidence
    reasons: List[str]
    recommendation: str


class FalsePositiveDetector:
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict:
        """Load known false positive patterns"""
        return {
            'file_patterns': {
                'adapters': ['adapter', 'integration', 'bridge'],
                'handlers': ['handler', 'middleware', 'processor'],
                'templates': ['template', 'formatter', 'generator'],
                'configs': ['config', 'settings', 'serve'],
                'tests': ['test', 'mock', 'fixture', 'factory'],
                'examples': ['example', 'demo', 'sample'],
                'migrations': ['migration', 'alembic'],
                'init_files': ['__init__.py']
            },
            'code_patterns': {
                'F401': {
                    'false_positive_indicators': [
                        r'TYPE_CHECKING',
                        r'__all__',
                        r'importlib\.util\.find_spec',
                        r'imported but unused; consider using.*find_spec',
                        # Dynamic usage patterns
                        r'getattr\(',
                        r'hasattr\(',
                        r'setattr\(',
                        r'globals\(\)',
                        r'locals\(\)',
                        # String-based usage
                        r'["\'].*\{.*\}.*["\']',  # f-strings
                        r'\.format\(',
                        # Type annotation usage
                        r':\s*\w+',
                        r'->\s*\w+',
                    ]
                },
                'BLE001': {
                    'false_positive_indicators': [
                        r'plugin',
                        r'adapter',
                        r'external',
                        r'third_party', 
                        r'fallback',
                        r'graceful',
                        r'cleanup',
                        r'finally',
                        r'observability',
                        r'benchmark',
                        r'integration',
                        r'migration',
                    ]
                },
                'E501': {
                    'false_positive_indicators': [
                        r'https?://',  # URLs
                        r'SELECT|INSERT|UPDATE|DELETE|CREATE',  # SQL
                        r'f["\'].*\{.*\}.*["\']',  # f-strings
                        r'logger\.|log\.',  # Logging
                        r'#.*',  # Comments
                        r'["\'][^"\']*["\']',  # String literals
                        r'raise \w+\(',  # Exception messages
                        r'return ["\']',  # Return strings
                    ]
                },
                'ANN': {
                    'false_positive_indicators': [
                        r'\*args',
                        r'\*\*kwargs', 
                        r'\*\*config',
                        r'app:',  # Framework objects
                        r'request:',
                        r'response:',
                        # Framework patterns
                        r'middleware',
                        r'handler',
                        r'factory',
                        r'serve',
                    ]
                }
            }
        }
    
    def analyze_file_context(self, filename: str) -> Tuple[bool, str]:
        """Analyze file context for false positive patterns"""
        path = Path(filename)
        
        for category, patterns in self.patterns['file_patterns'].items():
            if any(pattern in filename.lower() for pattern in patterns):
                return True, f"File type: {category}"
        
        # Check directory structure
        if any(part in ['tests', 'examples', 'migrations', 'scripts'] 
               for part in path.parts):
            return True, "Directory context"
        
        return False, ""
    
    def analyze_code_content(self, filename: str, line_num: int, code: str, message: str) -> Tuple[bool, List[str]]:
        """Analyze code content for false positive patterns"""
        reasons = []
        
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                
            # Get context around the violation
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 3)
            context = '\n'.join(lines[start:end])
            
            # Get the specific line
            if line_num <= len(lines):
                target_line = lines[line_num - 1]
            else:
                return False, []
                
            # Check patterns for this violation type
            code_prefix = code[:3] if len(code) > 3 else code
            if code_prefix in self.patterns['code_patterns']:
                indicators = self.patterns['code_patterns'][code_prefix]['false_positive_indicators']
                
                for pattern in indicators:
                    if re.search(pattern, context, re.IGNORECASE):
                        reasons.append(f"Pattern match: {pattern}")
                    if re.search(pattern, message, re.IGNORECASE):
                        reasons.append(f"Message pattern: {pattern}")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            return False, [f"Analysis error: {e}"]
    
    def analyze_structural_context(self, filename: str) -> Tuple[bool, str]:
        """Analyze structural/architectural context"""
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Check for architectural patterns
            if any(pattern in content for pattern in [
                'class.*Adapter',
                'class.*Handler', 
                'class.*Middleware',
                'class.*Factory',
                '@abstractmethod',
                'TYPE_CHECKING',
                'Protocol',
                '__all__'
            ]):
                return True, "Architectural pattern"
            
            # Check import density (high imports often indicate interface files)
            lines = content.split('\n')
            import_lines = len([line for line in lines if line.strip().startswith(('import ', 'from '))])
            total_lines = len([line for line in lines if line.strip()])
            
            if total_lines > 0 and import_lines / total_lines > 0.3:
                return True, "High import density (interface file)"
                
        except Exception:
            pass
        
        return False, ""
    
    def calculate_confidence(self, reasons: List[str]) -> Confidence:
        """Calculate confidence level based on analysis"""
        reason_count = len(reasons)
        
        # High confidence indicators
        high_confidence_patterns = [
            'TYPE_CHECKING', '__all__', 'Pattern match: https?://',
            'File type:', 'Architectural pattern'
        ]
        
        if any(pattern in reason for reason in reasons for pattern in high_confidence_patterns):
            return Confidence.HIGH
        elif reason_count >= 2:
            return Confidence.HIGH  
        elif reason_count == 1:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
    
    def generate_recommendation(self, analysis: ViolationAnalysis) -> str:
        """Generate recommendation based on analysis"""
        if analysis.is_false_positive:
            if analysis.confidence == Confidence.HIGH:
                return f"IGNORE: Add to ruff per-file-ignores for {analysis.code}"
            elif analysis.confidence == Confidence.MEDIUM:
                return f"REVIEW: Likely false positive, consider ignoring {analysis.code}"
            else:
                return f"INVESTIGATE: Might be false positive for {analysis.code}"
        else:
            return f"FIX: Legitimate {analysis.code} violation should be addressed"
    
    def analyze_violation(self, violation: Dict) -> ViolationAnalysis:
        """Perform comprehensive analysis of a single violation"""
        filename = violation['filename']
        line_num = violation.get('location', {}).get('row', 0)
        code = violation.get('code', '')
        message = violation.get('message', '')
        
        all_reasons = []
        
        # File context analysis
        file_fp, file_reason = self.analyze_file_context(filename)
        if file_fp:
            all_reasons.append(file_reason)
        
        # Code content analysis
        code_fp, code_reasons = self.analyze_code_content(filename, line_num, code, message)
        all_reasons.extend(code_reasons)
        
        # Structural analysis
        struct_fp, struct_reason = self.analyze_structural_context(filename)
        if struct_fp:
            all_reasons.append(struct_reason)
        
        # Determine if it's a false positive
        is_false_positive = len(all_reasons) > 0
        confidence = self.calculate_confidence(all_reasons)
        
        analysis = ViolationAnalysis(
            code=code,
            filename=filename,
            line_num=line_num,
            message=message,
            is_false_positive=is_false_positive,
            confidence=confidence,
            reasons=all_reasons,
            recommendation=""
        )
        
        analysis.recommendation = self.generate_recommendation(analysis)
        return analysis


def main():
    """Run comprehensive false positive detection"""
    try:
        result = subprocess.run(
            ["./.venv/bin/ruff", "check", "--output-format=json"],
            capture_output=True, text=True, cwd="/home/dotmac_framework"
        )
        violations = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception as e:
        print(f"❌ Could not get violations: {e}")
        return
    
    detector = FalsePositiveDetector()
    
    print(f"🔍 Comprehensive analysis of {len(violations)} violations...\n")
    
    # Analyze all violations
    analyses = []
    for violation in violations[:100]:  # Limit for performance
        analysis = detector.analyze_violation(violation)
        analyses.append(analysis)
    
    # Categorize results
    false_positives = [a for a in analyses if a.is_false_positive]
    real_issues = [a for a in analyses if not a.is_false_positive]
    
    # Group by confidence
    high_confidence_fp = [a for a in false_positives if a.confidence == Confidence.HIGH]
    medium_confidence_fp = [a for a in false_positives if a.confidence == Confidence.MEDIUM]
    
    # Report summary
    print("="*60)
    print("🎯 COMPREHENSIVE ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total analyzed: {len(analyses)}")
    print(f"False positives: {len(false_positives)} ({len(false_positives)/len(analyses)*100:.1f}%)")
    print(f"Real issues: {len(real_issues)} ({len(real_issues)/len(analyses)*100:.1f}%)")
    print()
    print("False Positive Confidence:")
    print(f"  High confidence: {len(high_confidence_fp)}")
    print(f"  Medium confidence: {len(medium_confidence_fp)}")
    print()
    
    # Show top false positives by confidence
    print("🔍 HIGH CONFIDENCE FALSE POSITIVES:")
    for analysis in high_confidence_fp[:5]:
        file_short = Path(analysis.filename).name
        print(f"   {analysis.code}: {file_short}:{analysis.line_num}")
        print(f"     Reasons: {', '.join(analysis.reasons[:2])}")
        print(f"     {analysis.recommendation}")
        print()
    
    print("⚠️  REAL ISSUES TO ADDRESS:")
    for analysis in real_issues[:5]:
        file_short = Path(analysis.filename).name
        print(f"   {analysis.code}: {file_short}:{analysis.line_num}")
        print(f"     {analysis.message[:80]}...")
        print(f"     {analysis.recommendation}")
        print()


if __name__ == "__main__":
    main()