"""
Reseller Onboarding Workflow System
Provides structured onboarding process for new resellers
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from dotmac.database.base import Base

from .services_complete import ResellerService


class OnboardingTaskStatus(str, Enum):
    """Onboarding task status options"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class OnboardingTaskPriority(str, Enum):
    """Task priority levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OnboardingTaskCategory(str, Enum):
    """Task categories for organization"""

    SETUP = "setup"
    TRAINING = "training"
    LEGAL = "legal"
    TECHNICAL = "technical"
    BUSINESS = "business"


class ResellerOnboardingChecklist(Base):
    """Database model for reseller onboarding checklists"""

    __tablename__ = "reseller_onboarding_checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("isp_resellers.id"), nullable=False)
    checklist_version = Column(String(50), default="1.0")

    # Progress tracking
    total_tasks = Column(String(10), default="0")
    completed_tasks = Column(String(10), default="0")
    completion_percentage = Column(String(10), default="0")

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    target_completion_date = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)

    # Additional data
    metadata = Column(JSON, default=dict)
    notes = Column(Text, nullable=True)

    # Relationships
    reseller = relationship("Reseller", back_populates="onboarding_checklists")


class OnboardingTask(Base):
    """Database model for individual onboarding tasks"""

    __tablename__ = "onboarding_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_onboarding_checklists.id"),
        nullable=False,
    )

    # Task identification
    task_id = Column(String(100), nullable=False, unique=True, index=True)
    task_name = Column(String(300), nullable=False)
    task_description = Column(Text, nullable=True)

    # Task properties
    category = Column(String(50), default=OnboardingTaskCategory.SETUP.value)
    priority = Column(String(20), default=OnboardingTaskPriority.MEDIUM.value)
    estimated_duration_minutes = Column(String(10), nullable=True)

    # Status and progress
    status = Column(String(50), default=OnboardingTaskStatus.PENDING.value)
    completion_percentage = Column(String(10), default="0")

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Task requirements and completion
    prerequisites = Column(JSON, default=list)  # List of task_ids that must be completed first
    completion_criteria = Column(Text, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Resources and guidance
    instructions = Column(Text, nullable=True)
    resources = Column(JSON, default=list)  # List of helpful resources/links
    assigned_to = Column(String(200), nullable=True)  # Who is responsible

    # Additional data
    metadata = Column(JSON, default=dict)

    # Relationships
    checklist = relationship("ResellerOnboardingChecklist", back_populates="tasks")


# Add relationships to existing models (would be added to db_models.py)
# Reseller.onboarding_checklists = relationship("ResellerOnboardingChecklist", back_populates="reseller")
# ResellerOnboardingChecklist.tasks = relationship("OnboardingTask", back_populates="checklist")


class OnboardingTaskTemplate:
    """Template for creating standardized onboarding tasks"""

    @staticmethod
    def get_standard_onboarding_tasks() -> list[dict[str, Any]]:
        """Get the standard onboarding task templates"""

        return [
            # Setup Phase
            {
                "task_id": "setup_001",
                "task_name": "Complete Reseller Agreement",
                "task_description": "Review and sign the reseller partnership agreement",
                "category": OnboardingTaskCategory.LEGAL,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 45,
                "instructions": """
1. Review the reseller agreement document carefully
2. Pay attention to commission structure, territory assignments, and obligations
3. Sign and return the agreement within 5 business days
4. Keep a copy for your records
                """,
                "completion_criteria": "Signed agreement received and processed",
                "resources": [
                    {
                        "name": "Reseller Agreement Template",
                        "url": "/docs/reseller-agreement.pdf",
                    },
                    {
                        "name": "Commission Structure Guide",
                        "url": "/docs/commission-guide.pdf",
                    },
                ],
                "due_days": 5,
            },
            {
                "task_id": "setup_002",
                "task_name": "Portal Account Setup",
                "task_description": "Set up your reseller portal account and complete profile",
                "category": OnboardingTaskCategory.SETUP,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 30,
                "instructions": """
