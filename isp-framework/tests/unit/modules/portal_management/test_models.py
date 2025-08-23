"""Tests for portal management models."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

from dotmac_isp.modules.portal_management.models import (
    PortalAccountStatus,
    PortalAccountType,
    PortalAccount,
    PortalSession,
    PortalLoginAttempt,
)


class TestPortalAccountStatus:
    """Test PortalAccountStatus enum."""
    
    def test_portal_account_status_values(self):
        """Test PortalAccountStatus enum values."""
        assert PortalAccountStatus.ACTIVE.value == "active"
        assert PortalAccountStatus.SUSPENDED.value == "suspended"
        assert PortalAccountStatus.LOCKED.value == "locked"
        assert PortalAccountStatus.PENDING_ACTIVATION.value == "pending_activation"
        assert PortalAccountStatus.DEACTIVATED.value == "deactivated"
    
    def test_portal_account_status_count(self):
        """Test expected number of status values."""
        assert len(PortalAccountStatus) == 5


class TestPortalAccountType:
    """Test PortalAccountType enum."""
    
    def test_portal_account_type_values(self):
        """Test PortalAccountType enum values."""
        assert PortalAccountType.CUSTOMER.value == "customer"
        assert PortalAccountType.TECHNICIAN.value == "technician"
        assert PortalAccountType.RESELLER.value == "reseller"
    
    def test_portal_account_type_count(self):
        """Test expected number of type values."""
        assert len(PortalAccountType) == 3


class TestPortalAccount:
    """Test PortalAccount model."""
    
    def test_portal_account_creation_with_portal_id(self):
        """Test PortalAccount creation with provided portal_id."""
        tenant_id = uuid4()
        portal_id = "TEST1234"
        
        account = PortalAccount(
            tenant_id=tenant_id,
            portal_id=portal_id,
            password_hash="hashed_password"
        )
        
        assert account.tenant_id == tenant_id
        assert account.portal_id == portal_id
        assert account.account_type == PortalAccountType.CUSTOMER.value  # Default
        assert account.status == PortalAccountStatus.PENDING_ACTIVATION.value  # Default
        assert account.password_hash == "hashed_password"
        assert account.two_factor_enabled is False  # Default
        assert account.failed_login_attempts == 0  # Default
        assert account.must_change_password is True  # Default
        assert account.session_timeout_minutes == 30  # Default
        assert account.auto_logout_enabled is True  # Default
        assert account.email_notifications is True  # Default
        assert account.sms_notifications is False  # Default
        assert account.theme_preference == "light"  # Default
        assert account.language_preference == "en"  # Default
        assert account.timezone_preference == "UTC"  # Default
        assert account.email_verified is False  # Default
        assert account.phone_verified is False  # Default
    
    @patch('dotmac_isp.modules.portal_management.models.PortalAccount._generate_portal_id')
    def test_portal_account_creation_auto_portal_id(self, mock_generate):
        """Test PortalAccount creation with auto-generated portal_id."""
        mock_generate.return_value = "AUTO5678"
        tenant_id = uuid4()
        
        account = PortalAccount(
            tenant_id=tenant_id,
            password_hash="hashed_password"
        )
        
        assert account.portal_id == "AUTO5678"
        mock_generate.assert_called_once()
    
    def test_generate_portal_id_static_method(self):
        """Test _generate_portal_id static method."""
        portal_id = PortalAccount._generate_portal_id()
        
        # Should be 8 characters long
        assert len(portal_id) == 8
        
        # Should only contain allowed characters (no 0, O, I, 1)
        forbidden_chars = {'0', 'O', 'I', '1'}
        assert not any(char in portal_id for char in forbidden_chars)
        
        # Should be uppercase alphanumeric
        allowed_chars = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        assert all(char in allowed_chars for char in portal_id)
        
        # Generate multiple IDs to test uniqueness (statistically)
        ids = [PortalAccount._generate_portal_id() for _ in range(100)]
        assert len(set(ids)) == len(ids)  # All should be unique
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_is_locked_property_not_locked(self, mock_datetime):
        """Test is_locked property when not locked."""
        mock_datetime.utcnow.return_value = datetime(2023, 12, 15, 10, 30, 0)
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed"
        )
        
        # No lock time set
        assert account.is_locked is False
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_is_locked_property_locked_future(self, mock_datetime):
        """Test is_locked property when locked until future time."""
        current_time = datetime(2023, 12, 15, 10, 30, 0)
        lock_until = datetime(2023, 12, 15, 11, 0, 0)  # 30 minutes later
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            locked_until=lock_until
        )
        
        assert account.is_locked is True
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_is_locked_property_lock_expired(self, mock_datetime):
        """Test is_locked property when lock has expired."""
        current_time = datetime(2023, 12, 15, 11, 30, 0)
        lock_until = datetime(2023, 12, 15, 11, 0, 0)  # 30 minutes ago
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            locked_until=lock_until
        )
        
        assert account.is_locked is False
    
    def test_is_active_property_active_account(self):
        """Test is_active property for active account."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            status=PortalAccountStatus.ACTIVE.value
        )
        account.is_deleted = False  # Simulate database default
        
        with patch.object(account, 'is_locked', False):
            assert account.is_active is True
    
    def test_is_active_property_inactive_status(self):
        """Test is_active property for inactive status."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            status=PortalAccountStatus.SUSPENDED.value
        )
        account.is_deleted = False
        
        with patch.object(account, 'is_locked', False):
            assert account.is_active is False
    
    def test_is_active_property_locked_account(self):
        """Test is_active property for locked account."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            status=PortalAccountStatus.ACTIVE.value
        )
        account.is_deleted = False
        
        with patch.object(account, 'is_locked', True):
            assert account.is_active is False
    
    def test_is_active_property_deleted_account(self):
        """Test is_active property for deleted account."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            status=PortalAccountStatus.ACTIVE.value
        )
        account.is_deleted = True
        
        with patch.object(account, 'is_locked', False):
            assert account.is_active is False
    
    def test_password_expired_property_no_changed_date(self):
        """Test password_expired property with no change date."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed"
        )
        
        # No password_changed_at means expired
        assert account.password_expired is True
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_password_expired_property_recent_change(self, mock_datetime):
        """Test password_expired property with recent password change."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        changed_time = datetime(2023, 12, 1, 10, 0, 0)  # 14 days ago
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            password_changed_at=changed_time
        )
        
        assert account.password_expired is False
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_password_expired_property_old_change(self, mock_datetime):
        """Test password_expired property with old password change."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        changed_time = datetime(2023, 9, 1, 10, 0, 0)  # 105 days ago
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            password_changed_at=changed_time
        )
        
        assert account.password_expired is True
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_lock_account_method(self, mock_datetime):
        """Test lock_account method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            status=PortalAccountStatus.ACTIVE.value
        )
        
        # Lock for 60 minutes with reason
        account.lock_account(60, "Suspicious activity")
        
        expected_unlock_time = current_time + timedelta(minutes=60)
        assert account.locked_until == expected_unlock_time
        assert account.status == PortalAccountStatus.LOCKED.value
        assert "Suspicious activity" in account.security_notes
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_lock_account_method_defaults(self, mock_datetime):
        """Test lock_account method with default parameters."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            security_notes="Previous notes\n"
        )
        
        # Lock with defaults (30 minutes, no reason)
        account.lock_account()
        
        expected_unlock_time = current_time + timedelta(minutes=30)
        assert account.locked_until == expected_unlock_time
        assert account.status == PortalAccountStatus.LOCKED.value
        # Should preserve existing notes
        assert "Previous notes" in account.security_notes
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_unlock_account_method(self, mock_datetime):
        """Test unlock_account method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        admin_id = uuid4()
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            locked_until=current_time + timedelta(hours=1),
            failed_login_attempts=3,
            status=PortalAccountStatus.LOCKED.value
        )
        
        # Unlock with admin ID
        account.unlock_account(admin_id)
        
        assert account.locked_until is None
        assert account.failed_login_attempts == 0
        assert account.status == PortalAccountStatus.ACTIVE.value
        assert account.last_modified_by_admin_id == admin_id
        assert "Unlocked by admin" in account.security_notes
    
    def test_unlock_account_method_no_admin(self):
        """Test unlock_account method without admin ID."""
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            locked_until=datetime.utcnow() + timedelta(hours=1),
            failed_login_attempts=5,
            status=PortalAccountStatus.LOCKED.value,
            security_notes="Previous notes\n"
        )
        
        # Unlock without admin ID
        account.unlock_account()
        
        assert account.locked_until is None
        assert account.failed_login_attempts == 0
        assert account.status == PortalAccountStatus.ACTIVE.value
        assert account.last_modified_by_admin_id is None
        # Should preserve existing notes
        assert "Previous notes" in account.security_notes
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_record_failed_login_method(self, mock_datetime):
        """Test record_failed_login method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            failed_login_attempts=2
        )
        
        # Record failed login
        account.record_failed_login()
        
        assert account.failed_login_attempts == 3
        assert account.last_failed_login == current_time
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_record_failed_login_method_auto_lock(self, mock_datetime):
        """Test record_failed_login method triggers auto-lock."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            failed_login_attempts=4  # One below threshold
        )
        
        # Record failed login - should trigger auto-lock
        account.record_failed_login()
        
        assert account.failed_login_attempts == 5
        assert account.status == PortalAccountStatus.LOCKED.value
        assert account.locked_until is not None
        assert "Too many failed login attempts" in account.security_notes
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_record_successful_login_method(self, mock_datetime):
        """Test record_successful_login method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        account = PortalAccount(
            tenant_id=uuid4(),
            portal_id="TEST1234",
            password_hash="hashed",
            failed_login_attempts=3,
            locked_until=current_time + timedelta(minutes=30)
        )
        
        # Record successful login
        account.record_successful_login()
        
        assert account.failed_login_attempts == 0
        assert account.last_successful_login == current_time
        assert account.locked_until is None


