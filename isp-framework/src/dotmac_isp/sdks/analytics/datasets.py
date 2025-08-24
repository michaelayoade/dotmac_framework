"""
Datasets SDK for analytics data source management.
"""

import logging
from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError
from ..models.datasets import DataPoint, Dataset, DataSource
from ..models.enums import DataSourceType

logger = logging.getLogger(__name__)


class DatasetsSDK:
    """SDK for analytics datasets operations."""

    def __init__(self, tenant_id: str, db: Session):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.db = db

    async def create_dataset(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new dataset."""
        try:
            dataset = Dataset(
                tenant_id=self.tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                schema_definition=schema_definition or {},
                tags=tags or {},
            )

            self.db.add(dataset)
            self.db.commit()
            self.db.refresh(dataset)

            return {
                "dataset_id": str(dataset.id),
                "name": dataset.name,
                "display_name": dataset.display_name,
                "created_at": dataset.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create dataset: {e}")
            raise AnalyticsError(f"Dataset creation failed: {str(e)}")

    async def create_data_source(
        self,
        name: str,
        source_type: DataSourceType,
        connection_config: Dict[str, Any],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new data source."""
        try:
            data_source = DataSource(
                tenant_id=self.tenant_id,
                name=name,
                source_type=source_type.value,
                connection_config=connection_config,
                description=description,
            )

            self.db.add(data_source)
            self.db.commit()
            self.db.refresh(data_source)

            return {
                "data_source_id": str(data_source.id),
                "name": data_source.name,
                "source_type": data_source.source_type,
                "created_at": data_source.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create data source: {e}")
            raise AnalyticsError(f"Data source creation failed: {str(e)}")

    async def get_datasets(
        self, tags: Optional[Dict[str, str]] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get datasets with filtering."""
        try:
            query = self.db.query(Dataset).filter(
                Dataset.tenant_id == self.tenant_id, Dataset.is_active == True
            )

            if tags:
                for key, value in tags.items():
                    query = query.filter(Dataset.tags[key].astext == value)

            datasets = query.offset(offset).limit(limit).all()

            return [
                {
                    "id": str(dataset.id),
                    "name": dataset.name,
                    "display_name": dataset.display_name,
                    "description": dataset.description,
                    "schema_definition": dataset.schema_definition,
                    "tags": dataset.tags,
                    "created_at": dataset.created_at,
                }
                for dataset in datasets
            ]

        except Exception as e:
            logger.error(f"Failed to get datasets: {e}")
            raise AnalyticsError(f"Datasets retrieval failed: {str(e)}")

    async def add_data_point(
        self,
        dataset_id: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Add a data point to a dataset."""
        try:
            data_point = DataPoint(
                tenant_id=self.tenant_id,
                dataset_id=dataset_id,
                data=data,
                timestamp=timestamp or utc_now(),
            )

            self.db.add(data_point)
            self.db.commit()
            self.db.refresh(data_point)

            return {
                "data_point_id": str(data_point.id),
                "dataset_id": dataset_id,
                "timestamp": data_point.timestamp,
                "created_at": data_point.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add data point: {e}")
            raise AnalyticsError(f"Data point creation failed: {str(e)}")
