#!/usr/bin/env python3
"""
PII Cleanup Validation Script
Ensures no Personal Identifiable Information remains in the codebase

CRITICAL: This script validates that Day 1 security cleanup was successful
"""

import os
import re
import json
from typing import List, Dict, Tuple

class PIIValidator:
    def __init__(self):
        self.violations = []
        self.warnings = []
        
        # Define PII patterns
        self.pii_patterns = {
            'real_names': r'\b(?:John|Jane|Smith|Johnson|Williams|Brown|Davis|Miller|Wilson|Moore|Taylor|Anderson|Thomas|Jackson|White|Harris|Martin|Thompson|Garcia|Martinez|Robinson|Clark|Rodriguez|Lewis|Lee|Walker|Allen|Young|Hernandez|King|Wright|Lopez|Hill|Scott|Green|Adams|Baker|Gonzalez|Nelson|Carter|Mitchell|Perez|Roberts|Turner|Phillips|Campbell|Parker|Evans|Edwards|Collins|Stewart|Sanchez|Morris|Rogers|Reed|Cook|Morgan|Bell|Murphy|Bailey|Rivera|Cooper|Richardson|Cox|Howard|Ward|Torres|Peterson|Gray|Ramirez|James|Watson|Brooks|Kelly|Sanders|Price|Bennett|Wood|Barnes|Ross|Henderson|Coleman|Jenkins|Perry|Powell|Long|Patterson|Hughes|Flores|Washington|Butler|Simmons|Foster|Gonzales|Bryant|Alexander|Russell|Griffin|Diaz|Hayes)\b'
        }
        
        self.real_email_domains = [
            'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'aol.com',
            'icloud.com', 'protonmail.com', 'company.com', 'business.com'
        ]
        
        self.phone_patterns = [
            r'\+?1[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\(?555\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'  # Common test numbers
        ]
    
    def scan_file(self, file_path: str) -> List[Dict]:
        """Scan a single file for PII violations"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Check for real names (excluding safe test patterns)
                    if re.search(self.pii_patterns['real_names'], line) and 'Test' not in line:
                        if not any(safe in line for safe in ['Test User', 'Test Partner', 'Test Customer']):
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'type': 'real_name',
                                'content': line.strip()[:100],
                                'severity': 'CRITICAL'
                            })
                    
                    # Check for real email domains
                    email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
                    for domain in email_matches:
                        if domain in self.real_email_domains or (domain != 'dev.local' and '.' in domain):
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'type': 'real_email',
                                'content': line.strip()[:100],
                                'severity': 'CRITICAL'
                            })
                    
                    # Check for phone numbers (should be [REDACTED])
                    for pattern in self.phone_patterns:
                        if re.search(pattern, line) and '[REDACTED]' not in line:
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'type': 'phone_number',
                                'content': line.strip()[:100],
                                'severity': 'CRITICAL'
                            })
                    
                    # Check for addresses (should be redacted in dev)
                    address_patterns = [
                        r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln|Road|Rd|Way|Place|Pl)\b'
                    ]
                    for pattern in address_patterns:
                        if re.search(pattern, line) and '[REDACTED]' not in line and 'Dev Location' not in line:
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'type': 'address',
                                'content': line.strip()[:100],
                                'severity': 'HIGH'
                            })
        
        except Exception as e:
            self.warnings.append(f"Could not scan {file_path}: {e}")
        
        return violations
    
    def scan_directory(self, directory: str) -> List[Dict]:
        """Scan directory for PII violations"""
        all_violations = []
        
        # File types to scan
        extensions = ['.ts', '.tsx', '.js', '.jsx', '.py', '.json']
        
        for root, dirs, files in os.walk(directory):
            # Skip certain directories
            skip_dirs = ['.git', 'node_modules', '__pycache__', '.pytest_cache', 'docs-env']
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    violations = self.scan_file(file_path)
                    all_violations.extend(violations)
        
        return all_violations
    
    def generate_report(self, violations: List[Dict]) -> str:
        """Generate PII cleanup validation report"""
        report = []
        report.append("🔒 PII CLEANUP VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Scan completed: {len(violations)} violations found")
        report.append("")
        
        if not violations:
            report.append("✅ SUCCESS: No PII violations detected!")
            report.append("🛡️  Codebase is safe for development use")
        else:
            # Group by severity
            critical = [v for v in violations if v['severity'] == 'CRITICAL']
            high = [v for v in violations if v['severity'] == 'HIGH']
            
            report.append(f"🚨 CRITICAL violations: {len(critical)}")
            report.append(f"⚠️  HIGH violations: {len(high)}")
            report.append("")
            
            # Show critical violations first
            for violation in critical:
                report.append(f"❌ CRITICAL: {violation['type']} in {violation['file']}:{violation['line']}")
                report.append(f"   Content: {violation['content']}")
                report.append("")
            
            # Show high priority violations
            for violation in high:
                report.append(f"⚠️  HIGH: {violation['type']} in {violation['file']}:{violation['line']}")
                report.append(f"   Content: {violation['content']}")
                report.append("")
        
        # Show warnings
        if self.warnings:
            report.append("⚠️  WARNINGS:")
            for warning in self.warnings:
                report.append(f"   {warning}")
        
        report.append("")
        report.append("NEXT STEPS:")
        if violations:
            report.append("1. Fix all CRITICAL violations immediately")
            report.append("2. Address HIGH priority violations")
            report.append("3. Re-run validation until clean")
        else:
            report.append("1. ✅ PII cleanup complete - proceed to Day 2")
            report.append("2. 🚀 Continue with authentication consolidation")
        
        return "\n".join(report)

def main():
    """Run PII cleanup validation"""
    print("🔍 Starting PII cleanup validation...")
    
    validator = PIIValidator()
    
    # Scan the entire codebase
    violations = validator.scan_directory('/home/dotmac_framework')
    
    # Generate and display report
    report = validator.generate_report(violations)
    print(report)
    
    # Save report to file
    with open('/home/dotmac_framework/PII_CLEANUP_VALIDATION.md', 'w') as f:
        f.write(report)
    
    # Return exit code based on results
    if any(v['severity'] == 'CRITICAL' for v in violations):
        print("\n🚨 CRITICAL PII violations found - must fix before proceeding!")
        exit(1)
    elif violations:
        print("\n⚠️  Some PII violations found - recommend fixing before proceeding")
        exit(1)
    else:
        print("\n🎉 PII cleanup validation passed - safe to proceed to Day 2!")
        exit(0)

if __name__ == "__main__":
    main()