1. Log into your reseller portal account
2. Complete your company profile information
3. Upload company logo and marketing materials
4. Set up payment information for commission payments
5. Configure notification preferences
                """,
                "completion_criteria": "Portal profile 100% complete with all required information",
                "resources": [
                    {"name": "Portal Setup Guide", "url": "/docs/portal-setup.pdf"},
                    {
                        "name": "Profile Completion Checklist",
                        "url": "/portal/profile/checklist",
                    },
                ],
                "due_days": 3,
            },
            {
                "task_id": "setup_003",
                "task_name": "Banking & Payment Setup",
                "task_description": "Configure banking information for commission payments",
                "category": OnboardingTaskCategory.BUSINESS,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 20,
                "instructions": """
1. Provide banking details for ACH transfers
2. Complete W-9 or equivalent tax forms
3. Set up payment schedule preferences
4. Verify account information with test deposit
                """,
                "completion_criteria": "Banking information verified and test payment successful",
                "resources": [
                    {"name": "Payment Setup Guide", "url": "/docs/payment-setup.pdf"},
                    {"name": "Tax Forms", "url": "/forms/tax-documents"},
                ],
                "due_days": 7,
            },
            # Training Phase
            {
                "task_id": "training_001",
                "task_name": "Product Training - Basic",
                "task_description": "Complete basic product training modules",
                "category": OnboardingTaskCategory.TRAINING,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 180,
                "instructions": """
1. Complete all basic product training modules
2. Take and pass the product knowledge quiz (80% minimum)
3. Review service offerings and pricing structures
4. Understand customer onboarding process
                """,
                "completion_criteria": "All training modules completed with quiz score ≥80%",
                "resources": [
                    {
                        "name": "Product Training Portal",
                        "url": "/training/products/basic",
                    },
                    {"name": "Service Catalog", "url": "/docs/service-catalog.pdf"},
                    {"name": "Pricing Guide", "url": "/docs/pricing-guide.pdf"},
                ],
                "prerequisites": ["setup_002"],
                "due_days": 14,
            },
            {
                "task_id": "training_002",
                "task_name": "Sales Process Training",
                "task_description": "Learn the sales methodology and customer lifecycle",
                "category": OnboardingTaskCategory.TRAINING,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 120,
                "instructions": """
1. Complete sales methodology training
2. Learn customer needs assessment process
3. Practice using sales tools and CRM
4. Understand lead qualification criteria
                """,
                "completion_criteria": "Sales training completed with practical assessment",
                "resources": [
                    {"name": "Sales Training Modules", "url": "/training/sales"},
                    {"name": "CRM User Guide", "url": "/docs/crm-guide.pdf"},
                    {"name": "Sales Playbook", "url": "/docs/sales-playbook.pdf"},
                ],
                "prerequisites": ["training_001"],
                "due_days": 21,
            },
            # Technical Setup
            {
                "task_id": "technical_001",
                "task_name": "Technical Assessment",
                "task_description": "Complete technical capabilities assessment",
                "category": OnboardingTaskCategory.TECHNICAL,
                "priority": OnboardingTaskPriority.MEDIUM,
                "estimated_duration_minutes": 60,
                "instructions": """
1. Complete technical assessment questionnaire
2. Provide details about your technical team
3. List any certifications or specializations
4. Identify any training needs or skill gaps
                """,
                "completion_criteria": "Technical assessment completed and reviewed",
                "resources": [
                    {
                        "name": "Technical Assessment Form",
                        "url": "/forms/technical-assessment",
                    },
                    {
                        "name": "Recommended Certifications",
                        "url": "/docs/certifications.pdf",
                    },
                ],
                "due_days": 10,
            },
            {
                "task_id": "technical_002",
                "task_name": "API & Integration Setup",
                "task_description": "Set up API access and integration tools",
                "category": OnboardingTaskCategory.TECHNICAL,
                "priority": OnboardingTaskPriority.MEDIUM,
                "estimated_duration_minutes": 90,
                "instructions": """
