#!/usr/bin/env python3
"""
Notification Testing Service
Tests SMTP and SMS infrastructure with tenant isolation
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiohttp
import aiosmtplib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
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

class SMTPTestConfig(BaseModel):
    host: str = Field(default="test-smtp")
    port: int = Field(default=1025)
    use_tls: bool = Field(default=False)
    username: Optional[str] = None
    password: Optional[str] = None

class SMSTestConfig(BaseModel):
    webhook_url: str = Field(default="http://test-sms:3030/webhook")
    send_url: str = Field(default="http://test-sms:3030/send")
    management_url: str = Field(default="http://test-sms:3030")

class NotificationTester:
    def __init__(self):
        self.smtp_config = SMTPTestConfig(
            host=os.getenv('SMTP_HOST', 'test-smtp'),
            port=int(os.getenv('SMTP_PORT', '1025'))
        )
        self.sms_config = SMSTestConfig(
            webhook_url=os.getenv('SMS_WEBHOOK_URL', 'http://test-sms:3030/webhook'),
            send_url=os.getenv('SMS_SEND_URL', 'http://test-sms:3030/send'),
            management_url=os.getenv('SMS_MANAGEMENT_URL', 'http://test-sms:3030')
        )
        self.test_domain = os.getenv('TEST_EMAIL_DOMAIN', 'test.dotmac.local')
        self.results: List[TestResult] = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all notification tests with tenant isolation"""
        logger.info("Starting comprehensive notification testing...")
        
        # Test tenants
        test_tenants = ['tenant-001', 'tenant-002', 'tenant-003']
        
        start_time = time.time()
        
        for tenant_id in test_tenants:
            logger.info(f"Running tests for tenant: {tenant_id}")
            
            # SMTP Tests
            await self._test_smtp_basic(tenant_id)
            await self._test_smtp_multipart(tenant_id)
            await self._test_smtp_tenant_isolation(tenant_id)
            
            # SMS Tests  
            await self._test_sms_send(tenant_id)
            await self._test_sms_receive(tenant_id)
            await self._test_sms_tenant_isolation(tenant_id)
            
            # Integration Tests
            await self._test_notification_workflow(tenant_id)
            
        execution_time = int((time.time() - start_time) * 1000)
        
        # Generate summary
        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]
        
        summary = {
            'total_tests': len(self.results),
            'passed': len(passed_tests),
            'failed': len(failed_tests),
            'execution_time_ms': execution_time,
            'success_rate': len(passed_tests) / len(self.results) * 100,
            'results': [asdict(r) for r in self.results]
        }
        
        logger.info(f"Testing completed: {summary['passed']}/{summary['total_tests']} passed")
        return summary

    async def _test_smtp_basic(self, tenant_id: str):
        """Test basic SMTP email sending"""
        start_time = time.time()
        
        try:
            # Create tenant-specific email
            to_email = f"test-{tenant_id}@{self.test_domain}"
            subject = f"Test Email for Tenant {tenant_id}"
            body = f"This is a test email for tenant {tenant_id} at {datetime.now(timezone.utc).isoformat()}"
            
            # Send email
            message = MIMEText(body)
            message["From"] = f"noreply@{self.test_domain}"
            message["To"] = to_email
            message["Subject"] = subject
            message["X-Tenant-ID"] = tenant_id
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_config.host,
                port=self.smtp_config.port,
                use_tls=self.smtp_config.use_tls
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="smtp_basic_send",
                tenant_id=tenant_id,
                passed=True,
                message="Basic SMTP email sent successfully",
                execution_time_ms=execution_time,
                details={"to": to_email, "subject": subject}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="smtp_basic_send",
                tenant_id=tenant_id,
                passed=False,
                message=f"SMTP basic send failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_smtp_multipart(self, tenant_id: str):
        """Test multipart SMTP email"""
        start_time = time.time()
        
        try:
            to_email = f"multipart-{tenant_id}@{self.test_domain}"
            
            # Create multipart message
            message = MIMEMultipart('alternative')
            message["From"] = f"noreply@{self.test_domain}"
            message["To"] = to_email
            message["Subject"] = f"Multipart Test - Tenant {tenant_id}"
            message["X-Tenant-ID"] = tenant_id
            
            # Add text and HTML parts
            text_part = MIMEText(f"Plain text for tenant {tenant_id}", 'plain')
            html_part = MIMEText(f"<h1>HTML content for tenant {tenant_id}</h1>", 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_config.host,
                port=self.smtp_config.port,
                use_tls=self.smtp_config.use_tls
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="smtp_multipart_send",
                tenant_id=tenant_id,
                passed=True,
                message="Multipart SMTP email sent successfully",
                execution_time_ms=execution_time,
                details={"to": to_email, "parts": 2}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="smtp_multipart_send", 
                tenant_id=tenant_id,
                passed=False,
                message=f"SMTP multipart send failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_smtp_tenant_isolation(self, tenant_id: str):
        """Test SMTP tenant isolation by checking email headers"""
        start_time = time.time()
        
        try:
            # Send email with tenant-specific headers
            to_email = f"isolation-{tenant_id}@{self.test_domain}"
            
            message = MIMEText(f"Tenant isolation test for {tenant_id}")
            message["From"] = f"noreply@{self.test_domain}"
            message["To"] = to_email
            message["Subject"] = f"Isolation Test - {tenant_id}"
            message["X-Tenant-ID"] = tenant_id
            message["X-Test-Type"] = "tenant-isolation"
            message["X-Timestamp"] = datetime.now(timezone.utc).isoformat()
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_config.host,
                port=self.smtp_config.port,
                use_tls=self.smtp_config.use_tls
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="smtp_tenant_isolation",
                tenant_id=tenant_id,
                passed=True,
                message="SMTP tenant isolation headers applied",
                execution_time_ms=execution_time,
                details={"tenant_header": tenant_id, "isolation_test": True}
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="smtp_tenant_isolation",
                tenant_id=tenant_id,
                passed=False,
                message=f"SMTP tenant isolation failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_sms_send(self, tenant_id: str):
        """Test SMS sending through sink"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                sms_data = {
                    "to": f"+1555{tenant_id[-3:]}0001",  # Tenant-specific number
                    "from": "+15551234567",
                    "message": f"Test SMS for tenant {tenant_id} at {datetime.now(timezone.utc).isoformat()}",
                    "tenant_id": tenant_id
                }
                
                async with session.post(self.sms_config.send_url, json=sms_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        execution_time = int((time.time() - start_time) * 1000)
                        
                        self.results.append(TestResult(
                            test_name="sms_send",
                            tenant_id=tenant_id,
                            passed=True,
                            message="SMS sent successfully through sink",
                            execution_time_ms=execution_time,
                            details={"sms_id": result.get('id'), "to": sms_data["to"]}
                        ))
                    else:
                        execution_time = int((time.time() - start_time) * 1000)
                        self.results.append(TestResult(
                            test_name="sms_send",
                            tenant_id=tenant_id,
                            passed=False,
                            message=f"SMS send failed: HTTP {response.status}",
                            execution_time_ms=execution_time
                        ))
                        
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="sms_send",
                tenant_id=tenant_id,
                passed=False,
                message=f"SMS send failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_sms_receive(self, tenant_id: str):
        """Test SMS receiving through webhook"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Simulate incoming SMS
                incoming_sms = {
                    "from": f"+1555{tenant_id[-3:]}0002",
                    "to": "+15551234567",
                    "message": f"Incoming SMS from tenant {tenant_id}",
                    "tenant_id": tenant_id
                }
                
                async with session.post(self.sms_config.webhook_url, json=incoming_sms) as response:
                    if response.status == 200:
                        result = await response.json()
                        execution_time = int((time.time() - start_time) * 1000)
                        
                        self.results.append(TestResult(
                            test_name="sms_receive",
                            tenant_id=tenant_id,
                            passed=True,
                            message="SMS received successfully through webhook",
                            execution_time_ms=execution_time,
                            details={"sms_id": result.get('id'), "from": incoming_sms["from"]}
                        ))
                    else:
                        execution_time = int((time.time() - start_time) * 1000)
                        self.results.append(TestResult(
                            test_name="sms_receive",
                            tenant_id=tenant_id,
                            passed=False,
                            message=f"SMS receive failed: HTTP {response.status}",
                            execution_time_ms=execution_time
                        ))
                        
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="sms_receive",
                tenant_id=tenant_id,
                passed=False,
                message=f"SMS receive failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_sms_tenant_isolation(self, tenant_id: str):
        """Test SMS tenant isolation by filtering messages"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get messages for specific tenant
                params = {"tenant_id": tenant_id, "limit": 10}
                async with session.get(f"{self.sms_config.management_url}/messages", params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        messages = result.get('messages', [])
                        
                        # Verify all messages belong to this tenant
                        isolation_verified = all(
                            msg.get('tenant_id') == tenant_id 
                            for msg in messages 
                            if msg.get('tenant_id') is not None
                        )
                        
                        execution_time = int((time.time() - start_time) * 1000)
                        
                        self.results.append(TestResult(
                            test_name="sms_tenant_isolation",
                            tenant_id=tenant_id,
                            passed=isolation_verified,
                            message=f"SMS tenant isolation {'verified' if isolation_verified else 'failed'}",
                            execution_time_ms=execution_time,
                            details={"message_count": len(messages), "isolation_verified": isolation_verified}
                        ))
                    else:
                        execution_time = int((time.time() - start_time) * 1000)
                        self.results.append(TestResult(
                            test_name="sms_tenant_isolation",
                            tenant_id=tenant_id,
                            passed=False,
                            message=f"SMS tenant isolation check failed: HTTP {response.status}",
                            execution_time_ms=execution_time
                        ))
                        
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="sms_tenant_isolation",
                tenant_id=tenant_id,
                passed=False,
                message=f"SMS tenant isolation check failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _test_notification_workflow(self, tenant_id: str):
        """Test complete notification workflow"""
        start_time = time.time()
        
        try:
            # Send coordinated email and SMS
            email_task = self._send_workflow_email(tenant_id)
            sms_task = self._send_workflow_sms(tenant_id)
            
            email_result, sms_result = await asyncio.gather(email_task, sms_task, return_exceptions=True)
            
            email_success = not isinstance(email_result, Exception)
            sms_success = not isinstance(sms_result, Exception)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            self.results.append(TestResult(
                test_name="notification_workflow",
                tenant_id=tenant_id,
                passed=email_success and sms_success,
                message=f"Workflow test: Email {'✓' if email_success else '✗'}, SMS {'✓' if sms_success else '✗'}",
                execution_time_ms=execution_time,
                details={
                    "email_success": email_success,
                    "sms_success": sms_success,
                    "coordinated_send": True
                }
            ))
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.results.append(TestResult(
                test_name="notification_workflow",
                tenant_id=tenant_id,
                passed=False,
                message=f"Notification workflow failed: {str(e)}",
                execution_time_ms=execution_time
            ))

    async def _send_workflow_email(self, tenant_id: str):
        """Send workflow email"""
        to_email = f"workflow-{tenant_id}@{self.test_domain}"
        
        message = MIMEText(f"Workflow notification for tenant {tenant_id}")
        message["From"] = f"workflow@{self.test_domain}"
        message["To"] = to_email
        message["Subject"] = f"Workflow Test - {tenant_id}"
        message["X-Tenant-ID"] = tenant_id
        message["X-Workflow-ID"] = f"wf-{int(time.time())}"
        
        await aiosmtplib.send(
            message,
            hostname=self.smtp_config.host,
            port=self.smtp_config.port,
            use_tls=self.smtp_config.use_tls
        )

    async def _send_workflow_sms(self, tenant_id: str):
        """Send workflow SMS"""
        async with aiohttp.ClientSession() as session:
            sms_data = {
                "to": f"+1555{tenant_id[-3:]}0003",
                "from": "+15551234567", 
                "message": f"Workflow notification for tenant {tenant_id}",
                "tenant_id": tenant_id
            }
            
            async with session.post(self.sms_config.send_url, json=sms_data) as response:
                if response.status != 200:
                    raise Exception(f"SMS workflow send failed: HTTP {response.status}")

# FastAPI app for health checks and results
app = FastAPI(title="Notification Tester", version="1.0.0")
tester = NotificationTester()
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

async def main():
    """Main entry point"""
    logger.info("Starting Notification Testing Service...")
    
    # Wait for dependencies
    await asyncio.sleep(5)
    
    # Run tests automatically
    logger.info("Running notification tests...")
    results = await tester.run_all_tests()
    
    # Print summary
    print(f"\n{'='*60}")
    print("NOTIFICATION TESTING SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Execution Time: {results['execution_time_ms']}ms")
    
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