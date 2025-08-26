"""
JSON configuration file handler.
"""

import json
from pathlib import Path
from typing import Dict, Any
import logging

from .configuration_handler import ConfigurationHandler, ReloadContext, ConfigurationHandlerError

logger = logging.getLogger(__name__)


class JsonConfigHandler(ConfigurationHandler):
    """Handler for JSON configuration files."""
    
    def can_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """Check if this is a JSON configuration file."""
        return (config_path.suffix.lower() == '.json' and 
                self._is_file_readable(config_path)
    
    def handle(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Process JSON configuration file.
        
        REFACTORED: Extracted from 22-complexity _perform_reload method.
        This handler focuses only on JSON file processing.
        """
        try:
            # Read and parse JSON file
            config_data = self._load_json_file(config_path)
            
            if config_data:
                # Validate JSON structure
                self._validate_json_config(config_data, config_path)
                
                # Merge configuration
                context.merge_config(config_data, f"json:{config_path.name}")
                
                logger.info(f"Successfully loaded JSON config from {config_path}")
            else:
                context.add_warning(f"JSON file {config_path} is empty or invalid")
                
        except ConfigurationHandlerError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ConfigurationHandlerError(f"Failed to process JSON config {config_path}: {str(e)}")
        
        return context
    
    def _load_json_file(self, config_path: Path) -> Dict[str, Any]:
        """Load and parse JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                if not content:
                    logger.warning(f"JSON file {config_path} is empty")
                    return {}
                
                config_data = json.loads(content)
                
                if not isinstance(config_data, dict):
                    raise ConfigurationHandlerError(
                        f"JSON config {config_path} must be an object, not {type(config_data).__name__}"
                    )
                
                return config_data
                
        except json.JSONDecodeError as e:
            raise ConfigurationHandlerError(
                f"Invalid JSON in {config_path} at line {e.lineno}, column {e.colno}: {e.msg}"
            )
        except UnicodeDecodeError as e:
            raise ConfigurationHandlerError(
                f"Cannot decode {config_path} as UTF-8: {str(e)}"
            )
    
    def _validate_json_config(self, config_data: Dict[str, Any], config_path: Path) -> None:
        """Validate JSON configuration structure."""
        # Basic validation - can be extended
        if not config_data:
            logger.warning(f"JSON config {config_path} is empty")
            return
        
        # Check for reserved keys that might cause conflicts
        reserved_keys = ['_metadata', '_version', '_checksum']
        found_reserved = [key for key in config_data.keys() if key in reserved_keys]
        
        if found_reserved:
            logger.warning(f"JSON config {config_path} contains reserved keys: {found_reserved}")
        
        # Validate nested structure depth (prevent excessive nesting)
        max_depth = 10
        if self._get_dict_depth(config_data) > max_depth:
            raise ConfigurationHandlerError(
                f"JSON config {config_path} exceeds maximum nesting depth of {max_depth}"
            )
        
        logger.debug(f"JSON config {config_path} validation passed")
    
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