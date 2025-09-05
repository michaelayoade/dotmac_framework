"""
GitHub CI/CD Integration for Performance Benchmarking

Provides GitHub Actions integration for automated performance testing,
including PR comments, status checks, and artifact management.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional

import requests
from pydantic import BaseModel, Field

from ..utils.decorators import standard_exception_handler
from .pipeline_runner import PerformancePipelineRunner, PipelineConfig, PipelineResult, PipelineStatus

logger = logging.getLogger(__name__)


class GitHubBenchmarkConfig(BaseModel):
    """Configuration for GitHub performance benchmarking integration"""

    # GitHub settings
    github_token: Optional[str] = None
    repository: Optional[str] = None  # format: owner/repo
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None

    # Pipeline settings
    pipeline_config: PipelineConfig = Field(default_factory=PipelineConfig)

    # GitHub integration settings
    post_pr_comments: bool = True
    update_status_checks: bool = True
    upload_artifacts: bool = True
    fail_on_regression: bool = True
    fail_on_critical_issues: bool = True

    # Comparison settings
    compare_with_main: bool = True
    main_branch: str = "main"
    baseline_runs_to_compare: int = Field(default=5, ge=1, le=20)

    # Notification settings
    mention_team_on_regression: bool = False
    team_to_mention: Optional[str] = None  # e.g., "@performance-team"


class GitHubPerformanceCI:
    """GitHub Actions integration for automated performance testing"""

    def __init__(self, config: GitHubBenchmarkConfig):
        self.config = config
        self.github_token = config.github_token or os.getenv("GITHUB_TOKEN")
        self.repository = config.repository or os.getenv("GITHUB_REPOSITORY")
        self.pr_number = config.pr_number or self._get_pr_number_from_env()
        self.commit_sha = config.commit_sha or os.getenv("GITHUB_SHA")

        # Initialize pipeline runner
        self.pipeline_runner = PerformancePipelineRunner(config.pipeline_config)

        # GitHub API base URL
        self.github_api_base = "https://api.github.com"

    @standard_exception_handler
    async def run_performance_checks(self) -> dict[str, Any]:
        """Run complete performance checks for GitHub PR/commit"""

        # Set initial status check
        if self.config.update_status_checks and self._can_update_status():
            await self._update_status_check("pending", "Running performance benchmarks...")

        try:
            # Run the performance pipeline
            pipeline_result = await self.pipeline_runner.run_pipeline()

            # Process results for GitHub
            github_result = await self._process_pipeline_result(pipeline_result)

            # Update status check based on results
            if self.config.update_status_checks and self._can_update_status():
                await self._update_final_status_check(pipeline_result)

            # Post PR comment if enabled
            if self.config.post_pr_comments and self.pr_number and self._can_comment():
                await self._post_pr_comment(pipeline_result)

            # Upload artifacts if enabled
            if self.config.upload_artifacts:
                await self._upload_artifacts(pipeline_result)

            return github_result

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Performance check failed: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Update status check on error
            if self.config.update_status_checks and self._can_update_status():
                await self._update_status_check("error", f"Performance check failed: {str(e)}")

            return error_result

    @standard_exception_handler
    async def compare_with_baseline(self, current_results: dict[str, float]) -> dict[str, Any]:
        """Compare current results with baseline from main branch"""
        if not self.config.compare_with_main:
            return {"status": "skipped", "reason": "Baseline comparison disabled"}

        # Get baseline results (this would typically fetch from storage/API)
        baseline_results = await self._get_baseline_results()

        if not baseline_results:
            return {"status": "no_baseline", "message": "No baseline results found for comparison"}

        # Use comparator to analyze differences
        if self.pipeline_runner.comparator:
            comparison = self.pipeline_runner.comparator.compare_benchmark_sets(
                baseline_results,
                current_results,
                f"{self.config.main_branch}_baseline",
                f"pr_{self.pr_number}_current" if self.pr_number else "current",
            )

            return {
                "status": "completed",
                "comparison_result": comparison.__dict__,
                "performance_change": comparison.overall_performance_change,
                "regression_detected": comparison.overall_performance_change > 10,  # 10% threshold
                "significant_changes": len(comparison.significant_changes),
            }

        return {"status": "error", "message": "Comparator not available"}

    async def _process_pipeline_result(self, pipeline_result: PipelineResult) -> dict[str, Any]:
        """Process pipeline result for GitHub integration"""

        # Determine if we should fail the check
        should_fail = False
        failure_reasons = []

        if pipeline_result.status == PipelineStatus.FAILED:
            should_fail = True
            failure_reasons.append("Pipeline execution failed")

        if self.config.fail_on_regression and pipeline_result.regression_detected:
            should_fail = True
            failure_reasons.append("Performance regression detected")

        if self.config.fail_on_critical_issues and pipeline_result.critical_issues:
            should_fail = True
            failure_reasons.append(f"{len(pipeline_result.critical_issues)} critical issues found")

        return {
            "pipeline_id": pipeline_result.pipeline_id,
            "status": "failed" if should_fail else "success",
            "should_fail_check": should_fail,
            "failure_reasons": failure_reasons,
            "performance_score": pipeline_result.overall_performance_score,
            "regression_detected": pipeline_result.regression_detected,
            "critical_issues_count": len(pipeline_result.critical_issues),
            "execution_time": pipeline_result.total_execution_time,
            "summary": pipeline_result.summary,
            "recommendations": pipeline_result.recommendations,
            "artifacts": pipeline_result.artifacts,
        }

    async def _update_status_check(self, state: str, description: str, target_url: Optional[str] = None):
        """Update GitHub status check"""
        if not self._can_update_status():
            return

        url = f"{self.github_api_base}/repos/{self.repository}/statuses/{self.commit_sha}"

        data = {
            "state": state,  # pending, success, error, failure
            "description": description[:140],  # GitHub limits to 140 chars
            "context": "performance-benchmarks",
            "target_url": target_url,
        }

        headers = {"Authorization": f"token {self.github_token}", "Accept": "application/vnd.github.v3+json"}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.info(f"Failed to update status check: {e}")

    async def _update_final_status_check(self, pipeline_result: PipelineResult):
        """Update final status check based on pipeline results"""
        if pipeline_result.status == PipelineStatus.SUCCESS:
            if pipeline_result.regression_detected and self.config.fail_on_regression:
                state = "failure"
                description = (
                    f"Performance regression detected (score: {pipeline_result.overall_performance_score:.1f}%)"
                )
            elif pipeline_result.critical_issues and self.config.fail_on_critical_issues:
                state = "failure"
                description = f"{len(pipeline_result.critical_issues)} critical issues found"
            else:
                state = "success"
                description = f"Performance benchmarks passed (score: {pipeline_result.overall_performance_score:.1f}%)"
        else:
            state = "error"
            description = "Performance benchmark pipeline failed"

        await self._update_status_check(state, description)

    async def _post_pr_comment(self, pipeline_result: PipelineResult):
        """Post performance results as PR comment"""
        if not self._can_comment():
            return

        # Generate comment content
        comment_body = self._generate_pr_comment(pipeline_result)

        url = f"{self.github_api_base}/repos/{self.repository}/issues/{self.pr_number}/comments"

        headers = {"Authorization": f"token {self.github_token}", "Accept": "application/vnd.github.v3+json"}

        data = {"body": comment_body}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.info(f"Failed to post PR comment: {e}")

    def _generate_pr_comment(self, pipeline_result: PipelineResult) -> str:
        """Generate PR comment content"""

        # Status emoji
        if pipeline_result.status == PipelineStatus.SUCCESS:
            status_emoji = "✅" if not pipeline_result.regression_detected else "⚠️"
        else:
            status_emoji = "❌"

        # Build comment
        comment = f"""## {status_emoji} Performance Benchmark Results

