"""
GDPR compliance management for DotMac Core Events.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """GDPR request types."""
    ACCESS = "access"           # Right to access personal data
    RECTIFICATION = "rectification"  # Right to rectify inaccurate data
    ERASURE = "erasure"         # Right to be forgotten
    PORTABILITY = "portability"  # Right to data portability
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"     # Right to object to processing


class RequestStatus(str, Enum):
    """GDPR request status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DataCategory(str, Enum):
    """Categories of personal data."""
    IDENTITY = "identity"       # Name, email, phone, etc.
    PROFILE = "profile"         # User preferences, settings
    BEHAVIORAL = "behavioral"   # Usage patterns, interactions
    TECHNICAL = "technical"     # IP addresses, device info
    LOCATION = "location"       # Geographic data
    COMMUNICATION = "communication"  # Messages, notifications
    FINANCIAL = "financial"     # Payment info, billing
    ALL = "all"                # All personal data


class DataSubjectRequest(BaseModel):
    """GDPR data subject request."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., description="Tenant ID")
    subject_id: str = Field(..., description="Data subject identifier")
    request_type: RequestType = Field(..., description="Type of request")
    data_categories: List[DataCategory] = Field(..., description="Data categories")

    # Request details
    description: Optional[str] = Field(None, description="Request description")
    legal_basis: Optional[str] = Field(None, description="Legal basis for request")
    verification_method: str = Field(..., description="How identity was verified")

    # Status tracking
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: datetime = Field(..., description="Due date (30 days from creation)")
    completed_at: Optional[datetime] = Field(None)

    # Processing details
    assigned_to: Optional[str] = Field(None, description="Assigned processor")
    processing_notes: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = Field(None)

    # Results
    data_found: Dict[str, Any] = Field(default_factory=dict)
    actions_taken: List[str] = Field(default_factory=list)
    files_generated: List[str] = Field(default_factory=list)

    created_by: Optional[str] = Field(None, description="Request creator")


class GDPRComplianceManager:
    """Manages GDPR compliance requests and data processing."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.requests: Dict[str, DataSubjectRequest] = {}
        self.active_requests: Set[str] = set()

        # Mock data stores (would be real databases in production)
        self.user_data: Dict[str, Dict] = {}
        self.event_data: Dict[str, Dict] = {}
        self.workflow_data: Dict[str, Dict] = {}
        self.audit_logs: Dict[str, Dict] = {}
        self.communication_logs: Dict[str, Dict] = {}

    async def create_request(
        self,
        tenant_id: str,
        subject_id: str,
        request_type: RequestType,
        data_categories: List[DataCategory],
        verification_method: str,
        description: Optional[str] = None,
        legal_basis: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> DataSubjectRequest:
        """Create a new GDPR data subject request."""

        # Calculate due date (30 days from creation)
        due_date = datetime.now(timezone.utc) + timedelta(days=30)

        request = DataSubjectRequest(
            tenant_id=tenant_id,
            subject_id=subject_id,
            request_type=request_type,
            data_categories=data_categories,
            description=description,
            legal_basis=legal_basis,
            verification_method=verification_method,
            due_date=due_date,
            created_by=created_by
        )

        self.requests[request.request_id] = request

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "ops.gdpr.request.created",
                {
                    "request_id": request.request_id,
                    "tenant_id": tenant_id,
                    "subject_id": subject_id,
                    "request_type": request_type.value,
                    "data_categories": [cat.value for cat in data_categories],
                    "due_date": due_date.isoformat()
                },
                partition_key=tenant_id
            )

        return request

    async def process_request(  # noqa: C901
        self,
        request_id: str,
        assigned_to: Optional[str] = None
    ) -> DataSubjectRequest:
        """Process a GDPR request."""
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        if request.status != RequestStatus.PENDING:
            raise ValueError(f"Request is in status {request.status}, cannot process")

        if request_id in self.active_requests:
            raise ValueError("Request is already being processed")

        # Update status
        request.status = RequestStatus.IN_PROGRESS
        request.assigned_to = assigned_to
        request.updated_at = datetime.now(timezone.utc)
        self.active_requests.add(request_id)

        try:
            # Publish start event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.gdpr.request.processing_started",
                    {
                        "request_id": request_id,
                        "tenant_id": request.tenant_id,
                        "subject_id": request.subject_id,
                        "request_type": request.request_type.value,
                        "assigned_to": assigned_to
                    },
                    partition_key=request.tenant_id
                )

            # Process based on request type
            if request.request_type == RequestType.ACCESS:
                await self._process_access_request(request)
            elif request.request_type == RequestType.ERASURE:
                await self._process_erasure_request(request)
            elif request.request_type == RequestType.RECTIFICATION:
                await self._process_rectification_request(request)
            elif request.request_type == RequestType.PORTABILITY:
                await self._process_portability_request(request)
            elif request.request_type == RequestType.RESTRICTION:
                await self._process_restriction_request(request)
            elif request.request_type == RequestType.OBJECTION:
                await self._process_objection_request(request)

            # Mark as completed
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.now(timezone.utc)
            request.updated_at = datetime.now(timezone.utc)

            # Publish completion event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.gdpr.request.completed",
                    {
                        "request_id": request_id,
                        "tenant_id": request.tenant_id,
                        "subject_id": request.subject_id,
                        "request_type": request.request_type.value,
                        "actions_taken": request.actions_taken,
                        "data_categories_processed": len(request.data_categories)
                    },
                    partition_key=request.tenant_id
                )

        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.rejection_reason = str(e)
            request.updated_at = datetime.now(timezone.utc)

            # Publish failure event
            if self.event_bus:
                await self.event_bus.publish(
                    "ops.gdpr.request.failed",
                    {
                        "request_id": request_id,
                        "tenant_id": request.tenant_id,
                        "subject_id": request.subject_id,
                        "error": str(e)
                    },
                    partition_key=request.tenant_id
                )

            raise

        finally:
            self.active_requests.discard(request_id)

        return request

    async def reject_request(
        self,
        request_id: str,
        reason: str,
        rejected_by: Optional[str] = None
    ) -> DataSubjectRequest:
        """Reject a GDPR request."""
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        if request.status not in [RequestStatus.PENDING, RequestStatus.IN_PROGRESS]:
            raise ValueError(f"Cannot reject request in status {request.status}")

        request.status = RequestStatus.REJECTED
        request.rejection_reason = reason
        request.updated_at = datetime.now(timezone.utc)

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "ops.gdpr.request.rejected",
                {
                    "request_id": request_id,
                    "tenant_id": request.tenant_id,
                    "subject_id": request.subject_id,
                    "reason": reason,
                    "rejected_by": rejected_by
                },
                partition_key=request.tenant_id
            )

        return request

    async def get_request(self, request_id: str, tenant_id: str) -> Optional[DataSubjectRequest]:
        """Get a GDPR request."""
        if request_id not in self.requests:
            return None

        request = self.requests[request_id]

        # Check tenant access
        if request.tenant_id != tenant_id:
            return None

        return request

    async def list_requests(
        self,
        tenant_id: str,
        subject_id: Optional[str] = None,
        request_type: Optional[RequestType] = None,
        status: Optional[RequestStatus] = None,
        overdue_only: bool = False
    ) -> List[DataSubjectRequest]:
        """List GDPR requests with filters."""
        requests = []
        now = datetime.now(timezone.utc)

        for request in self.requests.values():
            if request.tenant_id != tenant_id:
                continue

            if subject_id and request.subject_id != subject_id:
                continue

            if request_type and request.request_type != request_type:
                continue

            if status and request.status != status:
                continue

            if overdue_only:
                if request.status in [RequestStatus.COMPLETED, RequestStatus.REJECTED]:
                    continue
                if request.due_date > now:
                    continue

            requests.append(request)

        return sorted(requests, key=lambda r: r.created_at, reverse=True)

    async def get_overdue_requests(self, tenant_id: Optional[str] = None) -> List[DataSubjectRequest]:
        """Get overdue GDPR requests."""
        now = datetime.now(timezone.utc)
        overdue = []

        for request in self.requests.values():
            if tenant_id and request.tenant_id != tenant_id:
                continue

            if request.status in [RequestStatus.COMPLETED, RequestStatus.REJECTED]:
                continue

            if request.due_date <= now:
                overdue.append(request)

        return sorted(overdue, key=lambda r: r.due_date)

    async def add_processing_note(
        self,
        request_id: str,
        note: str,
        added_by: Optional[str] = None
    ) -> DataSubjectRequest:
        """Add a processing note to a request."""
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        timestamp = datetime.now(timezone.utc).isoformat()
        formatted_note = f"[{timestamp}] {added_by or 'System'}: {note}"

        request.processing_notes.append(formatted_note)
        request.updated_at = datetime.now(timezone.utc)

        return request

    async def _process_access_request(self, request: DataSubjectRequest):
        """Process a data access request."""
        request.actions_taken.append("Started data access request processing")

        # Collect data from various sources
        collected_data = {}

        for category in request.data_categories:
            if category == DataCategory.ALL or category == DataCategory.IDENTITY:
                # Collect identity data
                identity_data = await self._collect_identity_data(request.subject_id, request.tenant_id)
                if identity_data:
                    collected_data["identity"] = identity_data

            if category == DataCategory.ALL or category == DataCategory.BEHAVIORAL:
                # Collect behavioral data
                behavioral_data = await self._collect_behavioral_data(request.subject_id, request.tenant_id)
                if behavioral_data:
                    collected_data["behavioral"] = behavioral_data

            if category == DataCategory.ALL or category == DataCategory.TECHNICAL:
                # Collect technical data
                technical_data = await self._collect_technical_data(request.subject_id, request.tenant_id)
                if technical_data:
                    collected_data["technical"] = technical_data

            if category == DataCategory.ALL or category == DataCategory.COMMUNICATION:
                # Collect communication data
                comm_data = await self._collect_communication_data(request.subject_id, request.tenant_id)
                if comm_data:
                    collected_data["communication"] = comm_data

        request.data_found = collected_data
        request.actions_taken.append(f"Collected data from {len(collected_data)} categories")

        # Generate export file (mock)
        export_file = f"gdpr_export_{request.subject_id}_{request.request_id}.json"
        request.files_generated.append(export_file)
        request.actions_taken.append(f"Generated export file: {export_file}")

    async def _process_erasure_request(self, request: DataSubjectRequest):
        """Process a data erasure request (right to be forgotten)."""
        request.actions_taken.append("Started data erasure request processing")

        deleted_records = 0

        for category in request.data_categories:
            if category == DataCategory.ALL or category == DataCategory.IDENTITY:
                # Delete identity data
                count = await self._delete_identity_data(request.subject_id, request.tenant_id)
                deleted_records += count

            if category == DataCategory.ALL or category == DataCategory.BEHAVIORAL:
                # Delete behavioral data
                count = await self._delete_behavioral_data(request.subject_id, request.tenant_id)
                deleted_records += count

            if category == DataCategory.ALL or category == DataCategory.TECHNICAL:
                # Delete technical data
                count = await self._delete_technical_data(request.subject_id, request.tenant_id)
                deleted_records += count

            if category == DataCategory.ALL or category == DataCategory.COMMUNICATION:
                # Delete communication data
                count = await self._delete_communication_data(request.subject_id, request.tenant_id)
                deleted_records += count

        request.actions_taken.append(f"Deleted {deleted_records} records")
        request.data_found = {"deleted_records": deleted_records}

    async def _process_rectification_request(self, request: DataSubjectRequest):
        """Process a data rectification request."""
        request.actions_taken.append("Started data rectification request processing")

        # This would typically require specific correction instructions
        # For now, we'll mark data as requiring manual review

        corrected_records = 0

        for category in request.data_categories:
            if category in [DataCategory.ALL, DataCategory.IDENTITY]:
                # Mark identity data for correction
                count = await self._mark_for_correction(request.subject_id, request.tenant_id, "identity")
                corrected_records += count

        request.actions_taken.append(f"Marked {corrected_records} records for manual correction")
        request.data_found = {"records_marked_for_correction": corrected_records}

    async def _process_portability_request(self, request: DataSubjectRequest):
        """Process a data portability request."""
        request.actions_taken.append("Started data portability request processing")

        # Similar to access request but in machine-readable format
        portable_data = {}

        for category in request.data_categories:
            if category in [DataCategory.ALL, DataCategory.IDENTITY, DataCategory.PROFILE]:
                # Export portable data
                data = await self._export_portable_data(request.subject_id, request.tenant_id, category)
                if data:
                    portable_data[category.value] = data

        # Generate portable export file
        export_file = f"gdpr_portable_{request.subject_id}_{request.request_id}.json"
        request.files_generated.append(export_file)
        request.data_found = portable_data
        request.actions_taken.append(f"Generated portable export: {export_file}")

    async def _process_restriction_request(self, request: DataSubjectRequest):
        """Process a data processing restriction request."""
        request.actions_taken.append("Started processing restriction request")

        restricted_records = 0

        for category in request.data_categories:
            # Mark data as restricted from processing
            count = await self._restrict_processing(request.subject_id, request.tenant_id, category)
            restricted_records += count

        request.actions_taken.append(f"Restricted processing for {restricted_records} records")
        request.data_found = {"restricted_records": restricted_records}

    async def _process_objection_request(self, request: DataSubjectRequest):
        """Process an objection to processing request."""
        request.actions_taken.append("Started processing objection request")

        # Stop automated processing for the subject
        stopped_processes = await self._stop_automated_processing(request.subject_id, request.tenant_id)

        request.actions_taken.append(f"Stopped {len(stopped_processes)} automated processes")
        request.data_found = {"stopped_processes": stopped_processes}

    # Mock data collection methods (would interface with real data stores)

    async def _collect_identity_data(self, subject_id: str, tenant_id: str) -> Dict[str, Any]:
        """Collect identity data for a subject."""
        data = {}
        for user_id, user_data in self.user_data.items():
            if user_data.get("subject_id") == subject_id and user_data.get("tenant_id") == tenant_id:
                data[user_id] = {
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "phone": user_data.get("phone"),
                    "created_at": user_data.get("created_at")
                }
        return data

    async def _collect_behavioral_data(self, subject_id: str, tenant_id: str) -> Dict[str, Any]:
        """Collect behavioral data for a subject."""
        data = {}
        for event_id, event_data in self.event_data.items():
            if event_data.get("subject_id") == subject_id and event_data.get("tenant_id") == tenant_id:
                data[event_id] = {
                    "event_type": event_data.get("event_type"),
                    "timestamp": event_data.get("timestamp"),
                    "properties": event_data.get("properties", {})
                }
        return data

    async def _collect_technical_data(self, subject_id: str, tenant_id: str) -> Dict[str, Any]:
        """Collect technical data for a subject."""
        # Mock technical data collection
        return {
            "ip_addresses": ["192.168.1.1", "10.0.0.1"],
            "user_agents": ["Mozilla/5.0..."],
            "session_data": {"last_login": "2024-01-01T00:00:00Z"}
        }

    async def _collect_communication_data(self, subject_id: str, tenant_id: str) -> Dict[str, Any]:
        """Collect communication data for a subject."""
        data = {}
        for comm_id, comm_data in self.communication_logs.items():
            if comm_data.get("subject_id") == subject_id and comm_data.get("tenant_id") == tenant_id:
                data[comm_id] = {
                    "type": comm_data.get("type"),
                    "timestamp": comm_data.get("timestamp"),
                    "content": comm_data.get("content")
                }
        return data

    async def _delete_identity_data(self, subject_id: str, tenant_id: str) -> int:
        """Delete identity data for a subject."""
        deleted = 0
        for user_id in list(self.user_data.keys()):
            user_data = self.user_data[user_id]
            if user_data.get("subject_id") == subject_id and user_data.get("tenant_id") == tenant_id:
                del self.user_data[user_id]
                deleted += 1
        return deleted

    async def _delete_behavioral_data(self, subject_id: str, tenant_id: str) -> int:
        """Delete behavioral data for a subject."""
        deleted = 0
        for event_id in list(self.event_data.keys()):
            event_data = self.event_data[event_id]
            if event_data.get("subject_id") == subject_id and event_data.get("tenant_id") == tenant_id:
                del self.event_data[event_id]
                deleted += 1
        return deleted

    async def _delete_technical_data(self, subject_id: str, tenant_id: str) -> int:
        """Delete technical data for a subject."""
        # Mock deletion
        return 5  # Simulated deleted records

    async def _delete_communication_data(self, subject_id: str, tenant_id: str) -> int:
        """Delete communication data for a subject."""
        deleted = 0
        for comm_id in list(self.communication_logs.keys()):
            comm_data = self.communication_logs[comm_id]
            if comm_data.get("subject_id") == subject_id and comm_data.get("tenant_id") == tenant_id:
                del self.communication_logs[comm_id]
                deleted += 1
        return deleted

    async def _mark_for_correction(self, subject_id: str, tenant_id: str, category: str) -> int:
        """Mark data for manual correction."""
        # Mock marking for correction
        return 3  # Simulated marked records

    async def _export_portable_data(self, subject_id: str, tenant_id: str, category: DataCategory) -> Dict[str, Any]:
        """Export data in portable format."""
        # Mock portable data export
        return {
            "format": "JSON",
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "data": {"mock": "portable_data"}
        }

    async def _restrict_processing(self, subject_id: str, tenant_id: str, category: DataCategory) -> int:
        """Restrict processing for subject data."""
        # Mock processing restriction
        return 2  # Simulated restricted records

    async def _stop_automated_processing(self, subject_id: str, tenant_id: str) -> List[str]:
        """Stop automated processing for a subject."""
        # Mock stopping automated processes
        return ["email_marketing", "behavioral_analysis", "recommendation_engine"]
