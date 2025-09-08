"""
OAuth Provider Flow Testing
Implementation of AUTH-002: OAuth2/OIDC integration testing for all providers.
"""

import pytest
import json
from unittest.mock import Mock, patch
import httpx
import hashlib
import base64

from dotmac.platform.auth.oauth_providers import (
    GoogleOAuthProvider, 
    MicrosoftOAuthProvider,
    OAuthResult,
    OAuthError
)


class TestOAuthProvidersIntegration:
    """Integration tests for OAuth provider flows"""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for OAuth requests"""
        return Mock(spec=httpx.AsyncClient)
    
    @pytest.fixture
    def oauth_config(self):
        """OAuth configuration for testing"""
        return {
            'google': {
                'client_id': 'test_google_client_id',
                'client_secret': 'test_google_client_secret',
                'redirect_uri': 'http://localhost:8000/auth/google/callback'
            },
            'microsoft': {
                'client_id': 'test_microsoft_client_id', 
                'client_secret': 'test_microsoft_client_secret',
                'redirect_uri': 'http://localhost:8000/auth/microsoft/callback'
            }
        }
    
    # Google OAuth Flow Tests
    
    @pytest.mark.asyncio
    async def test_google_oauth_authorization_url_generation(self, oauth_config):
        """Test Google OAuth authorization URL generation"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Generate authorization URL with state and PKCE
        auth_url, state, code_verifier = provider.get_authorization_url(
            scopes=['openid', 'email', 'profile']
        )
        
        assert auth_url.startswith('https://accounts.google.com/o/oauth2/v2/auth')
        assert 'client_id=test_google_client_id' in auth_url
        assert 'redirect_uri=' in auth_url
        assert 'scope=openid%20email%20profile' in auth_url
        assert f'state={state}' in auth_url
        assert 'code_challenge=' in auth_url  # PKCE parameter
        assert 'code_challenge_method=S256' in auth_url
        
        # State should be cryptographically random
        assert len(state) >= 32
        
        # Code verifier should be base64url encoded
        assert len(code_verifier) >= 43
    
    @pytest.mark.asyncio 
    async def test_google_oauth_token_exchange_success(self, oauth_config):
        """Test successful Google OAuth token exchange"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Mock successful token response
        mock_token_response = {
            'access_token': 'ya29.test_access_token',
            'id_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test_payload.signature',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        # Mock user info response
        mock_userinfo_response = {
            'sub': '1234567890',
            'email': 'user@gmail.com', 
            'email_verified': True,
            'name': 'Test User',
            'picture': 'https://lh3.googleusercontent.com/a/test'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock token exchange request
            mock_instance.post.return_value.json.return_value = mock_token_response
            mock_instance.post.return_value.status_code = 200
            
            # Mock userinfo request
            mock_instance.get.return_value.json.return_value = mock_userinfo_response
            mock_instance.get.return_value.status_code = 200
            
            # Execute token exchange
            result = await provider.exchange_code(
                code='test_auth_code',
                state='test_state',
                code_verifier='test_code_verifier'
            )
            
            assert isinstance(result, OAuthResult)
            assert result.provider == 'google'
            assert result.access_token == 'ya29.test_access_token'
            assert result.refresh_token == 'test_refresh_token'
            assert result.user_info['email'] == 'user@gmail.com'
            assert result.user_info['sub'] == '1234567890'
            assert result.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_google_oauth_invalid_code_handling(self, oauth_config):
        """Test Google OAuth handling of invalid authorization codes"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Mock error response for invalid code
        mock_error_response = {
            'error': 'invalid_grant',
            'error_description': 'Bad Request'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.post.return_value.json.return_value = mock_error_response
            mock_instance.post.return_value.status_code = 400
            
            with pytest.raises(OAuthError) as exc_info:
                await provider.exchange_code(
                    code='invalid_code',
                    state='test_state', 
                    code_verifier='test_verifier'
                )
            
            assert 'invalid_grant' in str(exc_info.value)
    
    # Microsoft OAuth Flow Tests
    
    @pytest.mark.asyncio
    async def test_microsoft_oauth_authorization_url_generation(self, oauth_config):
        """Test Microsoft OAuth authorization URL generation"""
        provider = MicrosoftOAuthProvider(oauth_config['microsoft'])
        
        auth_url, state, code_verifier = provider.get_authorization_url(
            scopes=['openid', 'email', 'profile'],
            tenant='common'
        )
        
        assert auth_url.startswith('https://login.microsoftonline.com/common/oauth2/v2.0/authorize')
        assert 'client_id=test_microsoft_client_id' in auth_url
        assert 'scope=openid%20email%20profile' in auth_url
        assert f'state={state}' in auth_url
        assert 'code_challenge=' in auth_url
    
    @pytest.mark.asyncio
    async def test_microsoft_oauth_token_exchange_success(self, oauth_config):
        """Test successful Microsoft OAuth token exchange"""
        provider = MicrosoftOAuthProvider(oauth_config['microsoft'])
        
        mock_token_response = {
            'access_token': 'EwAoA8l6BAAHU_token',
            'id_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.signature',
            'refresh_token': 'M.R3_BAY.test_refresh',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        mock_userinfo_response = {
            'sub': '9f4880d8-80ba-4c40-97bc-f75323515cbf',
            'email': 'user@outlook.com',
            'name': 'Test User',
            'preferred_username': 'user@outlook.com'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            
            mock_instance.post.return_value.json.return_value = mock_token_response
            mock_instance.post.return_value.status_code = 200
            
            mock_instance.get.return_value.json.return_value = mock_userinfo_response
            mock_instance.get.return_value.status_code = 200
            
            result = await provider.exchange_code(
                code='test_auth_code',
                state='test_state',
                code_verifier='test_verifier'
            )
            
            assert result.provider == 'microsoft'
            assert result.user_info['email'] == 'user@outlook.com'
    
    # State Parameter Security Tests
    
    @pytest.mark.asyncio
    async def test_oauth_state_parameter_validation(self, oauth_config):
        """Test OAuth state parameter validation for CSRF protection"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Generate authorization URL and capture state
        auth_url, original_state, code_verifier = provider.get_authorization_url()
        
        # Mock successful token response
        mock_response = {
            'access_token': 'test_token',
            'id_token': 'test_id_token'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.post.return_value.json.return_value = mock_response
            mock_instance.post.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = {'sub': '123', 'email': 'test@test.com'}
            mock_instance.get.return_value.status_code = 200
            
            # Test with correct state
            result = await provider.exchange_code(
                code='test_code',
                state=original_state,
                code_verifier=code_verifier
            )
            assert result is not None
            
            # Test with incorrect state (should raise error)
            with pytest.raises(OAuthError) as exc_info:
                await provider.exchange_code(
                    code='test_code', 
                    state='wrong_state',
                    code_verifier=code_verifier
                )
            
            assert 'state' in str(exc_info.value).lower()
    
    # PKCE Flow Implementation Tests
    
    def test_pkce_code_challenge_generation(self, oauth_config):
        """Test PKCE code challenge generation"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Generate multiple code verifier/challenge pairs
        pairs = []
        for _ in range(10):
            code_verifier = provider._generate_code_verifier()
            code_challenge = provider._generate_code_challenge(code_verifier)
            pairs.append((code_verifier, code_challenge))
        
        # All code verifiers should be unique
        verifiers = [pair[0] for pair in pairs]
        assert len(set(verifiers)) == 10
        
        # All code challenges should be unique
        challenges = [pair[1] for pair in pairs]
        assert len(set(challenges)) == 10
        
        # Verify code challenge generation is correct (SHA256 + base64url)
        code_verifier, code_challenge = pairs[0]
        
        # Manual verification
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        assert code_challenge == expected_challenge
    
    # Scope Validation Tests
    
    @pytest.mark.asyncio
    async def test_oauth_scope_validation(self, oauth_config):
        """Test OAuth scope parameter validation"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        # Test valid scopes
        valid_scopes = ['openid', 'email', 'profile']
        auth_url, _, _ = provider.get_authorization_url(scopes=valid_scopes)
        assert 'scope=openid%20email%20profile' in auth_url
        
        # Test empty scopes (should use default)
        auth_url_default, _, _ = provider.get_authorization_url(scopes=[])
        assert 'scope=' in auth_url_default
        
        # Test custom scopes
        custom_scopes = ['https://www.googleapis.com/auth/drive.readonly']
        auth_url_custom, _, _ = provider.get_authorization_url(scopes=custom_scopes)
        assert 'googleapis.com%2Fauth%2Fdrive.readonly' in auth_url_custom
    
    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_oauth_network_error_handling(self, oauth_config):
        """Test OAuth provider behavior during network errors"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            
            # Simulate network timeout
            mock_instance.post.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(OAuthError) as exc_info:
                await provider.exchange_code(
                    code='test_code',
                    state='test_state',
                    code_verifier='test_verifier'
                )
            
            assert 'network' in str(exc_info.value).lower() or 'timeout' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_oauth_malformed_response_handling(self, oauth_config):
        """Test OAuth provider handling of malformed responses"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            
            # Test malformed JSON response
            mock_instance.post.return_value.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
            mock_instance.post.return_value.status_code = 200
            
            with pytest.raises(OAuthError):
                await provider.exchange_code(
                    code='test_code',
                    state='test_state', 
                    code_verifier='test_verifier'
                )
    
    # Token Refresh Tests
    
    @pytest.mark.asyncio
    async def test_oauth_token_refresh(self, oauth_config):
        """Test OAuth token refresh functionality"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        mock_refresh_response = {
            'access_token': 'new_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.post.return_value.json.return_value = mock_refresh_response
            mock_instance.post.return_value.status_code = 200
            
            # Test token refresh
            new_result = await provider.refresh_token('existing_refresh_token')
            
            assert new_result.access_token == 'new_access_token'
            assert new_result.provider == 'google'
    
    @pytest.mark.asyncio
    async def test_oauth_expired_refresh_token(self, oauth_config):
        """Test handling of expired refresh tokens"""
        provider = GoogleOAuthProvider(oauth_config['google'])
        
        mock_error_response = {
            'error': 'invalid_grant',
            'error_description': 'Token has been expired or revoked.'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.post.return_value.json.return_value = mock_error_response
            mock_instance.post.return_value.status_code = 400
            
            with pytest.raises(OAuthError) as exc_info:
                await provider.refresh_token('expired_refresh_token')
            
            assert 'expired' in str(exc_info.value).lower() or 'revoked' in str(exc_info.value).lower()