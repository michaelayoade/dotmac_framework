"""
OAuth Providers Integration

Comprehensive OAuth 2.0/OpenID Connect support with multiple provider integration,
PKCE support, token management, and social login capabilities.
"""

import base64
import hashlib
import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, HttpUrl
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

from .exceptions import (
    AuthenticationError,
    ConfigurationError,
)

Base = declarative_base()


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    FACEBOOK = "facebook"
    APPLE = "apple"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    DISCORD = "discord"
    SLACK = "slack"
    GENERIC = "generic"


class OAuthGrantType(str, Enum):
    """OAuth grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"


class OAuthTokenType(str, Enum):
    """OAuth token types."""

    BEARER = "Bearer"
    MAC = "MAC"


class OAuthProviderConfig(Base):
    """Database model for OAuth provider configurations."""

    __tablename__ = "oauth_provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider = Column(String(20), nullable=False, unique=True)

    # OAuth endpoints
    authorization_url = Column(String(500), nullable=False)
    token_url = Column(String(500), nullable=False)
    userinfo_url = Column(String(500), nullable=True)
    jwks_url = Column(String(500), nullable=True)

    # Client configuration
    client_id = Column(String(500), nullable=False)
    client_secret = Column(Text, nullable=False)  # Encrypted in production

    # OAuth configuration
    scopes = Column(JSON, default=list)  # Default scopes to request
    response_type = Column(String(50), default="code")
    grant_type = Column(String(50), default="authorization_code")

    # Provider-specific settings
    additional_params = Column(JSON, default=dict)  # Additional parameters
    claim_mappings = Column(JSON, default=dict)  # How to map provider claims to our user fields

    # Security settings
    use_pkce = Column(Boolean, default=True)
    verify_ssl = Column(Boolean, default=True)

    # Status
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class OAuthSession(Base):
    """Database model for OAuth sessions."""

    __tablename__ = "oauth_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(64), nullable=False, unique=True, index=True)
    provider = Column(String(20), nullable=False)

    # OAuth flow data
    state = Column(String(128), nullable=False)
    code_verifier = Column(String(128), nullable=True)  # For PKCE
    code_challenge = Column(String(128), nullable=True)  # For PKCE
    redirect_uri = Column(String(500), nullable=False)
    scopes = Column(JSON, default=list)

    # User association
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Session metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    additional_data = Column(JSON, default=dict)


class OAuthToken(Base):
    """Database model for stored OAuth tokens."""

    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(20), nullable=False)

    # Token data
    access_token = Column(Text, nullable=False)  # Encrypted in production
    refresh_token = Column(Text, nullable=True)  # Encrypted in production
    token_type = Column(String(20), default="Bearer")
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Token metadata
    scopes = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Provider-specific data
    provider_data = Column(JSON, default=dict)


class OAuthUserProfile(Base):
    """Database model for OAuth user profiles."""

    __tablename__ = "oauth_user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(20), nullable=False)

    # Provider user information
    provider_user_id = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    given_name = Column(String(255), nullable=True)
    family_name = Column(String(255), nullable=True)
    picture = Column(String(500), nullable=True)
    locale = Column(String(10), nullable=True)

    # Profile metadata
    raw_profile = Column(JSON, default=dict)  # Full provider profile
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)


class OAuthAuthorizationRequest(BaseModel):
    """Request model for OAuth authorization."""

    provider: OAuthProvider
    redirect_uri: HttpUrl
    scopes: list[str] | None = None
    state: str | None = None
    additional_params: dict[str, Any] | None = None


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback."""

    session_id: str
    code: str
    state: str | None = None
    error: str | None = None
    error_description: str | None = None