**Pipeline ID:** `{pipeline_result.pipeline_id}`
**Performance Score:** {pipeline_result.overall_performance_score:.1f}%
**Execution Time:** {pipeline_result.total_execution_time:.1f}s

### Summary
{pipeline_result.summary}

"""

        # Add regression info if detected
        if pipeline_result.regression_detected:
            comment += """### 🚨 Performance Regression Detected
Performance has degraded compared to baseline. Please review the changes.

"""

        # Add critical issues
        if pipeline_result.critical_issues:
            comment += f"""### ⚠️ Critical Issues ({len(pipeline_result.critical_issues)})
"""
            for issue in pipeline_result.critical_issues[:5]:  # Limit to first 5
                comment += f"- {issue.get('message', 'Unknown issue')}\n"

            if len(pipeline_result.critical_issues) > 5:
                comment += f"- ... and {len(pipeline_result.critical_issues) - 5} more issues\n"
            comment += "\n"

        # Add stage results
        comment += """### Stage Results
| Stage | Status | Time |
|-------|--------|------|
"""

        for stage in pipeline_result.stages:
            status_icon = "✅" if stage.status.value == "success" else "❌" if stage.status.value == "failed" else "⏸️"
            comment += (
                f"| {stage.stage.value.title()} | {status_icon} {stage.status.value} | {stage.execution_time:.1f}s |\n"
            )

        # Add recommendations
        if pipeline_result.recommendations:
            comment += "\n### 💡 Recommendations\n"
            for rec in pipeline_result.recommendations[:3]:  # Limit to first 3
                comment += f"- {rec}\n"

        # Add team mention if regression and configured
        if (
            pipeline_result.regression_detected
            and self.config.mention_team_on_regression
            and self.config.team_to_mention
        ):
            comment += f"\n{self.config.team_to_mention} - Performance regression detected, please review.\n"

        # Add footer
        successful_count = len([s for s in pipeline_result.stages if s.status.value == "success"])
        total_stages = len(pipeline_result.stages)
        comment += f"""
