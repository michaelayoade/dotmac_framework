"""
Environment file configuration handler.
"""

import re
from pathlib import Path
from typing import Dict, Any
import logging

from .configuration_handler import ConfigurationHandler, ReloadContext, ConfigurationHandlerError

logger = logging.getLogger(__name__)


class EnvConfigHandler(ConfigurationHandler):
    """Handler for environment configuration files (.env, .environment)."""
    
    def can_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """Check if this is an environment configuration file."""
        env_extensions = {'.env', '.environment'}
        env_names = {'env', 'environment', '.env'}
        
        return ((config_path.suffix.lower() in env_extensions or 
                config_path.name.lower() in env_names) and
                self._is_file_readable(config_path)
    
    def handle(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Process environment configuration file.
        
        REFACTORED: Extracted from 22-complexity _perform_reload method.
        This handler focuses only on environment file processing.
        """
        try:
            # Parse environment file
            config_data = self._parse_env_file(config_path)
            
            if config_data:
                # Validate environment variables
                self._validate_env_config(config_data, config_path)
                
                # Merge configuration
                context.merge_config(config_data, f"env:{config_path.name}")
                
                logger.info(f"Successfully loaded env config from {config_path}")
            else:
                context.add_warning(f"Environment file {config_path} is empty or has no valid entries")
                
        except ConfigurationHandlerError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ConfigurationHandlerError(f"Failed to process env config {config_path}: {str(e)}")
        
        return context
    
    def _parse_env_file(self, config_path: Path) -> Dict[str, Any]:
        """Parse environment file into key-value pairs."""
        config_data = {}
        line_number = 0
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_number += 1
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    parsed_entry = self._parse_env_line(line, line_number)
                    if parsed_entry:
                        key, value = parsed_entry
                        config_data[key] = value
                        
        except UnicodeDecodeError as e:
            raise ConfigurationHandlerError(
                f"Cannot decode {config_path} as UTF-8: {str(e)}"
            )
        
        return config_data
    
    def _parse_env_line(self, line: str, line_number: int) -> tuple[str, Any] | None:
        """Parse a single line from environment file."""
        # Match pattern: KEY=VALUE or KEY="VALUE" or KEY='VALUE'
        env_pattern = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
        match = env_pattern.match(line)
        
        if not match:
            logger.warning(f"Invalid env line {line_number}: {line}")
            return None
        
        key, value = match.groups()
        
        # Handle quoted values
        value = self._process_env_value(value)
        
        # Convert to appropriate type
        typed_value = self._convert_env_value(value)
        
        return key, typed_value
    
    def _process_env_value(self, value: str) -> str:
        """Process environment value, handling quotes and escapes."""
        value = value.strip()
        
        # Handle quoted values
        if len(value) >= 2:
            if (value.startswith('"') and value.endswith('"') or \
               (value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
                
                # Handle escape sequences in double quotes
                if value.startswith('"'):
                    value = value.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        
        return value
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        if not value:
            return ""
        
        # Boolean values
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Numeric values
        try:
            # Try integer first
            if '.' not in value and 'e' not in value.lower():
                return int(value)
        except ValueError:
            pass
        
        try:
            # Try float
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _validate_env_config(self, config_data: Dict[str, Any], config_path: Path) -> None:
        """Validate environment configuration."""
        if not config_data:
            logger.warning(f"Environment config {config_path} has no valid entries")
            return
        
        # Check for required patterns
        required_prefixes = ['APP_', 'SERVICE_', 'DB_', 'REDIS_']
        has_required = any(
            key.startswith(prefix) for key in config_data.keys() 
            for prefix in required_prefixes
        )
        
        if not has_required:
            logger.warning(
                f"Environment config {config_path} may not contain application configuration. "
                f"Expected keys with prefixes: {required_prefixes}"
            )
        
        # Check for potentially sensitive data
        sensitive_patterns = ['password', 'secret', 'key', 'token']
        sensitive_keys = [
            key for key in config_data.keys()
            if any(pattern in key.lower() for pattern in sensitive_patterns)
        ]
        
        if sensitive_keys:
            logger.info(f"Environment config {config_path} contains {len(sensitive_keys)} potentially sensitive keys")
        
        logger.debug(f"Environment config {config_path} validation passed with {len(config_data)} entries")