class OAuthTokenResponse(BaseModel):
    """Response model for OAuth token exchange."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


class OAuthUserInfo(BaseModel):
    """OAuth user information."""

    provider: str
    provider_user_id: str
    email: str | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None
    raw_profile: dict[str, Any] = {}


class OAuthServiceConfig(BaseModel):
    """Configuration for OAuth Service."""

    session_expiry_minutes: int = 10
    token_refresh_threshold_minutes: int = 5
    max_sessions_per_user: int = 5
    enable_automatic_user_creation: bool = False
    default_scopes: dict[str, list[str]] = {
        "google": ["openid", "email", "profile"],
        "microsoft": ["openid", "email", "profile"],
        "github": ["user:email"],
        "facebook": ["email", "public_profile"],
    }


# Provider-specific configurations
PROVIDER_CONFIGS = {
    OAuthProvider.GOOGLE: {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
        "scopes": ["openid", "email", "profile"],
        "claim_mappings": {
            "sub": "provider_user_id",
            "email": "email",
            "name": "name",
            "given_name": "given_name",
            "family_name": "family_name",
            "picture": "picture",
            "locale": "locale",
        },
    },
    OAuthProvider.MICROSOFT: {
        "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["openid", "email", "profile"],
        "claim_mappings": {
            "id": "provider_user_id",
            "userPrincipalName": "email",
            "displayName": "name",
            "givenName": "given_name",
            "surname": "family_name",
        },
    },
    OAuthProvider.GITHUB: {
        "authorization_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["user:email"],
        "claim_mappings": {
            "id": "provider_user_id",
            "email": "email",
            "name": "name",
            "login": "given_name",
            "avatar_url": "picture",
        },
    },
    OAuthProvider.FACEBOOK: {
        "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "userinfo_url": "https://graph.facebook.com/v18.0/me",
        "scopes": ["email", "public_profile"],
        "additional_params": {"fields": "id,name,email,first_name,last_name,picture"},
        "claim_mappings": {
            "id": "provider_user_id",
            "email": "email",
            "name": "name",
            "first_name": "given_name",
            "last_name": "family_name",
            "picture.data.url": "picture",
        },
    },
}


class OAuthService:
    """
    Comprehensive OAuth 2.0/OpenID Connect Service.

    Features:
    - Multiple provider support (Google, Microsoft, GitHub, etc.)
    - PKCE (Proof Key for Code Exchange) support
    - Token refresh automation
    - Provider-specific claim mapping
    - Social login integration
    - Secure token storage
    - User profile management
    """

    def __init__(
        self,
        database_session,
        config: OAuthServiceConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = database_session
        self.config = config or OAuthServiceConfig()
        self.http_client = http_client or httpx.AsyncClient()

    async def get_authorization_url(self, request: OAuthAuthorizationRequest) -> dict[str, Any]:
        """
        Generate OAuth authorization URL for a provider.

        Returns authorization URL and session information.
        """
        # Get provider configuration
        provider_config = await self._get_provider_config(request.provider)
        if not provider_config:
            raise ConfigurationError(f"Provider {request.provider} not configured")

        if not provider_config.is_enabled:
            raise ConfigurationError(f"Provider {request.provider} is disabled")

        # Generate session ID
        session_id = secrets.token_urlsafe(32)

        # Generate state parameter
        state = request.state or secrets.token_urlsafe(32)

        # Prepare scopes
        scopes = (
            request.scopes
            or provider_config.scopes
            or self.config.default_scopes.get(request.provider.value, [])
        )

        # Generate PKCE parameters
        code_verifier = None
        code_challenge = None
        if provider_config.use_pkce:
            code_verifier = secrets.token_urlsafe(96)
            code_challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )

        # Create OAuth session
        oauth_session = OAuthSession(
            session_id=session_id,
            provider=request.provider.value,
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_uri=str(request.redirect_uri),
            scopes=scopes,
            expires_at=datetime.now(UTC) + timedelta(minutes=self.config.session_expiry_minutes),
            additional_data=request.additional_params or {},
        )

        self.db.add(oauth_session)
        await self.db.commit()

        # Build authorization URL parameters
        auth_params = {
            "client_id": provider_config.client_id,
            "redirect_uri": str(request.redirect_uri),
            "response_type": provider_config.response_type,
            "scope": " ".join(scopes),
            "state": state,
        }

        # Add PKCE parameters
        if provider_config.use_pkce:
            auth_params.update(
                {
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                }
            )

        # Add provider-specific parameters
        if provider_config.additional_params:
            auth_params.update(provider_config.additional_params)

        if request.additional_params:
            auth_params.update(request.additional_params)

        # Build authorization URL
        auth_url = f"{provider_config.authorization_url}?{urllib.parse.urlencode(auth_params)}"

        return {
            "authorization_url": auth_url,
            "session_id": session_id,
            "state": state,
            "expires_in": self.config.session_expiry_minutes * 60,
        }

    async def handle_callback(self, request: OAuthCallbackRequest) -> dict[str, Any]:
        """
        Handle OAuth callback and exchange authorization code for tokens.

        Returns user information and tokens.
        """
        # Handle OAuth error
        if request.error:
            error_msg = request.error_description or request.error
            raise AuthenticationError(f"OAuth error: {error_msg}")

        # Get OAuth session
        oauth_session = await self._get_oauth_session(request.session_id)
        if not oauth_session:
            raise AuthenticationError("Invalid or expired OAuth session")

        # Verify state parameter
        if request.state and request.state != oauth_session.state:
            raise AuthenticationError("Invalid state parameter")

        # Mark session as used
        oauth_session.used_at = datetime.now(UTC)

        # Get provider configuration
        provider_config = await self._get_provider_config(OAuthProvider(oauth_session.provider))
        if not provider_config:
            raise ConfigurationError(f"Provider {oauth_session.provider} not configured")

        # Exchange authorization code for tokens
        token_data = await self._exchange_code_for_tokens(
            provider_config, oauth_session, request.code
        )

        # Get user information
        user_info = await self._get_user_info(provider_config, token_data)

        # Store or update user profile
        user_profile = await self._store_user_profile(oauth_session.provider, user_info)

        # Store tokens if we have a user
        if oauth_session.user_id or user_profile:
            user_id = oauth_session.user_id or user_profile.user_id
            await self._store_tokens(user_id, oauth_session.provider, token_data)

        await self.db.commit()

        return {
            "success": True,
            "provider": oauth_session.provider,
            "user_info": {
                "provider_user_id": user_info.provider_user_id,
                "email": user_info.email,
                "name": user_info.name,
                "given_name": user_info.given_name,
                "family_name": user_info.family_name,
                "picture": user_info.picture,
                "locale": user_info.locale,
            },
            "tokens": {
                "access_token": token_data.access_token,
                "token_type": token_data.token_type,
                "expires_in": token_data.expires_in,
                "scope": token_data.scope,
            },
            "session_id": request.session_id,
        }

    async def refresh_token(
        self, user_id: str, provider: OAuthProvider
    ) -> dict[str, Any] | None:
        """
        Refresh OAuth tokens for a user and provider.

        Returns refreshed token information or None if no refresh token available.
        """
        # Get stored tokens
        stored_token = await self._get_stored_tokens(user_id, provider)
        if not stored_token or not stored_token.refresh_token:
            return None

        # Get provider configuration
        provider_config = await self._get_provider_config(provider)
        if not provider_config:
            raise ConfigurationError(f"Provider {provider} not configured")

        # Prepare token refresh request
        token_params = {
            "grant_type": "refresh_token",
            "refresh_token": stored_token.refresh_token,
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
        }

        # Make token refresh request
        try:
            response = await self.http_client.post(
                provider_config.token_url,
                data=token_params,
                headers={"Accept": "application/json"},
                verify=provider_config.verify_ssl,
            )
            response.raise_for_status()

            token_data_dict = response.json()
            token_data = OAuthTokenResponse(**token_data_dict)

        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {e!s}") from e

        # Update stored tokens
        stored_token.access_token = token_data.access_token
        stored_token.token_type = token_data.token_type
        if token_data.refresh_token:
            stored_token.refresh_token = token_data.refresh_token
        if token_data.expires_in:
            stored_token.expires_at = datetime.now(UTC) + timedelta(seconds=token_data.expires_in)
        if token_data.scope:
            stored_token.scopes = token_data.scope.split(" ")
        stored_token.updated_at = datetime.now(UTC)

        await self.db.commit()

        return {
            "access_token": token_data.access_token,
            "token_type": token_data.token_type,
            "expires_in": token_data.expires_in,
            "scope": token_data.scope,
        }

    async def get_user_tokens(
        self, user_id: str, provider: OAuthProvider | None = None
    ) -> list[dict[str, Any]]:
        """Get stored OAuth tokens for a user."""
        query = self.db.query(OAuthToken).filter(OAuthToken.user_id == user_id)

        if provider:
            query = query.filter(OAuthToken.provider == provider.value)

        tokens = query.all()

        result = []
        for token in tokens:
            # Check if token needs refresh
            needs_refresh = False
            if token.expires_at:
                time_until_expiry = token.expires_at - datetime.now(UTC)
                if time_until_expiry < timedelta(
                    minutes=self.config.token_refresh_threshold_minutes
                ):
                    needs_refresh = True

            result.append(
                {
                    "provider": token.provider,
                    "token_type": token.token_type,
                    "scopes": token.scopes,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "needs_refresh": needs_refresh,
                    "created_at": token.created_at.isoformat(),
                    "updated_at": token.updated_at.isoformat(),
                }
            )

        return result

    async def revoke_tokens(self, user_id: str, provider: OAuthProvider) -> bool:
        """Revoke and remove OAuth tokens for a user and provider."""
        stored_token = await self._get_stored_tokens(user_id, provider)
        if not stored_token:
            return False

        # Try to revoke tokens with provider (best effort)
        provider_config = await self._get_provider_config(provider)
        if provider_config:
            await self._revoke_tokens_with_provider(provider_config, stored_token)

        # Remove from database
        await self.db.delete(stored_token)
        await self.db.commit()

        return True

    async def get_user_profiles(
        self, user_id: str, provider: OAuthProvider | None = None
    ) -> list[dict[str, Any]]:
        """Get OAuth user profiles for a user."""
        query = self.db.query(OAuthUserProfile).filter(OAuthUserProfile.user_id == user_id)

        if provider:
            query = query.filter(OAuthUserProfile.provider == provider.value)

        profiles = query.all()

        return [
            {
                "provider": profile.provider,
                "provider_user_id": profile.provider_user_id,
                "email": profile.email,
                "name": profile.name,
                "given_name": profile.given_name,
                "family_name": profile.family_name,
                "picture": profile.picture,
                "locale": profile.locale,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
                "last_login": profile.last_login.isoformat() if profile.last_login else None,
            }
            for profile in profiles
        ]

    # Helper methods

    async def _get_provider_config(self, provider: OAuthProvider) -> OAuthProviderConfig | None:
        """Get provider configuration."""
        return (
            self.db.query(OAuthProviderConfig)
            .filter(OAuthProviderConfig.provider == provider.value)
            .first()
        )

    async def _get_oauth_session(self, session_id: str) -> OAuthSession | None:
        """Get OAuth session."""
        return (
            self.db.query(OAuthSession)
            .filter(
                OAuthSession.session_id == session_id,
                OAuthSession.expires_at > datetime.now(UTC),
                OAuthSession.used_at.is_(None),
            )
            .first()
        )

    async def _get_stored_tokens(
        self, user_id: str, provider: OAuthProvider
    ) -> OAuthToken | None:
        """Get stored OAuth tokens."""
        return (
            self.db.query(OAuthToken)
            .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider.value)
            .first()
        )

    async def _exchange_code_for_tokens(
        self, provider_config: OAuthProviderConfig, oauth_session: OAuthSession, code: str
    ) -> OAuthTokenResponse:
        """Exchange authorization code for tokens."""
        token_params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_session.redirect_uri,
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
        }

        # Add PKCE code verifier
        if oauth_session.code_verifier:
            token_params["code_verifier"] = oauth_session.code_verifier

        try:
            response = await self.http_client.post(
                provider_config.token_url,
                data=token_params,
                headers={"Accept": "application/json"},
                verify=provider_config.verify_ssl,
            )
            response.raise_for_status()

            token_data_dict = response.json()
            return OAuthTokenResponse(**token_data_dict)

        except Exception as e:
            raise AuthenticationError(f"Token exchange failed: {e!s}") from e

    async def _get_user_info(
        self, provider_config: OAuthProviderConfig, token_data: OAuthTokenResponse
    ) -> OAuthUserInfo:
        """Get user information from provider."""
        if not provider_config.userinfo_url:
            raise ConfigurationError("Provider does not support userinfo endpoint")

        try:
            headers = {
                "Authorization": f"{token_data.token_type} {token_data.access_token}",
                "Accept": "application/json",
            }

            response = await self.http_client.get(
                provider_config.userinfo_url,
                headers=headers,
                verify=provider_config.verify_ssl,
            )
            response.raise_for_status()

            user_data = response.json()

            # Map provider claims to our standard format
            mapped_data = self._map_provider_claims(user_data, provider_config.claim_mappings)

            return OAuthUserInfo(
                provider=provider_config.provider,
                provider_user_id=mapped_data.get("provider_user_id", ""),
                email=mapped_data.get("email"),
                name=mapped_data.get("name"),
                given_name=mapped_data.get("given_name"),
                family_name=mapped_data.get("family_name"),
                picture=mapped_data.get("picture"),
                locale=mapped_data.get("locale"),
                raw_profile=user_data,
            )

        except Exception as e:
            raise AuthenticationError(f"Failed to get user info: {e!s}") from e

    def _map_provider_claims(
        self, user_data: dict[str, Any], claim_mappings: dict[str, str]
    ) -> dict[str, Any]:
        """Map provider claims to standard format."""
        mapped = {}

        for provider_claim, our_claim in claim_mappings.items():
            # Support nested claims with dot notation
            value = user_data
            for key in provider_claim.split("."):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break

            if value is not None:
                mapped[our_claim] = value

        return mapped

    async def _store_user_profile(
        self, provider: str, user_info: OAuthUserInfo
    ) -> OAuthUserProfile | None:
        """Store or update user profile."""
        # In a real implementation, this would handle user lookup/creation
        # For now, we'll just return None to indicate no user association
        return None

    async def _store_tokens(
        self, user_id: str, provider: str, token_data: OAuthTokenResponse
    ) -> None:
        """Store OAuth tokens."""
        expires_at = None
        if token_data.expires_in:
            expires_at = datetime.now(UTC) + timedelta(seconds=token_data.expires_in)

        scopes = []
        if token_data.scope:
            scopes = token_data.scope.split(" ")

        # Check if we already have tokens for this user/provider
        existing_token = await self._get_stored_tokens(user_id, OAuthProvider(provider))

        if existing_token:
            # Update existing tokens
            existing_token.access_token = token_data.access_token
            existing_token.token_type = token_data.token_type
            existing_token.expires_at = expires_at
            existing_token.scopes = scopes
            existing_token.updated_at = datetime.now(UTC)

            if token_data.refresh_token:
                existing_token.refresh_token = token_data.refresh_token
        else:
            # Create new token record
            new_token = OAuthToken(
                user_id=user_id,
                provider=provider,
                access_token=token_data.access_token,
                refresh_token=token_data.refresh_token,
                token_type=token_data.token_type,
                expires_at=expires_at,
                scopes=scopes,
            )
            self.db.add(new_token)

    async def _revoke_tokens_with_provider(
        self, provider_config: OAuthProviderConfig, stored_token: OAuthToken
    ) -> None:
        """Attempt to revoke tokens with the provider."""
        # This would implement provider-specific token revocation
        # Different providers have different revocation endpoints and methods


# Provider setup helpers


async def setup_oauth_provider(
    db_session,
    provider: OAuthProvider,
    client_id: str,
    client_secret: str,
    custom_config: dict[str, Any] | None = None,
) -> OAuthProviderConfig:
    """Set up an OAuth provider configuration."""

    # Get default configuration
    default_config = PROVIDER_CONFIGS.get(provider, {})

    # Merge with custom configuration
    if custom_config:
        default_config.update(custom_config)

    # Check if provider already exists
    existing_config = (
        db_session.query(OAuthProviderConfig)
        .filter(OAuthProviderConfig.provider == provider.value)
        .first()
    )

    if existing_config:
        # Update existing configuration
        for key, value in default_config.items():
            if hasattr(existing_config, key):
                setattr(existing_config, key, value)
        existing_config.client_id = client_id
        existing_config.client_secret = client_secret  # Should be encrypted
        existing_config.updated_at = datetime.now(UTC)

        await db_session.commit()
        return existing_config
    # Create new configuration
    new_config = OAuthProviderConfig(
        provider=provider.value,
        client_id=client_id,
        client_secret=client_secret,  # Should be encrypted
        **default_config,
    )

    db_session.add(new_config)
    await db_session.commit()

    return new_config


def generate_oauth_state() -> str:
    """Generate a secure OAuth state parameter."""
    return secrets.token_urlsafe(32)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge pair."""
    code_verifier = secrets.token_urlsafe(96)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    return code_verifier, code_challenge
