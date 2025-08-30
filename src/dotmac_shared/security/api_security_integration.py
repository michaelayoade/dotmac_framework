"""
API Security Integration and Validation Suite
Integrates all API security components and provides comprehensive security validation

SECURITY: This module coordinates all security middleware and provides validation
tools to ensure complete API security coverage across the platform
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request

try:
    # Try relative imports first (when used as package)
    from .api_auth_middleware import (
        JWTTokenValidator,
        RoleBasedAccessControl,
        create_api_auth_middleware,
    )
    from .api_rate_limiter import RedisRateLimiter, create_rate_limit_middleware
    from .api_security_headers import setup_api_security
    from .api_threat_detector import (
        APIThreatDetector,
        create_threat_detection_middleware,
    )
    from .request_validation import (
        RequestValidationMiddleware,
        create_request_validation_middleware,
    )
except ImportError:
    # Fall back to direct imports (when shared is in path)
    from security.api_auth_middleware import (
        JWTTokenValidator,
        RoleBasedAccessControl,
        create_api_auth_middleware,
    )
    from security.api_rate_limiter import RedisRateLimiter, create_rate_limit_middleware
    from security.api_security_headers import setup_api_security
    from security.api_threat_detector import (
        APIThreatDetector,
        create_threat_detection_middleware,
    )
    from security.request_validation import (
        RequestValidationMiddleware,
        create_request_validation_middleware,
    )

logger = logging.getLogger(__name__)


class APISecuritySuite:
    """
    Comprehensive API security suite that orchestrates all security components
    """

    def __init__(
        self,
        environment: str = "development",
        jwt_secret_key: str = None,
        redis_url: Optional[str] = None,
        tenant_domains: Optional[List[str]] = None,
    ):
        self.environment = environment
        self.jwt_secret_key = jwt_secret_key
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.tenant_domains = tenant_domains or []

        # Initialize security components
        self.rate_limiter = None
        self.jwt_validator = None
        self.rbac = None
        self.threat_detector = None

        # Security configuration
        self.security_config = self._get_security_config()

        # Validation results
        self.validation_results = {}

    def _get_security_config(self) -> Dict[str, Any]:
        """Get environment-specific security configuration"""
        base_config = {
            "rate_limiting": {"enabled": True, "redis_db": 1, "tenant_aware": True},
            "authentication": {
                "enabled": True,
                "jwt_algorithm": "HS256",
                "token_expiry": 3600,
                "require_tenant_context": True,
            },
            "request_validation": {
                "enabled": True,
                "max_request_size": 10_000_000,
                "max_json_depth": 10,
            },
            "threat_detection": {"enabled": True, "redis_db": 2, "block_threats": True},
            "security_headers": {
                "enabled": True,
                "strict_csp": True,
                "cors_enabled": True,
            },
        }

        if self.environment == "production":
            base_config.update(
                {
                    "authentication": {
                        **base_config["authentication"],
                        "token_expiry": 1800,  # 30 minutes in production
                        "verify_email": True,
                    },
                    "request_validation": {
                        **base_config["request_validation"],
                        "max_request_size": 5_000_000,  # Stricter in production
                    },
                    "threat_detection": {
                        **base_config["threat_detection"],
                        "block_threats": True,
                        "alert_level": "high",
                    },
                }
            )

        elif self.environment == "development":
            base_config.update(
                {
                    "security_headers": {
                        **base_config["security_headers"],
                        "strict_csp": False,  # More permissive for development
                    }
                }
            )

        return base_config

    async def initialize_security_components(self):
        """Initialize all security components"""
        try:
            # Initialize rate limiter
            if self.security_config["rate_limiting"]["enabled"]:
                redis_db = self.security_config["rate_limiting"]["redis_db"]
                rate_limiter_redis_url = f"{self.redis_url}/{redis_db}"
                self.rate_limiter = RedisRateLimiter(redis_url=rate_limiter_redis_url)
                logger.info("Rate limiter initialized")

            # Initialize JWT validator and RBAC
            if (
                self.security_config["authentication"]["enabled"]
                and self.jwt_secret_key
            ):
                self.jwt_validator = JWTTokenValidator(
                    secret_key=self.jwt_secret_key,
                    algorithm=self.security_config["authentication"]["jwt_algorithm"],
                    max_token_age=self.security_config["authentication"][
                        "token_expiry"
                    ],
                    require_tenant_context=self.security_config["authentication"][
                        "require_tenant_context"
                    ],
                )
                self.rbac = RoleBasedAccessControl()
                logger.info("JWT authentication and RBAC initialized")

            # Initialize threat detector
            if self.security_config["threat_detection"]["enabled"]:
                redis_db = self.security_config["threat_detection"]["redis_db"]
                threat_redis_url = f"{self.redis_url}/{redis_db}"
                self.threat_detector = APIThreatDetector(redis_url=threat_redis_url)
                logger.info("Threat detection system initialized")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize security components: {e}")
            return False

    def configure_app_security(
        self, app: FastAPI, api_type: str = "api"
    ) -> Dict[str, Any]:
        """Configure comprehensive security for FastAPI application"""
        security_status = {"configured_components": [], "errors": [], "warnings": []}

        try:
            # 1. Configure CORS and security headers
            if self.security_config["security_headers"]["enabled"]:
                setup_result = setup_api_security(
                    app=app,
                    environment=self.environment,
                    api_type=api_type,
                    tenant_domains=self.tenant_domains,
                    strict_csp=self.security_config["security_headers"]["strict_csp"],
                )
                security_status["configured_components"].append("security_headers")
                security_status["cors_status"] = setup_result

            # 2. Add request validation middleware
            if self.security_config["request_validation"]["enabled"]:
                validation_middleware = create_request_validation_middleware(
                    max_request_size=self.security_config["request_validation"][
                        "max_request_size"
                    ],
                    max_json_depth=self.security_config["request_validation"][
                        "max_json_depth"
                    ],
                )
                app.middleware("http")(validation_middleware(app))
                security_status["configured_components"].append("request_validation")

            # 3. Add rate limiting middleware
            if self.rate_limiter and self.security_config["rate_limiting"]["enabled"]:
                rate_limit_middleware = create_rate_limit_middleware(
                    rate_limiter=self.rate_limiter,
                    tenant_aware=self.security_config["rate_limiting"]["tenant_aware"],
                )
                app.middleware("http")(rate_limit_middleware(app))
                security_status["configured_components"].append("rate_limiting")

            # 4. Add authentication middleware
            if (
                self.jwt_validator
                and self.rbac
                and self.security_config["authentication"]["enabled"]
            ):
                auth_middleware = create_api_auth_middleware(
                    jwt_validator=self.jwt_validator,
                    rbac=self.rbac,
                    require_auth=True,
                    exempt_paths=[
                        "/docs",
                        "/redoc",
                        "/openapi.json",
                        "/health",
                        "/api/auth/login",
                    ],
                )
                app.middleware("http")(auth_middleware(app))
                security_status["configured_components"].append("authentication")

            # 5. Add threat detection middleware (should be last)
            if (
                self.threat_detector
                and self.security_config["threat_detection"]["enabled"]
            ):
                threat_middleware = create_threat_detection_middleware(
                    threat_detector=self.threat_detector,
                    block_threats=self.security_config["threat_detection"][
                        "block_threats"
                    ],
                )
                app.middleware("http")(threat_middleware(app))
                security_status["configured_components"].append("threat_detection")

            logger.info(
                f"API security configured with components: {security_status['configured_components']}"
            )

        except Exception as e:
            error_msg = f"Error configuring app security: {e}"
            logger.error(error_msg)
            security_status["errors"].append(error_msg)

        return security_status

    async def validate_security_implementation(self) -> Dict[str, Any]:
        """Comprehensive validation of security implementation"""
        validation_results = {
            "overall_status": "UNKNOWN",
            "component_status": {},
            "security_score": 0.0,
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        total_score = 0
        max_score = 0

        try:
            # 1. Validate Rate Limiting
            if self.rate_limiter:
                rate_limit_status = await self._validate_rate_limiting()
                validation_results["component_status"][
                    "rate_limiting"
                ] = rate_limit_status
                total_score += rate_limit_status.get("score", 0)
                max_score += 100
            else:
                validation_results["critical_issues"].append(
                    "Rate limiting not configured"
                )

            # 2. Validate Authentication
            if self.jwt_validator and self.rbac:
                auth_status = self._validate_authentication()
                validation_results["component_status"]["authentication"] = auth_status
                total_score += auth_status.get("score", 0)
                max_score += 100
            else:
                validation_results["critical_issues"].append(
                    "Authentication not properly configured"
                )

            # 3. Validate Threat Detection
            if self.threat_detector:
                threat_status = await self._validate_threat_detection()
                validation_results["component_status"][
                    "threat_detection"
                ] = threat_status
                total_score += threat_status.get("score", 0)
                max_score += 100
            else:
                validation_results["warnings"].append("Threat detection not configured")

            # 4. Validate Security Configuration
            config_status = self._validate_security_configuration()
            validation_results["component_status"]["configuration"] = config_status
            total_score += config_status.get("score", 0)
            max_score += 100

            # Calculate overall score
            if max_score > 0:
                validation_results["security_score"] = (total_score / max_score) * 100

            # Determine overall status
            if (
                validation_results["security_score"] >= 90
                and not validation_results["critical_issues"]
            ):
                validation_results["overall_status"] = "EXCELLENT"
            elif (
                validation_results["security_score"] >= 75
                and len(validation_results["critical_issues"]) <= 1
            ):
                validation_results["overall_status"] = "GOOD"
            elif validation_results["security_score"] >= 60:
                validation_results["overall_status"] = "NEEDS_IMPROVEMENT"
            else:
                validation_results["overall_status"] = "CRITICAL"

            # Add recommendations
            validation_results["recommendations"] = (
                self._generate_security_recommendations(validation_results)
            )

        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            validation_results["critical_issues"].append(f"Validation failed: {str(e)}")
            validation_results["overall_status"] = "ERROR"

        self.validation_results = validation_results
        return validation_results

    async def _validate_rate_limiting(self) -> Dict[str, Any]:
        """Validate rate limiting implementation"""
        status = {"score": 0, "issues": [], "passed_checks": []}

        try:
            # Check Redis connection
            if await self.rate_limiter.redis.ping():
                status["passed_checks"].append("Redis connection successful")
                status["score"] += 30
            else:
                status["issues"].append("Redis connection failed")

            # Check tenant quotas configuration
            if (
                hasattr(self.rate_limiter, "tenant_quotas")
                and self.rate_limiter.tenant_quotas
            ):
                status["passed_checks"].append("Tenant quotas configured")
                status["score"] += 40
            else:
                status["issues"].append("Tenant quotas not configured")

            # Check rate limiting functionality
            test_result = await self.rate_limiter.check_rate_limit(
                identifier="test_validation", tenant_quota_type="basic", window="minute"
            )
            if test_result:
                status["passed_checks"].append("Rate limiting functional")
                status["score"] += 30
            else:
                status["issues"].append("Rate limiting test failed")

        except Exception as e:
            status["issues"].append(f"Rate limiting validation error: {str(e)}")

        return status

    def _validate_authentication(self) -> Dict[str, Any]:
        """Validate authentication implementation"""
        status = {"score": 0, "issues": [], "passed_checks": []}

        try:
            # Check JWT validator configuration
            if (
                self.jwt_validator.secret_key
                and len(self.jwt_validator.secret_key) >= 32
            ):
                status["passed_checks"].append("JWT secret key properly configured")
                status["score"] += 25
            else:
                status["issues"].append("JWT secret key too short or missing")

            # Check RBAC configuration
            if self.rbac.role_hierarchy and self.rbac.role_permissions:
                status["passed_checks"].append("RBAC roles and permissions configured")
                status["score"] += 25
            else:
                status["issues"].append("RBAC not properly configured")

            # Check token validation settings
            if self.jwt_validator.verify_exp and self.jwt_validator.verify_iat:
                status["passed_checks"].append("Token validation settings secure")
                status["score"] += 25
            else:
                status["issues"].append("Token validation settings too permissive")

            # Check tenant context requirement
            if self.jwt_validator.require_tenant_context:
                status["passed_checks"].append("Tenant context enforcement enabled")
                status["score"] += 25
            else:
                status["issues"].append("Tenant context not required")

        except Exception as e:
            status["issues"].append(f"Authentication validation error: {str(e)}")

        return status

    async def _validate_threat_detection(self) -> Dict[str, Any]:
        """Validate threat detection implementation"""
        status = {"score": 0, "issues": [], "passed_checks": []}

        try:
            # Check threat detector initialization
            if self.threat_detector.redis and await self.threat_detector.redis.ping():
                status["passed_checks"].append(
                    "Threat detector Redis connection active"
                )
                status["score"] += 20
            else:
                status["issues"].append("Threat detector Redis connection failed")

            # Check threat patterns configuration
            if (
                self.threat_detector.threat_patterns
                and len(self.threat_detector.threat_patterns) > 0
            ):
                status["passed_checks"].append("Threat patterns configured")
                status["score"] += 30
            else:
                status["issues"].append("No threat patterns configured")

            # Check brute force detector
            if self.threat_detector.brute_force_detector:
                status["passed_checks"].append("Brute force detection enabled")
                status["score"] += 25
            else:
                status["issues"].append("Brute force detection not configured")

            # Check anomaly detector
            if self.threat_detector.anomaly_detector:
                status["passed_checks"].append("Anomaly detection enabled")
                status["score"] += 25
            else:
                status["issues"].append("Anomaly detection not configured")

        except Exception as e:
            status["issues"].append(f"Threat detection validation error: {str(e)}")

        return status

    def _validate_security_configuration(self) -> Dict[str, Any]:
        """Validate overall security configuration"""
        status = {"score": 0, "issues": [], "passed_checks": []}

        try:
            # Check environment-specific settings
            if self.environment in ["development", "staging", "production"]:
                status["passed_checks"].append(f"Valid environment: {self.environment}")
                status["score"] += 20
            else:
                status["issues"].append(f"Invalid environment: {self.environment}")

            # Check production security requirements
            if self.environment == "production":
                if (
                    self.security_config["authentication"]["token_expiry"] <= 1800
                ):  # 30 minutes max
                    status["passed_checks"].append(
                        "Production token expiry properly configured"
                    )
                    status["score"] += 20
                else:
                    status["issues"].append("Production token expiry too long")

                if self.security_config["threat_detection"]["block_threats"]:
                    status["passed_checks"].append("Production threat blocking enabled")
                    status["score"] += 20
                else:
                    status["issues"].append("Production threat blocking disabled")

            # Check security component integration
            enabled_components = sum(
                1
                for config in self.security_config.values()
                if config.get("enabled", False)
            )
            if enabled_components >= 4:  # At least 4 out of 5 components
                status["passed_checks"].append(
                    f"Most security components enabled ({enabled_components}/5)"
                )
                status["score"] += 40
            else:
                status["issues"].append(
                    f"Too few security components enabled ({enabled_components}/5)"
                )

        except Exception as e:
            status["issues"].append(f"Configuration validation error: {str(e)}")

        return status

    def _generate_security_recommendations(
        self, validation_results: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations based on validation results"""
        recommendations = []

        # Critical issues recommendations
        if validation_results["critical_issues"]:
            recommendations.append("Address all critical security issues immediately")

        # Score-based recommendations
        if validation_results["security_score"] < 90:
            recommendations.append(
                "Consider implementing additional security hardening measures"
            )

        # Component-specific recommendations
        component_status = validation_results.get("component_status", {})

        if "rate_limiting" in component_status:
            if component_status["rate_limiting"]["score"] < 80:
                recommendations.append(
                    "Improve rate limiting configuration and monitoring"
                )

        if "authentication" in component_status:
            if component_status["authentication"]["score"] < 80:
                recommendations.append("Strengthen authentication security policies")

        if "threat_detection" not in component_status:
            recommendations.append("Implement comprehensive threat detection system")

        # Environment-specific recommendations
        if self.environment == "production":
            recommendations.extend(
                [
                    "Enable comprehensive audit logging",
                    "Set up real-time security monitoring",
                    "Implement automated security scanning",
                    "Configure security incident response procedures",
                ]
            )

        return recommendations

    async def get_security_health_report(self) -> Dict[str, Any]:
        """Get comprehensive security health report"""
        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "components_status": {},
            "threat_summary": {},
            "recommendations": [],
        }

        # Get component health
        if self.rate_limiter:
            try:
                health_report["components_status"]["rate_limiter"] = (
                    "healthy" if await self.rate_limiter.redis.ping() else "unhealthy"
                )
            except Exception:
                health_report["components_status"]["rate_limiter"] = "error"

        if self.threat_detector:
            try:
                health_report["threat_summary"] = (
                    await self.threat_detector.get_threat_summary()
                )
                health_report["components_status"]["threat_detector"] = "healthy"
            except Exception:
                health_report["components_status"]["threat_detector"] = "error"

        # Add validation results if available
        if self.validation_results:
            health_report["last_validation"] = self.validation_results

        return health_report


# Factory function for easy integration
async def setup_complete_api_security(
    app: FastAPI,
    environment: str,
    jwt_secret_key: str,
    redis_url: str = "redis://localhost:6379",
    api_type: str = "api",
    tenant_domains: Optional[List[str]] = None,
    validate_implementation: bool = True,
) -> Dict[str, Any]:
    """
    Complete API security setup with validation
    """
    security_suite = APISecuritySuite(
        environment=environment,
        jwt_secret_key=jwt_secret_key,
        redis_url=redis_url,
        tenant_domains=tenant_domains,
    )

    # Initialize security components
    init_success = await security_suite.initialize_security_components()
    if not init_success:
        return {
            "status": "ERROR",
            "message": "Failed to initialize security components",
        }

    # Configure app security
    config_result = security_suite.configure_app_security(app, api_type)

    # Validate implementation if requested
    validation_result = {}
    if validate_implementation:
        validation_result = await security_suite.validate_security_implementation()

    return {
        "status": "SUCCESS",
        "security_suite": security_suite,
        "configuration_result": config_result,
        "validation_result": validation_result,
        "message": "Complete API security configured successfully",
    }
