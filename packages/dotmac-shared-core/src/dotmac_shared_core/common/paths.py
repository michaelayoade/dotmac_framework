"""
Safe path utilities for file system operations.

Provides functions for secure path manipulation that prevent directory
traversal attacks and ensure paths remain within allowed boundaries.
"""

from pathlib import Path
from typing import Union

from ..exceptions import ValidationError


def safe_join(root: Union[Path, str], *parts: str) -> Path:
    """
    Safely join path components, preventing directory traversal attacks.
    
    Ensures the resulting path is within the root directory by resolving
    all symbolic links and relative path components, then checking that
    the result is contained within the root.
    
    Args:
        root: Root directory path (as Path or string)
        *parts: Path components to join to the root
        
    Returns:
        Path object representing the safe joined path
        
    Raises:
        ValidationError: If the resulting path would escape the root directory
        
    Example:
        >>> safe_join("/var/data", "uploads", "file.txt")
        PosixPath('/var/data/uploads/file.txt')
        
        >>> safe_join("/var/data", "../etc/passwd")  # Raises ValidationError
        ValidationError: Path traversal detected: attempted to access path outside root directory
        
        >>> safe_join("/var/data", "subdir/../file.txt")  # OK - resolves within root  
        PosixPath('/var/data/file.txt')
    """
    # Convert root to Path and resolve it
    root_path = Path(root).resolve()

    # Check for suspicious patterns in path components before joining
    for part in parts:
        # Convert backslashes to forward slashes to handle Windows-style paths
        normalized_part = part.replace("\\", "/")
        # Check for directory traversal patterns
        if ".." in normalized_part or normalized_part.startswith("/"):
            # Do a preliminary check for obvious traversal attempts
            test_path = (root_path / normalized_part).resolve()
            try:
                test_path.relative_to(root_path)
            except ValueError:
                raise ValidationError(
                    "Path traversal detected: attempted to access path outside root directory",
                    "PATH_TRAVERSAL",
                    {
                        "root_path": str(root_path),
                        "attempted_path": str(test_path),
                        "parts": parts
                    }
                ) from None

    # Join all parts to the root
    joined_path = root_path
    for part in parts:
        # Normalize backslashes before joining
        normalized_part = part.replace("\\", "/")
        joined_path = joined_path / normalized_part

    # Resolve the final path (handles .. and symlinks)
    try:
        resolved_path = joined_path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(
            f"Invalid path: {e}",
            "INVALID_PATH",
            {"root_path": str(root_path), "parts": parts}
        ) from e

    # Check if the resolved path is within the root
    try:
        resolved_path.relative_to(root_path)
    except ValueError:
        raise ValidationError(
            "Path traversal detected: attempted to access path outside root directory",
            "PATH_TRAVERSAL",
            {
                "root_path": str(root_path),
                "attempted_path": str(resolved_path),
                "parts": parts
            }
        ) from None

    return resolved_path


def ensure_dir(path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Creates the directory and any necessary parent directories.
    Does not modify permissions or ownership.
    
    Args:
        path: Directory path to create
        
    Raises:
        ValidationError: If directory creation fails
        
    Example:
        >>> ensure_dir(Path("/tmp/myapp/data"))  # Creates /tmp/myapp/data and parents
        >>> ensure_dir(Path("/existing/dir"))   # No-op if already exists
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise ValidationError(
            f"Failed to create directory: {e}",
            "DIR_CREATE_FAILED",
            {"path": str(path), "error": str(e)}
        ) from e


__all__ = [
    "safe_join",
    "ensure_dir",
]
