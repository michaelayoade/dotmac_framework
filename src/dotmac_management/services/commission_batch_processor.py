"""
Commission Batch Processing System

Provides high-performance batch processing for commission calculations:
- Large-scale commission calculation batches
- Multi-tenant parallel processing
- Real-time progress tracking and reporting
- Error handling and partial failure recovery
- Commission reconciliation and validation
- Performance optimization for large datasets
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from dotmac.database.base import get_db_session
from dotmac.tasks.decorators import (
    TaskExecutionContext,
    background_task,
    scheduled_task,
)
from dotmac_management.models.commission_config import CommissionConfig
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CommissionBatchConfig:
    """Configuration for commission batch processing."""

    batch_size: int = 1000
    max_concurrent_batches: int = 5
    timeout_per_batch: int = 300  # 5 minutes
    retry_attempts: int = 3
    enable_validation: bool = True
    enable_reconciliation: bool = True
    notification_threshold: int = 10000  # Notify for batches > 10k records


@dataclass
class CommissionCalculationResult:
    """Result of commission calculation for a single transaction."""

    transaction_id: str
    partner_id: str
    commission_config_id: str
    base_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    tier_applied: Optional[str] = None
    calculation_method: str = "standard"
    metadata: dict[str, Any] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BatchProcessingResult:
    """Result of batch commission processing."""

    batch_id: str
    total_records: int
    processed_records: int
    successful_calculations: int
    failed_calculations: int
    total_commission_amount: Decimal
    processing_time_seconds: float
    errors: list[dict[str, Any]] = field(default_factory=list)
    partner_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    validation_results: Optional[dict[str, Any]] = None


class CommissionBatchProcessor:
    """
    High-performance commission batch processing system.

    Features:
    - Parallel processing of large commission calculation batches
    - Multi-tenant isolation and processing
    - Real-time progress tracking and notifications
    - Comprehensive error handling and recovery
    - Performance optimization for big data workloads
    - Automated reconciliation and validation
    """

    def __init__(
        self,
        config: CommissionBatchConfig = None,
        redis_url: str = "redis://localhost:6379",
    ):
        self.config = config or CommissionBatchConfig()
        self.redis_url = redis_url

        # Processing state
        self._processing_stats = {
            "total_batches_processed": 0,
            "total_records_processed": 0,
            "total_commission_calculated": Decimal("0.00"),
            "average_processing_time": 0.0,
            "error_rate": 0.0,
        }

        # Cache for commission configurations
        self._commission_config_cache: dict[str, CommissionConfig] = {}
        self._cache_ttl = 3600  # 1 hour

    @background_task(
        name="process_commission_batch",
        queue="commission_processing",
        timeout=3600.0,  # 1 hour for large batches
        tags=["commission", "batch", "calculation"],
    )
    async def process_commission_batch(
        self,
        batch_id: str,
        transaction_data: list[dict[str, Any]],
        partner_filter: Optional[list[str]] = None,
        date_range: Optional[tuple[str, str]] = None,
        task_context: Optional[dict] = None,
    ) -> BatchProcessingResult:
        """
        Process a batch of commission calculations.

        Args:
            batch_id: Unique identifier for this batch
            transaction_data: List of transaction records to process
            partner_filter: Optional list of partner IDs to filter by
            date_range: Optional date range filter (start_date, end_date)
            task_context: Task execution context

        Returns:
            BatchProcessingResult with comprehensive processing results
        """
        async with TaskExecutionContext(
            task_name="process_commission_batch",
            progress_callback=task_context.get("progress_callback") if task_context else None,
            metadata={"batch_id": batch_id, "record_count": len(transaction_data)},
        ) as ctx:
            start_time = time.time()

            await ctx.update_progress(
                5,
                f"Starting commission batch {batch_id} with {len(transaction_data)} records",
            )

            # Initialize batch result
            batch_result = BatchProcessingResult(
                batch_id=batch_id,
                total_records=len(transaction_data),
                processed_records=0,
                successful_calculations=0,
                failed_calculations=0,
                total_commission_amount=Decimal("0.00"),
                processing_time_seconds=0.0,
            )

            try:
                # Step 1: Validate and prepare data
                await ctx.update_progress(10, "Validating and preparing transaction data")
                validated_data = await self._validate_and_prepare_data(transaction_data, partner_filter, date_range)

                if not validated_data:
                    raise ValueError("No valid transaction data after filtering and validation")

                # Step 2: Load commission configurations
                await ctx.update_progress(20, "Loading commission configurations")
                commission_configs = await self._load_commission_configurations(validated_data)

                # Step 3: Split data into processing batches
                await ctx.update_progress(25, "Splitting data into processing batches")
                processing_batches = self._split_into_processing_batches(validated_data, self.config.batch_size)

                # Step 4: Process batches in parallel
                await ctx.update_progress(30, f"Processing {len(processing_batches)} batches in parallel")

                batch_results = []
                processed_count = 0

                # Process batches with controlled concurrency
                semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)

                async def process_single_batch(batch_data: list[dict], batch_index: int):
                    async with semaphore:
                        return await self._process_single_batch(
                            batch_data, commission_configs, f"{batch_id}_{batch_index}"
                        )

                # Create tasks for all batches
                batch_tasks = [process_single_batch(batch_data, i) for i, batch_data in enumerate(processing_batches)]

                # Process batches and update progress
                for completed_task in asyncio.as_completed(batch_tasks):
                    try:
                        single_result = await completed_task
                        batch_results.append(single_result)
                        processed_count += single_result["processed_count"]

                        progress = 30 + (processed_count / len(validated_data) * 60)
                        await ctx.update_progress(
                            int(progress),
                            f"Processed {processed_count}/{len(validated_data)} records",
                        )

                    except Exception as e:
                        logger.error(f"Batch processing failed: {e}")
                        batch_result.errors.append(
                            {
                                "type": "batch_processing_error",
                                "message": str(e),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )

                # Step 5: Aggregate results
                await ctx.update_progress(90, "Aggregating batch results")
                await self._aggregate_batch_results(batch_result, batch_results)

                # Step 6: Validation and reconciliation
                if self.config.enable_validation:
                    await ctx.update_progress(95, "Running validation checks")
                    batch_result.validation_results = await self._validate_batch_results(batch_result, validated_data)

                # Step 7: Generate partner summaries
                await ctx.update_progress(98, "Generating partner summaries")
                batch_result.partner_summaries = await self._generate_partner_summaries(batch_results)

                # Final processing time calculation
                batch_result.processing_time_seconds = time.time() - start_time

                # Update statistics
                self._update_processing_stats(batch_result)

                await ctx.update_progress(
                    100,
                    f"Commission batch completed: {batch_result.successful_calculations} successful, "
                    f"${batch_result.total_commission_amount} total commission",
                )

                logger.info(
                    "Commission batch processing completed",
                    extra={
                        "batch_id": batch_id,
                        "total_records": batch_result.total_records,
                        "successful_calculations": batch_result.successful_calculations,
                        "total_commission": str(batch_result.total_commission_amount),
                        "processing_time": batch_result.processing_time_seconds,
                    },
                )

                return batch_result

            except Exception as e:
                batch_result.processing_time_seconds = time.time() - start_time
                batch_result.errors.append(
                    {
                        "type": "batch_processing_fatal_error",
                        "message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.error(
                    "Commission batch processing failed",
                    extra={
                        "batch_id": batch_id,
                        "error": str(e),
                        "processing_time": batch_result.processing_time_seconds,
                    },
                )

                raise

    @background_task(
        name="process_monthly_commissions",
        queue="commission_processing",
        timeout=7200.0,  # 2 hours for monthly processing
        tags=["commission", "monthly", "batch"],
    )
    async def process_monthly_commission_batch(
        self,
        year: int,
        month: int,
        partner_ids: Optional[list[str]] = None,
        task_context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Process monthly commission calculations for all partners.

        Args:
            year: Year to process
            month: Month to process (1-12)
            partner_ids: Optional list of specific partner IDs to process
            task_context: Task execution context

        Returns:
            Dict containing comprehensive monthly processing results
        """
        async with TaskExecutionContext(
            task_name="process_monthly_commission_batch",
            progress_callback=task_context.get("progress_callback") if task_context else None,
            metadata={"year": year, "month": month},
        ) as ctx:
            batch_id = f"monthly_{year}_{month:02d}_{int(time.time())}"

            await ctx.update_progress(5, f"Starting monthly commission processing for {year}-{month:02d}")

            # Step 1: Load transaction data for the month
            await ctx.update_progress(15, "Loading transaction data")
            transaction_data = await self._load_monthly_transaction_data(year, month, partner_ids)

            if not transaction_data:
                return {
                    "batch_id": batch_id,
                    "status": "completed",
                    "message": f"No transactions found for {year}-{month:02d}",
                    "total_records": 0,
                }

            await ctx.update_progress(25, f"Found {len(transaction_data)} transactions to process")

            # Step 2: Process the batch
            batch_result = await self.process_commission_batch(
                batch_id=batch_id,
                transaction_data=transaction_data,
                partner_filter=partner_ids,
                date_range=(
                    f"{year}-{month:02d}-01",
                    f"{year}-{month:02d}-{self._get_days_in_month(year, month):02d}",
                ),
                task_context={"progress_callback": lambda pct, msg: ctx.update_progress(int(25 + (pct * 0.7)), msg)},
            )

            # Step 3: Generate monthly reports
            await ctx.update_progress(95, "Generating monthly commission reports")
            monthly_reports = await self._generate_monthly_reports(batch_result, year, month)

            await ctx.update_progress(100, "Monthly commission processing completed")

            return {
                "batch_id": batch_id,
                "status": "completed",
                "year": year,
                "month": month,
                "batch_result": batch_result,
                "monthly_reports": monthly_reports,
                "processing_summary": {
                    "total_partners": len(batch_result.partner_summaries),
                    "total_transactions": batch_result.total_records,
                    "total_commission_amount": str(batch_result.total_commission_amount),
                    "processing_time_minutes": batch_result.processing_time_seconds / 60,
                    "success_rate": batch_result.successful_calculations / batch_result.total_records
                    if batch_result.total_records > 0
                    else 0,
                },
            }

    @scheduled_task(
        "0 2 1 * *",  # Run on the 1st of every month at 2 AM
        name="auto_monthly_commission_processing",
        queue="commission_scheduled",
        tags=["commission", "scheduled", "monthly"],
    )
    async def auto_process_monthly_commissions(self, task_context: Optional[dict] = None) -> dict[str, Any]:
        """
        Automatically process previous month's commissions.

        Scheduled to run monthly for automated commission processing.
        """
        # Calculate previous month
        now = datetime.now(timezone.utc)
        if now.month == 1:
            prev_year = now.year - 1
            prev_month = 12
        else:
            prev_year = now.year
            prev_month = now.month - 1

        return await self.process_monthly_commission_batch(year=prev_year, month=prev_month, task_context=task_context)

    @background_task(
        name="reconcile_commission_calculations",
        queue="commission_processing",
        timeout=1800.0,  # 30 minutes
        tags=["commission", "reconciliation", "validation"],
    )
    async def reconcile_commission_calculations(
        self,
        batch_id: str,
        external_data: Optional[list[dict[str, Any]]] = None,
        tolerance_percentage: float = 0.01,  # 1% tolerance
        task_context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Reconcile commission calculations against external data or previous calculations.

        Args:
            batch_id: Batch ID to reconcile
            external_data: Optional external data to reconcile against
            tolerance_percentage: Acceptable variance tolerance
            task_context: Task execution context

        Returns:
            Dict containing reconciliation results and discrepancies
        """
        async with TaskExecutionContext(
            task_name="reconcile_commission_calculations",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(10, f"Starting reconciliation for batch {batch_id}")

            # Load batch results
            batch_data = await self._load_batch_results(batch_id)
            if not batch_data:
                raise ValueError(f"Batch {batch_id} not found")

            reconciliation_result = {
                "batch_id": batch_id,
                "reconciliation_type": "external" if external_data else "internal",
                "total_records_checked": 0,
                "matching_records": 0,
                "discrepancies": [],
                "tolerance_percentage": tolerance_percentage,
                "overall_variance": 0.0,
                "status": "completed",
            }

            await ctx.update_progress(30, "Performing reconciliation checks")

            # Perform reconciliation logic
            if external_data:
                reconciliation_result.update(
                    await self._reconcile_against_external_data(batch_data, external_data, tolerance_percentage)
                )
            else:
                reconciliation_result.update(
                    await self._reconcile_internal_calculations(batch_data, tolerance_percentage)
                )

            await ctx.update_progress(80, "Generating reconciliation report")

            # Generate detailed reconciliation report
            reconciliation_report = await self._generate_reconciliation_report(reconciliation_result)
            reconciliation_result["report"] = reconciliation_report

            await ctx.update_progress(100, "Reconciliation completed")

            return reconciliation_result

    # Implementation methods

    async def _validate_and_prepare_data(
        self,
        transaction_data: list[dict[str, Any]],
        partner_filter: Optional[list[str]],
        date_range: Optional[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        """Validate and prepare transaction data for processing."""
        validated_data = []

        for transaction in transaction_data:
            try:
                # Basic validation
                if not all(key in transaction for key in ["id", "partner_id", "amount", "date"]):
                    continue

                # Partner filter
                if partner_filter and transaction["partner_id"] not in partner_filter:
                    continue

                # Date range filter
                if date_range:
                    transaction_date = datetime.fromisoformat(transaction["date"])
                    start_date = datetime.fromisoformat(date_range[0])
                    end_date = datetime.fromisoformat(date_range[1])

                    if not (start_date <= transaction_date <= end_date):
                        continue

                # Amount validation
                if Decimal(str(transaction["amount"])) <= 0:
                    continue

                validated_data.append(transaction)

            except Exception as e:
                logger.warning(f"Transaction validation failed: {e}")
                continue

        return validated_data

    async def _load_commission_configurations(
        self, transaction_data: list[dict[str, Any]]
    ) -> dict[str, CommissionConfig]:
        """Load commission configurations for all partners in the batch."""
        partner_ids = list({t["partner_id"] for t in transaction_data})
        commission_configs = {}

        with get_db_session() as db:
            for partner_id in partner_ids:
                # Check cache first
                if partner_id in self._commission_config_cache:
                    commission_configs[partner_id] = self._commission_config_cache[partner_id]
                    continue

                # Load from database
                config = db.query(CommissionConfig).filter_by(partner_id=partner_id, is_active=True).first()

                if config:
                    commission_configs[partner_id] = config
                    self._commission_config_cache[partner_id] = config
                else:
                    # Use default configuration
                    commission_configs[partner_id] = self._get_default_commission_config(partner_id)

        return commission_configs

    def _split_into_processing_batches(self, data: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        """Split data into processing batches."""
        batches = []
        for i in range(0, len(data), batch_size):
            batches.append(data[i : i + batch_size])
        return batches

    async def _process_single_batch(
        self,
        batch_data: list[dict[str, Any]],
        commission_configs: dict[str, CommissionConfig],
        batch_id: str,
    ) -> dict[str, Any]:
        """Process a single batch of transactions."""
        results = []
        processing_errors = []

        for transaction in batch_data:
            try:
                partner_id = transaction["partner_id"]
                config = commission_configs.get(partner_id)

                if not config:
                    processing_errors.append(
                        {
                            "transaction_id": transaction["id"],
                            "error": f"No commission configuration for partner {partner_id}",
                        }
                    )
                    continue

                # Calculate commission
                calculation_result = await self._calculate_commission(transaction, config)
                results.append(calculation_result)

            except Exception as e:
                processing_errors.append(
                    {
                        "transaction_id": transaction.get("id", "unknown"),
                        "error": str(e),
                    }
                )

        return {
            "batch_id": batch_id,
            "processed_count": len(batch_data),
            "successful_count": len(results),
            "failed_count": len(processing_errors),
            "results": results,
            "errors": processing_errors,
        }

    async def _calculate_commission(
        self, transaction: dict[str, Any], config: CommissionConfig
    ) -> CommissionCalculationResult:
        """Calculate commission for a single transaction."""
        base_amount = Decimal(str(transaction["amount"]))

        # Determine commission rate based on configuration
        if config.commission_tiers:
            # Tiered commission calculation
            commission_rate, tier_name = self._get_tiered_commission_rate(base_amount, config)
        else:
            # Flat rate commission
            commission_rate = config.commission_rate
            tier_name = None

        # Calculate commission amount
        commission_amount = (base_amount * commission_rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return CommissionCalculationResult(
            transaction_id=transaction["id"],
            partner_id=transaction["partner_id"],
            commission_config_id=str(config.id),
            base_amount=base_amount,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            tier_applied=tier_name,
            metadata={
                "transaction_date": transaction["date"],
                "calculation_method": "tiered" if tier_name else "flat",
            },
        )

    def _get_tiered_commission_rate(self, amount: Decimal, config: CommissionConfig) -> tuple[Decimal, Optional[str]]:
        """Get commission rate based on tiered configuration."""
        for tier in sorted(config.commission_tiers, key=lambda t: t.min_amount):
            if amount >= tier.min_amount:
                if not tier.max_amount or amount <= tier.max_amount:
                    return tier.rate, tier.name

        # Fallback to base rate
        return config.commission_rate, None

    async def _aggregate_batch_results(
        self,
        batch_result: BatchProcessingResult,
        single_batch_results: list[dict[str, Any]],
    ):
        """Aggregate results from individual batch processing."""
        for single_result in single_batch_results:
            batch_result.processed_records += single_result["processed_count"]
            batch_result.successful_calculations += single_result["successful_count"]
            batch_result.failed_calculations += single_result["failed_count"]

            # Aggregate commission amounts
            for calc_result in single_result["results"]:
                batch_result.total_commission_amount += calc_result.commission_amount

            # Collect errors
            batch_result.errors.extend(single_result["errors"])

    async def _validate_batch_results(
        self, batch_result: BatchProcessingResult, original_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate batch processing results."""
        validation_result = {
            "data_integrity_check": True,
            "amount_validation": True,
            "partner_distribution_check": True,
            "validation_errors": [],
        }

        # Check data integrity
        if batch_result.processed_records != len(original_data):
            validation_result["data_integrity_check"] = False
            validation_result["validation_errors"].append(
                f"Processed {batch_result.processed_records} records but expected {len(original_data)}"
            )

        # Validate commission amounts are reasonable
        if batch_result.total_commission_amount <= 0:
            validation_result["amount_validation"] = False
            validation_result["validation_errors"].append("Total commission amount is zero or negative")

        return validation_result

    async def _generate_partner_summaries(self, batch_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Generate summary statistics per partner."""
        partner_summaries = defaultdict(
            lambda: {
                "total_transactions": 0,
                "total_commission": Decimal("0.00"),
                "average_commission_rate": Decimal("0.00"),
                "commission_tiers_used": set(),
                "processing_errors": 0,
            }
        )

        total_rates = defaultdict(list)

        for batch_result in batch_results:
            for calc_result in batch_result.get("results", []):
                partner_id = calc_result.partner_id
                summary = partner_summaries[partner_id]

                summary["total_transactions"] += 1
                summary["total_commission"] += calc_result.commission_amount
                total_rates[partner_id].append(calc_result.commission_rate)

                if calc_result.tier_applied:
                    summary["commission_tiers_used"].add(calc_result.tier_applied)

        # Calculate averages and finalize summaries
        final_summaries = {}
        for partner_id, summary in partner_summaries.items():
            if total_rates[partner_id]:
                summary["average_commission_rate"] = sum(total_rates[partner_id]) / len(total_rates[partner_id])

            summary["commission_tiers_used"] = list(summary["commission_tiers_used"])
            final_summaries[partner_id] = dict(summary)

        return final_summaries

    def _update_processing_stats(self, batch_result: BatchProcessingResult):
        """Update global processing statistics."""
        self._processing_stats["total_batches_processed"] += 1
        self._processing_stats["total_records_processed"] += batch_result.processed_records
        self._processing_stats["total_commission_calculated"] += batch_result.total_commission_amount

        # Update average processing time
        current_avg = self._processing_stats["average_processing_time"]
        batch_count = self._processing_stats["total_batches_processed"]
        self._processing_stats["average_processing_time"] = (
            current_avg * (batch_count - 1) + batch_result.processing_time_seconds
        ) / batch_count

        # Update error rate
        if batch_result.total_records > 0:
            batch_error_rate = batch_result.failed_calculations / batch_result.total_records
            total_processed = self._processing_stats["total_records_processed"]
            current_error_rate = self._processing_stats["error_rate"]

            self._processing_stats["error_rate"] = (
                current_error_rate * (total_processed - batch_result.processed_records)
                + batch_error_rate * batch_result.processed_records
            ) / total_processed

    # Additional helper methods...
    async def _load_monthly_transaction_data(
        self, year: int, month: int, partner_ids: Optional[list[str]]
    ) -> list[dict[str, Any]]:
        """Load transaction data for a specific month."""
        # This would integrate with your billing/transaction system
        # Placeholder implementation
        return []

    def _get_days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month."""
        import calendar

        return calendar.monthrange(year, month)[1]

    async def _generate_monthly_reports(
        self, batch_result: BatchProcessingResult, year: int, month: int
    ) -> dict[str, Any]:
        """Generate monthly commission reports."""
        return {
            "report_period": f"{year}-{month:02d}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_partners": len(batch_result.partner_summaries),
                "total_commission": str(batch_result.total_commission_amount),
            },
        }

    def _get_default_commission_config(self, partner_id: str) -> CommissionConfig:
        """Get default commission configuration."""
        # Placeholder - would return a default configuration
        config = CommissionConfig()
        config.partner_id = partner_id
        config.commission_rate = Decimal("5.0")  # 5% default
        config.is_active = True
        return config

    async def _load_batch_results(self, batch_id: str) -> Optional[dict[str, Any]]:
        """Load batch results from storage."""
        # Implementation would load from Redis/database
        return None

    async def _reconcile_against_external_data(
        self, batch_data: dict, external_data: list[dict], tolerance: float
    ) -> dict[str, Any]:
        """Reconcile against external data source."""
        return {"matching_records": 0, "discrepancies": []}

    async def _reconcile_internal_calculations(self, batch_data: dict, tolerance: float) -> dict[str, Any]:
        """Reconcile internal calculations."""
        return {"matching_records": 0, "discrepancies": []}

    async def _generate_reconciliation_report(self, reconciliation_result: dict) -> dict[str, Any]:
        """Generate detailed reconciliation report."""
        return {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": reconciliation_result,
        }

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get current processing statistics."""
        return {
            **self._processing_stats,
            "total_commission_calculated": str(self._processing_stats["total_commission_calculated"]),
            "cache_size": len(self._commission_config_cache),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


# Create service instance for task registration
commission_batch_processor = CommissionBatchProcessor()
