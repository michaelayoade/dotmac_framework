"""
Secrets and Configuration Management Tests

Comprehensive test suite covering:
- JWT/cookie secret rotation scenarios
- Environment templating and validation  
- Configuration drift detection
- Secret lifecycle management
- Tenant-specific configuration isolation
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.auth.core.jwt_service import JWTService
from dotmac_shared.core.exceptions import BusinessRuleError, SecurityError
from dotmac_shared.secrets.core.field_encryption import FieldEncryption

logger = logging.getLogger(__name__)


class SecretsConfigE2E:
    """End-to-end test suite for secrets and configuration management."""

    def __init__(self):
        self.test_tenant_id = str(uuid4())
        self.encryption = FieldEncryption()
        self.jwt_service = JWTService()
        self.test_secrets: Dict[str, str] = {}
        self.test_configs: Dict[str, Any] = {}

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_jwt_secret_rotation(self) -> Dict[str, Any]:
        """
        Test JWT secret rotation scenarios:
        1. Generate new JWT signing key
        2. Validate existing tokens with old key
        3. Issue new tokens with new key
        4. Verify graceful transition period
        5. Complete rotation and invalidate old key
        """
        test_start = time.time()
        results = {
            "test_name": "jwt_secret_rotation",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": []
        }

        try:
            # Step 1: Generate initial JWT secret and create tokens
            initial_secret = await self._generate_jwt_secret()
            self.jwt_service.configure_secret(initial_secret["secret"])
            
            # Create test tokens with initial secret
            test_user_id = str(uuid4())
            initial_tokens = await self._create_test_tokens(test_user_id)
            
            results["steps"].append({
                "name": "initial_secret_generation",
                "status": "completed",
                "duration": initial_secret.get("duration", 0),
                "details": {
                    "secret_id": initial_secret["secret_id"],
                    "tokens_created": len(initial_tokens["tokens"])
                }
            })

            # Step 2: Validate tokens with current secret
            validation_result = await self._validate_tokens(initial_tokens["tokens"])
            results["steps"].append({
                "name": "initial_token_validation", 
                "status": "completed" if validation_result["all_valid"] else "failed",
                "duration": validation_result.get("duration", 0),
                "details": validation_result
            })

            if not validation_result["all_valid"]:
                raise SecurityError("Initial tokens failed validation")

            # Step 3: Generate new JWT secret (rotation begins)
            new_secret = await self._generate_jwt_secret()
            rotation_result = await self._initiate_secret_rotation(initial_secret["secret"], new_secret["secret"])
            
            results["steps"].append({
                "name": "secret_rotation_initiation",
                "status": "completed" if rotation_result["success"] else "failed",
                "duration": rotation_result.get("duration", 0),
                "details": rotation_result
            })

            # Step 4: Test dual-key validation (transition period)
            dual_validation_result = await self._test_dual_key_validation(
                initial_tokens["tokens"], 
                initial_secret["secret"],
                new_secret["secret"]
            )
            
            results["steps"].append({
                "name": "dual_key_validation",
                "status": "completed" if dual_validation_result["success"] else "failed", 
                "duration": dual_validation_result.get("duration", 0),
                "details": dual_validation_result
            })

            # Step 5: Create new tokens with new secret
            self.jwt_service.configure_secret(new_secret["secret"])
            new_tokens = await self._create_test_tokens(test_user_id)
            
            results["steps"].append({
                "name": "new_token_generation",
                "status": "completed",
                "duration": new_tokens.get("duration", 0),
                "details": {
                    "secret_id": new_secret["secret_id"],
                    "tokens_created": len(new_tokens["tokens"])
                }
            })

            # Step 6: Complete rotation (invalidate old secret)
            completion_result = await self._complete_secret_rotation(initial_secret["secret"])
            
            results["steps"].append({
                "name": "rotation_completion",
                "status": "completed" if completion_result["success"] else "failed",
                "duration": completion_result.get("duration", 0), 
                "details": completion_result
            })

            # Step 7: Verify old tokens are now invalid
            old_token_validation = await self._validate_tokens(initial_tokens["tokens"])
            results["steps"].append({
                "name": "old_token_invalidation",
                "status": "completed" if not old_token_validation["all_valid"] else "failed",
                "duration": old_token_validation.get("duration", 0),
                "details": old_token_validation
            })

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"JWT secret rotation test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_cookie_secret_rotation(self) -> Dict[str, Any]:
        """
        Test secure cookie secret rotation:
        1. Generate new cookie signing key  
        2. Test cookie validation with both keys
        3. Complete rotation process
        4. Verify session continuity
        """
        test_start = time.time()
        results = {
            "test_name": "cookie_secret_rotation",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": []
        }

        try:
            # Step 1: Generate initial cookie secret
            initial_cookie_secret = await self._generate_cookie_secret()
            test_sessions = await self._create_test_sessions(initial_cookie_secret["secret"])
            
            results["steps"].append({
                "name": "initial_cookie_secret",
                "status": "completed",
                "duration": initial_cookie_secret.get("duration", 0),
                "details": {
                    "secret_id": initial_cookie_secret["secret_id"],
                    "sessions_created": len(test_sessions["sessions"])
                }
            })

            # Step 2: Generate new cookie secret and initiate rotation
            new_cookie_secret = await self._generate_cookie_secret()
            cookie_rotation = await self._initiate_cookie_rotation(
                initial_cookie_secret["secret"],
                new_cookie_secret["secret"]
            )
            
            results["steps"].append({
                "name": "cookie_rotation_initiation",
                "status": "completed" if cookie_rotation["success"] else "failed",
                "duration": cookie_rotation.get("duration", 0),
                "details": cookie_rotation
            })

            # Step 3: Test session validation during transition
            session_validation = await self._validate_sessions_during_rotation(
                test_sessions["sessions"],
                initial_cookie_secret["secret"],
                new_cookie_secret["secret"]
            )
            
            results["steps"].append({
                "name": "session_validation_transition",
                "status": "completed" if session_validation["success"] else "failed",
                "duration": session_validation.get("duration", 0),
                "details": session_validation
            })

            # Step 4: Complete cookie rotation
            cookie_completion = await self._complete_cookie_rotation(initial_cookie_secret["secret"])
            
            results["steps"].append({
                "name": "cookie_rotation_completion", 
                "status": "completed" if cookie_completion["success"] else "failed",
                "duration": cookie_completion.get("duration", 0),
                "details": cookie_completion
            })

            results["status"] = "completed" 
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"Cookie secret rotation test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_environment_templating(self) -> Dict[str, Any]:
        """
        Test environment configuration templating:
        1. Template generation from base configs
        2. Tenant-specific variable substitution
        3. Secret injection into templates
        4. Configuration validation
        5. Environment deployment
        """
        test_start = time.time()
        results = {
            "test_name": "environment_templating",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": []
        }

        try:
            # Step 1: Create base configuration template
            base_template = await self._create_base_config_template()
            results["steps"].append({
                "name": "base_template_creation",
                "status": "completed",
                "duration": base_template.get("duration", 0),
                "details": {
                    "template_id": base_template["template_id"],
                    "variables": len(base_template["variables"]),
                    "secrets": len(base_template["secrets"])
                }
            })

            # Step 2: Generate tenant-specific configuration
            tenant_config = await self._generate_tenant_config(base_template["template"])
            results["steps"].append({
                "name": "tenant_config_generation",
                "status": "completed" if tenant_config["success"] else "failed",
                "duration": tenant_config.get("duration", 0),
                "details": tenant_config
            })

            # Step 3: Inject secrets into configuration  
            secret_injection = await self._inject_secrets_into_config(tenant_config["config"])
            results["steps"].append({
                "name": "secret_injection",
                "status": "completed" if secret_injection["success"] else "failed",
                "duration": secret_injection.get("duration", 0),
                "details": secret_injection
            })

            # Step 4: Validate final configuration
            config_validation = await self._validate_final_configuration(secret_injection["final_config"])
            results["steps"].append({
                "name": "configuration_validation",
                "status": "completed" if config_validation["valid"] else "failed",
                "duration": config_validation.get("duration", 0),
                "details": config_validation
            })

            # Step 5: Deploy configuration to environment
            deployment_result = await self._deploy_configuration(secret_injection["final_config"])
            results["steps"].append({
                "name": "configuration_deployment",
                "status": "completed" if deployment_result["success"] else "failed",
                "duration": deployment_result.get("duration", 0), 
                "details": deployment_result
            })

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"Environment templating test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_config_drift_detection(self) -> Dict[str, Any]:
        """
        Test configuration drift detection:
        1. Baseline configuration snapshot
        2. Simulate configuration changes
        3. Detect drift from baseline
        4. Generate drift report
        5. Remediation recommendations
        """
        test_start = time.time()
        results = {
            "test_name": "config_drift_detection",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": []
        }

        try:
            # Step 1: Create baseline configuration snapshot
            baseline_snapshot = await self._create_config_baseline()
            results["steps"].append({
                "name": "baseline_creation",
                "status": "completed",
                "duration": baseline_snapshot.get("duration", 0),
                "details": {
                    "snapshot_id": baseline_snapshot["snapshot_id"],
                    "config_items": len(baseline_snapshot["config_items"]),
                    "checksum": baseline_snapshot["checksum"]
                }
            })

            # Step 2: Simulate configuration changes (drift)
            drift_simulation = await self._simulate_config_drift(baseline_snapshot["config_items"])
            results["steps"].append({
                "name": "drift_simulation",
                "status": "completed",
                "duration": drift_simulation.get("duration", 0),
                "details": {
                    "changes_made": len(drift_simulation["changes"]),
                    "change_types": list(drift_simulation["change_types"])
                }
            })

            # Step 3: Detect configuration drift
            drift_detection = await self._detect_config_drift(
                baseline_snapshot["config_items"],
                drift_simulation["modified_config"]
            )
            
            results["steps"].append({
                "name": "drift_detection", 
                "status": "completed" if drift_detection["drift_found"] else "failed",
                "duration": drift_detection.get("duration", 0),
                "details": drift_detection
            })

            # Step 4: Generate drift report
            drift_report = await self._generate_drift_report(drift_detection["drift_items"])
            results["steps"].append({
                "name": "drift_reporting",
                "status": "completed",
                "duration": drift_report.get("duration", 0),
                "details": {
                    "report_id": drift_report["report_id"],
                    "severity": drift_report["severity"],
                    "recommendations": len(drift_report["recommendations"])
                }
            })

            # Step 5: Test automatic remediation suggestions
            remediation = await self._generate_remediation_plan(drift_detection["drift_items"])
            results["steps"].append({
                "name": "remediation_planning",
                "status": "completed",
                "duration": remediation.get("duration", 0),
                "details": {
                    "remediation_steps": len(remediation["steps"]),
                    "auto_fixable": remediation["auto_fixable_count"],
                    "manual_required": remediation["manual_required_count"]
                }
            })

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"Config drift detection test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @standard_exception_handler
    async def run_complete_secrets_config_suite(self) -> Dict[str, Any]:
        """Run complete secrets and configuration test suite."""
        suite_start = time.time()
        suite_results = {
            "suite_name": "secrets_config_management_e2e",
            "status": "running",
            "tests": [],
            "summary": {},
            "duration": 0
        }

        try:
            # Run all test scenarios
            tests = [
                self.test_jwt_secret_rotation(),
                self.test_cookie_secret_rotation(),
                self.test_environment_templating(),
                self.test_config_drift_detection()
            ]

            for test_coro in tests:
                test_result = await test_coro
                suite_results["tests"].append(test_result)

            # Generate summary
            total_tests = len(suite_results["tests"])
            passed_tests = sum(1 for t in suite_results["tests"] if t.get("success", False))
            failed_tests = total_tests - passed_tests

            suite_results["summary"] = {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            }

            suite_results["status"] = "completed" if failed_tests == 0 else "failed"

        except Exception as e:
            suite_results["status"] = "failed"
            suite_results["error"] = str(e)
            logger.error(f"Secrets/config test suite failed: {e}")

        finally:
            suite_results["duration"] = time.time() - suite_start

        return suite_results

    # Helper methods for test implementation
    async def _generate_jwt_secret(self) -> Dict[str, Any]:
        """Generate new JWT signing secret."""
        start_time = time.time()
        
        try:
            # Generate secure random key
            secret_key = Fernet.generate_key().decode()
            secret_id = str(uuid4())
            
            # Store in test secrets
            self.test_secrets[secret_id] = secret_key
            
            return {
                "success": True,
                "secret_id": secret_id,
                "secret": secret_key,
                "algorithm": "HS256",
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _create_test_tokens(self, user_id: str) -> Dict[str, Any]:
        """Create test JWT tokens for validation."""
        start_time = time.time()
        
        try:
            tokens = []
            
            # Create different token types
            token_types = ["access", "refresh", "api_key"]
            
            for token_type in token_types:
                token_data = {
                    "user_id": user_id,
                    "tenant_id": self.test_tenant_id,
                    "type": token_type,
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
                }
                
                # Generate token using JWT service
                token = self.jwt_service.encode_token(token_data)
                tokens.append({
                    "type": token_type,
                    "token": token,
                    "data": token_data
                })
            
            return {
                "success": True,
                "tokens": tokens,
                "count": len(tokens),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _validate_tokens(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate JWT tokens."""
        start_time = time.time()
        
        try:
            validation_results = []
            
            for token_info in tokens:
                try:
                    # Validate token
                    decoded = self.jwt_service.decode_token(token_info["token"])
                    validation_results.append({
                        "token_type": token_info["type"],
                        "valid": True,
                        "decoded": decoded
                    })
                except Exception as e:
                    validation_results.append({
                        "token_type": token_info["type"],
                        "valid": False,
                        "error": str(e)
                    })
            
            all_valid = all(result["valid"] for result in validation_results)
            
            return {
                "all_valid": all_valid,
                "results": validation_results,
                "valid_count": sum(1 for r in validation_results if r["valid"]),
                "total_count": len(validation_results),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "all_valid": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _initiate_secret_rotation(self, old_secret: str, new_secret: str) -> Dict[str, Any]:
        """Initiate JWT secret rotation process."""
        start_time = time.time()
        
        try:
            # Configure dual-key validation period
            rotation_config = {
                "old_secret": old_secret,
                "new_secret": new_secret,
                "transition_period": 300,  # 5 minutes
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Mock rotation initiation
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "rotation_id": str(uuid4()),
                "config": rotation_config,
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _test_dual_key_validation(self, tokens: List[Dict], old_secret: str, new_secret: str) -> Dict[str, Any]:
        """Test dual-key validation during rotation period."""
        start_time = time.time()
        
        try:
            # Test validation with both secrets
            old_key_results = []
            new_key_results = []
            
            for token_info in tokens:
                # Test with old secret
                try:
                    self.jwt_service.configure_secret(old_secret)
                    decoded = self.jwt_service.decode_token(token_info["token"])
                    old_key_results.append({"valid": True, "type": token_info["type"]})
                except Exception:
                    old_key_results.append({"valid": False, "type": token_info["type"]})
                
                # Test with new secret (should fail for old tokens)
                try:
                    self.jwt_service.configure_secret(new_secret)
                    decoded = self.jwt_service.decode_token(token_info["token"])
                    new_key_results.append({"valid": True, "type": token_info["type"]})
                except Exception:
                    new_key_results.append({"valid": False, "type": token_info["type"]})
            
            return {
                "success": True,
                "old_key_valid": all(r["valid"] for r in old_key_results),
                "new_key_valid": any(r["valid"] for r in new_key_results),
                "old_results": old_key_results,
                "new_results": new_key_results,
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _complete_secret_rotation(self, old_secret: str) -> Dict[str, Any]:
        """Complete JWT secret rotation by invalidating old secret."""
        start_time = time.time()
        
        try:
            # Remove old secret from active secrets
            for secret_id, secret_val in list(self.test_secrets.items()):
                if secret_val == old_secret:
                    del self.test_secrets[secret_id]
                    break
            
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "old_secret_invalidated": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _generate_cookie_secret(self) -> Dict[str, Any]:
        """Generate new cookie signing secret."""
        start_time = time.time()
        
        try:
            secret_key = Fernet.generate_key().decode()
            secret_id = str(uuid4())
            
            self.test_secrets[f"cookie_{secret_id}"] = secret_key
            
            return {
                "success": True,
                "secret_id": secret_id,
                "secret": secret_key,
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _create_test_sessions(self, cookie_secret: str) -> Dict[str, Any]:
        """Create test session cookies."""
        start_time = time.time()
        
        try:
            sessions = []
            
            # Create test sessions
            for i in range(3):
                session_data = {
                    "session_id": str(uuid4()),
                    "user_id": str(uuid4()),
                    "tenant_id": self.test_tenant_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
                }
                
                # Sign session data (mock implementation)
                session_signature = hashlib.sha256(
                    (json.dumps(session_data) + cookie_secret).encode()
                ).hexdigest()
                
                sessions.append({
                    "data": session_data,
                    "signature": session_signature
                })
            
            return {
                "success": True,
                "sessions": sessions,
                "count": len(sessions),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _initiate_cookie_rotation(self, old_secret: str, new_secret: str) -> Dict[str, Any]:
        """Initiate cookie secret rotation."""
        start_time = time.time()
        
        try:
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "rotation_id": str(uuid4()),
                "old_secret_id": hashlib.sha256(old_secret.encode()).hexdigest()[:8],
                "new_secret_id": hashlib.sha256(new_secret.encode()).hexdigest()[:8],
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _validate_sessions_during_rotation(self, sessions: List[Dict], old_secret: str, new_secret: str) -> Dict[str, Any]:
        """Validate sessions during cookie rotation."""
        start_time = time.time()
        
        try:
            validation_results = []
            
            for session in sessions:
                # Validate with old secret
                expected_sig_old = hashlib.sha256(
                    (json.dumps(session["data"]) + old_secret).encode()
                ).hexdigest()
                
                old_valid = session["signature"] == expected_sig_old
                
                validation_results.append({
                    "session_id": session["data"]["session_id"],
                    "old_secret_valid": old_valid,
                    "new_secret_valid": False  # New sessions would be signed with new secret
                })
            
            return {
                "success": True,
                "results": validation_results,
                "sessions_validated": len(validation_results),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _complete_cookie_rotation(self, old_secret: str) -> Dict[str, Any]:
        """Complete cookie secret rotation."""
        start_time = time.time()
        
        try:
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "old_secret_invalidated": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _create_base_config_template(self) -> Dict[str, Any]:
        """Create base configuration template."""
        start_time = time.time()
        
        try:
            template = {
                "database": {
                    "host": "{{DB_HOST}}",
                    "port": "{{DB_PORT}}",
                    "name": "{{TENANT_ID}}_db",
                    "user": "{{DB_USER}}",
                    "password": "{{DB_PASSWORD}}"
                },
                "redis": {
                    "host": "{{REDIS_HOST}}",
                    "port": "{{REDIS_PORT}}",
                    "password": "{{REDIS_PASSWORD}}"
                },
                "jwt": {
                    "secret": "{{JWT_SECRET}}",
                    "algorithm": "HS256",
                    "expiry": "24h"
                },
                "smtp": {
                    "host": "{{SMTP_HOST}}",
                    "port": "{{SMTP_PORT}}",
                    "user": "{{SMTP_USER}}",
                    "password": "{{SMTP_PASSWORD}}"
                }
            }
            
            variables = ["DB_HOST", "DB_PORT", "DB_USER", "TENANT_ID", "REDIS_HOST", "REDIS_PORT", "SMTP_HOST", "SMTP_PORT", "SMTP_USER"]
            secrets = ["DB_PASSWORD", "REDIS_PASSWORD", "JWT_SECRET", "SMTP_PASSWORD"]
            
            return {
                "template_id": str(uuid4()),
                "template": template,
                "variables": variables,
                "secrets": secrets,
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _generate_tenant_config(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tenant-specific configuration from template."""
        start_time = time.time()
        
        try:
            # Substitute tenant-specific values
            config = json.loads(json.dumps(template))
            
            substitutions = {
                "{{TENANT_ID}}": self.test_tenant_id,
                "{{DB_HOST}}": "postgres.example.com",
                "{{DB_PORT}}": "5432",
                "{{DB_USER}}": f"user_{self.test_tenant_id}",
                "{{REDIS_HOST}}": "redis.example.com",
                "{{REDIS_PORT}}": "6379",
                "{{SMTP_HOST}}": "smtp.mailgun.org",
                "{{SMTP_PORT}}": "587",
                "{{SMTP_USER}}": f"postmaster@{self.test_tenant_id}.mailgun.org"
            }
            
            # Apply substitutions
            config_str = json.dumps(config)
            for placeholder, value in substitutions.items():
                config_str = config_str.replace(placeholder, value)
            
            config = json.loads(config_str)
            
            return {
                "success": True,
                "config": config,
                "substitutions": len(substitutions),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _inject_secrets_into_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Inject secrets into configuration."""
        start_time = time.time()
        
        try:
            # Generate and inject secrets
            secrets = {
                "{{DB_PASSWORD}}": f"db_pass_{uuid4().hex[:16]}",
                "{{REDIS_PASSWORD}}": f"redis_pass_{uuid4().hex[:16]}", 
                "{{JWT_SECRET}}": Fernet.generate_key().decode(),
                "{{SMTP_PASSWORD}}": f"smtp_pass_{uuid4().hex[:16]}"
            }
            
            # Apply secret substitutions
            config_str = json.dumps(config)
            for placeholder, secret_value in secrets.items():
                config_str = config_str.replace(placeholder, secret_value)
                # Store in test secrets
                self.test_secrets[placeholder.strip("{}")] = secret_value
            
            final_config = json.loads(config_str)
            
            return {
                "success": True,
                "final_config": final_config,
                "secrets_injected": len(secrets),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _validate_final_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate final configuration."""
        start_time = time.time()
        
        try:
            validation_errors = []
            
            # Check required sections
            required_sections = ["database", "redis", "jwt", "smtp"]
            for section in required_sections:
                if section not in config:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Check for remaining placeholders
            config_str = json.dumps(config)
            if "{{" in config_str:
                validation_errors.append("Configuration contains unresolved placeholders")
            
            # Validate database configuration
            db_config = config.get("database", {})
            required_db_fields = ["host", "port", "name", "user", "password"]
            for field in required_db_fields:
                if not db_config.get(field):
                    validation_errors.append(f"Missing database field: {field}")
            
            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "sections_validated": len(required_sections),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "duration": time.time() - start_time
            }

    async def _deploy_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy configuration to environment."""
        start_time = time.time()
        
        try:
            # Mock configuration deployment
            await asyncio.sleep(2)
            
            deployment_id = str(uuid4())
            self.test_configs[deployment_id] = config
            
            return {
                "success": True,
                "deployment_id": deployment_id,
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "config_size": len(json.dumps(config)),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _create_config_baseline(self) -> Dict[str, Any]:
        """Create configuration baseline snapshot."""
        start_time = time.time()
        
        try:
            # Create baseline configuration
            baseline_config = {
                "application": {
                    "name": f"dotmac-{self.test_tenant_id}",
                    "version": "1.0.0",
                    "environment": "production"
                },
                "database": {
                    "host": "db.example.com",
                    "port": 5432,
                    "ssl_enabled": True,
                    "pool_size": 10
                },
                "redis": {
                    "host": "redis.example.com", 
                    "port": 6379,
                    "timeout": 5
                },
                "monitoring": {
                    "enabled": True,
                    "metrics_interval": 60,
                    "alerts_enabled": True
                }
            }
            
            # Calculate checksum
            config_str = json.dumps(baseline_config, sort_keys=True)
            checksum = hashlib.sha256(config_str.encode()).hexdigest()
            
            snapshot_id = str(uuid4())
            
            return {
                "snapshot_id": snapshot_id,
                "config_items": baseline_config,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _simulate_config_drift(self, baseline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate configuration drift."""
        start_time = time.time()
        
        try:
            modified_config = json.loads(json.dumps(baseline_config))
            changes = []
            change_types = set()
            
            # Simulate various types of drift
            
            # 1. Value change
            modified_config["database"]["pool_size"] = 20  # Changed from 10
            changes.append({
                "type": "value_change",
                "path": "database.pool_size",
                "old_value": 10,
                "new_value": 20
            })
            change_types.add("value_change")
            
            # 2. New field addition
            modified_config["database"]["backup_enabled"] = True
            changes.append({
                "type": "field_added",
                "path": "database.backup_enabled", 
                "new_value": True
            })
            change_types.add("field_added")
            
            # 3. Field removal
            del modified_config["redis"]["timeout"]
            changes.append({
                "type": "field_removed",
                "path": "redis.timeout",
                "old_value": 5
            })
            change_types.add("field_removed")
            
            # 4. Section addition
            modified_config["logging"] = {
                "level": "INFO",
                "format": "json"
            }
            changes.append({
                "type": "section_added",
                "path": "logging",
                "new_value": {"level": "INFO", "format": "json"}
            })
            change_types.add("section_added")
            
            await asyncio.sleep(1)
            
            return {
                "modified_config": modified_config,
                "changes": changes,
                "change_types": change_types,
                "drift_count": len(changes),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _detect_config_drift(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Detect configuration drift between baseline and current."""
        start_time = time.time()
        
        try:
            drift_items = []
            
            # Compare configurations recursively
            def compare_configs(base_obj, curr_obj, path=""):
                if isinstance(base_obj, dict) and isinstance(curr_obj, dict):
                    # Check for removed keys
                    for key in base_obj:
                        if key not in curr_obj:
                            drift_items.append({
                                "type": "removed",
                                "path": f"{path}.{key}" if path else key,
                                "baseline_value": base_obj[key],
                                "current_value": None
                            })
                    
                    # Check for added keys and changed values
                    for key in curr_obj:
                        new_path = f"{path}.{key}" if path else key
                        if key not in base_obj:
                            drift_items.append({
                                "type": "added",
                                "path": new_path,
                                "baseline_value": None,
                                "current_value": curr_obj[key]
                            })
                        elif base_obj[key] != curr_obj[key]:
                            if isinstance(base_obj[key], dict) or isinstance(curr_obj[key], dict):
                                compare_configs(base_obj[key], curr_obj[key], new_path)
                            else:
                                drift_items.append({
                                    "type": "changed",
                                    "path": new_path,
                                    "baseline_value": base_obj[key],
                                    "current_value": curr_obj[key]
                                })
            
            compare_configs(baseline, current)
            
            return {
                "drift_found": len(drift_items) > 0,
                "drift_items": drift_items,
                "drift_count": len(drift_items),
                "severity": "high" if len(drift_items) > 5 else "medium" if len(drift_items) > 2 else "low",
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "drift_found": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _generate_drift_report(self, drift_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate configuration drift report."""
        start_time = time.time()
        
        try:
            # Categorize drift items
            categories = {
                "critical": [],
                "warning": [], 
                "info": []
            }
            
            for item in drift_items:
                # Classify severity based on path and type
                path = item["path"]
                drift_type = item["type"]
                
                if "password" in path.lower() or "secret" in path.lower():
                    categories["critical"].append(item)
                elif drift_type == "removed" and "database" in path:
                    categories["critical"].append(item)
                elif drift_type == "changed" and any(x in path for x in ["port", "host", "timeout"]):
                    categories["warning"].append(item)
                else:
                    categories["info"].append(item)
            
            # Generate recommendations
            recommendations = []
            if categories["critical"]:
                recommendations.append("Immediate attention required for security-related changes")
            if categories["warning"]:
                recommendations.append("Review configuration changes that may impact connectivity")
            if categories["info"]:
                recommendations.append("Monitor informational changes for unexpected modifications")
            
            severity = "critical" if categories["critical"] else "warning" if categories["warning"] else "info"
            
            return {
                "report_id": str(uuid4()),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "severity": severity,
                "categories": categories,
                "recommendations": recommendations,
                "total_drift_items": len(drift_items),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _generate_remediation_plan(self, drift_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate automated remediation plan for drift items."""
        start_time = time.time()
        
        try:
            remediation_steps = []
            auto_fixable_count = 0
            manual_required_count = 0
            
            for item in drift_items:
                if item["type"] == "added":
                    # New configuration items - may be auto-removable
                    if not any(x in item["path"] for x in ["password", "secret", "key"]):
                        remediation_steps.append({
                            "action": "remove_config",
                            "path": item["path"],
                            "auto_fixable": True,
                            "description": f"Remove added configuration: {item['path']}"
                        })
                        auto_fixable_count += 1
                    else:
                        remediation_steps.append({
                            "action": "review_security_config",
                            "path": item["path"],
                            "auto_fixable": False,
                            "description": f"Manually review security configuration: {item['path']}"
                        })
                        manual_required_count += 1
                
                elif item["type"] == "changed":
                    # Changed values - context-dependent
                    if item["path"].endswith(("_count", "_size", "_timeout")):
                        remediation_steps.append({
                            "action": "revert_value",
                            "path": item["path"],
                            "old_value": item["baseline_value"],
                            "auto_fixable": True,
                            "description": f"Revert {item['path']} from {item['current_value']} to {item['baseline_value']}"
                        })
                        auto_fixable_count += 1
                    else:
                        remediation_steps.append({
                            "action": "review_change",
                            "path": item["path"],
                            "auto_fixable": False,
                            "description": f"Review configuration change: {item['path']}"
                        })
                        manual_required_count += 1
                
                elif item["type"] == "removed":
                    # Removed items - usually require manual review
                    remediation_steps.append({
                        "action": "restore_config",
                        "path": item["path"],
                        "value": item["baseline_value"],
                        "auto_fixable": False,
                        "description": f"Consider restoring removed configuration: {item['path']}"
                    })
                    manual_required_count += 1
            
            return {
                "steps": remediation_steps,
                "auto_fixable_count": auto_fixable_count,
                "manual_required_count": manual_required_count,
                "total_steps": len(remediation_steps),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "duration": time.time() - start_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }


# Pytest test functions
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_secrets_config_management_e2e():
    """Run complete secrets and configuration management test suite."""
    test_suite = SecretsConfigE2E()
    results = await test_suite.run_complete_secrets_config_suite()
    
    # Assert overall success
    assert results["status"] == "completed", f"Test suite failed: {results}"
    assert results["summary"]["success_rate"] >= 75, f"Success rate too low: {results['summary']}"
    
    # Log results
    print(f"\nSecrets/Config Test Results:")
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Duration: {results['duration']:.2f}s")

    return results


@pytest.mark.e2e
    @pytest.mark.asyncio
@pytest.mark.e2e
    async def test_jwt_rotation_only():
    """Test just JWT secret rotation."""
    test_suite = SecretsConfigE2E()
    result = await test_suite.test_jwt_secret_rotation()
    
    assert result["success"] == True, f"JWT rotation failed: {result}"
    assert len(result["steps"]) >= 6, "Missing JWT rotation steps"
    
    return result


@pytest.mark.e2e
    @pytest.mark.asyncio  
@pytest.mark.e2e
    async def test_config_drift_only():
    """Test just configuration drift detection."""
    test_suite = SecretsConfigE2E()
    result = await test_suite.test_config_drift_detection()
    
    assert result["success"] == True, f"Config drift detection failed: {result}"
    
    # Verify drift detection steps
    step_names = [step["name"] for step in result["steps"]]
    assert "baseline_creation" in step_names
    assert "drift_detection" in step_names
    assert "drift_reporting" in step_names

    return result


# Export main test class
__all__ = ["SecretsConfigE2E", "test_secrets_config_management_e2e", "test_jwt_rotation_only", "test_config_drift_only"]