1. Request API credentials for your applications
2. Review API documentation and integration guides
3. Set up development/testing environment
4. Complete basic integration test
                """,
                "completion_criteria": "API integration successfully tested",
                "resources": [
                    {"name": "API Documentation", "url": "/docs/api"},
                    {
                        "name": "Integration Examples",
                        "url": "/docs/integration-examples",
                    },
                    {"name": "SDK Downloads", "url": "/downloads/sdk"},
                ],
                "prerequisites": ["technical_001"],
                "due_days": 21,
            },
            # Business Development
            {
                "task_id": "business_001",
                "task_name": "Territory Planning",
                "task_description": "Develop your territory and market strategy",
                "category": OnboardingTaskCategory.BUSINESS,
                "priority": OnboardingTaskPriority.MEDIUM,
                "estimated_duration_minutes": 120,
                "instructions": """
1. Review your assigned territories and customer segments
2. Develop target customer profiles and market strategy
3. Create initial business plan and goals
4. Schedule territory planning session with your account manager
                """,
                "completion_criteria": "Business plan submitted and approved",
                "resources": [
                    {
                        "name": "Territory Planning Template",
                        "url": "/docs/territory-planning.docx",
                    },
                    {"name": "Market Research Tools", "url": "/tools/market-research"},
                    {
                        "name": "Business Plan Template",
                        "url": "/docs/business-plan.docx",
                    },
                ],
                "prerequisites": ["training_002"],
                "due_days": 30,
            },
            {
                "task_id": "business_002",
                "task_name": "Marketing Materials Setup",
                "task_description": "Set up co-branded marketing materials and campaigns",
                "category": OnboardingTaskCategory.BUSINESS,
                "priority": OnboardingTaskPriority.LOW,
                "estimated_duration_minutes": 90,
                "instructions": """
1. Access the marketing resource portal
2. Customize co-branded materials with your company information
3. Set up marketing automation tools and templates
4. Plan initial marketing campaigns and activities
                """,
                "completion_criteria": "Marketing materials customized and campaign planned",
                "resources": [
                    {"name": "Marketing Portal", "url": "/marketing"},
                    {"name": "Brand Guidelines", "url": "/docs/brand-guidelines.pdf"},
                    {"name": "Campaign Templates", "url": "/marketing/templates"},
                ],
                "prerequisites": ["setup_002"],
                "due_days": 30,
            },
            # Final Steps
            {
                "task_id": "final_001",
                "task_name": "Account Manager Introduction",
                "task_description": "Meet your assigned account manager and establish communication",
                "category": OnboardingTaskCategory.BUSINESS,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 60,
                "instructions": """
1. Schedule introduction call with your account manager
2. Discuss your business goals and expectations
3. Establish regular communication schedule
4. Review support resources and escalation procedures
                """,
                "completion_criteria": "Introduction meeting completed and follow-up scheduled",
                "resources": [
                    {"name": "Account Manager Contact Info", "url": "/portal/contacts"},
                    {"name": "Support Resources", "url": "/support"},
                ],
                "prerequisites": ["setup_001", "setup_002"],
                "due_days": 7,
            },
            {
                "task_id": "final_002",
                "task_name": "First Customer Goal Setting",
                "task_description": "Set goals and timeline for acquiring your first customer",
                "category": OnboardingTaskCategory.BUSINESS,
                "priority": OnboardingTaskPriority.HIGH,
                "estimated_duration_minutes": 45,
                "instructions": """
