"""
Basic File Storage Testing
Simple tests for file storage functionality to build coverage.
"""

import hashlib
import tempfile
from pathlib import Path

import pytest


class SimpleFileStorage:
    """Simple file storage for testing"""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or tempfile.gettempdir()) / "test_storage"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_size = 1024 * 1024  # 1MB

    async def store_file(self, filename: str, content: bytes) -> dict:
        """Store file with basic validation"""
        # Basic size check
        if len(content) > self.max_size:
            raise ValueError("File too large")

        # Basic path check
        if ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid filename")

        file_path = self.base_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_bytes(content)

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        return {
            "success": True,
            "path": filename,
            "size": len(content),
            "checksum": checksum
        }

    async def get_file(self, filename: str) -> bytes:
        """Retrieve file content"""
        if ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid filename")

        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        return file_path.read_bytes()

    async def delete_file(self, filename: str) -> bool:
        """Delete file"""
        if ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid filename")

        file_path = self.base_path / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False


class TestBasicFileStorage:
    """Basic file storage tests for coverage"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def file_storage(self, temp_storage_dir):
        """Create file storage instance"""
        return SimpleFileStorage(temp_storage_dir)

    @pytest.mark.asyncio
    async def test_store_file_success(self, file_storage):
        """Test successful file storage"""
        content = b"Hello, World!"
        filename = "test.txt"

        result = await file_storage.store_file(filename, content)

        assert result["success"] is True
        assert result["path"] == filename
        assert result["size"] == len(content)
        assert "checksum" in result

    @pytest.mark.asyncio
    async def test_retrieve_file_success(self, file_storage):
        """Test successful file retrieval"""
        content = b"Test file content"
        filename = "retrieve_test.txt"

        # Store file first
        await file_storage.store_file(filename, content)

        # Retrieve file
        retrieved_content = await file_storage.get_file(filename)

        assert retrieved_content == content

    @pytest.mark.asyncio
    async def test_file_not_found(self, file_storage):
        """Test file not found error"""
        with pytest.raises(FileNotFoundError):
            await file_storage.get_file("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_invalid_filename_store(self, file_storage):
        """Test invalid filename rejection during storage"""
        invalid_filenames = [
            "../malicious.txt",
            "/absolute/path.txt",
            "subdir/../escape.txt"
        ]

        for invalid_filename in invalid_filenames:
            with pytest.raises(ValueError) as exc_info:
                await file_storage.store_file(invalid_filename, b"content")

            assert "Invalid filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_filename_retrieve(self, file_storage):
        """Test invalid filename rejection during retrieval"""
        invalid_filenames = [
            "../malicious.txt",
            "/absolute/path.txt"
        ]

        for invalid_filename in invalid_filenames:
            with pytest.raises(ValueError) as exc_info:
                await file_storage.get_file(invalid_filename)

            assert "Invalid filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_file_size_limit(self, file_storage):
        """Test file size limit enforcement"""
        large_content = b"A" * (file_storage.max_size + 1)

        with pytest.raises(ValueError) as exc_info:
            await file_storage.store_file("large.txt", large_content)

        assert "File too large" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_file_checksum_calculation(self, file_storage):
        """Test file checksum calculation"""
        content = b"Test checksum content"
        filename = "checksum_test.txt"

        result = await file_storage.store_file(filename, content)

        expected_checksum = hashlib.sha256(content).hexdigest()
        assert result["checksum"] == expected_checksum

    @pytest.mark.asyncio
    async def test_nested_directory_creation(self, file_storage):
        """Test creation of nested directories"""
        content = b"Nested file content"
        filename = "deep/nested/directory/file.txt"

        result = await file_storage.store_file(filename, content)

        assert result["success"] is True

        # Verify file can be retrieved
        retrieved_content = await file_storage.get_file(filename)
        assert retrieved_content == content

    @pytest.mark.asyncio
    async def test_delete_file_success(self, file_storage):
        """Test successful file deletion"""
        content = b"File to be deleted"
        filename = "delete_test.txt"

        # Store file first
        await file_storage.store_file(filename, content)

        # Delete file
        deleted = await file_storage.delete_file(filename)
        assert deleted is True

        # Verify file is gone
        with pytest.raises(FileNotFoundError):
            await file_storage.get_file(filename)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, file_storage):
        """Test deletion of nonexistent file"""
        deleted = await file_storage.delete_file("nonexistent.txt")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_multiple_file_operations(self, file_storage):
        """Test multiple file operations"""
        files = {
            "file1.txt": b"Content 1",
            "file2.txt": b"Content 2",
            "subdir/file3.txt": b"Content 3"
        }

        # Store all files
        for filename, content in files.items():
            result = await file_storage.store_file(filename, content)
            assert result["success"] is True

        # Retrieve all files
        for filename, expected_content in files.items():
            content = await file_storage.get_file(filename)
            assert content == expected_content

        # Delete all files
        for filename in files.keys():
            deleted = await file_storage.delete_file(filename)
            assert deleted is True
