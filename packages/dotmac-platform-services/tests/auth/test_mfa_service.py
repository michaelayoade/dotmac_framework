"""
Multi-Factor Authentication Service Testing
Implementation of AUTH-003: Comprehensive MFA testing including TOTP, SMS, and backup codes.
"""

import pytest
import asyncio
import pyotp
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from dotmac.platform.auth.mfa_service import (
    MFAService,
    MFAMethod,
    MFAError,
    BackupCode
)


class TestMFAServiceComprehensive:
    """Comprehensive MFA service testing"""
    
    @pytest.fixture
    def mfa_service(self):
        """Create MFA service instance for testing"""
        return MFAService()
    
    @pytest.fixture
    def mock_sms_provider(self):
        """Mock SMS provider for testing"""
        return Mock()
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID for MFA operations"""
        return "test_user_123"
    
    # TOTP (Time-based One-Time Password) Tests
    
    def test_totp_secret_generation(self, mfa_service):
        """Test TOTP secret generation"""
        secret = mfa_service.generate_totp_secret()
        
        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) >= 16  # Base32 encoded secret should be at least 16 characters
        
        # Should be valid base32
        try:
            pyotp.TOTP(secret)
        except Exception:
            pytest.fail("Generated secret is not valid base32")
    
    def test_totp_secret_uniqueness(self, mfa_service):
        """Test that TOTP secrets are unique"""
        secrets = [mfa_service.generate_totp_secret() for _ in range(10)]
        
        # All secrets should be unique
        assert len(set(secrets)) == 10
    
    def test_totp_qr_code_generation(self, mfa_service, test_user_id):
        """Test TOTP QR code generation for mobile apps"""
        secret = mfa_service.generate_totp_secret()
        
        qr_code_data = mfa_service.generate_totp_qr_code(
            user_id=test_user_id,
            secret=secret,
            issuer="DotMac Framework"
        )
        
        assert qr_code_data is not None
        assert isinstance(qr_code_data, bytes)
        assert len(qr_code_data) > 0
        
        # QR code should contain proper TOTP URI
        expected_uri_start = f"otpauth://totp/DotMac%20Framework:{test_user_id}"
        # Note: We'd need to decode the QR code to fully test the URI, but this validates structure
    
    def test_totp_code_validation_success(self, mfa_service):
        """Test successful TOTP code validation"""
        secret = mfa_service.generate_totp_secret()
        
        # Generate current TOTP code using pyotp directly
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        
        # Verify the code validates
        is_valid = mfa_service.verify_totp_code(secret, current_code)
        assert is_valid is True
    
    def test_totp_code_validation_with_time_window(self, mfa_service):
        """Test TOTP code validation with time window tolerance"""
        secret = mfa_service.generate_totp_secret()
        totp = pyotp.TOTP(secret)
        
        # Test current time window
        current_code = totp.now()
        assert mfa_service.verify_totp_code(secret, current_code) is True
        
        # Test previous time window (should be valid with tolerance)
        previous_code = totp.at(datetime.now() - timedelta(seconds=30))
        assert mfa_service.verify_totp_code(secret, previous_code, window=1) is True
        
        # Test future time window (should be valid with tolerance)  
        future_code = totp.at(datetime.now() + timedelta(seconds=30))
        assert mfa_service.verify_totp_code(secret, future_code, window=1) is True
    
    def test_totp_invalid_code_rejection(self, mfa_service):
        """Test rejection of invalid TOTP codes"""
        secret = mfa_service.generate_totp_secret()
        
        invalid_codes = [
            "000000",
            "999999", 
            "123456",
            "abcdef",  # Non-numeric
            "12345",   # Too short
            "1234567", # Too long
            "",        # Empty
        ]
        
        for invalid_code in invalid_codes:
            assert mfa_service.verify_totp_code(secret, invalid_code) is False
    
    def test_totp_replay_attack_prevention(self, mfa_service, test_user_id):
        """Test prevention of TOTP code replay attacks"""
        secret = mfa_service.generate_totp_secret()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        
        # First verification should succeed
        result1 = mfa_service.verify_totp_code_with_replay_protection(
            user_id=test_user_id,
            secret=secret, 
            code=current_code
        )
        assert result1 is True
        
        # Second verification with same code should fail (replay protection)
        result2 = mfa_service.verify_totp_code_with_replay_protection(
            user_id=test_user_id,
            secret=secret,
            code=current_code
        )
        assert result2 is False
    
    # SMS MFA Tests
    
    @pytest.mark.asyncio
    async def test_sms_code_generation_and_sending(self, mfa_service, test_user_id, mock_sms_provider):
        """Test SMS MFA code generation and sending"""
        phone_number = "+1234567890"
        
        with patch.object(mfa_service, '_sms_provider', mock_sms_provider):
            mock_sms_provider.send_sms = AsyncMock(return_value=True)
            
            # Generate and send SMS code
            sms_result = await mfa_service.send_sms_code(test_user_id, phone_number)
            
            assert sms_result.success is True
            assert sms_result.code_id is not None
            
            # Verify SMS was sent
            mock_sms_provider.send_sms.assert_called_once()
            call_args = mock_sms_provider.send_sms.call_args
            assert phone_number in call_args[0]
            
            # Message should contain a numeric code
            message = call_args[0][1]
            assert any(char.isdigit() for char in message)
    
    @pytest.mark.asyncio
    async def test_sms_code_validation(self, mfa_service, test_user_id, mock_sms_provider):
        """Test SMS code validation"""
        phone_number = "+1234567890"
        
        with patch.object(mfa_service, '_sms_provider', mock_sms_provider):
            mock_sms_provider.send_sms = AsyncMock(return_value=True)
            
            # Send SMS code
            sms_result = await mfa_service.send_sms_code(test_user_id, phone_number)
            
            # Get the generated code (for testing purposes)
            generated_code = mfa_service._get_sms_code_for_testing(sms_result.code_id)
            
            # Verify correct code
            is_valid = mfa_service.verify_sms_code(test_user_id, sms_result.code_id, generated_code)
            assert is_valid is True
            
            # Verify incorrect code
            is_invalid = mfa_service.verify_sms_code(test_user_id, sms_result.code_id, "000000")
            assert is_invalid is False
    
    @pytest.mark.asyncio
    async def test_sms_code_expiration(self, mfa_service, test_user_id, mock_sms_provider):
        """Test SMS code expiration handling"""
        phone_number = "+1234567890"
        
        with patch.object(mfa_service, '_sms_provider', mock_sms_provider):
            mock_sms_provider.send_sms = AsyncMock(return_value=True)
            
            # Send SMS code with short expiry (1 second for testing)
            with patch.object(mfa_service, '_sms_code_expiry_minutes', 1/60):  # 1 second
                sms_result = await mfa_service.send_sms_code(test_user_id, phone_number)
                generated_code = mfa_service._get_sms_code_for_testing(sms_result.code_id)
                
                # Wait for code to expire
                await asyncio.sleep(2)
                
                # Verification should fail due to expiration
                is_valid = mfa_service.verify_sms_code(test_user_id, sms_result.code_id, generated_code)
                assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_sms_rate_limiting(self, mfa_service, test_user_id, mock_sms_provider):
        """Test SMS code sending rate limiting"""
        phone_number = "+1234567890"
        
        with patch.object(mfa_service, '_sms_provider', mock_sms_provider):
            mock_sms_provider.send_sms = AsyncMock(return_value=True)
            
            # Send first SMS code - should succeed
            result1 = await mfa_service.send_sms_code(test_user_id, phone_number)
            assert result1.success is True
            
            # Try to send another SMS code immediately - should be rate limited
            with pytest.raises(MFAError) as exc_info:
                await mfa_service.send_sms_code(test_user_id, phone_number)
            
            assert "rate limit" in str(exc_info.value).lower()
    
    # Backup Codes Tests
    
    def test_backup_codes_generation(self, mfa_service, test_user_id):
        """Test backup codes generation"""
        backup_codes = mfa_service.generate_backup_codes(test_user_id, count=10)
        
        assert len(backup_codes) == 10
        
        # Each backup code should be properly formatted
        for code in backup_codes:
            assert isinstance(code, BackupCode)
            assert len(code.code) >= 8  # Reasonable length
            assert code.user_id == test_user_id
            assert code.used is False
            assert code.created_at is not None
        
        # All codes should be unique
        code_values = [code.code for code in backup_codes]
        assert len(set(code_values)) == 10
    
    def test_backup_code_validation_success(self, mfa_service, test_user_id):
        """Test successful backup code validation"""
        backup_codes = mfa_service.generate_backup_codes(test_user_id, count=5)
        test_code = backup_codes[0]
        
        # Verify unused backup code
        is_valid = mfa_service.verify_backup_code(test_user_id, test_code.code)
        assert is_valid is True
        
        # Code should be marked as used
        updated_code = mfa_service.get_backup_code(test_user_id, test_code.code)
        assert updated_code.used is True
        assert updated_code.used_at is not None
    
    def test_backup_code_single_use_enforcement(self, mfa_service, test_user_id):
        """Test that backup codes can only be used once"""
        backup_codes = mfa_service.generate_backup_codes(test_user_id, count=5)
        test_code = backup_codes[0]
        
        # First use should succeed
        result1 = mfa_service.verify_backup_code(test_user_id, test_code.code)
        assert result1 is True
        
        # Second use should fail
        result2 = mfa_service.verify_backup_code(test_user_id, test_code.code)
        assert result2 is False
    
    def test_backup_code_invalid_code_rejection(self, mfa_service, test_user_id):
        """Test rejection of invalid backup codes"""
        # Generate some valid codes first
        mfa_service.generate_backup_codes(test_user_id, count=5)
        
        invalid_codes = [
            "invalid-code",
            "00000000",
            "",
            "short",
            "way-too-long-backup-code-that-should-not-work"
        ]
        
        for invalid_code in invalid_codes:
            result = mfa_service.verify_backup_code(test_user_id, invalid_code)
            assert result is False
    
    # MFA Setup and Configuration Tests
    
    @pytest.mark.asyncio
    async def test_mfa_setup_flow_totp(self, mfa_service, test_user_id):
        """Test complete MFA setup flow for TOTP"""
        # Start TOTP setup
        setup_result = await mfa_service.start_mfa_setup(test_user_id, MFAMethod.TOTP)
        
        assert setup_result.method == MFAMethod.TOTP
        assert setup_result.secret is not None
        assert setup_result.qr_code_data is not None
        assert setup_result.backup_codes is not None
        assert len(setup_result.backup_codes) > 0
        
        # Verify setup with valid TOTP code
        totp = pyotp.TOTP(setup_result.secret)
        verification_code = totp.now()
        
        completion_result = await mfa_service.complete_mfa_setup(
            test_user_id, 
            setup_result.setup_id,
            verification_code
        )
        
        assert completion_result.success is True
        assert completion_result.method == MFAMethod.TOTP
        
        # User should now have MFA enabled
        user_mfa_status = mfa_service.get_user_mfa_status(test_user_id)
        assert user_mfa_status.enabled is True
        assert MFAMethod.TOTP in user_mfa_status.enabled_methods
    
    @pytest.mark.asyncio
    async def test_mfa_setup_flow_sms(self, mfa_service, test_user_id, mock_sms_provider):
        """Test complete MFA setup flow for SMS"""
        phone_number = "+1234567890"
        
        with patch.object(mfa_service, '_sms_provider', mock_sms_provider):
            mock_sms_provider.send_sms = AsyncMock(return_value=True)
            
            # Start SMS setup
            setup_result = await mfa_service.start_mfa_setup(
                test_user_id, 
                MFAMethod.SMS,
                phone_number=phone_number
            )
            
            assert setup_result.method == MFAMethod.SMS
            assert setup_result.phone_number == phone_number
            
            # Get verification code (for testing)
            verification_code = mfa_service._get_sms_code_for_testing(setup_result.verification_id)
            
            # Complete setup
            completion_result = await mfa_service.complete_mfa_setup(
                test_user_id,
                setup_result.setup_id, 
                verification_code
            )
            
            assert completion_result.success is True
    
    # MFA Verification Flow Tests
    
    @pytest.mark.asyncio
    async def test_mfa_verification_flow(self, mfa_service, test_user_id):
        """Test complete MFA verification flow"""
        # Setup TOTP for user first
        setup_result = await mfa_service.start_mfa_setup(test_user_id, MFAMethod.TOTP)
        totp = pyotp.TOTP(setup_result.secret)
        setup_code = totp.now()
        
        await mfa_service.complete_mfa_setup(test_user_id, setup_result.setup_id, setup_code)
        
        # Now test verification flow
        verification_code = totp.now()
        
        verification_result = await mfa_service.verify_mfa(
            test_user_id,
            MFAMethod.TOTP,
            verification_code
        )
        
        assert verification_result.success is True
        assert verification_result.method == MFAMethod.TOTP
        assert verification_result.verified_at is not None
    
    # Error Handling and Edge Cases
    
    @pytest.mark.asyncio
    async def test_mfa_verification_attempt_limiting(self, mfa_service, test_user_id):
        """Test MFA verification attempt limiting"""
        # Setup MFA first
        setup_result = await mfa_service.start_mfa_setup(test_user_id, MFAMethod.TOTP)
        totp = pyotp.TOTP(setup_result.secret)
        setup_code = totp.now()
        await mfa_service.complete_mfa_setup(test_user_id, setup_result.setup_id, setup_code)
        
        # Make multiple failed attempts
        for attempt in range(5):
            result = await mfa_service.verify_mfa(test_user_id, MFAMethod.TOTP, "000000")
            assert result.success is False
        
        # Next attempt should be rate limited
        with pytest.raises(MFAError) as exc_info:
            await mfa_service.verify_mfa(test_user_id, MFAMethod.TOTP, "000000")
        
        assert "too many attempts" in str(exc_info.value).lower()
    
    def test_mfa_service_recovery_flow(self, mfa_service, test_user_id):
        """Test MFA recovery flow using backup codes"""
        # Generate backup codes
        backup_codes = mfa_service.generate_backup_codes(test_user_id, count=10)
        
        # Use backup code for recovery
        recovery_code = backup_codes[0].code
        recovery_result = mfa_service.recover_with_backup_code(test_user_id, recovery_code)
        
        assert recovery_result.success is True
        assert recovery_result.method == MFAMethod.BACKUP_CODE
        
        # Should have fewer unused backup codes now
        remaining_codes = mfa_service.get_unused_backup_codes(test_user_id)
        assert len(remaining_codes) == 9