"""
PostgreSQL adapter for durable workflow execution storage.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

import asyncpg
import structlog
from pydantic import BaseModel

from ..contracts.common_schemas import ExecutionStatus
from ..contracts.workflow_events import WorkflowEventType

logger = structlog.get_logger(__name__)


class WorkflowRunRecord(BaseModel):
    """Database record for workflow runs."""

    tenant_id: str
    workflow_id: str
    execution_id: str
    business_key: Optional[str]
    run_key: str  # Composite key for idempotency
    status: ExecutionStatus
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    context_data: Dict[str, Any]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    version: int  # For optimistic locking


class WorkflowStepRecord(BaseModel):
    """Database record for workflow steps."""

    tenant_id: str
    execution_id: str
    step_id: str
    step_name: str
    step_type: str
    attempt: int
    step_key: str  # Composite key for idempotency
    status: ExecutionStatus
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    version: int


class PostgresAdapter:
    """PostgreSQL adapter for workflow execution persistence."""

    def __init__(self, connection_url: str, pool_size: int = 10):
        self.connection_url = connection_url
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the database connection pool and create schema."""
        async with self._lock:
            if self.pool is None:
                self.pool = await asyncpg.create_pool(
                    self.connection_url,
                    min_size=1,
                    max_size=self.pool_size,
                    command_timeout=60
                )
                await self._create_schema()
                logger.info("PostgreSQL adapter initialized")

    async def close(self):
        """Close the database connection pool."""
        async with self._lock:
            if self.pool:
                await self.pool.close()
                self.pool = None
                logger.info("PostgreSQL adapter closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            yield conn

    async def _create_schema(self):
        """Create database schema for workflow execution."""
        schema_sql = """
        -- Workflow runs table
        CREATE TABLE IF NOT EXISTS workflow_runs (
            tenant_id VARCHAR(255) NOT NULL,
            workflow_id VARCHAR(255) NOT NULL,
            execution_id VARCHAR(255) NOT NULL PRIMARY KEY,
            business_key VARCHAR(255),
            run_key VARCHAR(767) NOT NULL UNIQUE, -- tenant_id:workflow_id:business_key
            status VARCHAR(50) NOT NULL,
            input_data JSONB NOT NULL DEFAULT '{}',
            output_data JSONB NOT NULL DEFAULT '{}',
            context_data JSONB NOT NULL DEFAULT '{}',
            error_message TEXT,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL,
            completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            version INTEGER NOT NULL DEFAULT 1
        );

        -- Workflow steps table
        CREATE TABLE IF NOT EXISTS workflow_steps (
            tenant_id VARCHAR(255) NOT NULL,
            execution_id VARCHAR(255) NOT NULL,
            step_id VARCHAR(255) NOT NULL,
            step_name VARCHAR(255) NOT NULL,
            step_type VARCHAR(50) NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 1,
            step_key VARCHAR(767) NOT NULL, -- execution_id:step_id:attempt
            status VARCHAR(50) NOT NULL,
            input_data JSONB NOT NULL DEFAULT '{}',
            output_data JSONB NOT NULL DEFAULT '{}',
            error_message TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            next_retry_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            version INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (execution_id, step_id, attempt),
            FOREIGN KEY (execution_id) REFERENCES workflow_runs(execution_id) ON DELETE CASCADE
        );

        -- Workflow events table for event sourcing
        CREATE TABLE IF NOT EXISTS workflow_events (
            event_id VARCHAR(255) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(255) NOT NULL,
            execution_id VARCHAR(255) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            event_data JSONB NOT NULL,
            correlation_id VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            FOREIGN KEY (execution_id) REFERENCES workflow_runs(execution_id) ON DELETE CASCADE
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_tenant_status ON workflow_runs(tenant_id, status);
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_id ON workflow_runs(workflow_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_started_at ON workflow_runs(started_at);
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_run_key ON workflow_runs(run_key);

        CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution_id ON workflow_steps(execution_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_next_retry ON workflow_steps(next_retry_at) WHERE next_retry_at IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_step_key ON workflow_steps(step_key);

        CREATE INDEX IF NOT EXISTS idx_workflow_events_execution_id ON workflow_events(execution_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_events_type ON workflow_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_workflow_events_created_at ON workflow_events(created_at);

        -- Trigger to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS update_workflow_runs_updated_at ON workflow_runs;
        CREATE TRIGGER update_workflow_runs_updated_at
            BEFORE UPDATE ON workflow_runs
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_workflow_steps_updated_at ON workflow_steps;
        CREATE TRIGGER update_workflow_steps_updated_at
            BEFORE UPDATE ON workflow_steps
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """

        async with self.get_connection() as conn:
            await conn.execute(schema_sql)
            logger.info("Database schema created/updated")

    def _generate_run_key(self, tenant_id: str, workflow_id: str, business_key: Optional[str]) -> str:
        """Generate idempotent run key."""
        if business_key:
            return f"{tenant_id}:{workflow_id}:{business_key}"
        return f"{tenant_id}:{workflow_id}:default"

    def _generate_step_key(self, execution_id: str, step_id: str, attempt: int) -> str:
        """Generate idempotent step key."""
        return f"{execution_id}:{step_id}:{attempt}"

    async def create_or_get_workflow_run(
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        business_key: Optional[str],
        input_data: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> Tuple[WorkflowRunRecord, bool]:
        """
        Create a new workflow run or get existing one (idempotent).

        Returns:
            Tuple of (workflow_run_record, is_new)
        """
        run_key = self._generate_run_key(tenant_id, workflow_id, business_key)
        now = datetime.now(timezone.utc)

        async with self.get_connection() as conn:
            # Try to get existing run first
            existing = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE run_key = $1",
                run_key
            )

            if existing:
                logger.info("Found existing workflow run", run_key=run_key, execution_id=existing['execution_id'])
                return WorkflowRunRecord(**dict(existing)), False

            # Create new run
            try:
                record = await conn.fetchrow("""
                    INSERT INTO workflow_runs (
                        tenant_id, workflow_id, execution_id, business_key, run_key,
                        status, input_data, context_data, started_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING *
                """,
                    tenant_id, workflow_id, execution_id, business_key, run_key,
                    ExecutionStatus.RUNNING.value, json.dumps(input_data),
                    json.dumps(context_data), now
                )

                logger.info("Created new workflow run", run_key=run_key, execution_id=execution_id)
                return WorkflowRunRecord(**dict(record)), True

            except asyncpg.UniqueViolationError:
                # Race condition - another process created the run
                existing = await conn.fetchrow(
                    "SELECT * FROM workflow_runs WHERE run_key = $1",
                    run_key
                )
                logger.info("Race condition detected, using existing run", run_key=run_key)
                return WorkflowRunRecord(**dict(existing)), False

    async def update_workflow_run_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update workflow run status with optimistic locking."""
        async with self.get_connection() as conn:
            # Get current version
            current = await conn.fetchrow(
                "SELECT version FROM workflow_runs WHERE execution_id = $1",
                execution_id
            )

            if not current:
                return False

            current_version = current['version']
            completed_at = datetime.now(timezone.utc) if status in [
                ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED
            ] else None

            # Update with version check
            result = await conn.execute("""
                UPDATE workflow_runs
                SET status = $1, output_data = COALESCE($2, output_data),
                    error_message = $3, completed_at = $4, version = version + 1
                WHERE execution_id = $5 AND version = $6
            """,
                status.value,
                json.dumps(output_data) if output_data else None,
                error_message,
                completed_at,
                execution_id,
                current_version
            )

            return result == "UPDATE 1"

    async def create_or_update_workflow_step(  # noqa: PLR0913
        self,
        tenant_id: str,
        execution_id: str,
        step_id: str,
        step_name: str,
        step_type: str,
        attempt: int,
        status: ExecutionStatus,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        next_retry_at: Optional[datetime] = None
    ) -> WorkflowStepRecord:
        """Create or update a workflow step (idempotent)."""
        step_key = self._generate_step_key(execution_id, step_id, attempt)
        now = datetime.now(timezone.utc)

        started_at = now if status == ExecutionStatus.RUNNING else None
        completed_at = now if status in [
            ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED
        ] else None

        async with self.get_connection() as conn:
            record = await conn.fetchrow("""
                INSERT INTO workflow_steps (
                    tenant_id, execution_id, step_id, step_name, step_type, attempt, step_key,
                    status, input_data, output_data, error_message, retry_count, max_retries,
                    started_at, completed_at, next_retry_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (execution_id, step_id, attempt)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    output_data = EXCLUDED.output_data,
                    error_message = EXCLUDED.error_message,
                    retry_count = EXCLUDED.retry_count,
                    completed_at = EXCLUDED.completed_at,
                    next_retry_at = EXCLUDED.next_retry_at,
                    version = workflow_steps.version + 1
                RETURNING *
            """,
                tenant_id, execution_id, step_id, step_name, step_type, attempt, step_key,
                status.value, json.dumps(input_data),
                json.dumps(output_data or {}), error_message, retry_count, max_retries,
                started_at, completed_at, next_retry_at
            )

            return WorkflowStepRecord(**dict(record))

    async def get_workflow_run(self, execution_id: str) -> Optional[WorkflowRunRecord]:
        """Get workflow run by execution ID."""
        async with self.get_connection() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE execution_id = $1",
                execution_id
            )
            return WorkflowRunRecord(**dict(record)) if record else None

    async def get_workflow_steps(self, execution_id: str) -> List[WorkflowStepRecord]:
        """Get all steps for a workflow execution."""
        async with self.get_connection() as conn:
            records = await conn.fetch(
                "SELECT * FROM workflow_steps WHERE execution_id = $1 ORDER BY step_id, attempt",
                execution_id
            )
            return [WorkflowStepRecord(**dict(record)) for record in records]

    async def get_steps_for_retry(self, limit: int = 100) -> List[WorkflowStepRecord]:
        """Get steps that are ready for retry."""
        async with self.get_connection() as conn:
            records = await conn.fetch("""
                SELECT * FROM workflow_steps
                WHERE status = $1 AND next_retry_at <= NOW()
                ORDER BY next_retry_at
                LIMIT $2
            """, ExecutionStatus.PENDING.value, limit)

            return [WorkflowStepRecord(**dict(record)) for record in records]

    async def store_workflow_event(
        self,
        event_id: str,
        tenant_id: str,
        execution_id: str,
        event_type: WorkflowEventType,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Store workflow event for event sourcing."""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO workflow_events (
                    event_id, tenant_id, execution_id, event_type, event_data, correlation_id
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (event_id) DO NOTHING
            """, event_id, tenant_id, execution_id, event_type.value, json.dumps(event_data), correlation_id)

    async def get_workflow_events(
        self,
        execution_id: str,
        event_types: Optional[List[WorkflowEventType]] = None
    ) -> List[Dict[str, Any]]:
        """Get workflow events for an execution."""
        async with self.get_connection() as conn:
            if event_types:
                type_values = [et.value for et in event_types]
                records = await conn.fetch("""
                    SELECT * FROM workflow_events
                    WHERE execution_id = $1 AND event_type = ANY($2)
                    ORDER BY created_at
                """, execution_id, type_values)
            else:
                records = await conn.fetch("""
                    SELECT * FROM workflow_events
                    WHERE execution_id = $1
                    ORDER BY created_at
                """, execution_id)

            return [dict(record) for record in records]

    async def cleanup_completed_runs(self, older_than_days: int = 30) -> int:
        """Clean up completed workflow runs older than specified days."""
        async with self.get_connection() as conn:
            result = await conn.execute("""
                DELETE FROM workflow_runs
                WHERE status IN ('completed', 'failed', 'cancelled')
                AND completed_at < NOW() - INTERVAL '%s days'
            """, older_than_days)

            # Extract number of deleted rows from result
            deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0
            logger.info("Cleaned up completed workflow runs", deleted_count=deleted_count)
            return deleted_count
