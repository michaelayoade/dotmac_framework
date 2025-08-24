"""
Base configuration handler for Chain of Responsibility pattern.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReloadStatus(Enum):
    """Status of configuration reload operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class ReloadContext:
    """Context object passed through the handler chain."""
    config_paths: List[Path]
    original_config: Dict[str, Any]
    new_config: Dict[str, Any]
    changed_keys: List[str]
    errors: List[str]
    warnings: List[str]
    status: ReloadStatus
    tenant_id: Optional[str] = None
    
    def add_error(self, error: str) -> None:
        """Add an error to the context."""
        self.errors.append(error)
        logger.error(f"Config reload error: {error}")
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the context."""
        self.warnings.append(warning)
        logger.warning(f"Config reload warning: {warning}")
    
    def merge_config(self, config_data: Dict[str, Any], source: str) -> None:
        """Merge configuration data from a source."""
        for key, value in config_data.items():
            if key in self.new_config and self.new_config[key] != value:
                self.changed_keys.append(f"{source}:{key}")
            self.new_config[key] = value
    
    def has_errors(self) -> bool:
        """Check if context has any errors."""
        return len(self.errors) > 0
    
    def has_changes(self) -> bool:
        """Check if there are any configuration changes."""
        return len(self.changed_keys) > 0


class ConfigurationHandler(ABC):
    """
    Base class for configuration handlers.
    
    This replaces the monolithic 22-complexity _perform_reload method
    with a chain of focused handlers.
    """
    
    def __init__(self, next_handler: Optional['ConfigurationHandler'] = None):
        """  Init   operation."""
        self._next_handler = next_handler
    
    def set_next(self, handler: 'ConfigurationHandler') -> 'ConfigurationHandler':
        """Set the next handler in the chain."""
        self._next_handler = handler
        return handler
    
    @abstractmethod
    def can_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """Check if this handler can process the given configuration path."""
        pass
    
    @abstractmethod
    def handle(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Process the configuration file.
        
        Args:
            config_path: Path to the configuration file
            context: Reload context with current state
            
        Returns:
            Updated reload context
        """
        pass
    
    def process(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Process configuration file through the chain.
        
        This method implements the Chain of Responsibility pattern.
        """
        try:
            if self.can_handle(config_path, context):
                logger.debug(f"Handler {self.__class__.__name__} processing {config_path}")
                context = self.handle(config_path, context)
            else:
                logger.debug(f"Handler {self.__class__.__name__} skipping {config_path}")
        except Exception as e:
            error_msg = f"Handler {self.__class__.__name__} failed for {config_path}: {str(e)}"
            context.add_error(error_msg)
            logger.exception(error_msg)
        
        # Pass to next handler in chain
        if self._next_handler:
            context = self._next_handler.process(config_path, context)
        
        return context
    
    def _is_file_readable(self, config_path: Path) -> bool:
        """Check if file exists and is readable."""
        try:
            return config_path.exists() and config_path.is_file() and config_path.stat().st_size > 0
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot access {config_path}: {e}")
            return False
    
    def _calculate_file_checksum(self, config_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        import hashlib
        
        try:
            with open(config_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate checksum for {config_path}: {e}")
            return ""
    
    def _backup_config_file(self, config_path: Path) -> Optional[Path]:
        """Create backup of configuration file."""
        import shutil
        from datetime import datetime
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_path.with_suffix(f"{config_path.suffix}.backup_{timestamp}")
            shutil.copy2(config_path, backup_path)
            logger.info(f"Created config backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup of {config_path}: {e}")
            return None


class ConfigurationHandlerError(Exception):
    """Exception raised by configuration handlers."""
    pass


class UnsupportedConfigurationError(ConfigurationHandlerError):
    """Exception raised when configuration format is not supported."""
    pass