"""
Data retention management for DotMac Core Events.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field


class RetentionPeriod(str, Enum):
    """Retention period options."""
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    DAYS_180 = "180d"
    YEAR_1 = "1y"
    YEAR_3 = "3y"
    YEAR_7 = "7y"
    PERMANENT = "permanent"


class DataCategory(str, Enum):
    """Data category for retention policies."""
    EVENT_DATA = "event_data"
    WORKFLOW_RUNS = "workflow_runs"
    AUDIT_LOGS = "audit_logs"
    METRICS = "metrics"
    TRACES = "traces"
    USER_DATA = "user_data"
    SYSTEM_DATA = "system_data"


class RetentionAction(str, Enum):
    """Actions to take when data expires."""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    COMPRESS = "compress"


class RetentionPolicy(BaseModel):
    """Data retention policy definition."""
    policy_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    tenant_id: str = Field(..., description="Tenant ID")
    data_category: DataCategory = Field(..., description="Data category")
    retention_period: RetentionPeriod = Field(..., description="Retention period")
    action: RetentionAction = Field(..., description="Action when expired")
    enabled: bool = Field(default=True, description="Policy enabled")

    # Filters
    event_types: Optional[List[str]] = Field(None, description="Event types to apply to")
    workflow_ids: Optional[List[str]] = Field(None, description="Workflow IDs to apply to")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags to match")

    # Advanced settings
    grace_period_days: int = Field(default=7, description="Grace period before action")
    batch_size: int = Field(default=1000, description="Batch size for processing")
    max_daily_deletions: Optional[int] = Field(None, description="Max deletions per day")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(None, description="Created by user")


class RetentionExecution(BaseModel):
    """Retention execution record."""
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str = Field(..., description="Policy ID")
    tenant_id: str = Field(..., description="Tenant ID")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None)
    status: str = Field(default="running")

    # Statistics
    records_processed: int = Field(default=0)
    records_deleted: int = Field(default=0)
    records_archived: int = Field(default=0)
    records_anonymized: int = Field(default=0)
    records_failed: int = Field(default=0)

    # Error tracking
    error_message: Optional[str] = Field(None)
    last_processed_id: Optional[str] = Field(None)


class RetentionManager:
    """Manages data retention policies and execution."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.policies: Dict[str, RetentionPolicy] = {}
        self.executions: Dict[str, RetentionExecution] = {}
        self.active_executions: Set[str] = set()

        # Mock data stores (would be real databases in production)
        self.event_data: Dict[str, Dict] = {}
        self.workflow_runs: Dict[str, Dict] = {}
        self.audit_logs: Dict[str, Dict] = {}
        self.metrics: Dict[str, Dict] = {}
        self.traces: Dict[str, Dict] = {}

    async def create_policy(  # noqa: PLR0913
        self,
        name: str,
        tenant_id: str,
        data_category: DataCategory,
        retention_period: RetentionPeriod,
        action: RetentionAction,
        description: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        workflow_ids: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        created_by: Optional[str] = None
    ) -> RetentionPolicy:
        """Create a new retention policy."""
        policy = RetentionPolicy(
            name=name,
            description=description,
            tenant_id=tenant_id,
            data_category=data_category,
            retention_period=retention_period,
            action=action,
            event_types=event_types,
            workflow_ids=workflow_ids,
            tags=tags,
            created_by=created_by
        )

        self.policies[policy.policy_id] = policy

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "ops.retention.policy.created",
                {
                    "policy_id": policy.policy_id,
                    "tenant_id": tenant_id,
                    "name": name,
                    "data_category": data_category.value,
                    "retention_period": retention_period.value,
                    "action": action.value
                },
                partition_key=tenant_id
            )

        return policy

    async def update_policy(
        self,
        policy_id: str,
        tenant_id: str,
        **updates
    ) -> RetentionPolicy:
        """Update an existing retention policy."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]

        # Check tenant access
        if policy.tenant_id != tenant_id:
            raise ValueError("Access denied")

        # Update fields
        for field, value in updates.items():
            if hasattr(policy, field):
                setattr(policy, field, value)

        policy.updated_at = datetime.now(timezone.utc)

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "ops.retention.policy.updated",
                {
                    "policy_id": policy_id,
                    "tenant_id": tenant_id,
                    "updates": updates
                },
                partition_key=tenant_id
            )

        return policy

    async def delete_policy(self, policy_id: str, tenant_id: str) -> bool:
        """Delete a retention policy."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]

        # Check tenant access
        if policy.tenant_id != tenant_id:
            raise ValueError("Access denied")

        # Check if policy is being executed
        if policy_id in self.active_executions:
            raise ValueError("Cannot delete policy while execution is running")

        del self.policies[policy_id]

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "ops.retention.policy.deleted",
                {
                    "policy_id": policy_id,
                    "tenant_id": tenant_id
                },
                partition_key=tenant_id
            )

        return True

    async def execute_policy(  # noqa: C901
        self,
        policy_id: str,
        dry_run: bool = False
    ) -> RetentionExecution:
        """Execute a retention policy."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]

        if not policy.enabled:
            raise ValueError("Policy is disabled")

        if policy_id in self.active_executions:
            raise ValueError("Policy execution already running")

        # Create execution record
        execution = RetentionExecution(
            policy_id=policy_id,
            tenant_id=policy.tenant_id
        )

        self.executions[execution.execution_id] = execution
        self.active_executions.add(policy_id)

        try:
            # Publish start event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.retention.execution.started",
                    {
                        "execution_id": execution.execution_id,
                        "policy_id": policy_id,
                        "tenant_id": policy.tenant_id,
                        "dry_run": dry_run
                    },
                    partition_key=policy.tenant_id
                )

            # Calculate cutoff date
            cutoff_date = self._calculate_cutoff_date(policy.retention_period)

            # Process data based on category
            if policy.data_category == DataCategory.EVENT_DATA:
                await self._process_event_data(policy, execution, cutoff_date, dry_run)
            elif policy.data_category == DataCategory.WORKFLOW_RUNS:
                await self._process_workflow_runs(policy, execution, cutoff_date, dry_run)
            elif policy.data_category == DataCategory.AUDIT_LOGS:
                await self._process_audit_logs(policy, execution, cutoff_date, dry_run)
            elif policy.data_category == DataCategory.METRICS:
                await self._process_metrics(policy, execution, cutoff_date, dry_run)
            elif policy.data_category == DataCategory.TRACES:
                await self._process_traces(policy, execution, cutoff_date, dry_run)

            # Mark as completed
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)

            # Publish completion event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.retention.execution.completed",
                    {
                        "execution_id": execution.execution_id,
                        "policy_id": policy_id,
                        "tenant_id": policy.tenant_id,
                        "records_processed": execution.records_processed,
                        "records_deleted": execution.records_deleted,
                        "records_archived": execution.records_archived,
                        "records_anonymized": execution.records_anonymized,
                        "dry_run": dry_run
                    },
                    partition_key=policy.tenant_id
                )

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)

            # Publish failure event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.retention.execution.failed",
                    {
                        "execution_id": execution.execution_id,
                        "policy_id": policy_id,
                        "tenant_id": policy.tenant_id,
                        "error": str(e)
                    },
                    partition_key=policy.tenant_id
                )

            raise

        finally:
            self.active_executions.discard(policy_id)

        return execution

    async def execute_all_policies(self, tenant_id: Optional[str] = None) -> List[RetentionExecution]:
        """Execute all enabled retention policies."""
        executions = []

        for policy in self.policies.values():
            if tenant_id and policy.tenant_id != tenant_id:
                continue

            if not policy.enabled:
                continue

            if policy.policy_id in self.active_executions:
                continue

            try:
                execution = await self.execute_policy(policy.policy_id)
                executions.append(execution)
            except Exception as e:
                # Log error but continue with other policies
                print(f"Failed to execute policy {policy.policy_id}: {e}")

        return executions

    async def get_policy(self, policy_id: str, tenant_id: str) -> Optional[RetentionPolicy]:
        """Get a retention policy."""
        if policy_id not in self.policies:
            return None

        policy = self.policies[policy_id]

        # Check tenant access
        if policy.tenant_id != tenant_id:
            return None

        return policy

    async def list_policies(
        self,
        tenant_id: str,
        data_category: Optional[DataCategory] = None,
        enabled_only: bool = False
    ) -> List[RetentionPolicy]:
        """List retention policies."""
        policies = []

        for policy in self.policies.values():
            if policy.tenant_id != tenant_id:
                continue

            if data_category and policy.data_category != data_category:
                continue

            if enabled_only and not policy.enabled:
                continue

            policies.append(policy)

        return sorted(policies, key=lambda p: p.created_at, reverse=True)

    async def get_execution(self, execution_id: str, tenant_id: str) -> Optional[RetentionExecution]:
        """Get a retention execution."""
        if execution_id not in self.executions:
            return None

        execution = self.executions[execution_id]

        # Check tenant access
        if execution.tenant_id != tenant_id:
            return None

        return execution

    async def list_executions(
        self,
        tenant_id: str,
        policy_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[RetentionExecution]:
        """List retention executions."""
        executions = []

        for execution in self.executions.values():
            if execution.tenant_id != tenant_id:
                continue

            if policy_id and execution.policy_id != policy_id:
                continue

            if status and execution.status != status:
                continue

            executions.append(execution)

        return sorted(executions, key=lambda e: e.started_at, reverse=True)

    def _calculate_cutoff_date(self, retention_period: RetentionPeriod) -> datetime:
        """Calculate cutoff date for retention."""
        now = datetime.now(timezone.utc)

        if retention_period == RetentionPeriod.DAYS_7:
            return now - timedelta(days=7)
        elif retention_period == RetentionPeriod.DAYS_30:
            return now - timedelta(days=30)
        elif retention_period == RetentionPeriod.DAYS_90:
            return now - timedelta(days=90)
        elif retention_period == RetentionPeriod.DAYS_180:
            return now - timedelta(days=180)
        elif retention_period == RetentionPeriod.YEAR_1:
            return now - timedelta(days=365)
        elif retention_period == RetentionPeriod.YEAR_3:
            return now - timedelta(days=365 * 3)
        elif retention_period == RetentionPeriod.YEAR_7:
            return now - timedelta(days=365 * 7)
        else:  # PERMANENT
            return datetime.min.replace(tzinfo=timezone.utc)

    async def _process_event_data(
        self,
        policy: RetentionPolicy,
        execution: RetentionExecution,
        cutoff_date: datetime,
        dry_run: bool
    ):
        """Process event data for retention."""
        for event_id, event_data in list(self.event_data.items()):
            # Check tenant
            if event_data.get("tenant_id") != policy.tenant_id:
                continue

            # Check event type filter
            if policy.event_types and event_data.get("event_type") not in policy.event_types:
                continue

            # Check date
            event_date = datetime.fromisoformat(event_data.get("created_at", "1970-01-01T00:00:00+00:00"))
            if event_date >= cutoff_date:
                continue

            execution.records_processed += 1

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self.event_data[event_id]
                    execution.records_deleted += 1
                elif policy.action == RetentionAction.ARCHIVE:
                    # Move to archive (mock)
                    event_data["archived"] = True
                    execution.records_archived += 1
                elif policy.action == RetentionAction.ANONYMIZE:
                    # Anonymize PII fields (mock)
                    event_data["anonymized"] = True
                    execution.records_anonymized += 1

            # Batch processing delay
            if execution.records_processed % policy.batch_size == 0:
                await asyncio.sleep(0.1)  # Prevent overwhelming the system

    async def _process_workflow_runs(
        self,
        policy: RetentionPolicy,
        execution: RetentionExecution,
        cutoff_date: datetime,
        dry_run: bool
    ):
        """Process workflow runs for retention."""
        for run_id, run_data in list(self.workflow_runs.items()):
            # Check tenant
            if run_data.get("tenant_id") != policy.tenant_id:
                continue

            # Check workflow ID filter
            if policy.workflow_ids and run_data.get("workflow_id") not in policy.workflow_ids:
                continue

            # Check date
            run_date = datetime.fromisoformat(run_data.get("created_at", "1970-01-01T00:00:00+00:00"))
            if run_date >= cutoff_date:
                continue

            execution.records_processed += 1

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self.workflow_runs[run_id]
                    execution.records_deleted += 1
                elif policy.action == RetentionAction.ARCHIVE:
                    run_data["archived"] = True
                    execution.records_archived += 1
                elif policy.action == RetentionAction.ANONYMIZE:
                    run_data["anonymized"] = True
                    execution.records_anonymized += 1

            # Batch processing delay
            if execution.records_processed % policy.batch_size == 0:
                await asyncio.sleep(0.1)

    async def _process_audit_logs(
        self,
        policy: RetentionPolicy,
        execution: RetentionExecution,
        cutoff_date: datetime,
        dry_run: bool
    ):
        """Process audit logs for retention."""
        for log_id, log_data in list(self.audit_logs.items()):
            # Check tenant
            if log_data.get("tenant_id") != policy.tenant_id:
                continue

            # Check date
            log_date = datetime.fromisoformat(log_data.get("created_at", "1970-01-01T00:00:00+00:00"))
            if log_date >= cutoff_date:
                continue

            execution.records_processed += 1

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self.audit_logs[log_id]
                    execution.records_deleted += 1
                elif policy.action == RetentionAction.ARCHIVE:
                    log_data["archived"] = True
                    execution.records_archived += 1

            # Batch processing delay
            if execution.records_processed % policy.batch_size == 0:
                await asyncio.sleep(0.1)

    async def _process_metrics(
        self,
        policy: RetentionPolicy,
        execution: RetentionExecution,
        cutoff_date: datetime,
        dry_run: bool
    ):
        """Process metrics for retention."""
        for metric_id, metric_data in list(self.metrics.items()):
            # Check tenant
            if metric_data.get("tenant_id") != policy.tenant_id:
                continue

            # Check date
            metric_date = datetime.fromisoformat(metric_data.get("timestamp", "1970-01-01T00:00:00+00:00"))
            if metric_date >= cutoff_date:
                continue

            execution.records_processed += 1

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self.metrics[metric_id]
                    execution.records_deleted += 1
                elif policy.action == RetentionAction.COMPRESS:
                    metric_data["compressed"] = True
                    execution.records_archived += 1

            # Batch processing delay
            if execution.records_processed % policy.batch_size == 0:
                await asyncio.sleep(0.1)

    async def _process_traces(
        self,
        policy: RetentionPolicy,
        execution: RetentionExecution,
        cutoff_date: datetime,
        dry_run: bool
    ):
        """Process traces for retention."""
        for trace_id, trace_data in list(self.traces.items()):
            # Check tenant
            if trace_data.get("tenant_id") != policy.tenant_id:
                continue

            # Check date
            trace_date = datetime.fromisoformat(trace_data.get("timestamp", "1970-01-01T00:00:00+00:00"))
            if trace_date >= cutoff_date:
                continue

            execution.records_processed += 1

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self.traces[trace_id]
                    execution.records_deleted += 1
                elif policy.action == RetentionAction.ARCHIVE:
                    trace_data["archived"] = True
                    execution.records_archived += 1

            # Batch processing delay
            if execution.records_processed % policy.batch_size == 0:
                await asyncio.sleep(0.1)
