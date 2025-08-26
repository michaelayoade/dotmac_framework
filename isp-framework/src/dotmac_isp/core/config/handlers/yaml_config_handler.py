"""
YAML configuration file handler.
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

from .configuration_handler import ConfigurationHandler, ReloadContext, ConfigurationHandlerError

logger = logging.getLogger(__name__)


class YamlConfigHandler(ConfigurationHandler):
    """Handler for YAML configuration files."""
    
    def can_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """Check if this is a YAML configuration file."""
        yaml_extensions = {'.yaml', '.yml'}
        return (config_path.suffix.lower() in yaml_extensions and 
                self._is_file_readable(config_path)
    
    def handle(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Process YAML configuration file.
        
        REFACTORED: Extracted from 22-complexity _perform_reload method.
        This handler focuses only on YAML file processing.
        """
        try:
            # Read and parse YAML file
            config_data = self._load_yaml_file(config_path)
            
            if config_data:
                # Validate YAML structure
                self._validate_yaml_config(config_data, config_path)
                
                # Merge configuration
                context.merge_config(config_data, f"yaml:{config_path.name}")
                
                logger.info(f"Successfully loaded YAML config from {config_path}")
            else:
                context.add_warning(f"YAML file {config_path} is empty or invalid")
                
        except ConfigurationHandlerError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ConfigurationHandlerError(f"Failed to process YAML config {config_path}: {str(e)}")
        
        return context
    
    def _load_yaml_file(self, config_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                if not content:
                    logger.warning(f"YAML file {config_path} is empty")
                    return {}
                
                config_data = yaml.safe_load(content)
                
                if config_data is None:
                    logger.warning(f"YAML file {config_path} contains only null/empty values")
                    return {}
                
                if not isinstance(config_data, dict):
                    raise ConfigurationHandlerError(
                        f"YAML config {config_path} must be an object, not {type(config_data).__name__}"
                    )
                
                return config_data
                
        except yaml.YAMLError as e:
            raise ConfigurationHandlerError(
                f"Invalid YAML in {config_path}: {str(e)}"
            )
        except UnicodeDecodeError as e:
            raise ConfigurationHandlerError(
                f"Cannot decode {config_path} as UTF-8: {str(e)}"
            )
    
    def _validate_yaml_config(self, config_data: Dict[str, Any], config_path: Path) -> None:
        """Validate YAML configuration structure."""
        if not config_data:
            logger.warning(f"YAML config {config_path} is empty")
            return
        
        # Check for reserved keys that might cause conflicts
        reserved_keys = ['_metadata', '_version', '_checksum', '__class__', '__module__']
        found_reserved = [key for key in config_data.keys() if key in reserved_keys]
        
        if found_reserved:
            logger.warning(f"YAML config {config_path} contains reserved keys: {found_reserved}")
        
        # Validate nested structure depth (prevent excessive nesting)
        max_depth = 10
        if self._get_dict_depth(config_data) > max_depth:
            raise ConfigurationHandlerError(
                f"YAML config {config_path} exceeds maximum nesting depth of {max_depth}"
            )
        
        # Check for potential security issues in YAML
        self._validate_yaml_security(config_data, config_path)
        
        logger.debug(f"YAML config {config_path} validation passed")
    
    def _get_dict_depth(self, d: Dict[str, Any], depth: int = 0) -> int:
        """Calculate maximum depth of nested dictionary."""
        if not isinstance(d, dict):
            return depth
        
        if not d:
            return depth + 1
        
        return max(
            self._get_dict_depth(value, depth + 1) 
            for value in d.values() 
            if isinstance(value, dict)
        ) if any(isinstance(value, dict) for value in d.values() else depth + 1
    
    def _validate_yaml_security(self, config_data: Dict[str, Any], config_path: Path) -> None:
        """Validate YAML for potential security issues."""
        # Check for potentially dangerous keys
        dangerous_keys = ['eval', 'exec', 'import', '__import__', 'compile']
        
        def check_keys(data, path=""):
            """Check Keys operation."""
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key in dangerous_keys:
                        logger.warning(
                            f"YAML config {config_path} contains potentially dangerous key '{key}' at {current_path}"
                        )
                    
                    check_keys(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    check_keys(item, f"{path}[{i}]")
        
        check_keys(config_data)