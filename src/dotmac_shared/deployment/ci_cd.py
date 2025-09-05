"""
CI/CD Pipeline Integration

Provides comprehensive CI/CD pipeline integration with deployment automation,
including webhook handlers, pipeline orchestration, and integration with
popular CI/CD platforms like GitHub Actions, GitLab CI, and Jenkins.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..observability import MonitoringStack
from .automation import DeploymentAutomation, DeploymentSpec, HealthCheckConfig


class PipelineStatus(str, Enum):
    """CI/CD pipeline status states."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class PipelineStage(str, Enum):
    """CI/CD pipeline stages."""

    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DEPLOY = "deploy"
    VALIDATE = "validate"
    PROMOTE = "promote"


class GitProvider(str, Enum):
    """Supported Git providers."""

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    GITEA = "gitea"


@dataclass
class PipelineConfig:
    """CI/CD pipeline configuration."""

    name: str
    repository: str
    branch: str
    trigger_events: list[str] = field(default_factory=lambda: ["push", "pull_request"])
    stages: list[PipelineStage] = field(
        default_factory=lambda: [PipelineStage.BUILD, PipelineStage.TEST, PipelineStage.DEPLOY]
    )
    environment_variables: dict[str, str] = field(default_factory=dict)
    deployment_spec: Optional[DeploymentSpec] = None
    auto_deploy_branches: list[str] = field(default_factory=lambda: ["main", "production"])
    approval_required: bool = False
    notification_channels: list[str] = field(default_factory=list)
    timeout_minutes: int = 60
    parallel_stages: bool = False
    rollback_on_failure: bool = True


