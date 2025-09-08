"""
Workflow state models for business logic orchestration.

These minimal tables persist execution state for critical workflows so that
restarts do not lose in-flight transactions or audit history.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from dotmac.database.base import BaseModel


# Incident Response
class Incident(BaseModel):
    __tablename__ = "bl_incidents"

    tenant_id = Column(String(255), nullable=True, index=True)
    reporter_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # sev1..sev5
    status = Column(String(30), nullable=False, index=True, default="open")
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)


class IncidentEscalation(BaseModel):
    __tablename__ = "bl_incident_escalations"

    incident_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    assignee = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    escalated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class IncidentTimelineEvent(BaseModel):
    __tablename__ = "bl_incident_timeline"

    incident_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Payment Processing
class PaymentTransaction(BaseModel):
    __tablename__ = "bl_payments"

    tenant_id = Column(String(255), nullable=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(30), default="pending", nullable=False, index=True)
    provider = Column(String(50), nullable=True)
    provider_ref = Column(String(255), nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class PaymentFraudScore(BaseModel):
    __tablename__ = "bl_payment_fraud_scores"

    payment_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    score = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=True)
    factors = Column(JSON, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PaymentSettlement(BaseModel):
    __tablename__ = "bl_payment_settlements"

    payment_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(30), default="pending", nullable=False)
    batch_id = Column(String(100), nullable=True, index=True)
    settled_at = Column(DateTime, nullable=True)


# Service Provisioning
class ServiceProvisioningRequest(BaseModel):
    __tablename__ = "bl_provisioning_requests"

    tenant_id = Column(String(255), nullable=True, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_type = Column(String(100), nullable=False)
    status = Column(String(30), default="pending", nullable=False, index=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    details = Column(JSON, nullable=True)


class ServiceProvisioningValidation(BaseModel):
    __tablename__ = "bl_provisioning_validations"

    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    check_name = Column(String(100), nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    info = Column(JSON, nullable=True)
    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ServiceProvisioningStep(BaseModel):
    __tablename__ = "bl_provisioning_steps"

    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    step_name = Column(String(100), nullable=False)
    status = Column(String(30), default="pending", nullable=False)
    logs = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Workflow execution state/history/metrics
class WorkflowState(BaseModel):
    __tablename__ = "bl_workflow_state"

    workflow_name = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), default="running", nullable=False, index=True)
    state = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorkflowExecutionHistory(BaseModel):
    __tablename__ = "bl_workflow_history"

    workflow_name = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    event = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkflowMetric(BaseModel):
    __tablename__ = "bl_workflow_metrics"

    workflow_name = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    labels = Column(JSON, nullable=True)
    observed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
