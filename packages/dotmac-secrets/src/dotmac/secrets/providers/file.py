"""
File-based provider for secrets (development/testing)
Supports JSON, YAML, and TOML formats
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..interfaces import SecretNotFoundError, SecretsProviderError
from ..types import SecretData
from .base import BaseProvider

logger = logging.getLogger(__name__)

# Optional dependencies for different file formats
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomllib
    HAS_TOML = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False


class FileProvider(BaseProvider):
    """
    File-based secrets provider for development and testing
    Supports JSON, YAML, and TOML file formats
    """
    
    def __init__(
        self,
        base_path: str,
        file_format: str = "json",
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        
        self.base_path = Path(base_path).resolve()
        self.file_format = file_format.lower()
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate provider configuration"""
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")
        
        if not self.base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {self.base_path}")
        
        if self.file_format not in {"json", "yaml", "yml", "toml"}:
            raise ValueError(f"Unsupported file format: {self.file_format}")
        
        # Check for required dependencies
        if self.file_format in {"yaml", "yml"} and not HAS_YAML:
            raise ValueError("PyYAML is required for YAML format support")
        
        if self.file_format == "toml" and not HAS_TOML:
            raise ValueError("tomllib/tomli is required for TOML format support")
    
    def _path_to_filename(self, path: str) -> Path:
        """
        Convert secret path to filename
        
        Args:
            path: Secret path (e.g., "jwt/app/keypair")
            
        Returns:
            File path for the secret
        """
        normalized_path = self._normalize_path(path)
        
        # Replace path separators with underscores for flat file structure
        filename = normalized_path.replace('/', '_')
        
        # Add appropriate extension
        if self.file_format == "json":
            filename += ".json"
        elif self.file_format in {"yaml", "yml"}:
            filename += ".yaml"
        elif self.file_format == "toml":
            filename += ".toml"
        
        return self.base_path / filename
    
    def _load_file_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Load data from file based on format
        
        Args:
            file_path: Path to file
            
        Returns:
            Loaded data as dictionary
            
        Raises:
            SecretsProviderError: If file cannot be loaded
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if self.file_format == "json":
                    return json.load(f)
                elif self.file_format in {"yaml", "yml"}:
                    if not HAS_YAML:
                        raise SecretsProviderError("PyYAML not available for YAML files")
                    return yaml.safe_load(f) or {}
                elif self.file_format == "toml":
                    if not HAS_TOML:
                        raise SecretsProviderError("tomllib/tomli not available for TOML files")
                    content = f.read()
                    return tomllib.loads(content)
                else:
                    raise SecretsProviderError(f"Unsupported file format: {self.file_format}")
                    
        except FileNotFoundError:
            raise SecretNotFoundError(f"Secret file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise SecretsProviderError(f"Invalid JSON in {file_path}: {e}")
        except yaml.YAMLError as e:
            raise SecretsProviderError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise SecretsProviderError(f"Failed to load {file_path}: {e}")
    
    def _save_file_data(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Save data to file based on format
        
        Args:
            file_path: Path to file
            data: Data to save
            
        Raises:
            SecretsProviderError: If file cannot be saved
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if self.file_format == "json":
                    json.dump(data, f, indent=2, sort_keys=True)
                elif self.file_format in {"yaml", "yml"}:
                    if not HAS_YAML:
                        raise SecretsProviderError("PyYAML not available for YAML files")
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=True)
                elif self.file_format == "toml":
                    # Note: tomllib is read-only, would need tomli-w for writing
                    raise SecretsProviderError("TOML writing not supported")
                else:
                    raise SecretsProviderError(f"Unsupported file format: {self.file_format}")
                    
        except Exception as e:
            raise SecretsProviderError(f"Failed to save {file_path}: {e}")
    
    async def get_secret(self, path: str) -> SecretData:
        """
        Retrieve secret from file
        
        Args:
            path: Secret path
            
        Returns:
            Secret data dictionary
            
        Raises:
            SecretNotFoundError: If secret file doesn't exist
            SecretsProviderError: If file cannot be loaded
        """
        file_path = self._path_to_filename(path)
        data = self._load_file_data(file_path)
        
        return self._validate_secret_data(data, str(path))
    
    async def put_secret(self, path: str, data: SecretData) -> bool:
        """
        Store secret to file
        
        Args:
            path: Secret path
            data: Secret data to store
            
        Returns:
            True if successful
            
        Raises:
            SecretsProviderError: If file cannot be saved
        """
        if self.file_format == "toml":
            logger.warning("TOML format does not support writing secrets")
            return False
        
        try:
            file_path = self._path_to_filename(path)
            self._save_file_data(file_path, data)
            logger.info(f"Successfully stored secret: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {path}: {e}")
            raise SecretsProviderError(f"Failed to store secret {path}: {e}")
    
    async def delete_secret(self, path: str) -> bool:
        """
        Delete secret file
        
        Args:
            path: Secret path
            
        Returns:
            True if successful or file didn't exist
        """
        try:
            file_path = self._path_to_filename(path)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Successfully deleted secret: {path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {path}: {e}")
            raise SecretsProviderError(f"Failed to delete secret {path}: {e}")
    
    async def list_secrets(self, path_prefix: str = "") -> List[str]:
        """
        List available secret files
        
        Args:
            path_prefix: Optional path prefix to filter results
            
        Returns:
            List of secret paths
        """
        try:
            secrets = []
            
            # Get file extension for current format
            if self.file_format == "json":
                extension = ".json"
            elif self.file_format in {"yaml", "yml"}:
                extension = ".yaml"
            elif self.file_format == "toml":
                extension = ".toml"
            else:
                return []
            
            # Scan directory for files with matching extension
            for file_path in self.base_path.glob(f"*{extension}"):
                if file_path.is_file():
                    # Convert filename back to secret path
                    name = file_path.stem
                    secret_path = name.replace('_', '/')
                    
                    # Apply prefix filter if specified
                    if not path_prefix or secret_path.startswith(path_prefix):
                        secrets.append(secret_path)
            
            return sorted(secrets)
            
        except Exception as e:
            logger.warning(f"Failed to list secrets: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check if file provider is healthy
        
        Returns:
            True if base path is accessible
        """
        try:
            # Check if we can read the directory
            if not self.base_path.exists() or not self.base_path.is_dir():
                self._healthy = False
                return False
            
            # Try to list directory contents
            list(self.base_path.iterdir())
            
            self._healthy = True
            return True
            
        except Exception as e:
            logger.warning(f"File provider health check failed: {e}")
            self._healthy = False
            return False
    
    def __repr__(self) -> str:
        """String representation of provider"""
        return f"FileProvider(base_path={self.base_path}, format={self.file_format})"