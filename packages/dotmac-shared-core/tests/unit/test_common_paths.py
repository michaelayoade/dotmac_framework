"""
Unit tests for dotmac_shared_core.common.paths module.
"""

import tempfile
from pathlib import Path

import pytest

from dotmac_shared_core.common.paths import safe_join
from dotmac_shared_core.exceptions import ValidationError


class TestSafeJoin:
    """Test the safe_join function for secure path joining."""

    def test_basic_join(self):
        """Test basic path joining within root."""
        root = Path("/home/user")
        result = safe_join(root, "documents", "file.txt")
        expected = root / "documents" / "file.txt"
        assert result == expected

    def test_single_component(self):
        """Test joining with single path component."""
        root = Path("/var/data")
        result = safe_join(root, "config.json")
        expected = root / "config.json"
        assert result == expected

    def test_no_components(self):
        """Test safe_join with no additional components."""
        root = Path("/home/user")
        result = safe_join(root)
        assert result == root

    def test_string_root(self):
        """Test safe_join with string root path."""
        root = "/home/user"
        result = safe_join(root, "documents", "file.txt")
        expected = Path(root) / "documents" / "file.txt"
        assert result == expected

    def test_prevents_directory_traversal(self):
        """Test that directory traversal attacks are prevented."""
        root = Path("/home/user")

        # These should all raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            safe_join(root, "..", "etc", "passwd")
        assert "Path traversal" in exc_info.value.message

        with pytest.raises(ValidationError):
            safe_join(root, "documents", "..", "..", "etc", "passwd")

        with pytest.raises(ValidationError):
            safe_join(root, "../../../etc/passwd")

    def test_prevents_absolute_path_injection(self):
        """Test that absolute path injection is prevented."""
        root = Path("/home/user")

        with pytest.raises(ValidationError) as exc_info:
            safe_join(root, "/etc/passwd")
        assert "Path traversal" in exc_info.value.message

        with pytest.raises(ValidationError):
            safe_join(root, "documents", "/tmp/evil")

    def test_allows_current_directory(self):
        """Test that current directory references are handled safely."""
        root = Path("/home/user")

        # These should be safe
        result1 = safe_join(root, ".", "file.txt")
        expected1 = root / "file.txt"
        assert result1 == expected1

        result2 = safe_join(root, "docs", ".", "file.txt")
        expected2 = root / "docs" / "file.txt"
        assert result2 == expected2

    def test_complex_valid_paths(self):
        """Test complex but valid path constructions."""
        root = Path("/var/www/app")

        # Deeply nested paths should work
        result = safe_join(root, "static", "css", "themes", "dark", "style.css")
        expected = root / "static" / "css" / "themes" / "dark" / "style.css"
        assert result == expected

        # Paths with dots in names should work
        result2 = safe_join(root, "uploads", "image.2023.jpg")
        expected2 = root / "uploads" / "image.2023.jpg"
        assert result2 == expected2

    def test_symlink_protection(self):
        """Test protection against symlink-based attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # Create a subdirectory
            safe_dir = root / "safe"
            safe_dir.mkdir()

            # Create a file outside the root
            outside_file = Path(temp_dir).parent / "outside.txt"
            outside_file.write_text("sensitive data")

            # Create a symlink from inside root to outside
            link_path = safe_dir / "evil_link"
            try:
                link_path.symlink_to(outside_file)

                # Attempting to access through the symlink should fail
                with pytest.raises(ValidationError):
                    safe_join(root, "safe", "evil_link")

            except OSError:
                # Skip if symlinks not supported on this system
                pytest.skip("Symlinks not supported")
            finally:
                if outside_file.exists():
                    outside_file.unlink()

    def test_windows_path_separators(self):
        """Test handling of Windows-style path separators."""
        root = Path("/home/user")

        # Should handle Windows-style separators safely
        result = safe_join(root, "documents\\file.txt")
        # The result should normalize separators
        assert "documents" in str(result)
        assert "file.txt" in str(result)

    def test_empty_components(self):
        """Test handling of empty path components."""
        root = Path("/home/user")

        # Empty strings should be filtered out
        result = safe_join(root, "documents", "", "file.txt", "")
        expected = root / "documents" / "file.txt"
        assert result == expected

    def test_whitespace_components(self):
        """Test handling of whitespace-only components."""
        root = Path("/home/user")

        # Whitespace-only components should be preserved if they're valid filenames
        result = safe_join(root, "documents", " file with spaces ")
        expected = root / "documents" / " file with spaces "
        assert result == expected

    def test_unicode_paths(self):
        """Test handling of Unicode characters in paths."""
        root = Path("/home/user")

        # Unicode characters should be preserved
        result = safe_join(root, "documents", "файл.txt", "日本語.jpg")
        expected = root / "documents" / "файл.txt" / "日本語.jpg"
        assert result == expected

    def test_error_details(self):
        """Test that security errors include helpful details."""
        root = Path("/home/user")

        with pytest.raises(ValidationError) as exc_info:
            safe_join(root, "..", "etc", "passwd")

        error = exc_info.value
        assert error.error_code == "PATH_TRAVERSAL"
        assert error.details is not None
        assert "attempted_path" in error.details
        assert "root_path" in error.details


class TestSafeJoinEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_root_path_normalization(self):
        """Test that root paths are properly normalized."""
        # Root with trailing slash
        root1 = Path("/home/user/")
        result1 = safe_join(root1, "file.txt")

        # Root without trailing slash
        root2 = Path("/home/user")
        result2 = safe_join(root2, "file.txt")

        # Should produce the same result
        assert result1 == result2

    def test_relative_root_path(self):
        """Test safe_join with relative root paths."""
        root = Path("./data")
        result = safe_join(root, "configs", "app.json")

        # Should work with relative paths
        assert "data" in str(result)
        assert "configs" in str(result)
        assert "app.json" in str(result)

    def test_very_long_paths(self):
        """Test handling of very long path components."""
        root = Path("/home/user")
        long_name = "a" * 200  # Very long filename

        result = safe_join(root, "documents", long_name)
        expected = root / "documents" / long_name
        assert result == expected

    def test_special_characters(self):
        """Test handling of special characters in filenames."""
        root = Path("/home/user")

        # Various special characters that should be allowed
        special_chars = ["file@domain.com", "file#tag", "file$var", "file&more"]

        for special in special_chars:
            result = safe_join(root, special)
            expected = root / special
            assert result == expected

    def test_mixed_separators_attack(self):
        """Test protection against mixed separator attacks."""
        root = Path("/home/user")

        # Try to use mixed separators for traversal
        with pytest.raises(ValidationError):
            safe_join(root, "docs/../../../etc/passwd")

        with pytest.raises(ValidationError):
            safe_join(root, "docs\\..\\..\\..\\windows\\system32")


class TestSafeJoinRealFilesystem:
    """Test safe_join with real filesystem operations."""

    def test_with_temp_directory(self):
        """Test safe_join with actual temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # Create some test structure
            test_file = safe_join(root, "test", "data.txt")
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test content")

            # Verify the file was created in the right place
            assert test_file.exists()
            assert test_file.read_text() == "test content"
            assert test_file.is_relative_to(root)

    def test_directory_creation(self):
        """Test creating directories with safe_join results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # Create nested directory structure
            nested_dir = safe_join(root, "level1", "level2", "level3")
            nested_dir.mkdir(parents=True, exist_ok=True)

            # Verify directory was created safely
            assert nested_dir.exists()
            assert nested_dir.is_dir()
            assert nested_dir.is_relative_to(root)

    def test_prevents_escape_with_real_paths(self):
        """Test that escape attempts fail with real filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # Try to escape and create file outside
            with pytest.raises(ValidationError):
                escaped_path = safe_join(root, "..", "escaped.txt")
                # This line should never execute due to the exception
                Path(escaped_path).write_text("escaped")

    def test_file_operations_safety(self):
        """Test that file operations are safe with safe_join results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # Safe operations should work
            safe_file = safe_join(root, "safe", "file.txt")
            safe_file.parent.mkdir(parents=True, exist_ok=True)
            safe_file.write_text("safe content")

            # Reading should work
            content = safe_file.read_text()
            assert content == "safe content"

            # File should be within the root
            assert safe_file.is_relative_to(root)
