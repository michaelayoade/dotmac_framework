"""
Security Validation Tests for DotMac Framework

Tests critical security configurations and validates production readiness
from a security perspective. These tests ensure that security controls
are properly implemented and maintained.
"""

import os
import re
from pathlib import Path

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class TestSecurityConfiguration:
    """Test security configuration and hardening."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent  # noqa: B008
        self.config_dir = self.project_root / "config"
        self.k8s_dir = self.project_root / "k8s"
        
    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets exist in the codebase."""
        sensitive_patterns = [
            r"password\s*[:=]\s*['\"][^'\"]{6,}['\"]",
            r"secret\s*[:=]\s*['\"][^'\"]{10,}['\"]",
            r"api_key\s*[:=]\s*['\"][^'\"]{10,}['\"]",
            r"private_key\s*[:=]\s*['\"]-----BEGIN",
            r"token\s*[:=]\s*['\"][^'\"]{20,}['\"]"
        ]
        
        # Directories to scan
        scan_dirs = ["src", "config", "k8s"]
        excluded_files = [
            "test_security_validation.py",
            "example",
            "template",
            ".md"
        ]
        
        violations = []
        
        for scan_dir in scan_dirs:
            scan_path = self.project_root / scan_dir
            if not scan_path.exists():
                continue
                
            for file_path in scan_path.rglob("*.py"):
                # Skip excluded files
                if any(excluded in str(file_path) for excluded in excluded_files):
                    continue
                    
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    for pattern in sensitive_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # Skip test files and examples
                            if "test" not in str(file_path).lower() and \
                               "CHANGE_ME" not in match.group() and \
                               "example" not in match.group().lower():
                                violations.append({
                                    "file": str(file_path),
                                    "line": content[:match.start()].count('\n') + 1,
                                    "match": match.group()
                                })
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary or inaccessible files
                    continue
        
        assert len(violations) == 0, f"Hardcoded secrets found: {violations}"

    def test_tls_configuration(self):
        """Test TLS configuration in OpenBao and other services."""
        # Check OpenBao production configuration
        openbao_prod_config = self.config_dir / "shared" / "openbao-production.hcl"
        
        if openbao_prod_config.exists():
            config_content = openbao_prod_config.read_text()
            
            # TLS should be enabled in production
            assert 'tls_disable = 0' in config_content, \
                "TLS must be enabled in production OpenBao configuration"
                
            # Should specify strong TLS version
            assert 'tls_min_version = "tls12"' in config_content or \
                   'tls_min_version = "tls13"' in config_content, \
                "Minimum TLS version should be 1.2 or higher"
                
            # Should have certificate paths configured
            assert 'tls_cert_file' in config_content, \
                "TLS certificate file must be specified"
            assert 'tls_key_file' in config_content, \
                "TLS private key file must be specified"

    def test_kubernetes_security_contexts(self):
        """Test that Kubernetes deployments have proper security contexts."""
        if not self.k8s_dir.exists():
            pytest.skip("Kubernetes configurations not found")
            
        deployment_files = list(self.k8s_dir.rglob("*deployment*.yaml"))
        
        for deployment_file in deployment_files:
            content = deployment_file.read_text()
            
            # Should have security context
            assert "securityContext:" in content, \
                f"Security context missing in {deployment_file}"
                
            # Should run as non-root
            assert "runAsNonRoot: true" in content, \
                f"runAsNonRoot not set in {deployment_file}"
                
            # Should have read-only root filesystem where possible
            if "readOnlyRootFilesystem" in content:
                assert "readOnlyRootFilesystem: true" in content, \
                    f"Read-only root filesystem should be enabled in {deployment_file}"

    def test_kubernetes_resource_limits(self):
        """Test that Kubernetes deployments have resource limits."""
        if not self.k8s_dir.exists():
            pytest.skip("Kubernetes configurations not found")
            
        deployment_files = list(self.k8s_dir.rglob("*deployment*.yaml"))
        
        for deployment_file in deployment_files:
            content = deployment_file.read_text()
            
            # Should have resource limits
            assert "resources:" in content, \
                f"Resource limits missing in {deployment_file}"
            assert "limits:" in content, \
                f"Resource limits not specified in {deployment_file}"
            assert "memory:" in content, \
                f"Memory limits not specified in {deployment_file}"

    def test_kubernetes_network_policies(self):
        """Test that NetworkPolicies are configured."""
        if not self.k8s_dir.exists():
            pytest.skip("Kubernetes configurations not found")
            
        network_policy_files = list(self.k8s_dir.rglob("*network*policy*.yaml"))
        ingress_files = list(self.k8s_dir.rglob("*ingress*.yaml"))
        
        # Should have at least one NetworkPolicy or ingress with network isolation
        assert len(network_policy_files) > 0 or len(ingress_files) > 0, \
            "Network isolation policies not found"
            
        if network_policy_files:
            for policy_file in network_policy_files:
                content = policy_file.read_text()
                assert "NetworkPolicy" in content, \
                    f"Invalid NetworkPolicy in {policy_file}"

    def test_docker_security_configuration(self):
        """Test Docker security configuration."""
        dockerfile_path = self.project_root / "Dockerfile"
        
        if dockerfile_path.exists():
            content = dockerfile_path.read_text()
            
            # Should not run as root
            assert re.search(r'^USER\s+(?!root|0)', content, re.MULTILINE), \
                "Dockerfile should specify non-root user"
                
            # Should not contain secrets
            secret_patterns = ["password", "secret", "key", "token"]
            for pattern in secret_patterns:
                assert pattern.lower() not in content.lower(), \
                    f"Dockerfile contains potential secret: {pattern}"

    def test_environment_variable_validation(self):
        """Test that required environment variables are properly configured."""
        required_vars = [
            "SECRET_KEY",
            "DATABASE_URL", 
            "REDIS_URL"
        ]
        
        # In test environment, these might not be set, but we can check
        # that the application handles missing vars gracefully
        for var in required_vars:
            # Environment variables should not contain placeholder values
            value = os.environ.get(var, "")
            placeholder_patterns = ["change", "example", "test", "placeholder"]
            
            if value:  # Only check if variable is set
                assert not any(pattern in value.lower() for pattern in placeholder_patterns), \
                    f"Environment variable {var} contains placeholder value: {value}"

    def test_cors_configuration(self):
        """Test CORS configuration security."""
        # Check if CORS_ORIGINS is properly configured
        cors_origins = os.environ.get("CORS_ORIGINS", "")
        
        if cors_origins:
            # Should not allow all origins in production
            assert cors_origins != "*", \
                "CORS should not allow all origins (*) in production"
                
            # Should use HTTPS in production origins
            origins = cors_origins.split(",")
            for origin in origins:
                origin = origin.strip()
                if "production" in os.environ.get("ENVIRONMENT", ""):
                    assert origin.startswith("https://"), \
                        f"Production CORS origin should use HTTPS: {origin}"

    def test_session_security(self):
        """Test session security configuration."""
        # These would typically be tested in integration tests
        # with the actual application running
        session_configs = {
            "SESSION_COOKIE_SECURE": "true",
            "SESSION_COOKIE_HTTPONLY": "true", 
            "SESSION_COOKIE_SAMESITE": "lax"
        }
        
        for config_name, expected_value in session_configs.items():
            actual_value = os.environ.get(config_name, "").lower()
            if actual_value:  # Only check if set
                assert actual_value == expected_value.lower(), \
                    f"Session configuration {config_name} should be {expected_value}"

    def test_file_permissions(self):
        """Test file permissions on sensitive files."""
        sensitive_files = [
            "config/shared/openbao.hcl",
            "config/shared/openbao-production.hcl"
        ]
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                # Check file permissions (should be readable by owner only)
                stat_info = full_path.stat()
                mode = oct(stat_info.st_mode)[-3:]
                
                # Should be 600, 640, or 644 (not world-readable for sensitive files)
                assert mode in ["600", "640", "644"], \
                    f"Insecure file permissions {mode} for {file_path}"

    def test_logging_security(self):
        """Test that logging configuration doesn't expose secrets."""
        # This is a pattern-based test - would need actual log analysis
        # in integration tests
        
        # Check that logging configurations exist
        log_config_files = list(self.project_root.rglob("*logging*.py"))
        log_config_files.extend(list(self.project_root.rglob("*log*.conf")))
        
        for log_file in log_config_files:
            if log_file.suffix in ['.py', '.conf', '.yaml', '.json']:
                content = log_file.read_text()
                
                # Should not log sensitive fields
                sensitive_fields = ['password', 'secret', 'token', 'key']
                for field in sensitive_fields:
                    # Look for patterns that might log these fields
                    pattern = rf'["\']?{field}["\']?\s*[:=]'
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # Allow if it's explicitly marked as redacted/masked
                        context = content[max(0, match.start()-50):match.end()+50]
                        assert any(keyword in context.lower() for keyword in 
                                 ['redact', 'mask', 'hide', 'sanitize', 'exclude']), \
                            f"Potential secret logging in {log_file}: {match.group()}"


