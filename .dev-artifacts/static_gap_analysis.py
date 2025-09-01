#!/usr/bin/env python3
"""
Static Gap Analysis
Analyzes codebase structure to identify missing components for complete E2E journey
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any

class StaticGapAnalyzer:
    """Analyzes codebase for missing E2E journey components"""
    
    def __init__(self):
        self.root_path = Path(".")
        self.gaps = []
        self.components_found = {}
        self.missing_components = {}
        
    def analyze_complete_journey(self):
        """Analyze all journey components"""
        
        print("🔍 ANALYZING E2E JOURNEY COMPONENTS")
        print("="*60)
        
        # Management Platform Components
        self.check_management_platform_apis()
        
        # ISP Framework Components  
        self.check_isp_framework_apis()
        
        # Customer Portal Components
        self.check_customer_portal_components()
        
        # Integration Components
        self.check_integration_components()
        
        # Infrastructure Components
        self.check_infrastructure_components()
        
        return self.generate_comprehensive_report()
    
    def check_management_platform_apis(self):
        """Check Management Platform API completeness"""
        
        print("📋 Management Platform APIs")
        
        required_endpoints = {
            "public_signup.py": "✅ Found - Public tenant signup",
            "tenants.py": "🔍 Checking - Tenant management", 
            "licensing_endpoints.py": "✅ Found - License management",
            "vps_customers.py": "✅ Found - VPS customer management",
            "admin.py": "✅ Found - Admin operations"
        }
        
        mgmt_api_path = self.root_path / "src" / "dotmac_management" / "api" / "v1"
        
        for endpoint, description in required_endpoints.items():
            file_path = mgmt_api_path / endpoint
            if file_path.exists():
                print(f"   {description}")
                self.components_found[f"mgmt_api_{endpoint}"] = True
            else:
                print(f"   ❌ Missing - {endpoint}")
                self.gaps.append({
                    "severity": "HIGH",
                    "component": "Management API",
                    "missing": endpoint,
                    "description": f"Missing {endpoint} endpoint"
                })
                self.missing_components[f"mgmt_api_{endpoint}"] = False
    
    def check_isp_framework_apis(self):
        """Check ISP Framework API completeness"""
        
        print("\n🏢 ISP Framework APIs")
        
        # Check ISP modules structure
        isp_modules_path = self.root_path / "src" / "dotmac_isp" / "modules"
        
        required_modules = {
            "identity": {
                "models.py": "User and customer management models",
                "routers.py": "Authentication and user APIs",
                "services.py": "User management services"
            },
            "services": {
                "models.py": "Service plans and instances models", 
                "routers.py": "Service management APIs",
                "services.py": "Service provisioning logic"
            },
            "billing": {
                "models.py": "Billing and payment models",
                "routers.py": "Billing APIs", 
                "services.py": "Billing calculation services"
            },
            "captive_portal": {
                "models.py": "Portal access models",
                "routers.py": "Customer portal APIs",
                "services.py": "Portal authentication"
            }
        }
        
        for module_name, files in required_modules.items():
            module_path = isp_modules_path / module_name
            print(f"   📂 {module_name} module:")
            
            if not module_path.exists():
                print(f"      ❌ Module directory missing")
                self.gaps.append({
                    "severity": "CRITICAL",
                    "component": "ISP Framework",
                    "missing": f"{module_name} module",
                    "description": f"Missing entire {module_name} module directory"
                })
                continue
            
            for filename, description in files.items():
                file_path = module_path / filename
                if file_path.exists():
                    print(f"      ✅ {filename} - {description}")
                    self.components_found[f"isp_{module_name}_{filename}"] = True
                else:
                    print(f"      ❌ {filename} - {description}")
                    self.gaps.append({
                        "severity": "HIGH",
                        "component": f"ISP {module_name}",
                        "missing": filename,
                        "description": f"Missing {description}"
                    })
                    self.missing_components[f"isp_{module_name}_{filename}"] = False
    
    def check_customer_portal_components(self):
        """Check customer portal components"""
        
        print("\n👥 Customer Portal Components")
        
        # Check for customer portal implementation
        portal_components = {
            "Customer Authentication": [
                "src/dotmac_isp/modules/identity/routers.py",
                "Customer login/signup endpoints"
            ],
            "Service Plans Display": [
                "src/dotmac_isp/modules/services/routers.py", 
                "Public service plans API"
            ],
            "Customer Signup": [
                "src/dotmac_isp/modules/identity/routers.py",
                "Customer registration API"
            ],
            "Service Provisioning": [
                "src/dotmac_isp/modules/services/services.py",
                "Service activation logic"
            ],
            "Customer Dashboard": [
                "src/dotmac_isp/portals/customer/",
                "Customer portal frontend"
            ],
            "Billing Integration": [
                "src/dotmac_isp/modules/billing/routers.py",
                "Customer billing APIs"
            ]
        }
        
        for component_name, (file_path, description) in portal_components.items():
            full_path = self.root_path / file_path
            
            if full_path.exists():
                print(f"   ✅ {component_name} - {description}")
                self.components_found[f"portal_{component_name}"] = True
            else:
                print(f"   ❌ {component_name} - {description}")
                severity = "HIGH" if "API" in description else "MEDIUM"
                self.gaps.append({
                    "severity": severity,
                    "component": "Customer Portal",
                    "missing": component_name,
                    "description": f"Missing {description}"
                })
                self.missing_components[f"portal_{component_name}"] = False
    
    def check_integration_components(self):
        """Check integration and orchestration components"""
        
        print("\n🔗 Integration Components")
        
        integration_components = {
            "License Enforcement": [
                "src/dotmac_shared/licensing/enforcement_middleware.py",
                "License limit enforcement in ISP instances"
            ],
            "Admin Provisioning": [
                "src/dotmac_management/services/tenant_admin_provisioning.py", 
                "Admin account creation service"
            ],
            "Auto License Provisioning": [
                "src/dotmac_management/services/auto_license_provisioning.py",
                "Automatic license creation service" 
            ],
            "Tenant Provisioning": [
                "src/dotmac_management/services/tenant_provisioning.py",
                "Main provisioning orchestration"
            ],
            "Coolify Client": [
                "src/dotmac_management/services/coolify_client.py",
                "Infrastructure deployment client"
            ],
            "Notification Service": [
                "src/dotmac_shared/notifications/service.py",
                "Email and SMS notifications"
            ]
        }
        
        for component_name, (file_path, description) in integration_components.items():
            full_path = self.root_path / file_path
            
            if full_path.exists():
                print(f"   ✅ {component_name} - {description}")
                self.components_found[f"integration_{component_name}"] = True
            else:
                print(f"   ❌ {component_name} - {description}")
                self.gaps.append({
                    "severity": "HIGH",
                    "component": "Integration",
                    "missing": component_name,
                    "description": f"Missing {description}"
                })
                self.missing_components[f"integration_{component_name}"] = False
    
    def check_infrastructure_components(self):
        """Check infrastructure and deployment components"""
        
        print("\n🏗️ Infrastructure Components")
        
        infra_components = {
            "Docker Compose": [
                "docker-compose.coolify.yml",
                "Coolify deployment configuration"
            ],
            "Production Dockerfile": [
                "Dockerfile.production",
                "Production Docker image build"
            ],
            "Database Migrations": [
                "alembic/",
                "Database schema management"
            ],
            "Tenant Compose Template": [
                "docker/tenant-compose-template.yml",
                "Template for tenant deployments"
            ],
            "Migration Scripts": [
                "docker/migrate.sh",
                "Database migration runner"
            ],
            "Production Entrypoint": [
                "docker/production-entrypoint.sh",
                "Production container startup script"
            ],
            "CI/CD Pipeline": [
                ".github/workflows/build-and-deploy.yml",
                "Automated build and deployment"
            ]
        }
        
        for component_name, (file_path, description) in infra_components.items():
            full_path = self.root_path / file_path
            
            if full_path.exists():
                print(f"   ✅ {component_name} - {description}")
                self.components_found[f"infra_{component_name}"] = True
            else:
                print(f"   ❌ {component_name} - {description}")
                severity = "CRITICAL" if component_name in ["Docker Compose", "Production Dockerfile"] else "MEDIUM"
                self.gaps.append({
                    "severity": severity,
                    "component": "Infrastructure",
                    "missing": component_name,
                    "description": f"Missing {description}"
                })
                self.missing_components[f"infra_{component_name}"] = False
    
    def analyze_api_completeness(self):
        """Analyze API endpoint completeness"""
        
        print("\n🌐 API Completeness Analysis")
        
        # Check ISP Framework API structure
        expected_isp_apis = [
            # Authentication & Users
            "/api/v1/auth/login",
            "/api/v1/auth/logout", 
            "/api/v1/auth/register",
            "/api/v1/users",
            
            # Customers
            "/api/v1/customers",
            "/api/v1/customers/{id}",
            "/api/v1/customers/signup",
            
            # Service Plans
            "/api/v1/service-plans",
            "/api/v1/service-plans/{id}",
            "/api/v1/public/service-plans",
            
            # Services
            "/api/v1/services",
            "/api/v1/services/{id}/provision",
            "/api/v1/services/{id}/suspend",
            
            # Billing
            "/api/v1/billing/invoices",
            "/api/v1/billing/payments",
            "/api/v1/billing/subscriptions",
            
            # System
            "/api/v1/system/license",
            "/api/v1/system/status",
            "/health"
        ]
        
        # This would require actually parsing router files to check endpoints
        # For now, we'll infer from file structure
        
        api_coverage = self.estimate_api_coverage()
        print(f"   📊 Estimated API Coverage: {api_coverage}%")
        
        if api_coverage < 70:
            self.gaps.append({
                "severity": "HIGH",
                "component": "API Coverage",
                "missing": "Multiple API endpoints",
                "description": f"API coverage estimated at {api_coverage}% - many endpoints missing"
            })
    
    def estimate_api_coverage(self) -> int:
        """Estimate API coverage based on existing files"""
        
        # Count existing router files
        isp_modules = self.root_path / "src" / "dotmac_isp" / "modules"
        router_files = 0
        total_expected = 6  # identity, services, billing, analytics, captive_portal, portal_management
        
        if isp_modules.exists():
            for module_dir in isp_modules.iterdir():
                if module_dir.is_dir():
                    router_file = module_dir / "routers.py"
                    if router_file.exists():
                        router_files += 1
        
        coverage = (router_files / total_expected) * 100
        return int(coverage)
    
    def check_critical_journey_blockers(self):
        """Identify critical blockers for E2E journey"""
        
        print("\n🚨 Critical Journey Blockers")
        
        critical_requirements = {
            "Public Signup API": "src/dotmac_management/api/v1/public_signup.py",
            "Tenant Provisioning": "src/dotmac_management/services/tenant_provisioning.py", 
            "Admin Account Creation": "src/dotmac_management/services/tenant_admin_provisioning.py",
            "License Provisioning": "src/dotmac_management/services/auto_license_provisioning.py",
            "ISP Authentication": "src/dotmac_isp/modules/identity/routers.py",
            "Customer Management": "src/dotmac_isp/modules/identity/models.py",
            "Service Plans": "src/dotmac_isp/modules/services/models.py"
        }
        
        critical_gaps = []
        
        for requirement, file_path in critical_requirements.items():
            full_path = self.root_path / file_path
            
            if full_path.exists():
                print(f"   ✅ {requirement}")
            else:
                print(f"   🚨 {requirement} - CRITICAL BLOCKER")
                critical_gaps.append(requirement)
                self.gaps.append({
                    "severity": "CRITICAL",
                    "component": "Journey Blocker",
                    "missing": requirement,
                    "description": f"Critical component required for E2E journey"
                })
        
        return critical_gaps
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate detailed gap analysis report"""
        
        print("\n" + "="*80)
        print("📊 GENERATING COMPREHENSIVE REPORT")
        print("="*80)
        
        # Analyze API completeness
        self.analyze_api_completeness()
        
        # Check critical blockers
        critical_blockers = self.check_critical_journey_blockers()
        
        # Categorize gaps
        gaps_by_severity = {
            "CRITICAL": [g for g in self.gaps if g["severity"] == "CRITICAL"],
            "HIGH": [g for g in self.gaps if g["severity"] == "HIGH"], 
            "MEDIUM": [g for g in self.gaps if g["severity"] == "MEDIUM"]
        }
        
        # Calculate completion percentage
        total_components = len(self.components_found) + len(self.missing_components)
        completion_rate = (len(self.components_found) / total_components * 100) if total_components > 0 else 0
        
        report = {
            "analysis_summary": {
                "total_gaps": len(self.gaps),
                "critical_gaps": len(gaps_by_severity["CRITICAL"]),
                "high_priority_gaps": len(gaps_by_severity["HIGH"]),
                "medium_priority_gaps": len(gaps_by_severity["MEDIUM"]),
                "completion_rate": round(completion_rate, 1),
                "critical_blockers": critical_blockers
            },
            "gaps_by_severity": gaps_by_severity,
            "components_analysis": {
                "found": self.components_found,
                "missing": self.missing_components
            },
            "journey_readiness": self.assess_journey_readiness(),
            "implementation_priorities": self.generate_implementation_priorities(),
            "estimated_effort": self.estimate_implementation_effort()
        }
        
        # Print summary
        print(f"\n📈 ANALYSIS SUMMARY:")
        print(f"   Overall completion: {completion_rate:.1f}%")
        print(f"   Total gaps found: {len(self.gaps)}")
        print(f"   Critical gaps: {len(gaps_by_severity['CRITICAL'])}")
        print(f"   High priority gaps: {len(gaps_by_severity['HIGH'])}")
        print(f"   Medium priority gaps: {len(gaps_by_severity['MEDIUM'])}")
        
        if critical_blockers:
            print(f"\n🚨 CRITICAL BLOCKERS ({len(critical_blockers)}):")
            for blocker in critical_blockers:
                print(f"   - {blocker}")
        
        return report
    
    def assess_journey_readiness(self) -> Dict[str, Any]:
        """Assess readiness for each journey phase"""
        
        journey_phases = {
            "Tenant Signup": {
                "required": ["mgmt_api_public_signup.py", "mgmt_api_tenants.py"],
                "readiness": 0
            },
            "Tenant Provisioning": {
                "required": ["integration_Tenant Provisioning", "integration_Admin Provisioning"],
                "readiness": 0
            },
            "ISP Deployment": {
                "required": ["infra_Docker Compose", "infra_Production Dockerfile"],
                "readiness": 0
            },
            "Admin Setup": {
                "required": ["isp_identity_routers.py", "isp_identity_models.py"],
                "readiness": 0
            },
            "Service Management": {
                "required": ["isp_services_models.py", "isp_services_routers.py"],
                "readiness": 0
            },
            "Customer Onboarding": {
                "required": ["portal_Customer Authentication", "portal_Service Plans Display"],
                "readiness": 0
            }
        }
        
        for phase_name, phase_info in journey_phases.items():
            required_count = len(phase_info["required"])
            found_count = sum(1 for req in phase_info["required"] if req in self.components_found)
            readiness = (found_count / required_count) * 100 if required_count > 0 else 0
            journey_phases[phase_name]["readiness"] = round(readiness, 1)
        
        return journey_phases
    
    def generate_implementation_priorities(self) -> List[Dict[str, Any]]:
        """Generate prioritized implementation list"""
        
        priorities = [
            {
                "priority": 1,
                "title": "Complete ISP Framework Core APIs",
                "description": "Implement missing router files for identity, services, and billing modules",
                "components": ["isp_identity_routers.py", "isp_services_routers.py", "isp_billing_routers.py"],
                "estimated_days": 5,
                "blocker": True
            },
            {
                "priority": 2,
                "title": "Implement Customer Portal Components",
                "description": "Create customer-facing portal for service signup and management",
                "components": ["portal_Customer Authentication", "portal_Customer Dashboard"],
                "estimated_days": 8,
                "blocker": True
            },
            {
                "priority": 3,
                "title": "Complete Infrastructure Components",
                "description": "Finish deployment templates and migration scripts",
                "components": ["infra_Tenant Compose Template", "infra_Migration Scripts"],
                "estimated_days": 3,
                "blocker": False
            },
            {
                "priority": 4,
                "title": "Implement ISP Setup Wizard",
                "description": "Create guided setup for new ISP tenants",
                "components": ["Setup Wizard API", "Setup Wizard Frontend"],
                "estimated_days": 4,
                "blocker": False
            },
            {
                "priority": 5,
                "title": "Add Service Provisioning Logic",
                "description": "Implement automated service activation and provisioning",
                "components": ["Service Provisioning", "Network Integration"],
                "estimated_days": 6,
                "blocker": False
            }
        ]
        
        return priorities
    
    def estimate_implementation_effort(self) -> Dict[str, Any]:
        """Estimate total implementation effort"""
        
        gap_effort_mapping = {
            "CRITICAL": 2,  # 2 days per critical gap
            "HIGH": 1,      # 1 day per high gap  
            "MEDIUM": 0.5   # 0.5 days per medium gap
        }
        
        total_days = 0
        effort_breakdown = {}
        
        for severity, gaps in [("CRITICAL", [g for g in self.gaps if g["severity"] == "CRITICAL"]),
                              ("HIGH", [g for g in self.gaps if g["severity"] == "HIGH"]),
                              ("MEDIUM", [g for g in self.gaps if g["severity"] == "MEDIUM"])]:
            
            gap_count = len(gaps)
            effort_days = gap_count * gap_effort_mapping[severity]
            total_days += effort_days
            
            effort_breakdown[severity.lower()] = {
                "gap_count": gap_count,
                "days_per_gap": gap_effort_mapping[severity],
                "total_days": effort_days
            }
        
        return {
            "total_estimated_days": total_days,
            "total_estimated_weeks": round(total_days / 5, 1),
            "breakdown": effort_breakdown,
            "confidence": "Medium" if total_days < 20 else "Low"
        }