---
<details>
<summary>Benchmark Details</summary>

**Artifacts:** {len(pipeline_result.artifacts)} files generated
**Stages Completed:** {successful_count}/{total_stages}

</details>
"""

        return comment

    async def _upload_artifacts(self, pipeline_result: PipelineResult):
        """Upload benchmark artifacts (placeholder - would integrate with GitHub Actions artifacts)"""
        # This would typically use GitHub Actions artifact upload
        # For now, just log the artifacts that would be uploaded
        if pipeline_result.artifacts:
            logger.info(f"Would upload {len(pipeline_result.artifacts)} artifacts:")
            for artifact in pipeline_result.artifacts:
                logger.info(f"  - {artifact}")

    async def _get_baseline_results(self) -> Optional[dict[str, float]]:
        """Get baseline results from main branch (placeholder implementation)"""
        # This would typically:
        # 1. Query GitHub API for recent commits on main branch
        # 2. Look for benchmark results in a database/storage
        # 3. Aggregate the results for comparison

        # For now, return placeholder baseline data
        return {
            "api_response_time": 120.5,
            "database_query_time": 45.2,
            "memory_usage_mb": 256.8,
            "cpu_usage_percent": 35.2,
        }

    def _can_update_status(self) -> bool:
        """Check if we can update GitHub status checks"""
        return bool(self.github_token and self.repository and self.commit_sha)

    def _can_comment(self) -> bool:
        """Check if we can post PR comments"""
        return bool(self.github_token and self.repository and self.pr_number)

    def _get_pr_number_from_env(self) -> Optional[int]:
        """Extract PR number from GitHub environment"""
        github_ref = os.getenv("GITHUB_REF", "")
        if github_ref.startswith("refs/pull/"):
            try:
                return int(github_ref.split("/")[2])
            except (IndexError, ValueError):
                pass
        return None


# GitHub Actions workflow example
GITHUB_WORKFLOW_EXAMPLE = """
# .github/workflows/performance-tests.yml
name: Performance Benchmarks

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  performance-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run Performance Benchmarks
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
        API_BASE_URL: ${{ secrets.API_BASE_URL }}
      run: |
        python -c "
        import asyncio
        from dotmac_shared.benchmarking.cicd import (
            GitHubPerformanceCI,
            GitHubBenchmarkConfig,
            PipelineConfig
        )

        config = GitHubBenchmarkConfig(
            pipeline_config=PipelineConfig(
                api_base_url='${{ secrets.API_BASE_URL }}',
                database_url='${{ secrets.TEST_DATABASE_URL }}',
                api_concurrent_users=10,
                db_concurrent_connections=5
            ),
            fail_on_regression=True,
            post_pr_comments=True
        )

        ci = GitHubPerformanceCI(config)
        result = asyncio.run(ci.run_performance_checks())

        # Exit with error code if benchmarks failed
        if result.get('should_fail_check', False):
            exit(1)
        "

    - name: Upload Benchmark Artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: benchmark-results
        path: ./benchmark_results/
        retention-days: 30
"""