class TestPortalSession:
    """Test PortalSession model."""
    
    def test_portal_session_creation(self):
        """Test PortalSession creation."""
        tenant_id = uuid4()
        account_id = uuid4()
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        expires_time = current_time + timedelta(minutes=30)
        
        session = PortalSession(
            tenant_id=tenant_id,
            session_token="session_token_123",
            portal_account_id=account_id,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            expires_at=expires_time,
            login_at=current_time
        )
        
        assert session.tenant_id == tenant_id
        assert session.session_token == "session_token_123"
        assert session.portal_account_id == account_id
        assert session.ip_address == "192.168.1.100"
        assert session.user_agent == "Mozilla/5.0..."
        assert session.expires_at == expires_time
        assert session.login_at == current_time
        assert session.is_active is True  # Default
        assert session.suspicious_activity is False  # Default
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_is_expired_property_not_expired(self, mock_datetime):
        """Test is_expired property for non-expired session."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        expires_time = datetime(2023, 12, 15, 10, 30, 0)  # 30 minutes later
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            expires_at=expires_time
        )
        
        assert session.is_expired is False
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_is_expired_property_expired(self, mock_datetime):
        """Test is_expired property for expired session."""
        current_time = datetime(2023, 12, 15, 10, 30, 0)
        expires_time = datetime(2023, 12, 15, 10, 0, 0)  # 30 minutes ago
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            expires_at=expires_time
        )
        
        assert session.is_expired is True
    
    def test_is_valid_property_valid_session(self):
        """Test is_valid property for valid session."""
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            is_active=True
        )
        
        with patch.object(session, 'is_expired', False):
            assert session.is_valid is True
    
    def test_is_valid_property_inactive_session(self):
        """Test is_valid property for inactive session."""
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            is_active=False
        )
        
        with patch.object(session, 'is_expired', False):
            assert session.is_valid is False
    
    def test_is_valid_property_expired_session(self):
        """Test is_valid property for expired session."""
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            is_active=True
        )
        
        with patch.object(session, 'is_expired', True):
            assert session.is_valid is False
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_duration_minutes_property_ongoing(self, mock_datetime):
        """Test duration_minutes property for ongoing session."""
        current_time = datetime(2023, 12, 15, 10, 30, 0)
        login_time = datetime(2023, 12, 15, 10, 0, 0)  # 30 minutes ago
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            login_at=login_time
        )
        
        assert session.duration_minutes == 30
    
    def test_duration_minutes_property_logged_out(self):
        """Test duration_minutes property for logged out session."""
        login_time = datetime(2023, 12, 15, 10, 0, 0)
        logout_time = datetime(2023, 12, 15, 10, 45, 0)  # 45 minutes later
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            login_at=login_time,
            logout_at=logout_time
        )
        
        assert session.duration_minutes == 45
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_extend_session_method(self, mock_datetime):
        """Test extend_session method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4()
        )
        
        # Extend by 60 minutes
        session.extend_session(60)
        
        expected_expires = current_time + timedelta(minutes=60)
        assert session.expires_at == expected_expires
        assert session.last_activity == current_time
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_extend_session_method_default(self, mock_datetime):
        """Test extend_session method with default duration."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4()
        )
        
        # Extend with default (30 minutes)
        session.extend_session()
        
        expected_expires = current_time + timedelta(minutes=30)
        assert session.expires_at == expected_expires
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_terminate_session_method(self, mock_datetime):
        """Test terminate_session method."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4(),
            is_active=True
        )
        
        # Terminate session
        session.terminate_session("timeout")
        
        assert session.is_active is False
        assert session.logout_at == current_time
        assert session.logout_reason == "timeout"
    
    @patch('dotmac_isp.modules.portal_management.models.datetime')
    def test_terminate_session_method_default_reason(self, mock_datetime):
        """Test terminate_session method with default reason."""
        current_time = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        session = PortalSession(
            tenant_id=uuid4(),
            session_token="token123",
            portal_account_id=uuid4()
        )
        
        # Terminate with default reason
        session.terminate_session()
        
        assert session.logout_reason == "manual"