@dataclass
class PipelineRun:
    """Represents a single pipeline execution."""

    id: str
    pipeline_name: str
    repository: str
    branch: str
    commit_sha: str
    trigger_event: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    stages: dict[PipelineStage, dict[str, Any]] = field(default_factory=dict)
    deployment_id: Optional[str] = None
    logs: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class WebhookEvent:
    """Webhook event data from Git providers."""

    provider: GitProvider
    event_type: str
    repository: str
    branch: str
    commit_sha: str
    commit_message: str
    author: str
    timestamp: datetime
    pull_request_id: Optional[str] = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class PipelineExecutor(ABC):
    """Abstract base class for pipeline executors."""

    @abstractmethod
    async def execute_stage(
        self, stage: PipelineStage, config: PipelineConfig, run: PipelineRun, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a pipeline stage."""
        pass

    @abstractmethod
    async def cleanup(self, run: PipelineRun):
        """Cleanup resources after pipeline completion."""
        pass


class DockerPipelineExecutor(PipelineExecutor):
    """Docker-based pipeline executor."""

    def __init__(self, monitoring: MonitoringStack, deployment: DeploymentAutomation):
        self.monitoring = monitoring
        self.deployment = deployment
        self.logger = logging.getLogger(__name__)

    async def execute_stage(
        self, stage: PipelineStage, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a pipeline stage using Docker."""
        stage_start = datetime.now()
        stage_result = {"status": "success", "start_time": stage_start, "logs": [], "artifacts": {}, "metrics": {}}

        try:
            with self.monitoring.create_span(f"pipeline_stage_{stage}", config.name) as span:
                span.set_tag("pipeline", config.name)
                span.set_tag("stage", stage)
                span.set_tag("run_id", run.id)

                if stage == PipelineStage.BUILD:
                    await self._execute_build_stage(config, run, context, stage_result)
                elif stage == PipelineStage.TEST:
                    await self._execute_test_stage(config, run, context, stage_result)
                elif stage == PipelineStage.SECURITY_SCAN:
                    await self._execute_security_scan_stage(config, run, context, stage_result)
                elif stage == PipelineStage.DEPLOY:
                    await self._execute_deploy_stage(config, run, context, stage_result)
                elif stage == PipelineStage.VALIDATE:
                    await self._execute_validate_stage(config, run, context, stage_result)
                elif stage == PipelineStage.PROMOTE:
                    await self._execute_promote_stage(config, run, context, stage_result)

                stage_result["end_time"] = datetime.now()
                stage_duration = (stage_result["end_time"] - stage_start).total_seconds()

                self.monitoring.record_histogram(
                    "pipeline_stage_duration_seconds",
                    stage_duration,
                    {"pipeline": config.name, "stage": stage, "status": stage_result["status"]},
                )

                return stage_result

        except Exception as e:
            stage_result["status"] = "failure"
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now()

            self.logger.error(f"Stage {stage} failed for pipeline {config.name}: {str(e)}")

            self.monitoring.increment_counter(
                "pipeline_stage_errors_total", {"pipeline": config.name, "stage": stage, "error": type(e).__name__}
            )

            raise

    async def _execute_build_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute build stage."""
        self.logger.info(f"Building {config.name} for commit {run.commit_sha}")

        # Clone repository
        workspace = await self._prepare_workspace(config, run)
        context["workspace"] = workspace

        try:
            # Build Docker image
            image_tag = f"{config.name}:{run.commit_sha[:8]}"

            build_cmd = ["docker", "build", "-t", image_tag, "-f", "Dockerfile", "."]

            build_result = await self._run_command_in_workspace(build_cmd, workspace)

            result["logs"].extend(build_result["logs"])
            result["artifacts"]["image"] = image_tag

            # Store image reference for later stages
            context["image_tag"] = image_tag

            self.logger.info(f"Successfully built image {image_tag}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def _execute_test_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute test stage."""
        self.logger.info(f"Running tests for {config.name}")

        workspace = context.get("workspace")
        if not workspace:
            raise Exception("Workspace not available from build stage")

        try:
            # Run tests in container
            image_tag = context.get("image_tag")
            if not image_tag:
                raise Exception("Image not available from build stage")

            test_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{workspace}:/app",
                image_tag,
                "sh",
                "-c",
                "cd /app && python -m pytest tests/ --junitxml=test-results.xml --cov=. --cov-report=xml",
            ]

            test_result = await self._run_command_in_workspace(test_cmd, workspace)

            result["logs"].extend(test_result["logs"])

            # Parse test results
            test_results_file = workspace / "test-results.xml"
            coverage_file = workspace / "coverage.xml"

            if test_results_file.exists():
                result["artifacts"]["test_results"] = str(test_results_file)

            if coverage_file.exists():
                result["artifacts"]["coverage_report"] = str(coverage_file)
                # Parse coverage percentage
                coverage_data = await self._parse_coverage_report(coverage_file)
                result["metrics"]["test_coverage"] = coverage_data.get("coverage_percentage", 0)

            self.logger.info(f"Tests completed for {config.name}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def _execute_security_scan_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute security scan stage."""
        self.logger.info(f"Running security scan for {config.name}")

        try:
            image_tag = context.get("image_tag")
            if not image_tag:
                raise Exception("Image not available from build stage")

            # Run security scan with Trivy (example)
            scan_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
                "aquasec/trivy",
                "image",
                "--format",
                "json",
                "--output",
                "/tmp/scan-results.json",
                image_tag,
            ]

            scan_result = await self._run_command(scan_cmd)

            result["logs"].extend(scan_result["logs"])

            # Parse scan results
            if scan_result["return_code"] == 0:
                # Parse vulnerability data
                scan_data = json.loads(scan_result["stdout"])
                result["metrics"]["vulnerabilities"] = {
                    "critical": len([v for v in scan_data.get("Results", []) if v.get("Severity") == "CRITICAL"]),
                    "high": len([v for v in scan_data.get("Results", []) if v.get("Severity") == "HIGH"]),
                    "medium": len([v for v in scan_data.get("Results", []) if v.get("Severity") == "MEDIUM"]),
                    "low": len([v for v in scan_data.get("Results", []) if v.get("Severity") == "LOW"]),
                }

                # Fail if critical vulnerabilities found
                if result["metrics"]["vulnerabilities"]["critical"] > 0:
                    raise Exception(
                        f"Critical vulnerabilities found: {result['metrics']['vulnerabilities']['critical']}"
                    )

            self.logger.info(f"Security scan completed for {config.name}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def _execute_deploy_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute deployment stage."""
        self.logger.info(f"Deploying {config.name}")

        try:
            if not config.deployment_spec:
                raise Exception("Deployment specification not configured")

            # Update deployment spec with built image
            deployment_spec = config.deployment_spec
            image_tag = context.get("image_tag")
            if image_tag:
                image_parts = image_tag.split(":")
                if len(image_parts) == 2:
                    deployment_spec.image = image_parts[0]
                    deployment_spec.tag = image_parts[1]

            # Deploy the service
            deployment_result = await self.deployment.deploy_service(deployment_spec)

            run.deployment_id = deployment_result.deployment_id
            result["artifacts"]["deployment_id"] = deployment_result.deployment_id
            result["metrics"]["deployment_status"] = deployment_result.status

            self.logger.info(f"Deployment completed for {config.name}: {deployment_result.deployment_id}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def _execute_validate_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute validation stage."""
        self.logger.info(f"Validating deployment for {config.name}")

        try:
            deployment_id = run.deployment_id
            if not deployment_id:
                raise Exception("No deployment to validate")

            # Wait for deployment to be ready
            await asyncio.sleep(30)  # Give deployment time to start

            # Run validation tests
            if config.deployment_spec and config.deployment_spec.health_checks:
                validation_results = await self._run_validation_tests(config.deployment_spec.health_checks)
                result["metrics"]["validation_results"] = validation_results

                # Check if all validations passed
                if not all(v["passed"] for v in validation_results.values()):
                    raise Exception("Deployment validation failed")

            self.logger.info(f"Validation completed for {config.name}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def _execute_promote_stage(
        self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any], result: Dict[str, Any]
    ):
        """Execute promotion stage."""
        self.logger.info(f"Promoting {config.name}")

        try:
            # This stage would promote the deployment to production
            # Implementation depends on your deployment strategy

            deployment_id = run.deployment_id
            if not deployment_id:
                raise Exception("No deployment to promote")

            # Example: Scale up replicas for production
            if config.deployment_spec:
                production_replicas = config.deployment_spec.replicas * 2
                await self.deployment.orchestrator.scale(config.deployment_spec.service_name, production_replicas)

                result["metrics"]["promoted_replicas"] = production_replicas

            self.logger.info(f"Promotion completed for {config.name}")

        except Exception as e:
            result["logs"].append({"level": "error", "message": str(e), "timestamp": datetime.now().isoformat()})
            raise

    async def cleanup(self, run: PipelineRun):
        """Cleanup pipeline resources."""
        try:
            # Remove workspace
            workspace_path = f"/tmp/pipeline-{run.id}"
            cleanup_cmd = ["rm", "-rf", workspace_path]
            await self._run_command(cleanup_cmd)

            # Clean up Docker images if needed
            # This would be configurable based on retention policy

            self.logger.info(f"Cleanup completed for pipeline run {run.id}")

        except Exception as e:
            self.logger.warning(f"Cleanup failed for pipeline run {run.id}: {str(e)}")

    async def _prepare_workspace(self, config: PipelineConfig, run: PipelineRun) -> Path:
        """Prepare workspace for pipeline execution."""
        workspace = Path(f"/tmp/pipeline-{run.id}")
        workspace.mkdir(parents=True, exist_ok=True)

        # Clone repository
        clone_cmd = ["git", "clone", "--branch", run.branch, "--single-branch", config.repository, str(workspace)]

        await self._run_command(clone_cmd)

        # Checkout specific commit
        checkout_cmd = ["git", "checkout", run.commit_sha]
        await self._run_command_in_workspace(checkout_cmd, workspace)

        return workspace

    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run a command and capture output."""
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        return {
            "return_code": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "logs": [
                {"level": "info", "message": stdout.decode(), "timestamp": datetime.now().isoformat()},
                {"level": "error", "message": stderr.decode(), "timestamp": datetime.now().isoformat()},
            ]
            if stderr
            else [{"level": "info", "message": stdout.decode(), "timestamp": datetime.now().isoformat()}],
        }

    async def _run_command_in_workspace(self, cmd: List[str], workspace: Path) -> Dict[str, Any]:
        """Run a command in the workspace directory."""
        process = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(workspace), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        return {
            "return_code": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "logs": [
                {"level": "info", "message": stdout.decode(), "timestamp": datetime.now().isoformat()},
                {"level": "error", "message": stderr.decode(), "timestamp": datetime.now().isoformat()},
            ]
            if stderr
            else [{"level": "info", "message": stdout.decode(), "timestamp": datetime.now().isoformat()}],
        }

    async def _parse_coverage_report(self, coverage_file: Path) -> Dict[str, Any]:
        """Parse coverage report from XML file."""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(coverage_file)
            root = tree.getroot()

            coverage_element = root.find(".//coverage")
            if coverage_element is not None:
                line_rate = float(coverage_element.get("line-rate", 0))
                return {"coverage_percentage": line_rate * 100}

        except Exception as e:
            self.logger.warning(f"Failed to parse coverage report: {str(e)}")

        return {"coverage_percentage": 0}

    async def _run_validation_tests(self, health_checks: List[HealthCheckConfig]) -> Dict[str, Any]:
        """Run validation tests against deployed service."""
        results = {}

        for i, health_check in enumerate(health_checks):
            test_name = f"health_check_{i}"

            try:
                if health_check.type.value == "http":
                    import aiohttp

                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(
                            health_check.endpoint, headers=health_check.headers, timeout=health_check.timeout_seconds
                        ) as response:
                            results[test_name] = {
                                "passed": response.status == health_check.expected_status,
                                "status_code": response.status,
                                "expected": health_check.expected_status,
                                "response_time": 0,  # Would measure actual response time
                            }

            except Exception as e:
                results[test_name] = {"passed": False, "error": str(e)}

        return results


class WebhookHandler:
    """Handles webhooks from Git providers."""

    def __init__(self, secret_token: Optional[str] = None):
        self.secret_token = secret_token
        self.logger = logging.getLogger(__name__)

    def verify_signature(self, payload: bytes, signature: str, provider: GitProvider) -> bool:
        """Verify webhook signature."""
        if not self.secret_token:
            return True  # Skip verification if no secret configured

        try:
            if provider == GitProvider.GITHUB:
                expected_signature = (
                    "sha256=" + hmac.new(self.secret_token.encode(), payload, hashlib.sha256).hexdigest()
                )
                return hmac.compare_digest(signature, expected_signature)

            elif provider == GitProvider.GITLAB:
                return hmac.compare_digest(signature, self.secret_token)

        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False

        return True

    def parse_webhook(self, payload: Dict[str, Any], provider: GitProvider, event_type: str) -> Optional[WebhookEvent]:
        """Parse webhook payload into WebhookEvent."""
        try:
            if provider == GitProvider.GITHUB:
                return self._parse_github_webhook(payload, event_type)
            elif provider == GitProvider.GITLAB:
                return self._parse_gitlab_webhook(payload, event_type)

        except Exception as e:
            self.logger.error(f"Failed to parse webhook from {provider}: {str(e)}")

        return None

    def _parse_github_webhook(self, payload: Dict[str, Any], event_type: str) -> WebhookEvent:
        """Parse GitHub webhook payload."""
        if event_type == "push":
            return WebhookEvent(
                provider=GitProvider.GITHUB,
                event_type=event_type,
                repository=payload["repository"]["full_name"],
                branch=payload["ref"].replace("refs/heads/", ""),
                commit_sha=payload["head_commit"]["id"],
                commit_message=payload["head_commit"]["message"],
                author=payload["head_commit"]["author"]["name"],
                timestamp=datetime.fromisoformat(payload["head_commit"]["timestamp"].replace("Z", "+00:00")),
                raw_payload=payload,
            )

        elif event_type == "pull_request":
            return WebhookEvent(
                provider=GitProvider.GITHUB,
                event_type=event_type,
                repository=payload["repository"]["full_name"],
                branch=payload["pull_request"]["head"]["ref"],
                commit_sha=payload["pull_request"]["head"]["sha"],
                commit_message=payload["pull_request"]["title"],
                author=payload["pull_request"]["user"]["login"],
                timestamp=datetime.fromisoformat(payload["pull_request"]["created_at"].replace("Z", "+00:00")),
                pull_request_id=str(payload["pull_request"]["number"]),
                raw_payload=payload,
            )

        raise ValueError(f"Unsupported GitHub event type: {event_type}")

    def _parse_gitlab_webhook(self, payload: Dict[str, Any], event_type: str) -> WebhookEvent:
        """Parse GitLab webhook payload."""
        if event_type == "Push Hook":
            return WebhookEvent(
                provider=GitProvider.GITLAB,
                event_type=event_type,
                repository=payload["project"]["path_with_namespace"],
                branch=payload["ref"].replace("refs/heads/", ""),
                commit_sha=payload["checkout_sha"],
                commit_message=payload["commits"][0]["message"] if payload["commits"] else "",
                author=payload["user_name"],
                timestamp=datetime.fromisoformat(payload["commits"][0]["timestamp"])
                if payload["commits"]
                else datetime.now(),
                raw_payload=payload,
            )

        elif event_type == "Merge Request Hook":
            return WebhookEvent(
                provider=GitProvider.GITLAB,
                event_type=event_type,
                repository=payload["project"]["path_with_namespace"],
                branch=payload["object_attributes"]["source_branch"],
                commit_sha=payload["object_attributes"]["last_commit"]["id"],
                commit_message=payload["object_attributes"]["title"],
                author=payload["user"]["name"],
                timestamp=datetime.fromisoformat(payload["object_attributes"]["created_at"]),
                pull_request_id=str(payload["object_attributes"]["iid"]),
                raw_payload=payload,
            )

        raise ValueError(f"Unsupported GitLab event type: {event_type}")


class CICDPipeline:
    """Main CI/CD pipeline orchestrator."""

    def __init__(
        self, executor: PipelineExecutor, monitoring: MonitoringStack, webhook_handler: Optional[WebhookHandler] = None
    ):
        self.executor = executor
        self.monitoring = monitoring
        self.webhook_handler = webhook_handler or WebhookHandler()
        self.logger = logging.getLogger(__name__)
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.pipeline_runs: Dict[str, PipelineRun] = {}
        self._running_pipelines: Dict[str, asyncio.Task] = {}

    def register_pipeline(self, config: PipelineConfig):
        """Register a pipeline configuration."""
        self.pipelines[config.name] = config
        self.logger.info(f"Registered pipeline: {config.name}")

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str, provider: GitProvider, event_type: str
    ) -> Optional[str]:
        """Handle incoming webhook and trigger pipeline if needed."""
        try:
            # Verify signature
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
            if not self.webhook_handler.verify_signature(payload_bytes, signature, provider):
                self.logger.warning("Webhook signature verification failed")
                return None

            # Parse webhook
            event = self.webhook_handler.parse_webhook(payload, provider, event_type)
            if not event:
                self.logger.warning("Failed to parse webhook event")
                return None

            # Find matching pipeline
            pipeline_config = self._find_matching_pipeline(event)
            if not pipeline_config:
                self.logger.info(f"No matching pipeline for {event.repository}:{event.branch}")
                return None

            # Check if pipeline should be triggered
            if not self._should_trigger_pipeline(pipeline_config, event):
                self.logger.info(f"Pipeline {pipeline_config.name} not triggered for event {event_type}")
                return None

            # Create and start pipeline run
            run_id = await self.trigger_pipeline(pipeline_config.name, event)

            self.logger.info(f"Pipeline {pipeline_config.name} triggered with run ID: {run_id}")
            return run_id

        except Exception as e:
            self.logger.error(f"Webhook handling failed: {str(e)}")
            self.monitoring.increment_counter(
                "webhook_errors_total", {"provider": provider, "event_type": event_type, "error": type(e).__name__}
            )
            return None

    async def trigger_pipeline(self, pipeline_name: str, event: WebhookEvent) -> str:
        """Manually trigger a pipeline."""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline {pipeline_name} not found")

        config = self.pipelines[pipeline_name]

        # Create pipeline run
        run_id = f"{pipeline_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{event.commit_sha[:8]}"

        run = PipelineRun(
            id=run_id,
            pipeline_name=pipeline_name,
            repository=event.repository,
            branch=event.branch,
            commit_sha=event.commit_sha,
            trigger_event=event.event_type,
            status=PipelineStatus.PENDING,
            start_time=datetime.now(),
        )

        self.pipeline_runs[run_id] = run

        # Start pipeline execution
        task = asyncio.create_task(self._execute_pipeline(config, run))
        self._running_pipelines[run_id] = task

        return run_id

    async def get_pipeline_status(self, run_id: str) -> Optional[PipelineRun]:
        """Get pipeline run status."""
        return self.pipeline_runs.get(run_id)

    async def cancel_pipeline(self, run_id: str) -> bool:
        """Cancel a running pipeline."""
        if run_id not in self._running_pipelines:
            return False

        try:
            task = self._running_pipelines[run_id]
            task.cancel()

            if run_id in self.pipeline_runs:
                self.pipeline_runs[run_id].status = PipelineStatus.CANCELLED
                self.pipeline_runs[run_id].end_time = datetime.now()

            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel pipeline {run_id}: {str(e)}")
            return False

    async def list_pipeline_runs(
        self, pipeline_name: Optional[str] = None, status: Optional[PipelineStatus] = None, limit: int = 50
    ) -> List[PipelineRun]:
        """List pipeline runs with filtering."""
        runs = list(self.pipeline_runs.values())

        if pipeline_name:
            runs = [r for r in runs if r.pipeline_name == pipeline_name]

        if status:
            runs = [r for r in runs if r.status == status]

        # Sort by start time descending
        runs.sort(key=lambda x: x.start_time, reverse=True)

        return runs[:limit]

    async def _execute_pipeline(self, config: PipelineConfig, run: PipelineRun):
        """Execute a complete pipeline."""
        try:
            run.status = PipelineStatus.RUNNING

            with self.monitoring.create_span("pipeline_execution", config.name) as span:
                span.set_tag("pipeline", config.name)
                span.set_tag("run_id", run.id)
                span.set_tag("branch", run.branch)
                span.set_tag("commit", run.commit_sha[:8])

                context: Dict[str, Any] = {}

                # Execute stages
                if config.parallel_stages:
                    await self._execute_stages_parallel(config, run, context)
                else:
                    await self._execute_stages_sequential(config, run, context)

                run.status = PipelineStatus.SUCCESS
                run.end_time = datetime.now()

                # Record metrics
                duration = (run.end_time - run.start_time).total_seconds()
                self.monitoring.record_histogram(
                    "pipeline_duration_seconds", duration, {"pipeline": config.name, "status": "success"}
                )

                self.logger.info(f"Pipeline {run.id} completed successfully")

        except Exception as e:
            run.status = PipelineStatus.FAILURE
            run.end_time = datetime.now()
            run.error_message = str(e)

            self.logger.error(f"Pipeline {run.id} failed: {str(e)}")

            # Record failure metrics
            if run.end_time:
                duration = (run.end_time - run.start_time).total_seconds()
                self.monitoring.record_histogram(
                    "pipeline_duration_seconds", duration, {"pipeline": config.name, "status": "failure"}
                )

            self.monitoring.increment_counter(
                "pipeline_failures_total", {"pipeline": config.name, "error": type(e).__name__}
            )

            # Rollback if configured
            if config.rollback_on_failure and run.deployment_id:
                try:
                    self.logger.info(f"Rolling back deployment {run.deployment_id}")
                    await self.executor.deployment.rollback_service(run.deployment_id, f"Pipeline failure: {str(e)}")
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed: {str(rollback_error)}")

        finally:
            # Cleanup
            try:
                await self.executor.cleanup(run)
            except Exception as cleanup_error:
                self.logger.warning(f"Cleanup failed for {run.id}: {str(cleanup_error)}")

            # Remove from running pipelines
            if run.id in self._running_pipelines:
                del self._running_pipelines[run.id]

    async def _execute_stages_sequential(self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any]):
        """Execute pipeline stages sequentially."""
        for stage in config.stages:
            self.logger.info(f"Executing stage {stage} for pipeline {run.id}")

            try:
                stage_result = await self.executor.execute_stage(stage, config, run, context)
                run.stages[stage] = stage_result

                if stage_result["status"] != "success":
                    raise Exception(f"Stage {stage} failed")

            except Exception as e:
                run.stages[stage] = {
                    "status": "failure",
                    "error": str(e),
                    "start_time": datetime.now(),
                    "end_time": datetime.now(),
                }
                raise

    async def _execute_stages_parallel(self, config: PipelineConfig, run: PipelineRun, context: Dict[str, Any]):
        """Execute pipeline stages in parallel where possible."""
        # For now, just execute sequentially
        # In a full implementation, you'd analyze stage dependencies
        await self._execute_stages_sequential(config, run, context)

    def _find_matching_pipeline(self, event: WebhookEvent) -> Optional[PipelineConfig]:
        """Find pipeline configuration matching the webhook event."""
        for config in self.pipelines.values():
            if self._pipeline_matches_event(config, event):
                return config
        return None

    def _pipeline_matches_event(self, config: PipelineConfig, event: WebhookEvent) -> bool:
        """Check if pipeline configuration matches the webhook event."""
        # Match repository
        if not re.match(config.repository.replace("*", ".*"), event.repository):
            return False

        # Match branch
        if not re.match(config.branch.replace("*", ".*"), event.branch):
            return False

        return True

    def _should_trigger_pipeline(self, config: PipelineConfig, event: WebhookEvent) -> bool:
        """Determine if pipeline should be triggered for the event."""
        # Check trigger events
        if event.event_type.lower() not in [e.lower() for e in config.trigger_events]:
            return False

        # Check if branch is in auto-deploy list for deploy events
        if PipelineStage.DEPLOY in config.stages:
            if event.branch not in config.auto_deploy_branches:
                self.logger.info(f"Branch {event.branch} not in auto-deploy list")
                return False

        return True


class CICDFactory:
    """Factory for creating CI/CD pipeline instances."""

    @staticmethod
    def create_docker_pipeline(
        monitoring: MonitoringStack, deployment: DeploymentAutomation, webhook_secret: Optional[str] = None
    ) -> CICDPipeline:
        """Create Docker-based CI/CD pipeline."""
        executor = DockerPipelineExecutor(monitoring, deployment)
        webhook_handler = WebhookHandler(webhook_secret)
        return CICDPipeline(executor, monitoring, webhook_handler)


# Convenience function for easy setup
async def setup_cicd_pipeline(
    monitoring: MonitoringStack, deployment: DeploymentAutomation, webhook_secret: Optional[str] = None
) -> CICDPipeline:
    """Setup CI/CD pipeline with monitoring and deployment integration."""
    factory = CICDFactory()
    return factory.create_docker_pipeline(monitoring, deployment, webhook_secret)
