"""
Configuration handler chain orchestrator.
Coordinates multiple handlers using Chain of Responsibility pattern.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from .configuration_handler import ConfigurationHandler, ReloadContext, ReloadStatus
from .json_config_handler import JsonConfigHandler
from .env_config_handler import EnvConfigHandler  
from .yaml_config_handler import YamlConfigHandler
from .validation_handler import ValidationHandler

logger = logging.getLogger(__name__)


class ConfigurationHandlerChain:
    """
    Orchestrates configuration file processing through handler chain.
    
    REFACTORED: Replaces 22-complexity _perform_reload method with
    focused, single-responsibility handlers.
    """
    
    def __init__(self):
        """Initialize the handler chain with default handlers."""
        self._chain = self._build_default_chain()
    
    def _build_default_chain(self) -> ConfigurationHandler:
        """Build the default handler chain."""
        # Create handlers
        json_handler = JsonConfigHandler()
        env_handler = EnvConfigHandler()
        yaml_handler = YamlConfigHandler()
        validation_handler = ValidationHandler()
        
        # Chain handlers together
        json_handler.set_next(env_handler)
        env_handler.set_next(yaml_handler)
        yaml_handler.set_next(validation_handler)
        
        return json_handler
    
    def process_configurations(self, config_paths: List[Path], 
                             original_config: Dict[str, Any],
                             tenant_id: Optional[str] = None) -> ReloadContext:
        """
        Process multiple configuration files through the handler chain.
        
        COMPLEXITY REDUCTION: This method replaces the original 22-complexity
        _perform_reload method with a simple 3-step process:
        1. Initialize context
        2. Process each file through chain
        3. Return results
        
        Args:
            config_paths: List of configuration file paths to process
            original_config: Current configuration for comparison
            tenant_id: Optional tenant identifier for multi-tenant setups
            
        Returns:
            ReloadContext containing processing results and new configuration
        """
        # Step 1: Initialize context (Complexity: 1)
        context = ReloadContext(
            config_paths=config_paths,
            original_config=original_config.copy(),
            new_config={},
            changed_keys=[],
            errors=[],
            warnings=[],
            status=ReloadStatus.IN_PROGRESS,
            tenant_id=tenant_id
        )
        
        # Step 2: Process each file through handler chain (Complexity: 1)  
        for config_path in config_paths:
            if not config_path.exists():
                context.add_warning(f"Configuration file {config_path} does not exist")
                continue
                
            try:
                context = self._chain.process(config_path, context)
            except Exception as e:
                context.add_error(f"Failed to process {config_path}: {str(e)}")
                logger.exception(f"Handler chain failed for {config_path}")
        
        # Step 3: Finalize and return results (Complexity: 1)
        context.status = self._determine_final_status(context)
        
        logger.info(
            f"Configuration processing completed: {context.status.value}, "
            f"errors: {len(context.errors)}, warnings: {len(context.warnings)}, "
            f"changes: {len(context.changed_keys)}"
        )
        
        return context
    
    def _determine_final_status(self, context: ReloadContext) -> ReloadStatus:
        """Determine final status based on processing results."""
        if context.has_errors():
            return ReloadStatus.FAILED
        elif context.warnings:
            return ReloadStatus.PARTIAL_SUCCESS  
        else:
            return ReloadStatus.SUCCESS
    
    def add_handler(self, handler: ConfigurationHandler, position: int = -1) -> None:
        """
        Add a custom handler to the chain.
        
        Args:
            handler: Handler to add
            position: Position in chain (-1 for end, before validation)
        """
        if position == -1:
            # Add before validation handler (which should be last)
            current = self._chain
            while current._next_handler and not isinstance(current._next_handler, ValidationHandler):
                current = current._next_handler
            
            # Insert before validation
            handler.set_next(current._next_handler)
            current.set_next(handler)
        else:
            # Insert at specific position (more complex, not implemented for simplicity)
            logger.warning(f"Positional insertion not implemented, adding at end")
            self.add_handler(handler, -1)
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['.json', '.env', '.environment', '.yaml', '.yml']
    
    def validate_configuration_files(self, config_paths: List[Path]) -> Dict[Path, bool]:
        """
        Validate that configuration files can be handled.
        
        Args:
            config_paths: List of paths to validate
            
        Returns:
            Dict mapping paths to whether they can be handled
        """
        results = {}
        dummy_context = ReloadContext(
            config_paths=[],
            original_config={},
            new_config={},
            changed_keys=[],
            errors=[],
            warnings=[],
            status=ReloadStatus.PENDING
        )
        
        for path in config_paths:
            # Check if any handler can process this file
            can_handle = self._can_chain_handle(path, dummy_context)
            results[path] = can_handle
            
            if not can_handle:
                logger.warning(f"No handler available for {path}")
        
        return results
    
    def _can_chain_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """Check if any handler in chain can process the file."""
        current = self._chain
        
        while current:
            if current.can_handle(config_path, context):
                return True
            current = current._next_handler
        
        return False
    
    def get_chain_info(self) -> List[str]:
        """Get information about handlers in the chain."""
        info = []
        current = self._chain
        position = 1
        
        while current:
            handler_name = current.__class__.__name__
            info.append(f"{position}. {handler_name}")
            current = current._next_handler
            position += 1
        
        return info
    
    def reset_chain(self) -> None:
        """Reset to default handler chain."""
        self._chain = self._build_default_chain()
        logger.info("Handler chain reset to defaults")


def create_configuration_handler_chain() -> ConfigurationHandlerChain:
    """
    Factory function to create a configured handler chain.
    
    This is the main entry point for replacing the 22-complexity method.
    """
    return ConfigurationHandlerChain()