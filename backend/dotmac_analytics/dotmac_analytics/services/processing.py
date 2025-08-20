"""
Data processing service for analytics pipelines and transformations.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.exceptions import ProcessingError, ValidationError
from ..models.events import AnalyticsEvent, EventBatch
from ..models.metrics import MetricValue

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for data processing and transformation pipelines."""

    def __init__(self, db: Session):
        self.db = db
        self.config = get_config()
        self.executor = ThreadPoolExecutor(max_workers=self.config.processing.max_workers)

    async def process_event_batch(
        self,
        tenant_id: str,
        batch_id: str,
        processing_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process a batch of events through analytics pipeline."""
        try:
            # Get batch
            batch = self.db.query(EventBatch).filter(
                EventBatch.tenant_id == tenant_id,
                EventBatch.id == batch_id
            ).first()

            if not batch:
                raise ProcessingError(f"Batch {batch_id} not found")

            # Get events in batch
            events = self.db.query(AnalyticsEvent).filter(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.created_at >= batch.created_at,
                AnalyticsEvent.created_at <= batch.created_at + timedelta(minutes=5)
            ).all()

            results = {
                "batch_id": batch_id,
                "processed_events": 0,
                "generated_metrics": 0,
                "errors": []
            }

            # Process each event
            for event in events:
                try:
                    await self._process_single_event(event, processing_rules)
                    results["processed_events"] += 1
                except Exception as e:
                    results["errors"].append(f"Event {event.id}: {str(e)}")

            # Update batch status
            batch.status = "completed" if not results["errors"] else "partial_success"
            batch.processed_at = utc_now()
            self.db.commit()

            logger.info(f"Processed batch {batch_id}: {results['processed_events']} events")
            return results

        except Exception as e:
            logger.error(f"Failed to process event batch: {e}")
            raise ProcessingError(f"Batch processing failed: {str(e)}")

    async def create_processing_pipeline(
        self,
        tenant_id: str,
        name: str,
        pipeline_config: Dict[str, Any],
        source_datasets: List[str],
        target_dataset: str
    ) -> Dict[str, Any]:
        """Create a data processing pipeline."""
        try:
            pipeline = {
                "id": f"pipeline_{utc_now().timestamp()}",
                "tenant_id": tenant_id,
                "name": name,
                "config": pipeline_config,
                "source_datasets": source_datasets,
                "target_dataset": target_dataset,
                "status": "active",
                "created_at": utc_now()
            }

            # Validate pipeline configuration
            await self._validate_pipeline_config(pipeline_config)

            # Schedule pipeline execution if configured
            if pipeline_config.get("schedule"):
                await self._schedule_pipeline(pipeline)

            logger.info(f"Created processing pipeline: {name}")
            return pipeline

        except Exception as e:
            logger.error(f"Failed to create processing pipeline: {e}")
            raise ProcessingError(f"Pipeline creation failed: {str(e)}")

    async def execute_transformation(
        self,
        tenant_id: str,
        transformation_id: str,
        input_data: List[Dict[str, Any]],
        transformation_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a data transformation."""
        try:
            transformation_type = transformation_config.get("type")

            if transformation_type == "filter":
                return await self._apply_filter_transformation(input_data, transformation_config)
            elif transformation_type == "aggregate":
                return await self._apply_aggregation_transformation(input_data, transformation_config)
            elif transformation_type == "join":
                return await self._apply_join_transformation(input_data, transformation_config)
            elif transformation_type == "custom":
                return await self._apply_custom_transformation(input_data, transformation_config)
            else:
                raise ProcessingError(f"Unknown transformation type: {transformation_type}")

        except Exception as e:
            logger.error(f"Failed to execute transformation: {e}")
            raise ProcessingError(f"Transformation execution failed: {str(e)}")

    async def calculate_derived_metrics(
        self,
        tenant_id: str,
        base_metrics: List[str],
        calculation_config: Dict[str, Any]
    ) -> List[MetricValue]:
        """Calculate derived metrics from base metrics."""
        try:
            derived_values = []

            # Get base metric values
            base_values = {}
            for metric_id in base_metrics:
                values = self.db.query(MetricValue).filter(
                    MetricValue.tenant_id == tenant_id,
                    MetricValue.metric_id == metric_id
                ).order_by(MetricValue.timestamp.desc()).limit(100).all()
                base_values[metric_id] = values

            # Apply calculation
            calculation_type = calculation_config.get("type")

            if calculation_type == "ratio":
                derived_values = await self._calculate_ratio_metric(base_values, calculation_config)
            elif calculation_type == "difference":
                derived_values = await self._calculate_difference_metric(base_values, calculation_config)
            elif calculation_type == "moving_average":
                derived_values = await self._calculate_moving_average_metric(base_values, calculation_config)
            elif calculation_type == "custom_formula":
                derived_values = await self._calculate_custom_formula_metric(base_values, calculation_config)

            return derived_values

        except Exception as e:
            logger.error(f"Failed to calculate derived metrics: {e}")
            raise ProcessingError(f"Derived metric calculation failed: {str(e)}")

    async def process_real_time_stream(
        self,
        tenant_id: str,
        stream_config: Dict[str, Any],
        data_handler: Callable[[Dict[str, Any]], None]
    ):
        """Process real-time data stream."""
        try:
            buffer_size = stream_config.get("buffer_size", self.config.real_time_buffer_size)
            batch_timeout = stream_config.get("batch_timeout", 5)  # seconds

            buffer = []
            last_flush = utc_now()

            while True:
                # Simulate receiving data (in real implementation, this would be from a message queue)
                await asyncio.sleep(0.1)

                # Check if buffer should be flushed
                now = utc_now()
                if (len(buffer) >= buffer_size or
                    (buffer and (now - last_flush).seconds >= batch_timeout)):

                    # Process buffer
                    await self._process_stream_buffer(tenant_id, buffer, data_handler)
                    buffer.clear()
                    last_flush = now

        except Exception as e:
            logger.error(f"Failed to process real-time stream: {e}")
            raise ProcessingError(f"Stream processing failed: {str(e)}")

    async def _process_single_event(
        self,
        event: AnalyticsEvent,
        processing_rules: Optional[List[Dict[str, Any]]] = None
    ):
        """Process a single event through analytics rules."""
        if not processing_rules:
            return

        for rule in processing_rules:
            rule_type = rule.get("type")

            if rule_type == "metric_generation":
                await self._generate_metrics_from_event(event, rule)
            elif rule_type == "event_enrichment":
                await self._enrich_event(event, rule)
            elif rule_type == "data_validation":
                await self._validate_event_data(event, rule)

    async def _generate_metrics_from_event(self, event: AnalyticsEvent, rule: Dict[str, Any]):
        """Generate metrics from event data."""
        metric_configs = rule.get("metrics", [])

        for metric_config in metric_configs:
            metric_name = metric_config.get("name")
            metric_value = self._extract_metric_value(event, metric_config)

            if metric_value is not None:
                metric_record = MetricValue(
                    tenant_id=event.tenant_id,
                    metric_id=metric_name,  # Would need to resolve to actual metric ID
                    value=metric_value,
                    timestamp=event.timestamp,
                    dimensions=metric_config.get("dimensions", {}),
                    context={"source_event_id": str(event.id)}
                )

                self.db.add(metric_record)

    def _extract_metric_value(self, event: AnalyticsEvent, metric_config: Dict[str, Any]) -> Optional[float]:
        """Extract metric value from event based on configuration."""
        extraction_method = metric_config.get("extraction_method")

        if extraction_method == "property":
            property_name = metric_config.get("property_name")
            return event.properties.get(property_name)
        elif extraction_method == "count":
            return 1.0
        elif extraction_method == "duration":
            start_time = event.properties.get("start_time")
            end_time = event.properties.get("end_time")
            if start_time and end_time:
                return (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds()

        return None

    async def _apply_filter_transformation(
        self,
        input_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filter transformation to data."""
        filter_conditions = config.get("conditions", [])

        filtered_data = []
        for record in input_data:
            if self._evaluate_filter_conditions(record, filter_conditions):
                filtered_data.append(record)

        return filtered_data

    async def _apply_aggregation_transformation(  # noqa: C901
        self,
        input_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply aggregation transformation to data."""
        group_by = config.get("group_by", [])
        aggregations = config.get("aggregations", [])

        # Group data
        groups = {}
        for record in input_data:
            key = tuple(record.get(field) for field in group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        # Apply aggregations
        result = []
        for key, group_records in groups.items():
            aggregated_record = {}

            # Add group by fields
            for i, field in enumerate(group_by):
                aggregated_record[field] = key[i]

            # Apply aggregation functions
            for agg in aggregations:
                field = agg.get("field")
                function = agg.get("function")
                alias = agg.get("alias", f"{function}_{field}")

                values = [r.get(field) for r in group_records if r.get(field) is not None]

                if function == "sum":
                    aggregated_record[alias] = sum(values)
                elif function == "avg":
                    aggregated_record[alias] = sum(values) / len(values) if values else 0
                elif function == "count":
                    aggregated_record[alias] = len(group_records)
                elif function == "min":
                    aggregated_record[alias] = min(values) if values else None
                elif function == "max":
                    aggregated_record[alias] = max(values) if values else None

            result.append(aggregated_record)

        return result

    async def _apply_join_transformation(
        self,
        input_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply join transformation to data."""
        # This would implement data joining logic
        # For now, return input data unchanged
        return input_data

    async def _apply_custom_transformation(
        self,
        input_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply custom transformation to data."""
        # This would execute custom transformation code
        # For now, return input data unchanged
        return input_data

    def _evaluate_filter_conditions(
        self,
        record: Dict[str, Any],
        conditions: List[Dict[str, Any]]
    ) -> bool:
        """Evaluate filter conditions against a record."""
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            record_value = record.get(field)

            if operator == "eq" and record_value != value or operator == "ne" and record_value == value or operator == "gt" and (record_value is None or record_value <= value) or operator == "lt" and (record_value is None or record_value >= value) or operator == "contains" and (record_value is None or value not in str(record_value)):
                return False

        return True

    async def _calculate_ratio_metric(
        self,
        base_values: Dict[str, List[MetricValue]],
        config: Dict[str, Any]
    ) -> List[MetricValue]:
        """Calculate ratio between two metrics."""
        numerator_metric = config.get("numerator")
        denominator_metric = config.get("denominator")

        if numerator_metric not in base_values or denominator_metric not in base_values:
            return []

        # Align timestamps and calculate ratios
        derived_values = []
        # Implementation would align timestamps and calculate ratios

        return derived_values

    async def _calculate_difference_metric(
        self,
        base_values: Dict[str, List[MetricValue]],
        config: Dict[str, Any]
    ) -> List[MetricValue]:
        """Calculate difference between two metrics."""
        # Implementation for difference calculation
        return []

    async def _calculate_moving_average_metric(
        self,
        base_values: Dict[str, List[MetricValue]],
        config: Dict[str, Any]
    ) -> List[MetricValue]:
        """Calculate moving average of a metric."""
        # Implementation for moving average calculation
        return []

    async def _calculate_custom_formula_metric(
        self,
        base_values: Dict[str, List[MetricValue]],
        config: Dict[str, Any]
    ) -> List[MetricValue]:
        """Calculate metric using custom formula."""
        # Implementation for custom formula calculation
        return []

    async def _validate_pipeline_config(self, config: Dict[str, Any]):
        """Validate pipeline configuration."""
        required_fields = ["steps", "source", "target"]

        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Pipeline config missing required field: {field}")

    async def _schedule_pipeline(self, pipeline: Dict[str, Any]):
        """Schedule pipeline for execution."""
        # This would integrate with a job scheduler
        logger.info(f"Pipeline {pipeline['name']} scheduled for execution")

    async def _process_stream_buffer(
        self,
        tenant_id: str,
        buffer: List[Dict[str, Any]],
        data_handler: Callable[[Dict[str, Any]], None]
    ):
        """Process a buffer of stream data."""
        for data in buffer:
            try:
                data_handler(data)
            except Exception as e:
                logger.error(f"Failed to process stream data: {e}")

    def __del__(self):
        """Cleanup executor on service destruction."""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)
