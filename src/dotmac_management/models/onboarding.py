"""
Onboarding data models: requests, steps, and artifacts.
"""

from enum import Enum

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship

from .base import UUID as GUID
from .base import BaseModel


class OnboardingStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OnboardingRequest(BaseModel):
    """Top-level onboarding request for a tenant/partner."""

    __tablename__ = "onboarding_requests"

    workflow_id = Column(String(100), unique=True, index=True, nullable=False)
    partner_id = Column(GUID(as_uuid=True), nullable=True, index=True)

    tenant_name = Column(String(100), nullable=False)
    tenant_slug = Column(String(100), nullable=False, index=True)

    status = Column(
        SQLEnum(OnboardingStatus), default=OnboardingStatus.PENDING, index=True
    )
    error_message = Column(String(500), nullable=True)

    # Summary/links
    endpoint_url = Column(String(500), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)

    # Relationships
    steps = relationship(
        "OnboardingStep", back_populates="request", cascade="all, delete-orphan"
    )
    artifacts = relationship(
        "OnboardingArtifact", back_populates="request", cascade="all, delete-orphan"
    )


class OnboardingStep(BaseModel):
    """Individual step record for an onboarding request."""

    __tablename__ = "onboarding_steps"

    request_id = Column(
        GUID(as_uuid=True),
        ForeignKey("onboarding_requests.id"),
        nullable=False,
        index=True,
    )
    step_key = Column(
        String(100), nullable=False, index=True
    )  # e.g., provision_container
    name = Column(String(200), nullable=False)
    status = Column(SQLEnum(StepStatus), default=StepStatus.PENDING, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(500), nullable=True)
    data = Column(JSON, default=dict, nullable=False)

    request = relationship("OnboardingRequest", back_populates="steps")


class OnboardingArtifact(BaseModel):
    """Artifact produced during onboarding (URLs, IDs, config blobs)."""

    __tablename__ = "onboarding_artifacts"

    request_id = Column(
        GUID(as_uuid=True),
        ForeignKey("onboarding_requests.id"),
        nullable=False,
        index=True,
    )
    artifact_type = Column(String(100), nullable=False)
    data = Column(JSON, default=dict, nullable=False)

    request = relationship("OnboardingRequest", back_populates="artifacts")
