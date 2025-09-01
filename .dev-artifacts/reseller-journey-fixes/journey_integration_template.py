"""
Journey Integration Template
Integrates all reseller journey fixes with the existing JourneyOrchestrator system
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Import all the journey templates we created
from .customer_success_journey import CUSTOMER_SUCCESS_JOURNEY_TEMPLATES
from .reseller_performance_journey import RESELLER_PERFORMANCE_JOURNEY_TEMPLATES  
from .commission_processing_automation import COMMISSION_PROCESSING_JOURNEY_TEMPLATES
from .lead_nurturing_automation import LEAD_NURTURING_JOURNEY_TEMPLATES
from .payment_processing_integration import PAYMENT_PROCESSING_JOURNEY_TEMPLATES

# Import services
from .customer_success_journey import CustomerSuccessJourneyService
from .reseller_performance_journey import ResellerPerformanceJourneyService
from .commission_processing_automation import CommissionProcessingService
from .customer_assignment_automation import CustomerAssignmentService
from .lead_nurturing_automation import LeadNurturingService
from .payment_processing_integration import PaymentProcessingService


class EnhancedJourneyTemplates:
    """
    Extended journey templates that include all the missing reseller workflows
    Integrates with the existing JourneyOrchestrator.ts system
    """
    
    @staticmethod
    def get_all_journey_templates() -> Dict[str, Any]:
        """Get complete set of journey templates including new reseller workflows"""
        
        # Merge all journey templates
        all_templates = {}
        
        # Customer Success Journeys
        all_templates.update(CUSTOMER_SUCCESS_JOURNEY_TEMPLATES)
        
        # Reseller Performance Journeys  
        all_templates.update(RESELLER_PERFORMANCE_JOURNEY_TEMPLATES)
        
        # Commission Processing Journeys
        all_templates.update(COMMISSION_PROCESSING_JOURNEY_TEMPLATES)
        
        # Lead Nurturing Journeys
        all_templates.update(LEAD_NURTURING_JOURNEY_TEMPLATES)
        
        # Payment Processing Journeys
        all_templates.update(PAYMENT_PROCESSING_JOURNEY_TEMPLATES)
        
        return all_templates
    
    @staticmethod
    def get_enhanced_isp_journey_templates() -> Dict[str, Any]:
        """
        Enhanced version of the ISP_JOURNEY_TEMPLATES from the existing system
        Adds the missing journey types identified in the gap analysis
        """
        
        # Get the new templates
        new_templates = EnhancedJourneyTemplates.get_all_journey_templates()
        
        # Original ISP templates from frontend/packages/journey-orchestration/src/index.ts
        original_templates = {
            "CUSTOMER_ACQUISITION": {
                "id": "customer_acquisition",
                "name": "Customer Acquisition Journey",
                "description": "Lead to customer conversion with service activation",
                "category": "acquisition",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "lead_qualification",
                        "name": "Lead Qualification", 
                        "description": "Qualify lead and assess service needs",
                        "stage": "lead",
                        "order": 1,
                        "type": "manual",
                        "packageName": "crm",
                        "estimatedDuration": 30
                    },
                    {
                        "id": "customer_conversion",
                        "name": "Convert to Customer",
                        "description": "Convert qualified lead to customer account",
                        "stage": "customer",
                        "order": 2,
                        "type": "integration", 
                        "packageName": "crm",
                        "actionType": "convert_lead",
                        "estimatedDuration": 15
                    },
                    {
                        "id": "service_selection",
                        "name": "Service Selection",
                        "description": "Customer selects service plan and options",
                        "stage": "customer",
                        "order": 3,
                        "type": "manual",
                        "packageName": "business-logic",
                        "estimatedDuration": 45
                    },
                    {
                        "id": "service_activation",
                        "name": "Service Activation",
                        "description": "Activate customer service and billing",
                        "stage": "active_service",
                        "order": 4,
                        "type": "integration",
                        "packageName": "business-logic",
                        "actionType": "activate_service",
                        "estimatedDuration": 30
                    },
                    {
                        "id": "installation_schedule",
                        "name": "Schedule Installation",
                        "description": "Schedule technician for service installation",
                        "stage": "active_service",
                        "order": 5,
                        "type": "integration",
                        "packageName": "field-ops",
                        "actionType": "schedule_installation",
                        "estimatedDuration": 20
                    }
                ]
            },
            
            "SUPPORT_RESOLUTION": {
                "id": "support_resolution",
                "name": "Support Resolution Journey",
                "description": "Customer support ticket resolution workflow",
                "category": "support",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "ticket_triage",
                        "name": "Ticket Triage",
                        "description": "Categorize and prioritize support ticket",
                        "stage": "support",
                        "order": 1,
                        "type": "automated",
                        "packageName": "support-system",
                        "estimatedDuration": 5
                    },
                    {
                        "id": "agent_assignment",
                        "name": "Agent Assignment", 
                        "description": "Assign ticket to appropriate support agent",
                        "stage": "support",
                        "order": 2,
                        "type": "automated",
                        "packageName": "support-system",
                        "estimatedDuration": 2
                    },
                    {
                        "id": "issue_diagnosis",
                        "name": "Issue Diagnosis",
                        "description": "Diagnose customer issue",
                        "stage": "support",
                        "order": 3,
                        "type": "manual",
                        "packageName": "support-system",
                        "estimatedDuration": 60
                    },
                    {
                        "id": "resolution_action",
                        "name": "Resolution Action",
                        "description": "Take action to resolve customer issue",
                        "stage": "support",
                        "order": 4,
                        "type": "manual",
                        "packageName": "support-system",
                        "estimatedDuration": 45
                    },
                    {
                        "id": "customer_verification",
                        "name": "Customer Verification",
                        "description": "Verify resolution with customer",
                        "stage": "support",
                        "order": 5,
                        "type": "manual",
                        "packageName": "support-system",
                        "estimatedDuration": 15
                    }
                ]
            },
            
            "CUSTOMER_ONBOARDING": {
                "id": "customer_onboarding",
                "name": "Customer Onboarding Journey",
                "description": "New customer onboarding and setup",
                "category": "onboarding",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "welcome_communication",
                        "name": "Welcome Communication",
                        "description": "Send welcome email and setup instructions",
                        "stage": "customer",
                        "order": 1,
                        "type": "notification",
                        "packageName": "communication-system",
                        "estimatedDuration": 5
                    },
                    {
                        "id": "billing_setup",
                        "name": "Billing Setup",
                        "description": "Set up customer billing and payment methods",
                        "stage": "customer",
                        "order": 2,
                        "type": "integration",
                        "packageName": "billing-system",
                        "actionType": "setup_billing",
                        "estimatedDuration": 30
                    },
                    {
                        "id": "equipment_provisioning",
                        "name": "Equipment Provisioning",
                        "description": "Provision and configure customer equipment",
                        "stage": "active_service",
                        "order": 3,
                        "type": "integration",
                        "packageName": "business-logic",
                        "actionType": "provision_equipment",
                        "estimatedDuration": 60
                    },
                    {
                        "id": "service_testing",
                        "name": "Service Testing",
                        "description": "Test service connectivity and functionality",
                        "stage": "active_service",
                        "order": 4,
                        "type": "integration",
                        "packageName": "field-ops",
                        "actionType": "test_service",
                        "estimatedDuration": 30
                    },
                    {
                        "id": "onboarding_complete",
                        "name": "Onboarding Complete",
                        "description": "Finalize onboarding and send confirmation",
                        "stage": "active_service",
                        "order": 5,
                        "type": "notification",
                        "packageName": "communication-system",
                        "estimatedDuration": 10
                    }
                ]
            }
        }
        
        # Merge original and new templates
        enhanced_templates = {**original_templates, **new_templates}
        
        return enhanced_templates


class ResellerJourneyOrchestrator:
    """
    Enhanced journey orchestrator specifically for reseller workflows
    Extends the existing JourneyOrchestrator with reseller-specific functionality
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.services = {
            'customer_success': CustomerSuccessJourneyService(None, tenant_id),
            'performance': ResellerPerformanceJourneyService(None, tenant_id), 
            'commission': CommissionProcessingService(None, tenant_id),
            'assignment': CustomerAssignmentService(None, tenant_id),
            'nurturing': LeadNurturingService(None, tenant_id),
            'payment': PaymentProcessingService(None, tenant_id)
        }
    
    async def start_customer_success_journey(self, customer_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start customer success monitoring journey"""
        
        # This would integrate with the existing JourneyOrchestrator.startJourney() method
        journey_context = {
            'customer_id': customer_id,
            'tenant_id': self.tenant_id,
            'priority': context.get('priority', 'medium'),
            'trigger_source': context.get('trigger_source', 'manual'),
            **context
        }
        
        # Use the existing journey orchestrator to start the journey
        # The template would be loaded from CUSTOMER_SUCCESS_JOURNEY_TEMPLATES
        return {
            'journey_id': f'cs_{customer_id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            'template_id': 'customer_success_monitoring',
            'status': 'started',
            'context': journey_context,
            'estimated_completion': (datetime.utcnow().timestamp() + 3600 * 24 * 7)  # 1 week
        }
    
    async def start_commission_processing_journey(self, reseller_id: str, period_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start automated commission processing journey"""
        
        journey_context = {
            'reseller_id': reseller_id,
            'tenant_id': self.tenant_id,
            'period_start': period_data.get('period_start'),
            'period_end': period_data.get('period_end'),
            'trigger_source': 'scheduled'
        }
        
        return {
            'journey_id': f'comm_{reseller_id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            'template_id': 'commission_calculation',
            'status': 'started',
            'context': journey_context,
            'estimated_completion': (datetime.utcnow().timestamp() + 3600 * 4)  # 4 hours
        }
    
    async def start_lead_nurturing_journey(self, lead_id: str, trigger_event: str) -> Dict[str, Any]:
        """Start lead nurturing automation journey"""
        
        journey_context = {
            'lead_id': lead_id,
            'tenant_id': self.tenant_id,
            'trigger_event': trigger_event,
            'sequence_type': self._determine_nurture_sequence(trigger_event)
        }
        
        return {
            'journey_id': f'nurture_{lead_id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            'template_id': 'lead_nurturing_automation',
            'status': 'started', 
            'context': journey_context,
            'estimated_completion': (datetime.utcnow().timestamp() + 3600 * 24 * 14)  # 2 weeks
        }
    
    def _determine_nurture_sequence(self, trigger_event: str) -> str:
        """Determine appropriate nurture sequence based on trigger event"""
        
        sequence_mapping = {
            'lead:created': 'welcome_series',
            'lead:quote_abandoned': 'abandonment_recovery',
            'lead:cold_for_30_days': 're_engagement',
            'lead:downloaded_content': 'educational_content',
            'lead:demo_requested': 'product_demo'
        }
        
        return sequence_mapping.get(trigger_event, 'welcome_series')


# Integration functions for existing system
def register_enhanced_journey_templates():
    """
    Function to register enhanced journey templates with existing system
    This would be called during system initialization
    """
    
    enhanced_templates = EnhancedJourneyTemplates.get_enhanced_isp_journey_templates()
    
    # This would integrate with the existing JourneyOrchestrator system
    registration_result = {
        'registered_templates': len(enhanced_templates),
        'template_ids': list(enhanced_templates.keys()),
        'categories': list(set(template.get('category', 'unknown') for template in enhanced_templates.values())),
        'registration_timestamp': datetime.utcnow().isoformat()
    }
    
    return registration_result


def create_reseller_journey_config() -> Dict[str, Any]:
    """
    Create configuration for reseller journey orchestration
    This extends the existing journey orchestrator configuration
    """
    
    return {
        'reseller_journey_config': {
            'auto_start_journeys': True,
            'parallel_journey_limit': 10,
            'default_timeout_hours': 72,
            'retry_failed_steps': True,
            'max_retries': 3,
            'notification_channels': ['email', 'slack', 'webhook'],
            'analytics_enabled': True,
            'journey_categories': [
                'customer_success',
                'performance_optimization', 
                'commission_processing',
                'lead_nurturing',
                'payment_processing',
                'customer_assignment'
            ],
            'triggers': {
                'scheduled_triggers': [
                    {
                        'name': 'monthly_commission_calculation',
                        'schedule': '0 9 1 * *',  # 1st of each month at 9 AM
                        'template_id': 'commission_calculation'
                    },
                    {
                        'name': 'weekly_customer_health_check',
                        'schedule': '0 10 * * MON',  # Every Monday at 10 AM
                        'template_id': 'customer_success_monitoring'
                    },
                    {
                        'name': 'monthly_performance_review',
                        'schedule': '0 9 1 * *',  # 1st of each month at 9 AM
                        'template_id': 'reseller_performance_review'
                    }
                ],
                'event_triggers': [
                    {
                        'name': 'lead_behavior_change',
                        'event': 'lead:behavior_recorded',
                        'template_id': 'lead_nurturing_automation'
                    },
                    {
                        'name': 'commission_calculation_approved', 
                        'event': 'commission:calculation_approved',
                        'template_id': 'payout_processing'
                    },
                    {
                        'name': 'customer_health_at_risk',
                        'event': 'customer:health_score_declined',
                        'template_id': 'customer_success_monitoring'
                    }
                ]
            }
        }
    }


# Export everything needed for integration
__all__ = [
    'EnhancedJourneyTemplates',
    'ResellerJourneyOrchestrator',
    'register_enhanced_journey_templates',
    'create_reseller_journey_config'
]