1. Set realistic timeline for first customer acquisition
2. Identify initial prospect list and approach strategy
3. Create action plan with specific milestones
4. Schedule regular check-ins with account manager
                """,
                "completion_criteria": "First customer acquisition plan approved",
                "resources": [
                    {"name": "Goal Setting Template", "url": "/docs/goal-setting.docx"},
                    {"name": "Prospecting Tools", "url": "/tools/prospecting"},
                ],
                "prerequisites": ["training_002", "business_001", "final_001"],
                "due_days": 14,
            },
        ]


class OnboardingWorkflowEngine:
    """Main engine for managing reseller onboarding workflows"""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.reseller_service = ResellerService(db, tenant_id)

    async def create_onboarding_checklist(self, reseller_id: str) -> dict[str, Any]:
        """Create a new onboarding checklist for a reseller"""

        # Verify reseller exists
        reseller = await self.reseller_service.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")

        # Create the checklist
        checklist_data = {
            "reseller_id": reseller.id,
            "checklist_version": "1.0",
            "target_completion_date": datetime.now(timezone.utc) + timedelta(days=45),  # 45 days to complete
            "metadata": {
                "created_by": "system",
                "reseller_type": reseller.reseller_type.value if reseller.reseller_type else "standard",
            },
        }

        # This would use a repository in production
        checklist = ResellerOnboardingChecklist(**checklist_data)
        self.db.add(checklist)
        await self.db.flush()

        # Create standard tasks
        standard_tasks = OnboardingTaskTemplate.get_standard_onboarding_tasks()
        created_tasks = []

        for task_template in standard_tasks:
            task_data = {
                "checklist_id": checklist.id,
                "task_id": task_template["task_id"],
                "task_name": task_template["task_name"],
                "task_description": task_template["task_description"],
                "category": task_template["category"],
                "priority": task_template["priority"],
                "estimated_duration_minutes": str(task_template.get("estimated_duration_minutes", 30)),
                "instructions": task_template.get("instructions", ""),
                "completion_criteria": task_template.get("completion_criteria", ""),
                "resources": task_template.get("resources", []),
                "prerequisites": task_template.get("prerequisites", []),
                "due_date": datetime.now(timezone.utc) + timedelta(days=task_template.get("due_days", 30)),
                "metadata": {"template_version": "1.0", "auto_created": True},
            }

            task = OnboardingTask(**task_data)
            self.db.add(task)
            created_tasks.append(task)

        # Update checklist totals
        checklist.total_tasks = str(len(created_tasks))

        await self.db.commit()

        return {
            "checklist_id": str(checklist.id),
            "reseller_id": reseller_id,
            "total_tasks": len(created_tasks),
            "target_completion_date": checklist.target_completion_date.isoformat(),
            "tasks_created": len(created_tasks),
            "created_at": checklist.created_at.isoformat(),
        }

    async def get_onboarding_progress(self, reseller_id: str) -> dict[str, Any]:
        """Get detailed onboarding progress for a reseller"""

        # In production, this would use proper repository queries
        # For now, simulate the data structure

        progress_data = {
            "reseller_id": reseller_id,
            "checklist_status": {
                "is_active": True,
                "is_completed": False,
                "completion_percentage": 35.0,
                "total_tasks": 11,
                "completed_tasks": 4,
                "in_progress_tasks": 2,
                "pending_tasks": 5,
                "overdue_tasks": 1,
            },
            "timeline": {
                "created_at": "2024-03-01T10:00:00Z",
                "started_at": "2024-03-01T14:30:00Z",
                "target_completion_date": "2024-04-15T23:59:59Z",
                "estimated_completion_date": "2024-04-10T12:00:00Z",
                "days_remaining": 12,
            },
            "category_progress": {
                "setup": {"total": 3, "completed": 2, "percentage": 66.7},
                "training": {"total": 2, "completed": 1, "percentage": 50.0},
                "technical": {"total": 2, "completed": 0, "percentage": 0.0},
                "business": {"total": 3, "completed": 1, "percentage": 33.3},
                "legal": {"total": 1, "completed": 1, "percentage": 100.0},
            },
            "recent_activity": [
                {
                    "task_id": "setup_002",
                    "task_name": "Portal Account Setup",
                    "action": "completed",
                    "timestamp": "2024-03-05T16:45:00Z",
                },
                {
                    "task_id": "training_001",
                    "task_name": "Product Training - Basic",
                    "action": "started",
                    "timestamp": "2024-03-04T09:15:00Z",
                },
            ],
            "upcoming_tasks": [
                {
                    "task_id": "training_001",
                    "task_name": "Product Training - Basic",
                    "due_date": "2024-03-15T23:59:59Z",
                    "priority": "high",
                    "status": "in_progress",
                },
                {
                    "task_id": "setup_003",
                    "task_name": "Banking & Payment Setup",
                    "due_date": "2024-03-08T23:59:59Z",
                    "priority": "high",
                    "status": "pending",
                },
            ],
            "recommendations": [
                "Complete the Banking & Payment Setup task to avoid delays in commission payments",
                "Schedule time for Product Training to stay on track with your timeline",
                "Consider reaching out to your account manager for assistance with technical tasks",
            ],
        }

        return progress_data

    async def update_task_status(
        self,
        reseller_id: str,
        task_id: str,
        new_status: str,
        completion_notes: Optional[str] = None,
        completion_percentage: Optional[int] = None,
    ) -> dict[str, Any]:
        """Update the status of a specific onboarding task"""

        # Validate status
        try:
            status_enum = OnboardingTaskStatus(new_status)
        except ValueError as e:
            raise ValueError(f"Invalid status: {new_status}") from e

        # In production, this would update the database
        # For now, return success response

        update_result = {
            "task_id": task_id,
            "reseller_id": reseller_id,
            "old_status": "pending",  # Would come from database
            "new_status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completion_notes": completion_notes,
            "completion_percentage": completion_percentage or 0,
        }

        # If task is completed, check if it unlocks other tasks
        if status_enum == OnboardingTaskStatus.COMPLETED:
            update_result["unlocked_tasks"] = await self._check_unlocked_tasks(task_id)
            update_result["overall_progress_updated"] = True

        return update_result

    async def get_task_details(self, reseller_id: str, task_id: str) -> dict[str, Any]:
        """Get detailed information about a specific task"""

        # In production, this would query the database
        # For now, return simulated task details

        task_details = {
            "task_id": task_id,
            "task_name": "Portal Account Setup",
            "task_description": "Set up your reseller portal account and complete profile",
            "category": "setup",
            "priority": "high",
            "status": "completed",
            "completion_percentage": 100,
            "estimated_duration_minutes": 30,
            "actual_duration_minutes": 25,
            "created_at": "2024-03-01T10:00:00Z",
            "started_at": "2024-03-01T14:30:00Z",
            "completed_at": "2024-03-01T15:00:00Z",
            "due_date": "2024-03-04T23:59:59Z",
            "instructions": """
