"""File Management Repository for the Management Platform."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from dotmac_isp.shared.base_repository import BaseRepository
from dotmac_shared.exceptions import NotFoundError, ValidationError
from dotmac_shared.file_management.models import (
    FileAccessLog,
    FileMetadata,
    FilePermission,
    FileUploadSession,
)
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FileRepository(BaseRepository):
    """Repository for file management operations."""

    def __init__(self, session: Session):
        super().__init__(session)
        self.model = FileMetadata

    # File Metadata Operations

    async def create_file_metadata(self, tenant_id: str, file_data: dict, user_id: str) -> FileMetadata:
        """Create new file metadata."""
        try:
            file_id = str(uuid4())

            file_metadata = FileMetadata(
                file_id=file_id, tenant_id=tenant_id, owner_user_id=user_id, created_by=user_id, **file_data
            )

            self.session.add(file_metadata)
            await self.session.commit()
            await self.session.refresh(file_metadata)

            logger.info(f"Created file metadata: {file_id}")
            return file_metadata

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create file metadata: {e}")
            raise ValidationError(f"Failed to create file metadata: {str(e)}") from e

    async def get_file_by_id(self, file_id: str, tenant_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID."""
        return (
            await self.session.query(FileMetadata)
            .filter(and_(FileMetadata.file_id == file_id, FileMetadata.tenant_id == tenant_id))
            .first()
        )

    async def get_files_by_owner(
        self, tenant_id: str, owner_user_id: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[FileMetadata], int]:
        """Get files by owner with pagination."""
        query = (
            self.session.query(FileMetadata)
            .filter(and_(FileMetadata.tenant_id == tenant_id, FileMetadata.owner_user_id == owner_user_id))
            .order_by(FileMetadata.created_at.desc())
        )

        total = await query.count()
        files = await query.offset(skip).limit(limit).all()

        return files, total

    async def search_files(
        self, tenant_id: str, filters: dict, skip: int = 0, limit: int = 50
    ) -> tuple[list[FileMetadata], int]:
        """Search files with filters."""
        query = self.session.query(FileMetadata).filter(FileMetadata.tenant_id == tenant_id)

        # Apply filters
        if filters.get("category"):
            query = query.filter(FileMetadata.file_category == filters["category"])

        if filters.get("status"):
            query = query.filter(FileMetadata.file_status == filters["status"])

        if filters.get("owner_user_id"):
            query = query.filter(FileMetadata.owner_user_id == filters["owner_user_id"])

        if filters.get("file_extension"):
            query = query.filter(FileMetadata.file_extension == filters["file_extension"])

        if filters.get("tags"):
            for tag in filters["tags"]:
                query = query.filter(FileMetadata.tags.contains([tag]))

        if filters.get("min_size_bytes"):
            query = query.filter(FileMetadata.file_size >= filters["min_size_bytes"])

        if filters.get("max_size_bytes"):
            query = query.filter(FileMetadata.file_size <= filters["max_size_bytes"])

        if filters.get("created_after"):
            query = query.filter(FileMetadata.created_at >= filters["created_after"])

        if filters.get("created_before"):
            query = query.filter(FileMetadata.created_at <= filters["created_before"])

        if filters.get("query"):
            search_term = f"%{filters['query']}%"
            query = query.filter(
                or_(FileMetadata.original_filename.ilike(search_term), FileMetadata.description.ilike(search_term))
            )

        # Apply sorting
        sort_by = filters.get("sort_by", "created_at")
        sort_order = filters.get("sort_order", "desc")

        if hasattr(FileMetadata, sort_by):
            column = getattr(FileMetadata, sort_by)
            if sort_order == "asc":
                query = query.order_by(column.asc())
            else:
                query = query.order_by(column.desc())

        total = await query.count()
        files = await query.offset(skip).limit(limit).all()

        return files, total

    async def update_file_metadata(self, file_id: str, tenant_id: str, updates: dict, user_id: str) -> FileMetadata:
        """Update file metadata."""
        file_metadata = await self.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")

        try:
            for key, value in updates.items():
                if hasattr(file_metadata, key):
                    setattr(file_metadata, key, value)

            file_metadata.updated_by = user_id
            file_metadata.updated_at = datetime.now(timezone.utc)

            await self.session.commit()
            await self.session.refresh(file_metadata)

            logger.info(f"Updated file metadata: {file_id}")
            return file_metadata

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update file metadata: {e}")
            raise ValidationError(f"Failed to update file metadata: {str(e)}") from e

    async def delete_file_metadata(self, file_id: str, tenant_id: str, user_id: str) -> bool:
        """Delete file metadata (soft delete)."""
        file_metadata = await self.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")

        try:
            # Soft delete by updating status
            file_metadata.file_status = "deleted"
            file_metadata.updated_by = user_id
            file_metadata.updated_at = datetime.now(timezone.utc)

            await self.session.commit()
            logger.info(f"Deleted file metadata: {file_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete file metadata: {e}")
            raise ValidationError(f"Failed to delete file metadata: {str(e)}") from e

    # File Permission Operations

    async def create_file_permission(self, tenant_id: str, permission_data: dict, user_id: str) -> FilePermission:
        """Create file permission."""
        try:
            permission = FilePermission(tenant_id=tenant_id, granted_by=user_id, created_by=user_id, **permission_data)

            self.session.add(permission)
            await self.session.commit()
            await self.session.refresh(permission)

            logger.info(f"Created file permission for file: {permission_data.get('file_id')}")
            return permission

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create file permission: {e}")
            raise ValidationError(f"Failed to create file permission: {str(e)}") from e

    async def get_file_permissions(self, file_id: str, tenant_id: str) -> list[FilePermission]:
        """Get all permissions for a file."""
        return (
            await self.session.query(FilePermission)
            .filter(and_(FilePermission.file_id == file_id, FilePermission.tenant_id == tenant_id))
            .all()
        )

    async def get_user_file_permissions(self, file_id: str, user_id: str, tenant_id: str) -> Optional[FilePermission]:
        """Get user's permissions for a specific file."""
        return (
            await self.session.query(FilePermission)
            .filter(
                and_(
                    FilePermission.file_id == file_id,
                    FilePermission.user_id == user_id,
                    FilePermission.tenant_id == tenant_id,
                )
            )
            .first()
        )

    # File Access Logging

    async def log_file_access(self, tenant_id: str, access_data: dict) -> FileAccessLog:
        """Log file access event."""
        try:
            access_log = FileAccessLog(tenant_id=tenant_id, **access_data)

            self.session.add(access_log)
            await self.session.commit()

            return access_log

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to log file access: {e}")
            raise

    async def get_file_access_logs(self, file_id: str, tenant_id: str, limit: int = 100) -> list[FileAccessLog]:
        """Get file access logs."""
        return (
            await self.session.query(FileAccessLog)
            .filter(and_(FileAccessLog.file_id == file_id, FileAccessLog.tenant_id == tenant_id))
            .order_by(FileAccessLog.access_timestamp.desc())
            .limit(limit)
            .all()
        )

    # Upload Session Management

    async def create_upload_session(self, tenant_id: str, session_data: dict, user_id: str) -> FileUploadSession:
        """Create file upload session."""
        try:
            session_id = str(uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry

            upload_session = FileUploadSession(
                upload_session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                expires_at=expires_at,
                max_chunks=session_data["total_size"] // session_data.get("chunk_size", 5242880) + 1,
                **session_data,
            )

            self.session.add(upload_session)
            await self.session.commit()
            await self.session.refresh(upload_session)

            logger.info(f"Created upload session: {session_id}")
            return upload_session

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create upload session: {e}")
            raise ValidationError(f"Failed to create upload session: {str(e)}") from e

    async def get_upload_session(self, session_id: str, tenant_id: str) -> Optional[FileUploadSession]:
        """Get upload session by ID."""
        return (
            await self.session.query(FileUploadSession)
            .filter(and_(FileUploadSession.upload_session_id == session_id, FileUploadSession.tenant_id == tenant_id))
            .first()
        )

    async def update_upload_progress(
        self, session_id: str, tenant_id: str, chunk_number: int, chunk_size: int
    ) -> FileUploadSession:
        """Update upload session progress."""
        session = await self.get_upload_session(session_id, tenant_id)
        if not session:
            raise NotFoundError(f"Upload session not found: {session_id}")

        try:
            # Add chunk to completed list
            completed_chunks = session.completed_chunks or []
            if chunk_number not in completed_chunks:
                completed_chunks.append(chunk_number)
                session.completed_chunks = completed_chunks
                session.uploaded_size += chunk_size
                session.chunk_count = len(completed_chunks)

            session.last_activity = datetime.now(timezone.utc)

            # Check if upload is complete
            if session.uploaded_size >= session.total_size:
                session.status = "completed"

            await self.session.commit()
            await self.session.refresh(session)

            return session

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update upload progress: {e}")
            raise ValidationError(f"Failed to update upload progress: {str(e)}") from e

    # Statistics and Analytics

    async def get_tenant_file_stats(self, tenant_id: str) -> dict:
        """Get file statistics for a tenant."""
        try:
            # Basic counts
            total_files = (
                await self.session.query(func.count(FileMetadata.id))
                .filter(FileMetadata.tenant_id == tenant_id)
                .scalar()
            )

            total_size = (
                await self.session.query(func.sum(FileMetadata.file_size))
                .filter(FileMetadata.tenant_id == tenant_id)
                .scalar()
                or 0
            )

            # Files by category
            category_stats = (
                await self.session.query(FileMetadata.file_category, func.count(FileMetadata.id))
                .filter(FileMetadata.tenant_id == tenant_id)
                .group_by(FileMetadata.file_category)
                .all()
            )

            # Files by status
            status_stats = (
                await self.session.query(FileMetadata.file_status, func.count(FileMetadata.id))
                .filter(FileMetadata.tenant_id == tenant_id)
                .group_by(FileMetadata.file_status)
                .all()
            )

            # Recent uploads (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_uploads = (
                await self.session.query(FileMetadata)
                .filter(and_(FileMetadata.tenant_id == tenant_id, FileMetadata.created_at >= week_ago))
                .order_by(FileMetadata.created_at.desc())
                .limit(10)
                .all()
            )

            # Files expiring soon (next 30 days)
            month_from_now = datetime.now(timezone.utc) + timedelta(days=30)
            expiring_soon = (
                await self.session.query(FileMetadata)
                .filter(
                    and_(
                        FileMetadata.tenant_id == tenant_id,
                        FileMetadata.expiration_date.isnot(None),
                        FileMetadata.expiration_date <= month_from_now,
                        FileMetadata.expiration_date > datetime.now(timezone.utc),
                    )
                )
                .order_by(FileMetadata.expiration_date.asc())
                .limit(10)
                .all()
            )

            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "files_by_category": dict(category_stats),
                "files_by_status": dict(status_stats),
                "recent_uploads": recent_uploads,
                "expiring_soon": expiring_soon,
            }

        except Exception as e:
            logger.error(f"Failed to get tenant file stats: {e}")
            raise ValidationError(f"Failed to get tenant file stats: {str(e)}") from e

    async def cleanup_expired_upload_sessions(self) -> int:
        """Clean up expired upload sessions."""
        try:
            expired_sessions = (
                await self.session.query(FileUploadSession)
                .filter(FileUploadSession.expires_at < datetime.now(timezone.utc))
                .all()
            )

            count = len(expired_sessions)

            for session in expired_sessions:
                await self.session.delete(session)

            await self.session.commit()

            logger.info(f"Cleaned up {count} expired upload sessions")
            return count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup expired upload sessions: {e}")
            raise ValidationError(f"Failed to cleanup expired upload sessions: {str(e)}") from e
