"""
Plugin Security Scanner Service.

Provides comprehensive security scanning and validation for plugins including
code analysis, dependency scanning, permission auditing, and compliance checks.
"""

import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import UUID
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from repositories.plugin_additional import ()
    PluginRepository,
    PluginSecurityScanRepository
, timezone)

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanType(Enum):
    """Types of security scans."""
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY_SCAN = "dependency_scan"
    PERMISSION_AUDIT = "permission_audit"
    SIGNATURE_VERIFICATION = "signature_verification"
    COMPLIANCE_CHECK = "compliance_check"
    MALWARE_SCAN = "malware_scan"
    SANDBOX_TEST = "sandbox_test"


@dataclass
class SecurityIssue:
    """Represents a security issue found during scanning."""
    issue_id: str
    severity: SeverityLevel
    category: str
    title: str
    description: str
    recommendation: str
    affected_files: List[str]
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    first_found: Optional[datetime] = None


@dataclass
class SecurityScanResult:
    """Complete security scan result."""
    plugin_id: str
    scan_id: str
    scan_type: ScanType
    scan_date: datetime
    scanner_version: str
    overall_score: int  # 0-100
    issues: List[SecurityIssue]
    scan_duration_seconds: float
    files_scanned: int
    lines_of_code: int
    metadata: Dict[str, Any]