def main():
    """Run static gap analysis"""
    
    analyzer = StaticGapAnalyzer()
    report = analyzer.analyze_complete_journey()
    
    # Save report
    os.makedirs('.dev-artifacts', exist_ok=True)
    with open('.dev-artifacts/static_gap_analysis.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Report saved to: .dev-artifacts/static_gap_analysis.json")
    
    # Print journey readiness
    print(f"\n🎯 JOURNEY READINESS BY PHASE:")
    for phase_name, phase_info in report["journey_readiness"].items():
        readiness = phase_info["readiness"]
        status = "✅" if readiness >= 80 else "⚠️" if readiness >= 50 else "❌"
        print(f"   {status} {phase_name}: {readiness}%")
    
    # Print implementation priorities
    print(f"\n📋 TOP IMPLEMENTATION PRIORITIES:")
    for priority in report["implementation_priorities"][:3]:
        blocker_text = " (BLOCKER)" if priority["blocker"] else ""
        print(f"   {priority['priority']}. {priority['title']}{blocker_text}")
        print(f"      {priority['description']}")
        print(f"      Estimated: {priority['estimated_days']} days")
    
    # Print effort estimate
    effort = report["estimated_effort"]
    print(f"\n⏱️  TOTAL IMPLEMENTATION EFFORT:")
    print(f"   Estimated: {effort['total_estimated_days']} days ({effort['total_estimated_weeks']} weeks)")
    print(f"   Confidence: {effort['confidence']}")
    
    return report


if __name__ == "__main__":
    main()