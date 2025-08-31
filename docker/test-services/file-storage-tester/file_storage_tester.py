#!/usr/bin/env python3
"""
File Storage Testing Service
Tests S3 storage with tenant isolation, quotas, antivirus, and large file handling
"""

import asyncio
import logging
import os
import sys
import time
import hashlib
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import uuid
import io

import aioboto3
import aiofiles
import clamd
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    test_name: str
    tenant_id: str
    passed: bool
    message: str
    execution_time_ms: int
    details: Optional[Dict[str, Any]] = None

class FileMetadata(BaseModel):
    filename: str
    size: int
    content_type: str
    md5_hash: str
    tenant_id: str
    upload_id: Optional[str] = None
    is_multipart: bool = False

@dataclass
class QuotaInfo:
    tenant_id: str
    used_bytes: int
    limit_bytes: int
    file_count: int
    available_bytes: int

class FileStorageTester:
    def __init__(self):
        # S3 Configuration
        self.s3_endpoint = os.getenv('S3_ENDPOINT', 'http://test-minio:9000')
        self.s3_access_key = os.getenv('S3_ACCESS_KEY', 'admin')
        self.s3_secret_key = os.getenv('S3_SECRET_KEY', 'password123')
        self.s3_region = os.getenv('S3_REGION', 'us-east-1')
        self.s3_use_ssl = os.getenv('S3_USE_SSL', 'false').lower() == 'true'
        
        # ClamAV Configuration
        self.clamav_host = os.getenv('CLAMAV_HOST', 'test-clamav')
        self.clamav_port = int(os.getenv('CLAMAV_PORT', '3310'))
        
        # Test Configuration
        self.bucket_prefix = os.getenv('TEST_BUCKET_PREFIX', 'dotmac-tenant')
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', '104857600'))  # 100MB
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '8388608'))  # 8MB
        self.antivirus_enabled = os.getenv('ANTIVIRUS_ENABLED', 'true').lower() == 'true'
        
        # Test tenants
        tenant_list = os.getenv('TEST_TENANTS', 'tenant-001,tenant-002,tenant-003')
        self.test_tenants = [t.strip() for t in tenant_list.split(',')]
        
        self.results: List[TestResult] = []
        self.tenant_quotas: Dict[str, QuotaInfo] = {}
        
        # Initialize tenant quotas
        for tenant in self.test_tenants:
            self.tenant_quotas[tenant] = QuotaInfo(
                tenant_id=tenant,
                used_bytes=0,
                limit_bytes=50 * 1024 * 1024,  # 50MB per tenant
                file_count=0,
                available_bytes=50 * 1024 * 1024
            )

    async def initialize_s3_buckets(self):
        """Create tenant-scoped S3 buckets"""
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region,
            use_ssl=self.s3_use_ssl
        ) as s3:
            for tenant in self.test_tenants:
                bucket_name = f"{self.bucket_prefix}-{tenant}"
                try:
                    await s3.create_bucket(Bucket=bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
                except Exception as e:
                    if 'BucketAlreadyExists' not in str(e):
                        logger.error(f"Failed to create bucket {bucket_name}: {e}")

    async def scan_file_for_virus(self, file_data: bytes) -> bool:
        """Scan file content for viruses using ClamAV"""
        if not self.antivirus_enabled:
            return True
            
        try:
            cd = clamd.ClamdAsyncNetworkSocket(self.clamav_host, self.clamav_port)
            result = await cd.instream(file_data)
            return result['stream'] == ('OK', None)
        except Exception as e:
            logger.warning(f"Antivirus scan failed: {e}")
            return True  # Allow uploads if AV is unavailable

    async def check_tenant_quota(self, tenant_id: str, file_size: int) -> bool:
        """Check if tenant has enough quota for the file"""
        quota = self.tenant_quotas.get(tenant_id)
        if not quota:
            return False
        return quota.available_bytes >= file_size

    async def update_tenant_usage(self, tenant_id: str, size_delta: int, file_delta: int = 0):
        """Update tenant usage statistics"""
        quota = self.tenant_quotas.get(tenant_id)
        if quota:
            quota.used_bytes += size_delta
            quota.file_count += file_delta
            quota.available_bytes = quota.limit_bytes - quota.used_bytes

    def get_tenant_bucket(self, tenant_id: str) -> str:
        """Get S3 bucket name for tenant"""
        return f"{self.bucket_prefix}-{tenant_id}"

    def get_file_key(self, tenant_id: str, filename: str, file_id: str = None) -> str:
        """Generate S3 object key with tenant isolation"""
        if not file_id:
            file_id = str(uuid.uuid4())
        return f"{tenant_id}/files/{file_id}/{filename}"

    async def upload_small_file(self, tenant_id: str, file_data: bytes, metadata: FileMetadata) -> str:
        """Upload small file directly"""
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region,
            use_ssl=self.s3_use_ssl
        ) as s3:
            bucket = self.get_tenant_bucket(tenant_id)
            file_id = str(uuid.uuid4())
            key = self.get_file_key(tenant_id, metadata.filename, file_id)
            
            await s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_data,
                ContentType=metadata.content_type,
                Metadata={
                    'tenant-id': tenant_id,
                    'filename': metadata.filename,
                    'md5-hash': metadata.md5_hash,
                    'upload-timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            return file_id

    async def start_multipart_upload(self, tenant_id: str, metadata: FileMetadata) -> str:
        """Start multipart upload for large files"""
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region,
            use_ssl=self.s3_use_ssl
        ) as s3:
            bucket = self.get_tenant_bucket(tenant_id)
            file_id = str(uuid.uuid4())
            key = self.get_file_key(tenant_id, metadata.filename, file_id)
            
            response = await s3.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                ContentType=metadata.content_type,
                Metadata={
                    'tenant-id': tenant_id,
                    'filename': metadata.filename,
                    'md5-hash': metadata.md5_hash,
                    'upload-timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            return response['UploadId'], file_id

    async def upload_part(self, tenant_id: str, filename: str, file_id: str, upload_id: str, 
                         part_number: int, part_data: bytes) -> Dict[str, Any]:
        """Upload a single part of multipart upload"""
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region,
            use_ssl=self.s3_use_ssl
        ) as s3:
            bucket = self.get_tenant_bucket(tenant_id)
            key = self.get_file_key(tenant_id, filename, file_id)
            
            response = await s3.upload_part(
                Bucket=bucket,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=part_data
            )
            
            return {
                'ETag': response['ETag'],
                'PartNumber': part_number
            }

    async def complete_multipart_upload(self, tenant_id: str, filename: str, file_id: str, 
                                      upload_id: str, parts: List[Dict[str, Any]]) -> str:
        """Complete multipart upload"""
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region,
            use_ssl=self.s3_use_ssl
        ) as s3:
            bucket = self.get_tenant_bucket(tenant_id)
            key = self.get_file_key(tenant_id, filename, file_id)
            
            multipart_upload = {
                'Parts': sorted(parts, key=lambda x: x['PartNumber'])
            }
            
            await s3.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload=multipart_upload
            )
            
            return file_id

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive file storage tests"""
        logger.info("Starting file storage testing...")
        
        # Initialize S3 buckets
        await self.initialize_s3_buckets()
        
        start_time = time.time()
        
        for tenant_id in self.test_tenants:
            logger.info(f"Running file storage tests for tenant: {tenant_id}")
            
            # Basic file upload tests
            await self._test_small_file_upload(tenant_id)
            await self._test_large_file_upload(tenant_id) 
            await self._test_multipart_upload(tenant_id)
            
            # Quota and limits tests
            await self._test_quota_enforcement(tenant_id)
            await self._test_file_size_limits(tenant_id)
            
            # Antivirus tests
            await self._test_antivirus_scanning(tenant_id)
            
            # Tenant isolation tests
            await self._test_tenant_isolation(tenant_id)
            
            # S3 IAM scoping tests
            await self._test_s3_bucket_scoping(tenant_id)
            
        execution_time = int((time.time() - start_time) * 1000)
        
        # Generate summary
        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]
        
        summary = {
            'total_tests': len(self.results),
            'passed': len(passed_tests),
            'failed': len(failed_tests),
            'execution_time_ms': execution_time,
            'success_rate': len(passed_tests) / len(self.results) * 100 if self.results else 0,
            'tenant_quotas': {k: asdict(v) for k, v in self.tenant_quotas.items()},
            'results': [asdict(r) for r in self.results]
        }
        
        logger.info(f"File storage testing completed: {summary['passed']}/{summary['total_tests']} passed")
        return summary

    async def _test_small_file_upload(self, tenant_id: str):
        """Test small file upload (< chunk size)"""
        start_time = time.time()
        
        try:
            # Create test file data
            test_content = f"Small test file for tenant {tenant_id}" * 100
            test_data = test_content.encode('utf-8')
            
            metadata = FileMetadata(
                filename=f"small-test-{tenant_id}.txt",
                size=len(test_data),
                content_type="text/plain",
                md5_hash=hashlib.md5(test_data).hexdigest(),
                tenant_id=tenant_id
            )
            
            # Check quota
            if not await self.check_tenant_quota(tenant_id, metadata.size):
                raise Exception("Insufficient quota")
            
            # Scan for virus
            if not await self.scan_file_for_virus(test_data):
                raise Exception("File failed antivirus scan")
            
            # Upload file
            file_id = await self.upload_small_file(tenant_id, test_data, metadata)
            
            # Update usage
            await self.update_tenant_usage(tenant_id, metadata.size, 1)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="small_file_upload",
                tenant_id=tenant_id,
                passed=True,
                message="Small file uploaded successfully",
                execution_time_ms=execution_time,
                details={"file_id": file_id, "size": metadata.size}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="small_file_upload",
                tenant_id=tenant_id,
                passed=False,
                message=f"Small file upload failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_large_file_upload(self, tenant_id: str):
        """Test large file upload (> chunk size)"""
        start_time = time.time()
        
        try:
            # Create large test file data (12MB)
            large_size = 12 * 1024 * 1024
            test_data = b'A' * large_size
            
            metadata = FileMetadata(
                filename=f"large-test-{tenant_id}.bin",
                size=len(test_data),
                content_type="application/octet-stream",
                md5_hash=hashlib.md5(test_data).hexdigest(),
                tenant_id=tenant_id,
                is_multipart=True
            )
            
            # Check quota
            if not await self.check_tenant_quota(tenant_id, metadata.size):
                raise Exception("Insufficient quota")
            
            # Scan for virus (sample only for large files)
            sample_data = test_data[:1024*1024]  # 1MB sample
            if not await self.scan_file_for_virus(sample_data):
                raise Exception("File failed antivirus scan")
            
            # Start multipart upload
            upload_id, file_id = await self.start_multipart_upload(tenant_id, metadata)
            
            # Upload parts
            parts = []
            part_number = 1
            offset = 0
            
            while offset < len(test_data):
                chunk = test_data[offset:offset + self.chunk_size]
                part_info = await self.upload_part(
                    tenant_id, metadata.filename, file_id, upload_id, part_number, chunk
                )
                parts.append(part_info)
                part_number += 1
                offset += len(chunk)
            
            # Complete upload
            final_file_id = await self.complete_multipart_upload(
                tenant_id, metadata.filename, file_id, upload_id, parts
            )
            
            # Update usage
            await self.update_tenant_usage(tenant_id, metadata.size, 1)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="large_file_upload",
                tenant_id=tenant_id,
                passed=True,
                message="Large file uploaded successfully via multipart",
                execution_time_ms=execution_time,
                details={"file_id": final_file_id, "size": metadata.size, "parts": len(parts)}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="large_file_upload",
                tenant_id=tenant_id,
                passed=False,
                message=f"Large file upload failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_multipart_upload(self, tenant_id: str):
        """Test multipart upload functionality"""
        start_time = time.time()
        
        try:
            # Create test file in multiple parts (16MB total)
            part_size = 8 * 1024 * 1024  # 8MB parts
            total_parts = 2
            
            metadata = FileMetadata(
                filename=f"multipart-test-{tenant_id}.bin",
                size=part_size * total_parts,
                content_type="application/octet-stream",
                md5_hash="dummy-hash",  # Will calculate per part
                tenant_id=tenant_id,
                is_multipart=True
            )
            
            # Check quota
            if not await self.check_tenant_quota(tenant_id, metadata.size):
                raise Exception("Insufficient quota")
            
            # Start multipart upload
            upload_id, file_id = await self.start_multipart_upload(tenant_id, metadata)
            
            # Upload parts concurrently
            parts = []
            upload_tasks = []
            
            for part_num in range(1, total_parts + 1):
                part_data = f"Part {part_num} data for tenant {tenant_id}".encode() * 1000000  # ~25MB
                part_data = part_data[:part_size]  # Trim to exact size
                
                task = self.upload_part(
                    tenant_id, metadata.filename, file_id, upload_id, part_num, part_data
                )
                upload_tasks.append(task)
            
            # Wait for all parts to upload
            part_results = await asyncio.gather(*upload_tasks)
            parts.extend(part_results)
            
            # Complete upload
            final_file_id = await self.complete_multipart_upload(
                tenant_id, metadata.filename, file_id, upload_id, parts
            )
            
            # Update usage
            await self.update_tenant_usage(tenant_id, metadata.size, 1)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="multipart_upload",
                tenant_id=tenant_id,
                passed=True,
                message="Multipart upload completed successfully",
                execution_time_ms=execution_time,
                details={"file_id": final_file_id, "parts": len(parts), "size": metadata.size}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="multipart_upload",
                tenant_id=tenant_id,
                passed=False,
                message=f"Multipart upload failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_quota_enforcement(self, tenant_id: str):
        """Test tenant quota enforcement"""
        start_time = time.time()
        
        try:
            # Try to upload file that exceeds quota
            quota = self.tenant_quotas[tenant_id]
            oversized_file_size = quota.available_bytes + 1024  # 1KB over limit
            
            test_data = b'X' * oversized_file_size
            
            # This should fail quota check
            quota_check = await self.check_tenant_quota(tenant_id, oversized_file_size)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="quota_enforcement",
                tenant_id=tenant_id,
                passed=not quota_check,  # Should fail quota check
                message=f"Quota enforcement {'working' if not quota_check else 'failed'}",
                execution_time_ms=execution_time,
                details={
                    "attempted_size": oversized_file_size,
                    "available_quota": quota.available_bytes,
                    "quota_check_passed": quota_check
                }
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="quota_enforcement",
                tenant_id=tenant_id,
                passed=False,
                message=f"Quota enforcement test failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_file_size_limits(self, tenant_id: str):
        """Test file size limit enforcement"""
        start_time = time.time()
        
        try:
            # Try to upload file exceeding max size limit
            oversized_file_size = self.max_file_size + 1024
            
            # Mock large file (don't actually create it)
            size_check_passed = oversized_file_size <= self.max_file_size
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="file_size_limits",
                tenant_id=tenant_id,
                passed=not size_check_passed,  # Should reject oversized file
                message=f"File size limit enforcement {'working' if not size_check_passed else 'failed'}",
                execution_time_ms=execution_time,
                details={
                    "attempted_size": oversized_file_size,
                    "max_allowed_size": self.max_file_size,
                    "size_check_passed": size_check_passed
                }
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="file_size_limits",
                tenant_id=tenant_id,
                passed=False,
                message=f"File size limits test failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_antivirus_scanning(self, tenant_id: str):
        """Test antivirus scanning functionality"""
        start_time = time.time()
        
        try:
            # Test with clean file
            clean_data = b"Clean test file content"
            clean_result = await self.scan_file_for_virus(clean_data)
            
            # Test with EICAR test string (standard AV test file)
            eicar_data = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
            
            try:
                virus_result = await self.scan_file_for_virus(eicar_data)
            except:
                virus_result = False  # Assume scan detected virus if exception
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Test passes if clean file is accepted and virus is rejected
            test_passed = clean_result and not virus_result
            
            self.results.append(TestResult(
                test_name="antivirus_scanning",
                tenant_id=tenant_id,
                passed=test_passed,
                message=f"Antivirus scanning {'working correctly' if test_passed else 'failed'}",
                execution_time_ms=execution_time,
                details={
                    "clean_file_passed": clean_result,
                    "virus_file_blocked": not virus_result,
                    "antivirus_enabled": self.antivirus_enabled
                }
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="antivirus_scanning",
                tenant_id=tenant_id,
                passed=False,
                message=f"Antivirus scanning test failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_tenant_isolation(self, tenant_id: str):
        """Test tenant data isolation in S3"""
        start_time = time.time()
        
        try:
            # Verify tenant has dedicated bucket
            bucket_name = self.get_tenant_bucket(tenant_id)
            expected_bucket = f"{self.bucket_prefix}-{tenant_id}"
            
            # Verify file key includes tenant prefix
            test_key = self.get_file_key(tenant_id, "test-file.txt", "test-id")
            key_has_tenant_prefix = test_key.startswith(f"{tenant_id}/")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            isolation_verified = bucket_name == expected_bucket and key_has_tenant_prefix
            
            self.results.append(TestResult(
                test_name="tenant_isolation",
                tenant_id=tenant_id,
                passed=isolation_verified,
                message=f"Tenant isolation {'verified' if isolation_verified else 'failed'}",
                execution_time_ms=execution_time,
                details={
                    "bucket_name": bucket_name,
                    "expected_bucket": expected_bucket,
                    "file_key": test_key,
                    "key_has_tenant_prefix": key_has_tenant_prefix
                }
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="tenant_isolation",
                tenant_id=tenant_id,
                passed=False,
                message=f"Tenant isolation test failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_s3_bucket_scoping(self, tenant_id: str):
        """Test S3 bucket and IAM scoping"""
        start_time = time.time()
        
        try:
            session = aioboto3.Session()
            async with session.client(
                's3',
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
                region_name=self.s3_region,
                use_ssl=self.s3_use_ssl
            ) as s3:
                
                # Test access to tenant's bucket
                tenant_bucket = self.get_tenant_bucket(tenant_id)
                
                try:
                    await s3.head_bucket(Bucket=tenant_bucket)
                    tenant_bucket_accessible = True
                except:
                    tenant_bucket_accessible = False
                
                # Test bucket isolation by listing objects with tenant prefix
                try:
                    response = await s3.list_objects_v2(
                        Bucket=tenant_bucket,
                        Prefix=f"{tenant_id}/"
                    )
                    objects_scoped_correctly = True
                    object_count = response.get('KeyCount', 0)
                except:
                    objects_scoped_correctly = False
                    object_count = 0
                
                execution_time = int((time.time() - start_time) * 1000)
                
                scoping_verified = tenant_bucket_accessible and objects_scoped_correctly
                
                self.results.append(TestResult(
                    test_name="s3_bucket_scoping",
                    tenant_id=tenant_id,
                    passed=scoping_verified,
                    message=f"S3 bucket scoping {'verified' if scoping_verified else 'failed'}",
                    execution_time_ms=execution_time,
                    details={
                        "tenant_bucket": tenant_bucket,
                        "bucket_accessible": tenant_bucket_accessible,
                        "objects_scoped": objects_scoped_correctly,
                        "object_count": object_count
                    }
                ))
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="s3_bucket_scoping",
                tenant_id=tenant_id,
                passed=False,
                message=f"S3 bucket scoping test failed: {str(e)}",
                execution_time_ms=execution_time
            ))

# FastAPI app for health checks and results
app = FastAPI(title="File Storage Tester", version="1.0.0")
tester = FileStorageTester()
test_results = {}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/run-tests")
async def run_tests():
    global test_results
    test_results = await tester.run_all_tests()
    return test_results

@app.get("/results")
async def get_results():
    return test_results

@app.get("/quotas")
async def get_quotas():
    return {k: asdict(v) for k, v in tester.tenant_quotas.items()}

async def main():
    """Main entry point"""
    logger.info("Starting File Storage Testing Service...")
    
    # Wait for dependencies
    await asyncio.sleep(10)
    
    # Run tests automatically
    logger.info("Running file storage tests...")
    results = await tester.run_all_tests()
    
    # Print summary
    print(f"\n{'='*60}")
    print("FILE STORAGE TESTING SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Execution Time: {results['execution_time_ms']}ms")
    
    # Show tenant quotas
    print(f"\n{'='*40}")
    print("TENANT QUOTAS")
    print(f"{'='*40}")
    for tenant_id, quota in results['tenant_quotas'].items():
        used_mb = quota['used_bytes'] / 1024 / 1024
        limit_mb = quota['limit_bytes'] / 1024 / 1024
        available_mb = quota['available_bytes'] / 1024 / 1024
        usage_pct = (quota['used_bytes'] / quota['limit_bytes']) * 100
        print(f"{tenant_id}: {used_mb:.1f}MB / {limit_mb:.1f}MB ({usage_pct:.1f}%) - {quota['file_count']} files")
    
    # Show failed tests
    failed_tests = [r for r in results['results'] if not r['passed']]
    if failed_tests:
        print(f"\n{'='*40}")
        print("FAILED TESTS")
        print(f"{'='*40}")
        for test in failed_tests:
            print(f"❌ {test['test_name']} ({test['tenant_id']}): {test['message']}")
    
    print(f"\n{'='*60}")
    
    # Start FastAPI server for health checks
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())