class TestPortalLoginAttempt:
    """Test PortalLoginAttempt model."""
    
    def test_portal_login_attempt_creation(self):
        """Test PortalLoginAttempt creation."""
        tenant_id = uuid4()
        account_id = uuid4()
        
        attempt = PortalLoginAttempt(
            tenant_id=tenant_id,
            portal_account_id=account_id,
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            country_code="US",
            city="New York",
            two_factor_used=True
        )
        
        assert attempt.tenant_id == tenant_id
        assert attempt.portal_account_id == account_id
        assert attempt.portal_id_attempted == "TEST1234"
        assert attempt.success is True
        assert attempt.ip_address == "192.168.1.100"
        assert attempt.user_agent == "Mozilla/5.0..."
        assert attempt.country_code == "US"
        assert attempt.city == "New York"
        assert attempt.two_factor_used is True
        assert attempt.risk_score == 0  # Default
        assert attempt.flagged_as_suspicious is False  # Default
    
    def test_is_high_risk_property_low_score(self):
        """Test is_high_risk property with low risk score."""
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            risk_score=30,
            flagged_as_suspicious=False
        )
        
        assert attempt.is_high_risk is False
    
    def test_is_high_risk_property_high_score(self):
        """Test is_high_risk property with high risk score."""
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            risk_score=80,
            flagged_as_suspicious=False
        )
        
        assert attempt.is_high_risk is True
    
    def test_is_high_risk_property_flagged(self):
        """Test is_high_risk property when flagged as suspicious."""
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            risk_score=30,
            flagged_as_suspicious=True
        )
        
        assert attempt.is_high_risk is True
    
    def test_calculate_risk_score_successful_attempt(self):
        """Test calculate_risk_score for successful attempt."""
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100"
        )
        
        score = attempt.calculate_risk_score([])
        assert score == 0  # No risk factors
    
    def test_calculate_risk_score_failed_attempt(self):
        """Test calculate_risk_score for failed attempt."""
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=False,
            ip_address="192.168.1.100"
        )
        
        score = attempt.calculate_risk_score([])
        assert score == 25  # Failed attempt adds 25
    
    def test_calculate_risk_score_multiple_ip_attempts(self):
        """Test calculate_risk_score with multiple attempts from same IP."""
        # Create mock recent attempts from same IP
        recent_attempts = []
        for i in range(4):
            mock_attempt = MagicMock()
            mock_attempt.ip_address = "192.168.1.100"
            recent_attempts.append(mock_attempt)
        
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100"
        )
        
        score = attempt.calculate_risk_score(recent_attempts)
        assert score == 30  # Multiple IP attempts adds 30
    
    def test_calculate_risk_score_new_location(self):
        """Test calculate_risk_score for new geographic location."""
        # Mock portal account
        mock_account = MagicMock()
        
        # Mock recent attempts with different countries
        recent_attempts = []
        for country in ['US', 'CA']:
            mock_attempt = MagicMock()
            mock_attempt.success = True
            mock_attempt.country_code = country
            recent_attempts.append(mock_attempt)
        
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            country_code="GB",  # New country
            portal_account=mock_account
        )
        
        score = attempt.calculate_risk_score(recent_attempts)
        assert score == 20  # New location adds 20
    
    def test_calculate_risk_score_no_2fa_when_enabled(self):
        """Test calculate_risk_score when 2FA is enabled but not used."""
        # Mock portal account with 2FA enabled
        mock_account = MagicMock()
        mock_account.two_factor_enabled = True
        
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=True,
            ip_address="192.168.1.100",
            two_factor_used=False,
            portal_account=mock_account
        )
        
        score = attempt.calculate_risk_score([])
        assert score == 15  # No 2FA when available adds 15
    
    def test_calculate_risk_score_combined_factors(self):
        """Test calculate_risk_score with multiple risk factors."""
        # Mock portal account with 2FA enabled
        mock_account = MagicMock()
        mock_account.two_factor_enabled = True
        
        # Mock multiple attempts from same IP
        recent_attempts = []
        for i in range(5):
            mock_attempt = MagicMock()
            mock_attempt.ip_address = "192.168.1.100"
            mock_attempt.success = True
            mock_attempt.country_code = "US"
            recent_attempts.append(mock_attempt)
        
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=False,  # Failed attempt: +25
            ip_address="192.168.1.100",  # Multiple IP attempts: +30
            country_code="GB",  # New location: +20
            two_factor_used=False,  # No 2FA: +15
            portal_account=mock_account
        )
        
        score = attempt.calculate_risk_score(recent_attempts)
        # Total: 25 + 30 + 20 + 15 = 90
        assert score == 90
    
    def test_calculate_risk_score_capped_at_100(self):
        """Test calculate_risk_score is capped at 100."""
        # Mock scenario that would exceed 100
        mock_account = MagicMock()
        mock_account.two_factor_enabled = True
        
        # Create many recent attempts to inflate score
        recent_attempts = []
        for i in range(10):  # This would add more than needed
            mock_attempt = MagicMock()
            mock_attempt.ip_address = "192.168.1.100"
            recent_attempts.append(mock_attempt)
        
        attempt = PortalLoginAttempt(
            tenant_id=uuid4(),
            portal_id_attempted="TEST1234",
            success=False,  # +25
            ip_address="192.168.1.100",  # +30
            country_code="GB",  # +20 (if previous locations exist)
            two_factor_used=False,  # +15
            portal_account=mock_account
        )
        
        score = attempt.calculate_risk_score(recent_attempts)
        assert score <= 100  # Should be capped at 100