1. Log into your reseller portal account
2. Complete your company profile information
3. Upload company logo and marketing materials
4. Set up payment information for commission payments
5. Configure notification preferences
            """,
            "completion_criteria": "Portal profile 100% complete with all required information",
            "completion_notes": "Profile completed successfully. All required fields filled.",
            "resources": [
                {"name": "Portal Setup Guide", "url": "/docs/portal-setup.pdf"},
                {
                    "name": "Profile Completion Checklist",
                    "url": "/portal/profile/checklist",
                },
            ],
            "prerequisites": [],
            "dependents": [
                "training_001",
                "business_002",
            ],  # Tasks that depend on this one
            "assigned_to": "reseller_self",
            "metadata": {
                "difficulty_level": "easy",
                "auto_created": True,
                "template_version": "1.0",
            },
        }

        return task_details

    async def _check_unlocked_tasks(self, completed_task_id: str) -> list[str]:
        """Check which tasks are unlocked when a task is completed"""

        # In production, this would query tasks with prerequisites
        # Return list of task_ids that are now available

        task_dependencies = {
            "setup_002": ["training_001", "business_002"],
            "training_001": ["training_002"],
            "training_002": ["business_001", "final_002"],
            "technical_001": ["technical_002"],
            "setup_001": ["final_001"],
        }

        return task_dependencies.get(completed_task_id, [])


# Export classes
__all__ = [
    "OnboardingTaskStatus",
    "OnboardingTaskPriority",
    "OnboardingTaskCategory",
    "ResellerOnboardingChecklist",
    "OnboardingTask",
    "OnboardingTaskTemplate",
    "OnboardingWorkflowEngine",
]
