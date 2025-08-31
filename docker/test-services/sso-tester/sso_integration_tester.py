#!/usr/bin/env python3
"""
SSO Integration Tester
Tests complete OIDC and SAML flows with mock identity provider
"""

import asyncio
import aiohttp
import json
import time
import base64
from urllib.parse import urlencode, parse_qs, urlparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SSOTestResult:
    test_name: str
    success: bool
    duration_ms: int
    error_message: str = ""
    details: Dict[str, Any] = None

@dataclass
class OIDCFlowResult:
    authorization_successful: bool
    token_exchange_successful: bool
    userinfo_retrieval_successful: bool
    id_token_valid: bool
    access_token_valid: bool
    user_claims: Dict[str, Any] = None

@dataclass
class SAMLFlowResult:
    saml_request_successful: bool
    saml_response_received: bool
    saml_response_valid: bool
    user_attributes: Dict[str, Any] = None

class SSOIntegrationTester:
    def __init__(self, sso_provider_url: str = "http://localhost:8040"):
        self.sso_provider_url = sso_provider_url
        self.session = None
        self.test_results = []
        
        # Test configuration
        self.test_client_id = "test-client-123"
        self.test_redirect_uri = "http://localhost:3001/auth/oidc/callback"
        self.test_portals = [
            {"name": "customer", "url": "http://localhost:3001", "role": "customer"},
            {"name": "admin", "url": "http://localhost:3002", "role": "admin"},
            {"name": "technician", "url": "http://localhost:3003", "role": "technician"},
            {"name": "reseller", "url": "http://localhost:3004", "role": "reseller"}
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_all_tests(self) -> List[SSOTestResult]:
        """Run comprehensive SSO integration tests"""
        logger.info("🚀 Starting SSO Integration Tests")
        
        # Test SSO provider health
        await self.test_provider_health()
        
        # Test OIDC discovery
        await self.test_oidc_discovery()
        
        # Test OIDC authorization flow
        await self.test_oidc_authorization_flow()
        
        # Test OIDC token exchange
        await self.test_oidc_token_exchange()
        
        # Test OIDC userinfo endpoint
        await self.test_oidc_userinfo()
        
        # Test OIDC token refresh
        await self.test_oidc_token_refresh()
        
        # Test SAML SSO flow
        await self.test_saml_sso_flow()
        
        # Test cross-portal scenarios
        await self.test_cross_portal_authentication()
        
        # Test error scenarios
        await self.test_error_scenarios()
        
        # Test token validation
        await self.test_token_validation()
        
        return self.test_results
    
    async def test_provider_health(self):
        """Test that SSO provider is healthy and responding"""
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.sso_provider_url}/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    logger.info(f"✅ SSO Provider healthy: {health_data}")
                    
                    self.test_results.append(SSOTestResult(
                        test_name="sso_provider_health",
                        success=True,
                        duration_ms=int((time.time() - start_time) * 1000),
                        details=health_data
                    ))
                else:
                    raise Exception(f"Health check failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ SSO Provider health check failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="sso_provider_health",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_oidc_discovery(self):
        """Test OIDC discovery endpoint"""
        start_time = time.time()
        
        try:
            discovery_url = f"{self.sso_provider_url}/.well-known/openid_configuration"
            async with self.session.get(discovery_url) as resp:
                if resp.status == 200:
                    config = await resp.json()
                    
                    # Validate required OIDC endpoints
                    required_endpoints = [
                        'authorization_endpoint',
                        'token_endpoint',
                        'userinfo_endpoint',
                        'jwks_uri'
                    ]
                    
                    for endpoint in required_endpoints:
                        if endpoint not in config:
                            raise Exception(f"Missing required endpoint: {endpoint}")
                    
                    logger.info(f"✅ OIDC Discovery successful")
                    
                    self.test_results.append(SSOTestResult(
                        test_name="oidc_discovery",
                        success=True,
                        duration_ms=int((time.time() - start_time) * 1000),
                        details=config
                    ))
                else:
                    raise Exception(f"Discovery failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ OIDC Discovery failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="oidc_discovery",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_oidc_authorization_flow(self):
        """Test OIDC authorization code flow"""
        start_time = time.time()
        
        try:
            # Step 1: Get authorization endpoint
            auth_params = {
                'client_id': self.test_client_id,
                'redirect_uri': self.test_redirect_uri,
                'response_type': 'code',
                'scope': 'openid email profile',
                'state': 'test-state-123'
            }
            
            auth_url = f"{self.sso_provider_url}/oauth2/authorize?" + urlencode(auth_params)
            
            # Step 2: Follow authorization flow
            async with self.session.get(auth_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    if 'Mock Identity Provider' in content and 'Authorize' in content:
                        logger.info("✅ OIDC Authorization page loaded successfully")
                        
                        self.test_results.append(SSOTestResult(
                            test_name="oidc_authorization_flow",
                            success=True,
                            duration_ms=int((time.time() - start_time) * 1000),
                            details={'auth_url': auth_url, 'form_present': True}
                        ))
                    else:
                        raise Exception("Authorization page malformed")
                else:
                    raise Exception(f"Authorization failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ OIDC Authorization flow failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="oidc_authorization_flow",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_oidc_token_exchange(self):
        """Test OIDC token exchange with authorization code"""
        start_time = time.time()
        
        try:
            # First simulate authorization decision to get code
            decision_data = {
                'approve': 'true',
                'client_id': self.test_client_id,
                'redirect_uri': self.test_redirect_uri,
                'state': 'test-state-123',
                'user_id': 'admin-123'
            }
            
            # Step 1: Submit authorization decision
            async with self.session.post(
                f"{self.sso_provider_url}/oauth2/authorize/decision",
                data=decision_data,
                allow_redirects=False
            ) as resp:
                if resp.status in [302, 303]:
                    # Extract authorization code from redirect
                    location = resp.headers.get('Location', '')
                    parsed_url = urlparse(location)
                    query_params = parse_qs(parsed_url.query)
                    
                    if 'code' in query_params:
                        auth_code = query_params['code'][0]
                        logger.info(f"✅ Authorization code obtained: {auth_code[:10]}...")
                        
                        # Step 2: Exchange code for tokens
                        token_data = {
                            'grant_type': 'authorization_code',
                            'code': auth_code,
                            'redirect_uri': self.test_redirect_uri,
                            'client_id': self.test_client_id
                        }
                        
                        async with self.session.post(
                            f"{self.sso_provider_url}/oauth2/token",
                            data=token_data
                        ) as token_resp:
                            if token_resp.status == 200:
                                tokens = await token_resp.json()
                                
                                # Validate token response
                                required_tokens = ['access_token', 'id_token', 'token_type']
                                for token_type in required_tokens:
                                    if token_type not in tokens:
                                        raise Exception(f"Missing token: {token_type}")
                                
                                logger.info("✅ Token exchange successful")
                                
                                self.test_results.append(SSOTestResult(
                                    test_name="oidc_token_exchange",
                                    success=True,
                                    duration_ms=int((time.time() - start_time) * 1000),
                                    details={
                                        'tokens_received': list(tokens.keys()),
                                        'token_type': tokens.get('token_type'),
                                        'expires_in': tokens.get('expires_in')
                                    }
                                ))
                                
                                # Store access token for further tests
                                self.test_access_token = tokens['access_token']
                                
                            else:
                                error_resp = await token_resp.text()
                                raise Exception(f"Token exchange failed: {token_resp.status} - {error_resp}")
                    else:
                        raise Exception("Authorization code not found in redirect")
                else:
                    raise Exception(f"Authorization decision failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ OIDC Token exchange failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="oidc_token_exchange",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_oidc_userinfo(self):
        """Test OIDC userinfo endpoint"""
        start_time = time.time()
        
        try:
            if not hasattr(self, 'test_access_token'):
                raise Exception("No access token available for userinfo test")
            
            headers = {
                'Authorization': f'Bearer {self.test_access_token}'
            }
            
            async with self.session.get(
                f"{self.sso_provider_url}/oauth2/userinfo",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    userinfo = await resp.json()
                    
                    # Validate userinfo response
                    required_claims = ['sub', 'email']
                    for claim in required_claims:
                        if claim not in userinfo:
                            raise Exception(f"Missing required claim: {claim}")
                    
                    logger.info(f"✅ UserInfo retrieved: {userinfo.get('email')}")
                    
                    self.test_results.append(SSOTestResult(
                        test_name="oidc_userinfo",
                        success=True,
                        duration_ms=int((time.time() - start_time) * 1000),
                        details=userinfo
                    ))
                else:
                    error_resp = await resp.text()
                    raise Exception(f"UserInfo failed: {resp.status} - {error_resp}")
                    
        except Exception as e:
            logger.error(f"❌ OIDC UserInfo failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="oidc_userinfo",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_oidc_token_refresh(self):
        """Test OIDC token refresh flow"""
        start_time = time.time()
        
        try:
            # This would need a refresh token from a previous flow
            # For now, we'll test the endpoint exists and responds properly
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': 'mock_refresh_token_for_testing'
            }
            
            async with self.session.post(
                f"{self.sso_provider_url}/oauth2/token",
                data=refresh_data
            ) as resp:
                # Expect 400 for invalid refresh token
                if resp.status == 400:
                    error = await resp.json()
                    if error.get('error') == 'invalid_grant':
                        logger.info("✅ Token refresh endpoint responding correctly to invalid token")
                        
                        self.test_results.append(SSOTestResult(
                            test_name="oidc_token_refresh",
                            success=True,
                            duration_ms=int((time.time() - start_time) * 1000),
                            details={'endpoint_responding': True, 'error_handling': 'correct'}
                        ))
                    else:
                        raise Exception(f"Unexpected error: {error}")
                else:
                    raise Exception(f"Unexpected status: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ OIDC Token refresh test failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="oidc_token_refresh",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_saml_sso_flow(self):
        """Test SAML SSO flow"""
        start_time = time.time()
        
        try:
            # Create mock SAML request
            saml_request = self.create_mock_saml_request()
            
            saml_data = {
                'SAMLRequest': base64.b64encode(saml_request.encode()).decode(),
                'RelayState': 'test-relay-state'
            }
            
            async with self.session.post(
                f"{self.sso_provider_url}/saml/sso",
                data=saml_data
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    
                    # Validate SAML response form is present
                    if 'SAMLResponse' in content and 'form' in content:
                        logger.info("✅ SAML SSO flow initiated successfully")
                        
                        self.test_results.append(SSOTestResult(
                            test_name="saml_sso_flow",
                            success=True,
                            duration_ms=int((time.time() - start_time) * 1000),
                            details={'saml_response_form_present': True}
                        ))
                    else:
                        raise Exception("SAML response form not found")
                else:
                    raise Exception(f"SAML SSO failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ SAML SSO flow failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="saml_sso_flow",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_cross_portal_authentication(self):
        """Test authentication across multiple portals"""
        start_time = time.time()
        
        try:
            success_count = 0
            total_portals = len(self.test_portals)
            
            for portal in self.test_portals:
                try:
                    # Test OIDC authorization for each portal
                    auth_params = {
                        'client_id': f"{portal['name']}-client",
                        'redirect_uri': f"{portal['url']}/auth/oidc/callback",
                        'response_type': 'code',
                        'scope': 'openid email profile',
                        'state': f"{portal['name']}-state"
                    }
                    
                    auth_url = f"{self.sso_provider_url}/oauth2/authorize?" + urlencode(auth_params)
                    
                    async with self.session.get(auth_url) as resp:
                        if resp.status == 200:
                            success_count += 1
                            logger.info(f"✅ {portal['name']} portal authentication configured correctly")
                        else:
                            logger.warning(f"⚠️ {portal['name']} portal authentication failed: {resp.status}")
                            
                except Exception as portal_error:
                    logger.warning(f"⚠️ {portal['name']} portal test failed: {portal_error}")
            
            success = success_count == total_portals
            
            self.test_results.append(SSOTestResult(
                test_name="cross_portal_authentication",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    'successful_portals': success_count,
                    'total_portals': total_portals,
                    'success_rate': f"{(success_count/total_portals)*100:.1f}%"
                }
            ))
            
            if success:
                logger.info(f"✅ Cross-portal authentication: {success_count}/{total_portals} portals")
            else:
                logger.warning(f"⚠️ Cross-portal authentication: {success_count}/{total_portals} portals")
                
        except Exception as e:
            logger.error(f"❌ Cross-portal authentication test failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="cross_portal_authentication",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_error_scenarios(self):
        """Test various error scenarios"""
        start_time = time.time()
        
        error_tests = [
            {
                'name': 'invalid_client_id',
                'params': {'client_id': 'invalid', 'redirect_uri': self.test_redirect_uri, 'response_type': 'code'},
                'expected_status': 400
            },
            {
                'name': 'invalid_redirect_uri',
                'params': {'client_id': self.test_client_id, 'redirect_uri': 'http://malicious.com', 'response_type': 'code'},
                'expected_status': 400
            },
            {
                'name': 'invalid_response_type',
                'params': {'client_id': self.test_client_id, 'redirect_uri': self.test_redirect_uri, 'response_type': 'token'},
                'expected_status': 400
            }
        ]
        
        passed_tests = 0
        
        for error_test in error_tests:
            try:
                auth_url = f"{self.sso_provider_url}/oauth2/authorize?" + urlencode(error_test['params'])
                
                async with self.session.get(auth_url) as resp:
                    if resp.status == error_test['expected_status'] or (resp.status == 200 and 'error' in await resp.text()):
                        passed_tests += 1
                        logger.info(f"✅ Error scenario '{error_test['name']}' handled correctly")
                    else:
                        logger.warning(f"⚠️ Error scenario '{error_test['name']}' not handled properly")
                        
            except Exception as e:
                logger.warning(f"⚠️ Error test '{error_test['name']}' failed: {e}")
        
        success = passed_tests == len(error_tests)
        
        self.test_results.append(SSOTestResult(
            test_name="error_scenarios",
            success=success,
            duration_ms=int((time.time() - start_time) * 1000),
            details={
                'passed_tests': passed_tests,
                'total_tests': len(error_tests),
                'success_rate': f"{(passed_tests/len(error_tests))*100:.1f}%"
            }
        ))
    
    async def test_token_validation(self):
        """Test token validation and security"""
        start_time = time.time()
        
        try:
            # Test invalid token
            invalid_headers = {'Authorization': 'Bearer invalid-token-123'}
            
            async with self.session.get(
                f"{self.sso_provider_url}/oauth2/userinfo",
                headers=invalid_headers
            ) as resp:
                if resp.status == 401:
                    error = await resp.json()
                    if error.get('error') == 'invalid_token':
                        logger.info("✅ Invalid token properly rejected")
                        
                        self.test_results.append(SSOTestResult(
                            test_name="token_validation",
                            success=True,
                            duration_ms=int((time.time() - start_time) * 1000),
                            details={'invalid_token_rejected': True}
                        ))
                    else:
                        raise Exception(f"Unexpected error: {error}")
                else:
                    raise Exception(f"Invalid token not properly rejected: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ Token validation test failed: {e}")
            self.test_results.append(SSOTestResult(
                test_name="token_validation",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    def create_mock_saml_request(self) -> str:
        """Create a mock SAML authentication request"""
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <saml2p:AuthnRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
                            xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion"
                            ID="mock_request_{int(time.time())}"
                            Version="2.0"
                            IssueInstant="{time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                            Destination="{self.sso_provider_url}/saml/sso">
            <saml2:Issuer>mock-service-provider</saml2:Issuer>
        </saml2p:AuthnRequest>"""
        return saml_request
    
    def print_test_summary(self):
        """Print test results summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.success)
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"🧪 SSO Integration Test Summary")
        print(f"{'='*60}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"{'='*60}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result.success:
                    print(f"  - {result.test_name}: {result.error_message}")
        
        print(f"\n⏱️ Test Durations:")
        for result in self.test_results:
            status = "✅" if result.success else "❌"
            print(f"  {status} {result.test_name}: {result.duration_ms}ms")
    
    async def save_results(self, filename: str = "/app/results/sso_test_results.json"):
        """Save test results to file"""
        try:
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            results_data = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'sso_provider_url': self.sso_provider_url,
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for r in self.test_results if r.success),
                'success_rate': (sum(1 for r in self.test_results if r.success) / len(self.test_results)) * 100,
                'results': [asdict(result) for result in self.test_results]
            }
            
            with open(filename, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"💾 Test results saved to {filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test runner"""
    import os
    
    sso_provider_url = os.getenv('SSO_PROVIDER_URL', 'http://localhost:8040')
    
    logger.info(f"🔐 Starting SSO Integration Tests against {sso_provider_url}")
    
    async with SSOIntegrationTester(sso_provider_url) as tester:
        # Wait for provider to be ready
        await asyncio.sleep(2)
        
        # Run all tests
        results = await tester.run_all_tests()
        
        # Print summary
        tester.print_test_summary()
        
        # Save results
        await tester.save_results()
        
        # Exit with error code if any tests failed
        failed_count = sum(1 for result in results if not result.success)
        if failed_count > 0:
            exit(1)
        else:
            logger.info("🎉 All SSO integration tests passed!")
            exit(0)

if __name__ == '__main__':
    asyncio.run(main())