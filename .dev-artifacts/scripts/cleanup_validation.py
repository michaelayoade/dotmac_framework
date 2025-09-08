#!/usr/bin/env python3
"""
Validation script to ensure analysis is complete and artifacts can be cleaned up
"""
import os
import json
from pathlib import Path

def validate_analysis_artifacts():
    """Validate that all analysis artifacts are present"""
    base_path = Path("/home/dotmac_framework/.dev-artifacts")
    
    required_files = [
        "scripts/comprehensive_analysis.py",
        "analysis/comprehensive_analysis_report.json", 
        "analysis/targeted_gap_analysis.json",
        "analysis/comprehensive_gap_analysis_report.md",
        "analysis/critical_fixes_action_plan.py"
    ]
    
    print("Validating analysis artifacts...")
    all_present = True
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_present = False
    
    return all_present

def summarize_findings():
    """Summarize key findings from analysis"""
    print("\n" + "="*60)
    print("DOTMAC FRAMEWORK GAP ANALYSIS SUMMARY")
    print("="*60)
    
    # Load comprehensive analysis
    try:
        with open("/home/dotmac_framework/.dev-artifacts/analysis/comprehensive_analysis_report.json", 'r') as f:
            data = json.load(f)
            
        print(f"📊 Total Python Files Analyzed: {data['summary']['total_python_files']:,}")
        print(f"🚨 Total Gaps Found: {data['summary']['total_gaps_found']}")
        print()
        
        for category, details in data['gap_categories'].items():
            severity = details['severity_breakdown']
            high_count = severity.get('high', 0)
            medium_count = severity.get('medium', 0)
            
            if high_count > 0:
                urgency = "🚨 CRITICAL" if high_count > 10 else "⚠️  HIGH"
            elif medium_count > 10:
                urgency = "⚠️  MEDIUM"
            else:
                urgency = "ℹ️  LOW"
                
            print(f"{urgency} {category.replace('_', ' ').title()}: {details['total_gaps']} issues")
            
    except Exception as e:
        print(f"Could not load analysis data: {e}")
    
    # Load targeted analysis  
    try:
        with open("/home/dotmac_framework/.dev-artifacts/analysis/targeted_gap_analysis.json", 'r') as f:
            targeted = json.load(f)
            
        print("\n" + "-"*40)
        print("PRIORITY ACTION ITEMS:")
        print("-"*40)
        print(f"🔴 Critical Issues: {targeted['summary']['total_critical']}")
        print(f"🟡 High Priority: {targeted['summary']['total_high']}")  
        print(f"🟢 Medium Priority: {targeted['summary']['total_medium']}")
        
        if targeted.get('critical_actions'):
            print("\nIMMEDIATE ACTIONS REQUIRED:")
            for action in targeted['critical_actions']:
                print(f"• {action['issue'].replace('_', ' ').title()}: {action['count']} instances")
                print(f"  Action: {action['action']}")
                
    except Exception as e:
        print(f"Could not load targeted analysis: {e}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Review comprehensive_gap_analysis_report.md for detailed findings")
    print("2. Implement critical security fixes from critical_fixes_action_plan.py")  
    print("3. Follow the 3-phase implementation roadmap")
    print("4. Set up security scanning in CI/CD pipeline")
    print("5. Begin architecture standardization with base classes")
    print()

if __name__ == "__main__":
    if validate_analysis_artifacts():
        print("\n✅ All analysis artifacts validated successfully!")
        summarize_findings()
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE - ARTIFACTS READY FOR REVIEW")
        print("="*60)
        print()
        print("All analysis files are located in .dev-artifacts/")
        print("Key deliverables:")
        print("• Comprehensive Gap Analysis Report (Markdown)")
        print("• Critical Fixes Action Plan (Python with code examples)")
        print("• Detailed JSON reports with specific file references")
        print()
        print("You can now review the findings and begin implementing fixes.")
        print("Run 'rm -rf .dev-artifacts/' when ready to clean up.")
        
    else:
        print("\n❌ Some analysis artifacts are missing!")
        print("Please ensure the analysis completed successfully.")