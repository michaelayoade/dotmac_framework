"""
Tests for Security Scanner

TESTING IMPROVEMENT: Unit tests for the security scanning system
to ensure it properly detects hardcoded secrets and security vulnerabilities.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
from datetime import datetime

from dotmac_isp.core.security.security_scanner import (
    SecurityScanner,
    SecurityScanType,
    SecurityFinding,
    SecurityScanResult,
    create_pre_commit_hook
, timezone)
from dotmac_isp.core.validation_types import ValidationSeverity, ValidationCategory


class TestSecurityScanner:
    """Test cases for SecurityScanner class."""
    
    @pytest.fixture
    def temp_project_path(self, tmp_path):
        """Create temporary project structure."""
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        
        # Create some test files
        (project_root / "test_file.py").write_text('''
secret_key = "testing123"
api_token = "secret123"
normal_var = "hello world"
password = "admin"
''')
        
        (project_root / "safe_file.py").write_text('''
import os
secret_key = os.getenv("SECRET_KEY")
normal_function = lambda x: x + 1
''')
        
        return project_root
    
    @pytest.fixture
    def scanner(self, temp_project_path):
        """Create security scanner instance."""
        return SecurityScanner(temp_project_path)
    
    def test_scanner_initialization(self, temp_project_path):
        """Test scanner initialization."""
        scanner = SecurityScanner(temp_project_path)
        
        assert scanner.project_root == temp_project_path
        assert isinstance(scanner.exclusion_patterns, list)
        assert isinstance(scanner.secret_patterns, dict)
        assert len(scanner.secret_patterns) > 0
    
    def test_scan_hardcoded_secrets_detects_vulnerabilities(self, scanner):
        """Test that hardcoded secrets scan detects known vulnerabilities."""
        # Run the scan
        result = scanner.scan_hardcoded_secrets()
        
        # Assertions
        assert isinstance(result, SecurityScanResult)
        assert result.scan_type == SecurityScanType.HARDCODED_SECRETS
        assert result.scan_successful is True
        assert result.total_files_scanned > 0
        
        # Should find some critical findings
        assert len(result.critical_findings) > 0
        
        # Check for specific patterns
        critical_messages = [f.message for f in result.critical_findings]
        assert any("testing123" in msg or "secret123" in msg for msg in critical_messages)
    
    def test_scan_hardcoded_secrets_file_filtering(self, scanner):
        """Test that scanner respects file filtering."""
        # Create a file that should be excluded
        (scanner.project_root / "__pycache__").mkdir()
        (scanner.project_root / "__pycache__" / "cached.py").write_text('secret = "testing123"')
        
        # Run scan
        result = scanner.scan_hardcoded_secrets()
        
        # __pycache__ files should be excluded
        scanned_files = [f.file_path for f in result.findings]
        assert not any("__pycache__" in path for path in scanned_files)
    
    def test_scan_specific_files(self, scanner):
        """Test scanning specific files."""
        # Create a specific file to scan
        test_file = scanner.project_root / "specific_test.py"
        test_file.write_text('secret_key = "testing123"')
        
        # Scan only this file
        result = scanner.scan_hardcoded_secrets([test_file])
        
        # Should scan only 1 file
        assert result.total_files_scanned == 1
        assert len(result.findings) > 0
    
    def test_scan_dependencies_basic(self, scanner):
        """Test basic dependency scanning."""
        # Create a mock requirements file
        req_file = scanner.project_root / "requirements.txt"
        req_file.write_text('''
django==2.2.0
flask==0.12.0
pyyaml==3.13
requests==2.25.0
''')
        
        # Run dependency scan
        result = scanner.scan_dependencies()
        
        # Should detect vulnerable dependencies
        assert isinstance(result, SecurityScanResult)
        assert result.scan_type == SecurityScanType.DEPENDENCY_VULNERABILITIES
        assert result.total_files_scanned >= 1
    
    def test_scan_configuration_security(self, scanner):
        """Test configuration security scanning."""
        # Create config files with security issues
        config_file = scanner.project_root / "config.yaml"
        config_file.write_text('''
debug: true
ssl_verify: false
password: admin
''')
        
        # Run config scan
        result = scanner.scan_configuration_security()
        
        # Should find configuration issues
        assert isinstance(result, SecurityScanResult)
        assert result.scan_type == SecurityScanType.CONFIGURATION_SECURITY
        assert len(result.findings) > 0
    
    def test_scan_file_permissions(self, scanner, tmp_path):
        """Test file permissions scanning."""
        # Create a file with problematic permissions
        test_file = scanner.project_root / "test_script.sh"
        test_file.write_text("#!/bin/bash\necho 'test'")
        test_file.chmod(0o777)  # World-writable
        
        # Run permissions scan
        result = scanner.scan_file_permissions()
        
        # Should detect permission issues
        assert isinstance(result, SecurityScanResult)
        assert result.scan_type == SecurityScanType.FILE_PERMISSIONS
    
    def test_scan_all_comprehensive(self, scanner):
        """Test running all scans."""
        results = scanner.scan_all()
        
        # Should run all scan types
        expected_scan_types = [
            SecurityScanType.HARDCODED_SECRETS,
            SecurityScanType.DEPENDENCY_VULNERABILITIES,
            SecurityScanType.CONFIGURATION_SECURITY,
            SecurityScanType.FILE_PERMISSIONS
        ]
        
        for scan_type in expected_scan_types:
            assert scan_type in results
            assert isinstance(results[scan_type], SecurityScanResult)
    
    def test_generate_security_report(self, scanner):
        """Test security report generation."""
        # Run scans first
        scanner.scan_all()
        
        # Generate report
        report = scanner.generate_security_report()
        
        # Verify report structure
        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "summary" in report
        assert "scan_results" in report
        assert "top_findings" in report
        assert "recommendations" in report
        
        # Verify summary data
        summary = report["summary"]
        assert "total_scans" in summary
        assert "total_findings" in summary
        assert "critical_findings" in summary
    
    def test_security_finding_creation(self):
        """Test SecurityFinding object creation."""
        finding = SecurityFinding(
            scan_type=SecurityScanType.HARDCODED_SECRETS,
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.SECURITY,
            file_path="test.py",
            line_number=10,
            rule_id="hardcoded_secret",
            message="Hardcoded secret detected",
            description="Test description",
            remediation="Use environment variables"
        )
        
        assert finding.scan_type == SecurityScanType.HARDCODED_SECRETS
        assert finding.severity == ValidationSeverity.CRITICAL
        assert finding.line_number == 10
    
    def test_security_scan_result_properties(self):
        """Test SecurityScanResult properties."""
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)
        
        # Create sample findings
        critical_finding = SecurityFinding(
            scan_type=SecurityScanType.HARDCODED_SECRETS,
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.SECURITY,
            file_path="test.py",
            line_number=1,
            rule_id="test",
            message="Critical issue",
            description="Test",
            remediation="Fix it"
        )
        
        high_finding = SecurityFinding(
            scan_type=SecurityScanType.HARDCODED_SECRETS,
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.SECURITY,
            file_path="test.py", 
            line_number=2,
            rule_id="test2",
            message="High issue",
            description="Test",
            remediation="Fix it"
        )
        
        result = SecurityScanResult(
            scan_type=SecurityScanType.HARDCODED_SECRETS,
            started_at=start_time,
            completed_at=end_time,
            total_files_scanned=1,
            findings=[critical_finding, high_finding]
        )
        
        # Test properties
        assert len(result.critical_findings) == 1
        assert len(result.high_findings) == 1
        assert result.duration_seconds >= 0
    
    @patch('builtins.open', new_callable=mock_open)
    def test_scan_file_for_secrets_patterns(self, mock_file, scanner):
        """Test scanning individual file for secret patterns."""
        # Mock file content with secrets
        file_content = '''
radius_secret = "testing123"
api_key = "secret123" 
jwt_token = "jwt_secret_token"
password = "admin"
safe_variable = "hello_world"
'''
        mock_file.return_value.read.return_value = file_content
        
        # Create a mock file path
        file_path = Path("test_file.py")
        
        # Test the internal method
        findings = scanner._scan_file_for_secrets(file_path)
        
        # Should find multiple secret patterns
        assert len(findings) > 0
        
        # Check for critical findings
        critical_findings = [f for f in findings if f.severity == ValidationSeverity.CRITICAL]
        assert len(critical_findings) > 0
    
    def test_should_scan_file_exclusions(self, scanner):
        """Test file exclusion logic."""
        # Files that should be excluded
        excluded_files = [
            Path(".git/config"),
            Path("__pycache__/test.py"),
            Path("node_modules/package/index.js"),
            Path("build/output.py"),
            Path("test.pyc")
        ]
        
        for file_path in excluded_files:
            # Mock the relative_to method
            with patch.object(Path, 'relative_to', return_value=file_path):
                assert scanner._should_scan_file(file_path) is False
        
        # Files that should be included
        included_files = [
            Path("src/main.py"),
            Path("lib/utils.py"),
            Path("config.yaml")
        ]
        
        for file_path in included_files:
            with patch.object(Path, 'relative_to', return_value=file_path):
                assert scanner._should_scan_file(file_path) is True


class TestCreatePreCommitHook:
    """Test cases for pre-commit hook creation."""
    
    @pytest.fixture
    def temp_git_repo(self, tmp_path):
        """Create temporary git repository structure."""
        git_repo = tmp_path / "git_repo"
        git_repo.mkdir()
        
        # Create .git/hooks directory
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        
        return git_repo
    
    def test_create_pre_commit_hook_success(self, temp_git_repo):
        """Test successful pre-commit hook creation."""
        result = create_pre_commit_hook(temp_git_repo)
        
        assert result is True
        
        # Check that hook file was created
        hook_file = temp_git_repo / ".git" / "hooks" / "pre-commit"
        assert hook_file.exists()
        
        # Check that hook is executable
        assert hook_file.stat().st_mode & 0o111  # Has execute permissions
        
        # Check hook content
        content = hook_file.read_text()
        assert "security scanning hook" in content.lower()
        assert "SecurityScanner" in content
    
    def test_create_pre_commit_hook_no_git_repo(self, tmp_path):
        """Test hook creation in non-git repository."""
        non_git_dir = tmp_path / "not_git"
        non_git_dir.mkdir()
        
        result = create_pre_commit_hook(non_git_dir)
        
        assert result is False
    
    def test_pre_commit_hook_content_validity(self, temp_git_repo):
        """Test that generated pre-commit hook has valid Python syntax."""
        create_pre_commit_hook(temp_git_repo)
        
        hook_file = temp_git_repo / ".git" / "hooks" / "pre-commit"
        content = hook_file.read_text()
        
        # Should be valid Python code
        try:
            compile(content, "pre-commit", "exec")
        except SyntaxError:
            pytest.fail("Generated pre-commit hook has invalid Python syntax")
        
        # Should contain expected functionality
        assert "SecurityScanner" in content
        assert "scan_hardcoded_secrets" in content
        assert "critical_findings" in content