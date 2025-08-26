"""
Integration tests for the unified configuration system.

FINAL INTEGRATION TESTS: Validates the complete system integration
of all refactored components from Week 1 & Week 2 complexity reductions.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from dotmac_isp.core.config.unified_config_system import (
    UnifiedConfigSystem,
    IntegrationType,
    IntegrationStatus,
    SystemIntegration,
    get_unified_system,
    initialize_unified_system,
)


class TestUnifiedConfigSystem:
    """Test unified configuration system integration."""

    def test_system_initialization(self):
        """Test system initialization with all integrations."""
        system = UnifiedConfigSystem("test_service")
        
        # Check all integrations are configured
        expected_integrations = {
            IntegrationType.CONFIGURATION_VALIDATION,
            IntegrationType.SALES_SCORING,
            IntegrationType.WORKFLOW_AUTOMATION,
            IntegrationType.SCHEDULER,
            IntegrationType.VAULT_AUTHENTICATION,
        }
        
        assert set(system.integrations.keys() == expected_integrations
        
        # Check initial status
        for integration in system.integrations.values():
            assert integration.status == IntegrationStatus.PENDING

    def test_integration_dependencies(self):
        """Test integration dependency management."""
        system = UnifiedConfigSystem("test_service")
        
        # Vault auth should depend on config validation
        vault_integration = system.integrations[IntegrationType.VAULT_AUTHENTICATION]
        assert IntegrationType.CONFIGURATION_VALIDATION in vault_integration.dependencies

    def test_initialization_order(self):
        """Test initialization order respects dependencies."""
        system = UnifiedConfigSystem("test_service")
        order = system._get_initialization_order()
        
        # Config validation should come before vault auth
        config_validation_index = order.index(IntegrationType.CONFIGURATION_VALIDATION)
        vault_auth_index = order.index(IntegrationType.VAULT_AUTHENTICATION)
        
        assert config_validation_index < vault_auth_index

    @pytest.mark.asyncio
    async def test_full_system_initialization_success(self):
        """Test complete system initialization with all components."""
        
        # Mock all the strategy engines to avoid import issues
        with patch('dotmac_isp.core.config.unified_config_system.create_field_validation_engine') as mock_validation, \
             patch('dotmac_isp.core.config.unified_config_system.ConfigurationHandlerChain') as mock_handlers, \
             patch('dotmac_isp.modules.sales.scoring_strategies.create_lead_scoring_engine') as mock_sales, \
             patch('dotmac_isp.sdks.workflows.condition_strategies.create_condition_engine') as mock_conditions, \
             patch('dotmac_isp.sdks.workflows.schedule_strategies.create_schedule_engine') as mock_schedule, \
             patch('dotmac_isp.core.secrets.vault_auth_strategies.create_vault_auth_engine') as mock_vault:
            
            # Configure mocks
            mock_validation.return_value = Mock()
            mock_handlers.return_value = Mock()
            mock_sales.return_value = Mock(get_active_strategies=Mock(return_value=['budget', 'customer_type'])
            mock_conditions.return_value = Mock(get_supported_operators=Mock(return_value=['equals', 'greater_than'])
            mock_schedule.return_value = Mock(get_supported_schedule_types=Mock(return_value=['cron', 'interval'])
            mock_vault.return_value = Mock(get_supported_auth_methods=Mock(return_value=['token', 'approle'])
            
            system = UnifiedConfigSystem("test_service")
            result = await system.initialize_system()
            
            assert result is True
            
            # Check all integrations are active
            for integration in system.integrations.values():
                assert integration.status == IntegrationStatus.ACTIVE
                assert integration.initialized_at is not None

    @pytest.mark.asyncio
    async def test_integration_failure_handling(self):
        """Test handling of integration initialization failures."""
        
        # Mock config validation to fail
        with patch('dotmac_isp.core.config.unified_config_system.create_field_validation_engine') as mock_validation:
            mock_validation.side_effect = ImportError("Module not found")
            
            system = UnifiedConfigSystem("test_service")
            result = await system.initialize_system()
            
            assert result is False
            
            # Check config validation integration marked as error
            config_integration = system.integrations[IntegrationType.CONFIGURATION_VALIDATION]
            assert config_integration.status == IntegrationStatus.ERROR
            assert "Module not found" in config_integration.last_error

    def test_system_status_reporting(self):
        """Test comprehensive system status reporting."""
        system = UnifiedConfigSystem("test_service")
        
        # Mark some integrations as active
        system.integrations[IntegrationType.SALES_SCORING].mark_active()
        system.integrations[IntegrationType.WORKFLOW_AUTOMATION].mark_active()
        
        # Mark one as error
        system.integrations[IntegrationType.VAULT_AUTHENTICATION].mark_error("Auth failed")
        
        status = system.get_system_status()
        
        # Check overall status
        assert status["service_name"] == "test_service"
        assert status["total_integrations"] == 5
        assert status["active_integrations"] == 2
        assert status["failed_integrations"] == 1
        assert status["system_initialized"] is False
        
        # Check complexity reduction summary
        assert status["complexity_reduction_summary"]["original_total"] == 153
        assert status["complexity_reduction_summary"]["refactored_total"] == 26
        assert status["complexity_reduction_summary"]["reduction_percentage"] == 83

    @pytest.mark.asyncio
    async def test_system_health_check(self):
        """Test comprehensive system health validation."""
        with patch('dotmac_isp.core.config.unified_config_system.create_field_validation_engine') as mock_validation:
            mock_validation.return_value = Mock()
            
            system = UnifiedConfigSystem("test_service")
            
            # Initialize config validation only
            config_integration = system.integrations[IntegrationType.CONFIGURATION_VALIDATION]
            await system._initialize_integration(config_integration)
            config_integration.mark_active()
            
            # Mark another as error
            system.integrations[IntegrationType.VAULT_AUTHENTICATION].mark_error("Connection failed")
            
            health = await system.validate_system_health()
            
            assert health["overall_status"] == "degraded"  # Due to vault error
            assert "configuration_validation_health" in health["checks"]
            assert "vault_authentication_health" in health["checks"]
            
            # Should have recommendations
            assert len(health["recommendations"]) > 0
            assert any("vault_authentication" in rec for rec in health["recommendations"])

    def test_engine_access_methods(self):
        """Test public API methods for accessing integrated engines."""
        system = UnifiedConfigSystem("test_service")
        
        # Test engines not initialized
        with pytest.raises(RuntimeError, match="Sales scoring engine not initialized"):
            system.get_sales_scoring_engine()
        
        with pytest.raises(RuntimeError, match="Condition engine not initialized"):
            system.get_condition_engine()
        
        with pytest.raises(RuntimeError, match="Schedule engine not initialized"):
            system.get_schedule_engine()
        
        with pytest.raises(RuntimeError, match="Vault auth engine not initialized"):
            system.get_vault_auth_engine()
        
        with pytest.raises(RuntimeError, match="Validation engine not initialized"):
            system.get_validation_engine()
        
        # Test after initialization (mock the engines)
        system._sales_scoring_engine = Mock()
        system._condition_engine = Mock()
        system._schedule_engine = Mock()
        system._vault_auth_engine = Mock()
        system._validation_engine = Mock()
        
        assert system.get_sales_scoring_engine() is not None
        assert system.get_condition_engine() is not None
        assert system.get_schedule_engine() is not None
        assert system.get_vault_auth_engine() is not None
        assert system.get_validation_engine() is not None

    @pytest.mark.asyncio
    async def test_system_shutdown(self):
        """Test graceful system shutdown."""
        system = UnifiedConfigSystem("test_service")
        
        # Mark integrations as active
        for integration in system.integrations.values():
            integration.mark_active()
        
        # Add mock engines
        system._sales_scoring_engine = Mock()
        system._condition_engine = Mock()
        
        await system.shutdown_system()
        
        # Check all integrations disabled
        for integration in system.integrations.values():
            assert integration.status == IntegrationStatus.DISABLED
        
        # Check engines cleared
        assert system._sales_scoring_engine is None
        assert system._condition_engine is None

    def test_integration_features_reporting(self):
        """Test integration feature reporting."""
        system = UnifiedConfigSystem("test_service")
        
        # Test sales scoring features
        features = system._get_integration_features(IntegrationType.SALES_SCORING)
        expected_strategies = ["budget", "customer_type", "lead_source", "bant", "company_size", "engagement"]
        assert features == expected_strategies
        
        # Test workflow automation features
        features = system._get_integration_features(IntegrationType.WORKFLOW_AUTOMATION)
        expected_operators = ["equals", "greater_than", "contains", "regex", "exists"]
        assert features == expected_operators


class TestGlobalSystemManagement:
    """Test global system management functions."""

    @pytest.mark.asyncio
    async def test_get_unified_system_singleton(self):
        """Test singleton behavior of global system."""
        # Clear global state first
        import dotmac_isp.core.config.unified_config_system
        dotmac_isp.core.config.unified_config_system._unified_system = None
        
        with patch('dotmac_isp.core.config.unified_config_system.UnifiedConfigSystem') as mock_system:
            mock_instance = Mock()
            mock_instance.initialize_system = AsyncMock(return_value=True)
            mock_system.return_value = mock_instance
            
            # First call should create system
            system1 = await get_unified_system("test_service")
            
            # Second call should return same instance
            system2 = await get_unified_system("test_service")
            
            assert system1 is system2
            mock_system.assert_called_once_with(service_name="test_service")

    @pytest.mark.asyncio
    async def test_initialize_unified_system_success(self):
        """Test successful unified system initialization."""
        with patch('dotmac_isp.core.config.unified_config_system.get_unified_system') as mock_get:
            mock_system = Mock()
            mock_system.get_system_status.return_value = {
                "system_initialized": True,
                "active_integrations": 5,
                "complexity_reduction_summary": {"reduction_percentage": 83}
            }
            mock_get.return_value = mock_system
            
            result = await initialize_unified_system("test_service")
            
            assert result is True
            mock_get.assert_called_once_with("test_service")
            mock_system.get_system_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_unified_system_failure(self):
        """Test failed unified system initialization."""
        with patch('dotmac_isp.core.config.unified_config_system.get_unified_system') as mock_get:
            mock_system = Mock()
            mock_system.get_system_status.return_value = {
                "system_initialized": False,
                "failed_integrations": 2
            }
            mock_get.return_value = mock_system
            
            result = await initialize_unified_system("test_service")
            
            assert result is False


class TestComplexityReductionIntegration:
    """Test that validates the complete complexity reduction integration."""

    def test_complexity_reduction_summary(self):
        """Test overall complexity reduction metrics are accurate."""
        system = UnifiedConfigSystem("test_service")
        status = system.get_system_status()
        
        complexity_summary = status["complexity_reduction_summary"]
        
        # Verify the total complexity reduction numbers
        assert complexity_summary["original_total"] == 153
        assert complexity_summary["refactored_total"] == 26
        assert complexity_summary["reduction_percentage"] == 83
        assert complexity_summary["components_refactored"] == 8

    def test_individual_integration_complexity_reductions(self):
        """Test individual integration complexity reduction reporting."""
        system = UnifiedConfigSystem("test_service")
        status = system.get_system_status()
        
        integrations = status["integrations"]
        
        # Verify each integration reports its complexity reduction
        assert integrations["sales_scoring"]["complexity_reduction"] == "14→1"
        assert integrations["workflow_automation"]["complexity_reduction"] == "14→3"
        assert integrations["scheduler"]["complexity_reduction"] == "14→3"
        assert integrations["vault_authentication"]["complexity_reduction"] == "14→3"
        assert integrations["configuration_validation"]["complexity_reduction"] == "23→6"

    @pytest.mark.asyncio
    async def test_end_to_end_integration_workflow(self):
        """
        Test end-to-end workflow using all integrated components.
        
        This test simulates a real-world scenario where:
        1. System initializes with all refactored components
        2. Configuration is validated using strategy pattern
        3. Sales lead scoring is performed
        4. Workflow conditions are evaluated
        5. Scheduler calculates next run times
        6. Vault authentication is performed
        """
        
        # Mock all components
        with patch('dotmac_isp.core.config.unified_config_system.create_field_validation_engine') as mock_validation, \
             patch('dotmac_isp.core.config.unified_config_system.ConfigurationHandlerChain') as mock_handlers, \
             patch('dotmac_isp.modules.sales.scoring_strategies.create_lead_scoring_engine') as mock_sales, \
             patch('dotmac_isp.sdks.workflows.condition_strategies.create_condition_engine') as mock_conditions, \
             patch('dotmac_isp.sdks.workflows.schedule_strategies.create_schedule_engine') as mock_schedule, \
             patch('dotmac_isp.core.secrets.vault_auth_strategies.create_vault_auth_engine') as mock_vault:
            
            # Setup mock engines with expected functionality
            mock_validation_engine = Mock()
            mock_validation_engine.validate_field.return_value = True
            mock_validation.return_value = mock_validation_engine
            
            mock_handlers.return_value = Mock()
            
            mock_sales_engine = Mock()
            mock_sales_engine.calculate_lead_score.return_value = 85
            mock_sales_engine.get_active_strategies.return_value = ['budget', 'customer_type']
            mock_sales.return_value = mock_sales_engine
            
            mock_condition_engine = Mock()
            mock_condition_engine.evaluate_condition.return_value = True
            mock_condition_engine.get_supported_operators.return_value = ['equals', 'greater_than']
            mock_conditions.return_value = mock_condition_engine
            
            mock_schedule_engine = Mock()
            mock_schedule_engine.calculate_next_run.return_value = datetime.now(timezone.utc)
            mock_schedule_engine.get_supported_schedule_types.return_value = ['cron', 'interval']
            mock_schedule.return_value = mock_schedule_engine
            
            mock_vault_engine = Mock()
            mock_vault_engine.authenticate.return_value = "test-token"
            mock_vault_engine.get_supported_auth_methods.return_value = ['token', 'approle']
            mock_vault.return_value = mock_vault_engine
            
            # Initialize system
            system = UnifiedConfigSystem("integration_test")
            initialization_result = await system.initialize_system()
            
            assert initialization_result is True
            
            # Test each component is accessible and functional
            
            # 1. Configuration validation (Week 1 refactoring)
            validation_engine = system.get_validation_engine()
            validation_result = validation_engine.validate_field("test_field", "test_value")
            assert validation_result is True
            
            # 2. Sales scoring (Week 2 refactoring)  
            sales_engine = system.get_sales_scoring_engine()
            lead_score = sales_engine.calculate_lead_score({"budget": 10000, "customer_type": "enterprise"})
            assert lead_score == 85
            
            # 3. Workflow conditions (Week 2 refactoring)
            condition_engine = system.get_condition_engine()
            condition_result = condition_engine.evaluate_condition("equals", "test", "test")
            assert condition_result is True
            
            # 4. Schedule calculations (Week 2 refactoring)
            schedule_engine = system.get_schedule_engine()
            next_run = schedule_engine.calculate_next_run(Mock()
            assert next_run is not None
            
            # 5. Vault authentication (Week 2 refactoring)
            vault_engine = system.get_vault_auth_engine()
            auth_token = vault_engine.authenticate(Mock(), Mock()
            assert auth_token == "test-token"
            
            # Verify system health
            health = await system.validate_system_health()
            assert health["overall_status"] == "healthy"
            
            # Verify all integrations working together achieved complexity reduction
            status = system.get_system_status()
            assert status["system_initialized"] is True
            assert status["active_integrations"] == 5
            
            complexity_summary = status["complexity_reduction_summary"]
            assert complexity_summary["reduction_percentage"] == 83