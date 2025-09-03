"""File Management Service for the Management Platform."""

import hashlib
import logging
import mimetypes
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from dotmac_shared.exceptions import NotFoundError, ValidationError, PermissionError
from dotmac_shared.file_management.models import AccessLevel, FileCategory, FileStatus, ScanStatus
from dotmac_shared.file_management.schemas import (
    FileMetadataCreate,
    FileMetadataResponse,
    FileMetadataUpdate,
    FilePermissionCreate,
    FileSearchFilters,
    FileUploadSessionCreate,
    FileValidationResponse,
)

from ..repositories.file_repository import FileRepository

logger = logging.getLogger(__name__)


class FileService:
    """Service for file management operations."""

    def __init__(self, file_repository: FileRepository):
        self.file_repository = file_repository
        self.storage_base_path = Path(os.getenv('FILE_STORAGE_PATH', '/var/dotmac/files'))
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
        
        # Ensure storage directory exists
        self.storage_base_path.mkdir(parents=True, exist_ok=True)

    # File Upload and Creation

    async def create_file(
        self,
        tenant_id: str,
        user_id: str,
        file_data: FileMetadataCreate,
        file_content: bytes = None
    ) -> FileMetadataResponse:
        """Create a new file with metadata."""
        try:
            # Generate unique file ID
            file_id = str(uuid4())
            
            # Determine storage path
            tenant_storage = self.storage_base_path / tenant_id
            tenant_storage.mkdir(parents=True, exist_ok=True)
            
            # Generate stored filename with file ID
            file_extension = self._get_file_extension(file_data.original_filename)
            stored_filename = f"{file_id}{file_extension}"
            storage_path = tenant_storage / stored_filename
            
            # Calculate file hash if content provided
            md5_hash = ""
            sha256_hash = ""
            file_size = 0
            mime_type = mimetypes.guess_type(file_data.original_filename)[0] or "application/octet-stream"
            
            if file_content:
                # Validate file size
                file_size = len(file_content)
                if file_size > self.max_file_size:
                    raise ValidationError(f"File size exceeds maximum allowed: {self.max_file_size} bytes")
                
                # Calculate hashes
                md5_hash = hashlib.md5(file_content).hexdigest()
                sha256_hash = hashlib.sha256(file_content).hexdigest()
                
                # Save file to storage
                with open(storage_path, 'wb') as f:
                    f.write(file_content)
                
                logger.info(f"Saved file content to: {storage_path}")
            
            # Create file metadata
            metadata_dict = {
                'file_id': file_id,
                'original_filename': file_data.original_filename,
                'stored_filename': stored_filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'file_extension': file_extension,
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash,
                'storage_type': 'local',
                'storage_path': str(storage_path),
                'file_category': file_data.file_category,
                'file_status': FileStatus.UPLOADED if file_content else FileStatus.UPLOADING,
                'access_level': file_data.access_level,
                'owner_user_id': user_id,
                'is_public': file_data.access_level == AccessLevel.PUBLIC,
                'scan_status': ScanStatus.PENDING,
                'description': file_data.description,
                'tags': file_data.tags,
                'related_entity_type': file_data.related_entity_type,
                'related_entity_id': file_data.related_entity_id,
                'upload_completed_at': datetime.now(timezone.utc) if file_content else None,
            }
            
            # Set expiration date if specified
            if file_data.expiration_days:
                metadata_dict['expiration_date'] = datetime.now(timezone.utc) + timedelta(days=file_data.expiration_days)
            
            file_metadata = await self.file_repository.create_file_metadata(
                tenant_id=tenant_id,
                file_data=metadata_dict,
                user_id=user_id
            )
            
            # Log file creation
            await self.file_repository.log_file_access(
                tenant_id=tenant_id,
                access_data={
                    'file_id': file_id,
                    'user_id': user_id,
                    'action': 'create',
                    'access_timestamp': datetime.now(timezone.utc)
                }
            )
            
            return self._convert_to_response(file_metadata)
            
        except Exception as e:
            # Cleanup file if it was saved
            if 'storage_path' in locals() and storage_path.exists():
                storage_path.unlink()
            
            logger.error(f"Failed to create file: {e}")
            raise ValidationError(f"Failed to create file: {str(e)}")

    async def get_file(
        self,
        file_id: str,
        tenant_id: str,
        user_id: str
    ) -> FileMetadataResponse:
        """Get file metadata by ID."""
        file_metadata = await self.file_repository.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")
        
        # Check permissions
        await self._check_file_permission(file_metadata, user_id, 'read')
        
        # Log access
        await self.file_repository.log_file_access(
            tenant_id=tenant_id,
            access_data={
                'file_id': file_id,
                'user_id': user_id,
                'action': 'read',
                'access_timestamp': datetime.now(timezone.utc)
            }
        )
        
        # Update last accessed
        await self.file_repository.update_file_metadata(
            file_id=file_id,
            tenant_id=tenant_id,
            updates={'last_accessed': datetime.now(timezone.utc)},
            user_id=user_id
        )
        
        return self._convert_to_response(file_metadata)

    async def get_file_content(
        self,
        file_id: str,
        tenant_id: str,
        user_id: str
    ) -> Tuple[bytes, str, str]:
        """Get file content for download."""
        file_metadata = await self.file_repository.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")
        
        # Check permissions
        await self._check_file_permission(file_metadata, user_id, 'download')
        
        # Check if file exists on disk
        storage_path = Path(file_metadata.storage_path)
        if not storage_path.exists():
            raise NotFoundError(f"File content not found: {file_id}")
        
        try:
            # Read file content
            with open(storage_path, 'rb') as f:
                content = f.read()
            
            # Log download
            await self.file_repository.log_file_access(
                tenant_id=tenant_id,
                access_data={
                    'file_id': file_id,
                    'user_id': user_id,
                    'action': 'download',
                    'bytes_transferred': len(content),
                    'access_timestamp': datetime.now(timezone.utc)
                }
            )
            
            # Update download count
            await self.file_repository.update_file_metadata(
                file_id=file_id,
                tenant_id=tenant_id,
                updates={
                    'download_count': file_metadata.download_count + 1,
                    'last_accessed': datetime.now(timezone.utc)
                },
                user_id=user_id
            )
            
            return content, file_metadata.original_filename, file_metadata.mime_type
            
        except Exception as e:
            logger.error(f"Failed to read file content: {e}")
            raise ValidationError(f"Failed to read file content: {str(e)}")

    async def update_file(
        self,
        file_id: str,
        tenant_id: str,
        user_id: str,
        updates: FileMetadataUpdate
    ) -> FileMetadataResponse:
        """Update file metadata."""
        file_metadata = await self.file_repository.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")
        
        # Check permissions
        await self._check_file_permission(file_metadata, user_id, 'write')
        
        # Prepare updates dictionary
        update_dict = {}
        if updates.original_filename is not None:
            update_dict['original_filename'] = updates.original_filename
        if updates.description is not None:
            update_dict['description'] = updates.description
        if updates.tags is not None:
            update_dict['tags'] = updates.tags
        if updates.access_level is not None:
            update_dict['access_level'] = updates.access_level
            update_dict['is_public'] = updates.access_level == AccessLevel.PUBLIC
        if updates.expiration_days is not None:
            update_dict['expiration_date'] = datetime.now(timezone.utc) + timedelta(days=updates.expiration_days)
        
        updated_metadata = await self.file_repository.update_file_metadata(
            file_id=file_id,
            tenant_id=tenant_id,
            updates=update_dict,
            user_id=user_id
        )
        
        # Log update
        await self.file_repository.log_file_access(
            tenant_id=tenant_id,
            access_data={
                'file_id': file_id,
                'user_id': user_id,
                'action': 'update',
                'access_timestamp': datetime.now(timezone.utc)
            }
        )
        
        return self._convert_to_response(updated_metadata)

    async def delete_file(
        self,
        file_id: str,
        tenant_id: str,
        user_id: str,
        permanent: bool = False
    ) -> bool:
        """Delete file (soft or hard delete)."""
        file_metadata = await self.file_repository.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")
        
        # Check permissions
        await self._check_file_permission(file_metadata, user_id, 'delete')
        
        if permanent:
            # Hard delete - remove file from storage and database
            storage_path = Path(file_metadata.storage_path)
            if storage_path.exists():
                storage_path.unlink()
            
            # Delete from database (implement this in repository)
            # For now, just mark as deleted
            await self.file_repository.delete_file_metadata(file_id, tenant_id, user_id)
        else:
            # Soft delete - mark as deleted
            await self.file_repository.delete_file_metadata(file_id, tenant_id, user_id)
        
        # Log deletion
        await self.file_repository.log_file_access(
            tenant_id=tenant_id,
            access_data={
                'file_id': file_id,
                'user_id': user_id,
                'action': 'delete',
                'access_timestamp': datetime.now(timezone.utc)
            }
        )
        
        return True

    # File Search and Listing

    async def search_files(
        self,
        tenant_id: str,
        user_id: str,
        search_filters: FileSearchFilters,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[FileMetadataResponse], int]:
        """Search files with filters."""
        skip = (page - 1) * size
        
        # Convert search filters to repository filters
        filters = {
            'query': search_filters.query,
            'category': search_filters.category,
            'status': search_filters.status,
            'access_level': search_filters.access_level,
            'scan_status': search_filters.scan_status,
            'owner_user_id': search_filters.owner_user_id,
            'tags': search_filters.tags,
            'file_extension': search_filters.file_extension,
            'min_size_bytes': search_filters.min_size_bytes,
            'max_size_bytes': search_filters.max_size_bytes,
            'created_after': search_filters.created_after,
            'created_before': search_filters.created_before,
            'related_entity_type': search_filters.related_entity_type,
            'related_entity_id': search_filters.related_entity_id,
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        files, total = await self.file_repository.search_files(
            tenant_id=tenant_id,
            filters=filters,
            skip=skip,
            limit=size
        )
        
        # Filter files based on user permissions
        accessible_files = []
        for file_metadata in files:
            try:
                await self._check_file_permission(file_metadata, user_id, 'read')
                accessible_files.append(self._convert_to_response(file_metadata))
            except PermissionError:
                continue  # Skip files user can't access
        
        return accessible_files, total

    async def get_user_files(
        self,
        tenant_id: str,
        user_id: str,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[FileMetadataResponse], int]:
        """Get files owned by a user."""
        skip = (page - 1) * size
        
        files, total = await self.file_repository.get_files_by_owner(
            tenant_id=tenant_id,
            owner_user_id=user_id,
            skip=skip,
            limit=size
        )
        
        file_responses = [self._convert_to_response(f) for f in files]
        return file_responses, total

    # File Permissions

    async def grant_file_permission(
        self,
        file_id: str,
        tenant_id: str,
        granter_user_id: str,
        permission_data: FilePermissionCreate
    ) -> bool:
        """Grant file permission to a user."""
        file_metadata = await self.file_repository.get_file_by_id(file_id, tenant_id)
        if not file_metadata:
            raise NotFoundError(f"File not found: {file_id}")
        
        # Check if granter has permission to share
        await self._check_file_permission(file_metadata, granter_user_id, 'share')
        
        # Create permission
        permission_dict = {
            'file_id': file_id,
            'user_id': permission_data.user_id,
            'user_group_id': permission_data.user_group_id,
            'role': permission_data.role,
            'can_read': permission_data.can_read,
            'can_write': permission_data.can_write,
            'can_delete': permission_data.can_delete,
            'can_share': permission_data.can_share,
            'can_download': permission_data.can_download,
            'expires_at': permission_data.expires_at,
            'notes': permission_data.notes,
        }
        
        await self.file_repository.create_file_permission(
            tenant_id=tenant_id,
            permission_data=permission_dict,
            user_id=granter_user_id
        )
        
        # Log permission grant
        await self.file_repository.log_file_access(
            tenant_id=tenant_id,
            access_data={
                'file_id': file_id,
                'user_id': granter_user_id,
                'action': 'grant_permission',
                'access_timestamp': datetime.now(timezone.utc)
            }
        )
        
        return True

    # File Validation

    async def validate_file(
        self,
        filename: str,
        file_size: int,
        content_type: str = None,
        category: FileCategory = None
    ) -> FileValidationResponse:
        """Validate file before upload."""
        errors = []
        warnings = []
        
        # Validate filename
        if not self._is_safe_filename(filename):
            errors.append("Filename contains invalid characters")
        
        # Validate file size
        if file_size > self.max_file_size:
            errors.append(f"File size ({file_size} bytes) exceeds maximum allowed ({self.max_file_size} bytes)")
        
        # Detect file category
        detected_category = self._detect_file_category(filename)
        
        # Get allowed extensions for category
        allowed_extensions = self._get_allowed_extensions(detected_category)
        
        # Validate extension
        file_extension = self._get_file_extension(filename).lower()
        if file_extension not in allowed_extensions:
            errors.append(f"File extension '{file_extension}' not allowed for category '{detected_category}'")
        
        # Security score (basic implementation)
        security_score = 100
        if file_extension in ['.exe', '.bat', '.cmd', '.scr']:
            security_score = 10
            warnings.append("Executable file detected - may pose security risk")
        elif file_extension in ['.js', '.vbs', '.ps1']:
            security_score = 30
            warnings.append("Script file detected - may pose security risk")
        
        return FileValidationResponse(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            detected_category=detected_category,
            max_allowed_size=self.max_file_size,
            allowed_extensions=allowed_extensions,
            security_score=security_score
        )

    # Statistics and Analytics

    async def get_tenant_file_stats(self, tenant_id: str) -> Dict:
        """Get file statistics for a tenant."""
        return await self.file_repository.get_tenant_file_stats(tenant_id)

    # Upload Session Management

    async def create_upload_session(
        self,
        tenant_id: str,
        user_id: str,
        session_data: FileUploadSessionCreate
    ):
        """Create file upload session for large files."""
        session_dict = {
            'filename': session_data.filename,
            'total_size': session_data.total_size,
            'mime_type': session_data.mime_type,
            'chunk_size': session_data.chunk_size,
        }
        
        return await self.file_repository.create_upload_session(
            tenant_id=tenant_id,
            session_data=session_dict,
            user_id=user_id
        )

    # Helper Methods

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        return Path(filename).suffix.lower()

    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        forbidden_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in filename for char in forbidden_chars)

    def _detect_file_category(self, filename: str) -> FileCategory:
        """Detect file category from filename."""
        extension = self._get_file_extension(filename)
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg'}
        
        if extension in image_extensions:
            return FileCategory.IMAGE
        elif extension in document_extensions:
            return FileCategory.DOCUMENT
        elif extension in video_extensions:
            return FileCategory.VIDEO
        elif extension in audio_extensions:
            return FileCategory.AUDIO
        else:
            return FileCategory.OTHER

    def _get_allowed_extensions(self, category: FileCategory) -> List[str]:
        """Get allowed extensions for file category."""
        extensions = {
            FileCategory.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            FileCategory.DOCUMENT: ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
            FileCategory.VIDEO: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
            FileCategory.AUDIO: ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            FileCategory.CONFIGURATION: ['.json', '.yaml', '.yml', '.xml', '.ini', '.cfg'],
            FileCategory.OTHER: [],  # Allow all for OTHER
        }
        
        return extensions.get(category, [])

    async def _check_file_permission(
        self,
        file_metadata,
        user_id: str,
        action: str
    ) -> bool:
        """Check if user has permission to perform action on file."""
        # Owner always has full permissions
        if file_metadata.owner_user_id == user_id:
            return True
        
        # Check if file is public and action is read/download
        if file_metadata.is_public and action in ['read', 'download']:
            return True
        
        # Check explicit permissions
        permission = await self.file_repository.get_user_file_permissions(
            file_id=file_metadata.file_id,
            user_id=user_id,
            tenant_id=file_metadata.tenant_id
        )
        
        if not permission:
            raise PermissionError(f"No permission to {action} file: {file_metadata.file_id}")
        
        # Check if permission has expired
        if permission.expires_at and datetime.now(timezone.utc) > permission.expires_at:
            raise PermissionError(f"Permission expired for file: {file_metadata.file_id}")
        
        # Check specific action permissions
        permission_map = {
            'read': permission.can_read,
            'download': permission.can_download,
            'write': permission.can_write,
            'delete': permission.can_delete,
            'share': permission.can_share,
        }
        
        if not permission_map.get(action, False):
            raise PermissionError(f"No {action} permission for file: {file_metadata.file_id}")
        
        return True

    def _convert_to_response(self, file_metadata) -> FileMetadataResponse:
        """Convert file metadata model to response schema."""
        return FileMetadataResponse(
            id=file_metadata.id,
            file_id=file_metadata.file_id,
            tenant_id=file_metadata.tenant_id,
            original_filename=file_metadata.original_filename,
            stored_filename=file_metadata.stored_filename,
            file_size=file_metadata.file_size,
            mime_type=file_metadata.mime_type,
            file_extension=file_metadata.file_extension,
            md5_hash=file_metadata.md5_hash,
            sha256_hash=file_metadata.sha256_hash,
            storage_type=file_metadata.storage_type,
            storage_path=file_metadata.storage_path,
            file_category=file_metadata.file_category,
            file_status=file_metadata.file_status,
            access_level=file_metadata.access_level,
            owner_user_id=file_metadata.owner_user_id,
            is_public=file_metadata.is_public,
            scan_status=file_metadata.scan_status,
            scan_result=file_metadata.scan_result,
            is_encrypted=file_metadata.is_encrypted,
            upload_completed_at=file_metadata.upload_completed_at,
            expiration_date=file_metadata.expiration_date,
            last_accessed=file_metadata.last_accessed,
            download_count=file_metadata.download_count,
            version=file_metadata.version,
            description=file_metadata.description,
            tags=file_metadata.tags,
            related_entity_type=file_metadata.related_entity_type,
            related_entity_id=file_metadata.related_entity_id,
            created_at=file_metadata.created_at,
            updated_at=file_metadata.updated_at,
        )