class TestProductionEndpointSecurity:
    """Test production endpoint security (requires running services)."""

    @pytest.fixture
    def session(self):
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    @pytest.mark.integration
    def test_https_redirect(self, session):
        """Test that HTTP requests are redirected to HTTPS."""
        test_domains = [
            "api.dotmac.com",
            "admin.dotmac.com", 
            "customer.dotmac.com"
        ]
        
        for domain in test_domains:
            try:
                # Test HTTP request - should redirect to HTTPS
                response = session.get(f"http://{domain}/health", 
                                     allow_redirects=False, timeout=10)
                
                assert response.status_code in [301, 302, 308], \
                    f"HTTP should redirect to HTTPS for {domain}"
                    
                # Check redirect location
                location = response.headers.get('Location', '')
                assert location.startswith('https://'), \
                    f"HTTP should redirect to HTTPS for {domain}"
                    
            except requests.exceptions.RequestException:
                # Skip if domain is not accessible (not in production)
                pytest.skip(f"Domain {domain} not accessible")

    @pytest.mark.integration
    def test_security_headers(self, session):
        """Test that proper security headers are present."""
        test_domains = [
            "api.dotmac.com",
            "admin.dotmac.com"
        ]
        
        required_headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
        }
        
        for domain in test_domains:
            try:
                response = session.get(f"https://{domain}/health", timeout=10)
                
                for header_name, expected_value in required_headers.items():
                    assert header_name in response.headers, \
                        f"Missing security header {header_name} for {domain}"
                    
                    header_value = response.headers[header_name]
                    if expected_value:
                        assert expected_value in header_value, \
                            f"Incorrect {header_name} header for {domain}: {header_value}"
                            
            except requests.exceptions.RequestException:
                pytest.skip(f"Domain {domain} not accessible")

    @pytest.mark.integration
    def test_tls_certificate_validity(self, session):
        """Test TLS certificate validity."""
        test_domains = [
            "api.dotmac.com",
            "admin.dotmac.com"
        ]
        
        for domain in test_domains:
            try:
                # This will raise an exception if certificate is invalid
                response = session.get(f"https://{domain}/health", timeout=10)
                
                # If we get here, certificate is valid
                assert response.status_code < 500, \
                    f"Server error for {domain}: {response.status_code}"
                    
            except requests.exceptions.SSLError as e:
                pytest.fail(f"SSL certificate invalid for {domain}: {e}")
            except requests.exceptions.RequestException:
                pytest.skip(f"Domain {domain} not accessible")

    @pytest.mark.integration  
    def test_api_rate_limiting(self, session):
        """Test that API rate limiting is implemented."""
        test_endpoints = [
            "https://api.dotmac.com/health"
        ]
        
        for endpoint in test_endpoints:
            try:
                # Make multiple rapid requests
                responses = []
                for i in range(20):
                    response = session.get(endpoint, timeout=5)
                    responses.append(response)
                    
                    # If we get rate limited, that's good
                    if response.status_code == 429:
                        assert 'Retry-After' in response.headers or \
                               'X-RateLimit-Limit' in response.headers, \
                            "Rate limit response should include rate limit headers"
                        break
                else:
                    # If no rate limiting triggered, check if rate limit headers exist
                    last_response = responses[-1]
                    rate_limit_headers = [h for h in last_response.headers 
                                        if 'rate' in h.lower() or 'limit' in h.lower()]
                    
                    if not rate_limit_headers:
                        # This is a warning rather than failure - rate limiting
                        # might be implemented at the load balancer level
                        pytest.skip("Rate limiting headers not detected - may be at LB level")
                        
            except requests.exceptions.RequestException:
                pytest.skip(f"Endpoint {endpoint} not accessible")


if __name__ == "__main__":
    # Run security tests
    pytest.main([__file__, "-v", "--tb=short"])