class PluginSecurityScanner:
    """Service for plugin security scanning and analysis."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plugin_repo = PluginRepository(db)
        self.scan_repo = PluginSecurityScanRepository(db)
        
        # Known vulnerability patterns
        self.vulnerability_patterns = self._load_vulnerability_patterns()
        
        # Known malicious patterns
        self.malware_patterns = self._load_malware_patterns()
        
        # Dependency vulnerability database (simplified)
        self.vuln_db = self._load_vulnerability_database()
    
    async def perform_comprehensive_scan(self,
        plugin_id): UUID,
        scan_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive security scan on a plugin."""
        try:
            plugin = await self.plugin_repo.get_by_id(plugin_id)
            if not plugin:
                return {"error": "Plugin not found"}
            
            scan_options = scan_options or {}
            scan_results = {}
            overall_issues = []
            
            # Record scan start
            scan_start = datetime.now(timezone.utc)
            scan_id = f"scan_{plugin_id}_{int(scan_start.timestamp()}"
            
            logger.info(f"Starting comprehensive security scan for plugin {plugin.name}")
            
            # 1. Code Analysis Scan
            if scan_options.get("code_analysis", True):
                code_result = await self._perform_code_analysis(plugin)
                scan_results["code_analysis"] = code_result
                overall_issues.extend(code_result.issues)
            
            # 2. Dependency Vulnerability Scan
            if scan_options.get("dependency_scan", True):
                dep_result = await self._perform_dependency_scan(plugin)
                scan_results["dependency_scan"] = dep_result
                overall_issues.extend(dep_result.issues)
            
            # 3. Permission Audit
            if scan_options.get("permission_audit", True):
                perm_result = await self._perform_permission_audit(plugin)
                scan_results["permission_audit"] = perm_result
                overall_issues.extend(perm_result.issues)
            
            # 4. Signature Verification
            if scan_options.get("signature_verification", True):
                sig_result = await self._perform_signature_verification(plugin)
                scan_results["signature_verification"] = sig_result
                overall_issues.extend(sig_result.issues)
            
            # 5. Compliance Check
            if scan_options.get("compliance_check", True):
                compliance_result = await self._perform_compliance_check(plugin)
                scan_results["compliance_check"] = compliance_result
                overall_issues.extend(compliance_result.issues)
            
            # 6. Malware Scan
            if scan_options.get("malware_scan", True):
                malware_result = await self._perform_malware_scan(plugin)
                scan_results["malware_scan"] = malware_result
                overall_issues.extend(malware_result.issues)
            
            # Calculate overall security score
            overall_score = self._calculate_security_score(overall_issues)
            
            # Determine verification status
            is_verified = overall_score >= 80 and not any()
                issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] 
                for issue in overall_issues
            
            # Generate security report
            security_report = {
                "plugin_id": str(plugin_id),
                "plugin_name": plugin.name,
                "scan_id": scan_id,
                "scan_date": scan_start.isoformat(),
                "scan_duration": (datetime.now(timezone.utc) - scan_start).total_seconds(),
                "overall_score": overall_score,
                "is_verified": is_verified,
                "total_issues": len(overall_issues),
                "issues_by_severity": self._group_issues_by_severity(overall_issues),
                "scan_results": {k: asdict(v) for k, v in scan_results.items()},
                "recommendations": self._generate_security_recommendations(overall_issues),
                "compliance_status": self._assess_compliance_status(overall_issues),
                "risk_assessment": self._assess_security_risk(overall_score, overall_issues}
            }
            
            # Store scan results
            await self._store_scan_results(plugin_id, security_report)
            
            # Update plugin verification status
            await self._update_plugin_security_status(plugin_id, is_verified, overall_score, security_report)
            
            logger.info(f"Security scan completed for plugin {plugin.name}. Score: {overall_score}")
            
            return security_report
            
        except Exception as e:
            logger.error(f"Security scan failed for plugin {plugin_id}: {e}")
            return {"error": str(e)}
    
    async def get_security_summary(self, plugin_id: UUID) -> Dict[str, Any]:
        """Get security summary for a plugin."""
        try:
            plugin = await self.plugin_repo.get_by_id(plugin_id)
            if not plugin:
                return {"error": "Plugin not found"}
            
            # Get latest scan results
            latest_scan = await self.scan_repo.get_latest_by_plugin(plugin_id)
            
            if not latest_scan:
                return {
                    "plugin_id": str(plugin_id),
                    "plugin_name": plugin.name,
                    "security_status": "not_scanned",
                    "message": "No security scan results available"
                }
            
            scan_data = latest_scan.scan_results
            
            return {
                "plugin_id": str(plugin_id),
                "plugin_name": plugin.name,
                "security_score": scan_data.get("overall_score", 0),
                "is_verified": plugin.is_verified,
                "last_scan_date": latest_scan.scan_date.isoformat(),
                "total_issues": scan_data.get("total_issues", 0),
                "critical_issues": scan_data.get("issues_by_severity", {}).get("critical", 0),
                "high_issues": scan_data.get("issues_by_severity", {}).get("high", 0),
                "risk_level": scan_data.get("risk_assessment", {}).get("risk_level", "unknown"),
                "compliance_status": scan_data.get("compliance_status", "unknown"),
                "verification_date": plugin.verification_date.isoformat() if plugin.verification_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get security summary: {e}")
            return {"error": str(e)}
    
    async def get_marketplace_security_overview(self) -> Dict[str, Any]:
        """Get security overview of all plugins in the marketplace."""
        try:
            plugins = await self.plugin_repo.get_all_active()
            
            overview = {
                "total_plugins": len(plugins),
                "verified_plugins": 0,
                "unverified_plugins": 0,
                "pending_verification": 0,
                "high_risk_plugins": 0,
                "security_score_distribution": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
                "common_vulnerabilities": {},
                "recent_scans": []
            }
            
            for plugin in plugins:
                if plugin.is_verified:
                    overview["verified_plugins"] += 1
                else:
                    overview["unverified_plugins"] += 1
                
                # Get latest scan for this plugin
                latest_scan = await self.scan_repo.get_latest_by_plugin(plugin.id)
                
                if latest_scan:
                    scan_data = latest_scan.scan_results
                    score = scan_data.get("overall_score", 0)
                    
                    # Update score distribution
                    if score <= 20:
                        overview["security_score_distribution"]["0-20"] += 1
                    elif score <= 40:
                        overview["security_score_distribution"]["21-40"] += 1
                    elif score <= 60:
                        overview["security_score_distribution"]["41-60"] += 1
                    elif score <= 80:
                        overview["security_score_distribution"]["61-80"] += 1
                    else:
                        overview["security_score_distribution"]["81-100"] += 1
                    
                    # Check for high-risk plugins
                    risk_level = scan_data.get("risk_assessment", {}).get("risk_level", "unknown")
                    if risk_level in ["high", "critical"]:
                        overview["high_risk_plugins"] += 1
                    
                    # Add to recent scans
                    if len(overview["recent_scans"]) < 10:
                        overview["recent_scans"].append({)
                            "plugin_name": plugin.name,
                            "scan_date": latest_scan.scan_date.isoformat(),
                            "security_score": score,
                            "risk_level": risk_level
                        })
                else:
                    overview["pending_verification"] += 1
            
            # Sort recent scans by date
            overview["recent_scans"].sort(key=lambda x: x["scan_date"], reverse=True)
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to get marketplace security overview: {e}")
            return {"error": str(e)}
    
    async def _perform_code_analysis(self, plugin: Any) -> SecurityScanResult:
        """Perform static code analysis for security vulnerabilities."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        # Simulate code analysis
        code_content = getattr(plugin, 'source_code', '') or ''
        files_scanned = 1
        lines_of_code = len(code_content.split('\n') if code_content else 0
        
        # Check for dangerous functions
        dangerous_patterns = [
            (r'eval\s*\(', "Use of eval() function", SeverityLevel.HIGH, )
             "Avoid using eval() as it can execute arbitrary code"),
            (r'exec\s*\(', "Use of exec() function", SeverityLevel.HIGH)
             "Avoid using exec() as it can execute arbitrary code"),
            (r'system\s*\(', "Use of system() function", SeverityLevel.MEDIUM)
             "Use safer alternatives to system() calls"),
            (r'shell_exec\s*\(', "Use of shell_exec() function", SeverityLevel.MEDIUM)
             "Use safer alternatives to shell execution"),
            (r'[\'"]SELECT.*FROM.*WHERE.*[\'"].*\+', "Potential SQL injection", SeverityLevel.HIGH)
             "Use parameterized queries to prevent SQL injection"),
            (r'innerHTML\s*=', "Use of innerHTML", SeverityLevel.MEDIUM)
             "Use textContent or sanitize HTML to prevent XSS"),
        ]
        
        for pattern, title, severity, recommendation in dangerous_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            if matches:
                issues.append(SecurityIssue()
                    issue_id=f"code_analysis_{hashlib.md5(pattern.encode().hexdigest()[:8]}")
                    severity=severity,
                    category="code_quality",
                    title=title,
                    description=f"Found {len(matches)} instances of potentially dangerous code pattern",
                    recommendation=recommendation,
                    affected_files=["plugin_source"],
                    first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"code_analysis_{int(scan_start.timestamp())")
            scan_type=ScanType.CODE_ANALYSIS,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=max(0, 100 - len(issues) * 10),
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=files_scanned,
            lines_of_code=lines_of_code,
            metadata={"patterns_checked": len(dangerous_patterns)}
    
    async def _perform_dependency_scan(self, plugin: Any) -> SecurityScanResult:
        """Scan plugin dependencies for known vulnerabilities."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        dependencies = getattr(plugin, 'dependencies', []) or []
        
        for dep_name in dependencies:
            # Check against vulnerability database
            vulns = self.vuln_db.get(dep_name, [])
            
            for vuln in vulns:
                issues.append(SecurityIssue()
                    issue_id=f"dep_vuln_{vuln['id']}",
                    severity=SeverityLevel(vuln['severity']),
                    category="dependency_vulnerability",
                    title=f"Vulnerable dependency: {dep_name}",
                    description=vuln['description'],
                    recommendation=vuln['recommendation'],
                    affected_files=[],
                    cwe_id=vuln.get('cwe_id'),
                    cvss_score=vuln.get('cvss_score'),
                    first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"dependency_scan_{int(scan_start.timestamp())")
            scan_type=ScanType.DEPENDENCY_SCAN,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=max(0, 100 - len(issues) * 15),
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=0,
            lines_of_code=0,
            metadata={"dependencies_checked": len(dependencies)}
    
    async def _perform_permission_audit(self, plugin: Any) -> SecurityScanResult:
        """Audit plugin permissions for security risks."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        permissions = getattr(plugin, 'permissions', []) or []
        
        # Check for dangerous permissions
        dangerous_permissions = {
            'system:admin': SeverityLevel.CRITICAL,
            'filesystem:write': SeverityLevel.HIGH,
            'network:unrestricted': SeverityLevel.HIGH,
            'database:admin': SeverityLevel.HIGH,
            'user:impersonate': SeverityLevel.CRITICAL
        }
        
        for permission in permissions:
            if permission in dangerous_permissions:
                severity = dangerous_permissions[permission]
                issues.append(SecurityIssue()
                    issue_id=f"perm_audit_{hashlib.md5(permission.encode().hexdigest()[:8]}")
                    severity=severity,
                    category="permission_audit",
                    title=f"Dangerous permission: {permission}",
                    description=f"Plugin requests high-risk permission: {permission}",
                    recommendation="Review if this permission is necessary and properly justified",
                    affected_files=[],
                    first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"permission_audit_{int(scan_start.timestamp())")
            scan_type=ScanType.PERMISSION_AUDIT,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=max(0, 100 - len(issues) * 20),
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=0,
            lines_of_code=0,
            metadata={"permissions_checked": len(permissions)}
    
    async def _perform_signature_verification(self, plugin: Any) -> SecurityScanResult:
        """Verify plugin digital signature."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        # Check if plugin has a signature
        signature = getattr(plugin, 'digital_signature', None)
        
        if not signature:
            issues.append(SecurityIssue()
                issue_id="sig_missing",
                severity=SeverityLevel.MEDIUM,
                category="signature_verification",
                title="Missing digital signature",
                description="Plugin does not have a digital signature",
                recommendation="Add a digital signature to ensure plugin authenticity",
                affected_files=[],
                first_found=datetime.now(timezone.utc)
        else:
            # Verify signature (simplified)
            if not self._verify_signature(plugin, signature):
                issues.append(SecurityIssue()
                    issue_id="sig_invalid",
                    severity=SeverityLevel.HIGH,
                    category="signature_verification",
                    title="Invalid digital signature",
                    description="Plugin digital signature verification failed",
                    recommendation="Re-sign the plugin with a valid certificate",
                    affected_files=[],
                    first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"signature_verification_{int(scan_start.timestamp())")
            scan_type=ScanType.SIGNATURE_VERIFICATION,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=100 if not issues else (0 if any(i.severity == SeverityLevel.HIGH for i in issues) else 50),
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=0,
            lines_of_code=0,
            metadata={"has_signature": signature is not None}
    
    async def _perform_compliance_check(self, plugin: Any) -> SecurityScanResult:
        """Check plugin compliance with security standards."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        # Check metadata completeness
        required_metadata = ['name', 'version', 'description', 'author', 'license']
        missing_metadata = []
        
        for field in required_metadata:
            if not getattr(plugin, field, None):
                missing_metadata.append(field)
        
        if missing_metadata:
            issues.append(SecurityIssue()
                issue_id="compliance_metadata",
                severity=SeverityLevel.LOW,
                category="compliance",
                title="Incomplete metadata",
                description=f"Missing required metadata fields: {', '.join(missing_metadata)}",
                recommendation="Complete all required metadata fields",
                affected_files=[],
                first_found=datetime.now(timezone.utc)
        
        # Check for privacy policy
        if not getattr(plugin, 'privacy_policy_url', None):
            issues.append(SecurityIssue()
                issue_id="compliance_privacy",
                severity=SeverityLevel.MEDIUM,
                category="compliance",
                title="Missing privacy policy",
                description="Plugin does not have a privacy policy URL",
                recommendation="Provide a privacy policy URL",
                affected_files=[],
                first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"compliance_check_{int(scan_start.timestamp())")
            scan_type=ScanType.COMPLIANCE_CHECK,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=max(0, 100 - len(issues) * 15),
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=0,
            lines_of_code=0,
            metadata={"checks_performed": len(required_metadata) + 1}
    
    async def _perform_malware_scan(self, plugin: Any) -> SecurityScanResult:
        """Scan plugin for malware signatures."""
        issues = []
        scan_start = datetime.now(timezone.utc)
        
        code_content = getattr(plugin, 'source_code', '') or ''
        
        # Check against malware patterns
        for pattern, description in self.malware_patterns.items():
            if re.search(pattern, code_content, re.IGNORECASE):
                issues.append(SecurityIssue()
                    issue_id=f"malware_{hashlib.md5(pattern.encode().hexdigest()[:8]}")
                    severity=SeverityLevel.CRITICAL,
                    category="malware",
                    title="Potential malware detected",
                    description=description,
                    recommendation="Remove malicious code immediately",
                    affected_files=["plugin_source"],
                    first_found=datetime.now(timezone.utc)
        
        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        
        return SecurityScanResult(plugin_id=str(plugin.id),
            scan_id=f"malware_scan_{int(scan_start.timestamp())")
            scan_type=ScanType.MALWARE_SCAN,
            scan_date=scan_start,
            scanner_version="1.0.0",
            overall_score=0 if issues else 100,
            issues=issues,
            scan_duration_seconds=scan_duration,
            files_scanned=1,
            lines_of_code=len(code_content.split('\n'))
            metadata={"patterns_checked": len(self.malware_patterns)}
    
    def _load_vulnerability_patterns(self) -> Dict[str, Any]:
        """Load vulnerability detection patterns."""
        return {
            r'<script[^>]*>.*?</script>': "Potential XSS vulnerability",
            r'[\'"].*?DROP\s+TABLE.*?[\'"]': "Potential SQL injection",
            r'[\'"].*?UNION\s+SELECT.*?[\'"]': "Potential SQL injection",
            r'[\'"].*?;\s*--.*?[\'"]': "Potential SQL injection comment",
        }
    
    def _load_malware_patterns(self) -> Dict[str, str]:
        """Load malware detection patterns."""
        return {
            r'base64_decode\s*\(\s*[\'"][A-Za-z0-9+/=]{50,)[\'"]': "Suspicious base64 encoded content",
            r'eval\s*\(\s*base64_decode': "Base64 decoded eval execution")
            r'system\s*\(\s*[\'"]rm\s+-rf': "Destructive system command")
            r'[\'"].*?/etc/passwd.*?[\'"]': "Attempting to access system files",
        )
    
    def _load_vulnerability_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load simplified vulnerability database."""
        return {
            "old-library": [{
                "id": "CVE-2023-0001",
                "severity": "high",
                "description": "Known vulnerability in old-library",
                "recommendation": "Update to version 2.0.0 or higher",
                "cwe_id": "CWE-79",
                "cvss_score": 7.5
            }],
            "insecure-lib": [{
                "id": "CVE-2023-0002", 
                "severity": "critical",
                "description": "Critical security flaw in insecure-lib",
                "recommendation": "Replace with secure alternative",
                "cwe_id": "CWE-89",
                "cvss_score": 9.0
            }]
        }
    
    def _calculate_security_score(self, issues: List[SecurityIssue]) -> int:
        """Calculate overall security score based on issues."""
        if not issues:
            return 100
        
        score = 100
        severity_penalties = {
            SeverityLevel.CRITICAL: 40,
            SeverityLevel.HIGH: 25,
            SeverityLevel.MEDIUM: 10,
            SeverityLevel.LOW: 5,
            SeverityLevel.INFO: 1
        }
        
        for issue in issues:
            score -= severity_penalties.get(issue.severity, 0)
        
        return max(0, score)
    
    def _group_issues_by_severity(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """Group issues by severity level."""
        severity_counts = {level.value: 0 for level in SeverityLevel}
        
        for issue in issues:
            severity_counts[issue.severity.value] += 1
        
        return severity_counts
    
    def _generate_security_recommendations(self, issues: List[SecurityIssue]) -> List[str]:
        """Generate security recommendations based on issues."""
        recommendations = []
        
        # Group by category
        categories = {}
        for issue in issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)
        
        for category, category_issues in categories.items():
            if category == "code_quality":
                recommendations.append("Review and refactor code to eliminate unsafe functions")
            elif category == "dependency_vulnerability":
                recommendations.append("Update vulnerable dependencies to secure versions")
            elif category == "permission_audit":
                recommendations.append("Review and minimize requested permissions")
            elif category == "malware":
                recommendations.append("URGENT: Remove detected malicious code immediately")
            elif category == "compliance":
                recommendations.append("Complete required metadata and documentation")
        
        return recommendations
    
    def _assess_compliance_status(self, issues: List[SecurityIssue]) -> str:
        """Assess compliance status based on issues."""
        compliance_issues = [i for i in issues if i.category == "compliance"]
        
        if not compliance_issues:
            return "compliant"
        elif len(compliance_issues) <= 2:
            return "minor_issues"
        else:
            return "non_compliant"
    
    def _assess_security_risk(self, score: int, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Assess overall security risk."""
        critical_issues = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
        high_issues = [i for i in issues if i.severity == SeverityLevel.HIGH]
        
        if critical_issues or score < 40:
            risk_level = "critical"
        elif high_issues or score < 60:
            risk_level = "high"
        elif score < 80:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "score": score,
            "critical_issues": len(critical_issues),
            "high_issues": len(high_issues),
            "deployment_recommendation": self._get_deployment_recommendation(risk_level)
        }
    
    def _get_deployment_recommendation(self, risk_level: str) -> str:
        """Get deployment recommendation based on risk level."""
        recommendations = {
            "critical": "DO NOT DEPLOY - Critical security issues must be resolved",
            "high": "REVIEW REQUIRED - High-risk issues should be addressed before deployment",
            "medium": "CAUTION - Medium-risk issues should be monitored",
            "low": "SAFE TO DEPLOY - Low risk with minor issues"
        }
        return recommendations.get(risk_level, "Unknown risk level")
    
    def _verify_signature(self, plugin: Any, signature: str) -> bool:
        """Verify plugin digital signature (simplified)."""
        # In a real implementation, this would verify against a certificate authority
        return signature and len(signature) > 10
    
    async def _store_scan_results(self, plugin_id: UUID, scan_report: Dict[str, Any]):
        """Store scan results in the database."""
        try:
            scan_record = {
                "plugin_id": plugin_id,
                "scan_date": datetime.now(timezone.utc),
                "scan_results": scan_report,
                "security_score": scan_report["overall_score"],
                "is_verified": scan_report["is_verified"]
            }
            
            await self.scan_repo.create(scan_record, "security_scanner")
            
        except Exception as e:
            logger.error(f"Failed to store scan results: {e}")
    
    async def _update_plugin_security_status(self,
        plugin_id): UUID,
        is_verified: bool,
        security_score: int,
        scan_report: Dict[str, Any]
    ):
        """Update plugin security verification status."""
        try:
            update_data = {
                "is_verified": is_verified,
                "security_score": security_score,
                "verification_date": datetime.now(timezone.utc) if is_verified else None
            }
            
            # Update plugin metadata with security information
            metadata = scan_report.get("risk_assessment", {})
            if metadata:
                update_data["metadata"] = metadata
            
            await self.plugin_repo.update(plugin_id, update_data, "security_scanner")
            
        except Exception as e:
            logger.error(f"Failed to update plugin security status: {e}")