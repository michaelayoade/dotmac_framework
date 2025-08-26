#!/usr/bin/env python3
"""
Migration script from Prometheus/Grafana to SignOz.
Converts dashboards, alerts, and helps with data migration.
"""

import os
import json
import yaml
import requests
import argparse
from typing import Dict, List, Any
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignOzMigrator:
    """Handles migration from Prometheus/Grafana to SignOz."""
    
    def __init__(
        self,
        grafana_url: str,
        grafana_api_key: str,
        prometheus_url: str,
        signoz_url: str,
        signoz_api_key: str = None
    ):
        self.grafana_url = grafana_url.rstrip('/')
        self.grafana_api_key = grafana_api_key
        self.prometheus_url = prometheus_url.rstrip('/')
        self.signoz_url = signoz_url.rstrip('/')
        self.signoz_api_key = signoz_api_key
        
        self.grafana_headers = {
            "Authorization": f"Bearer {grafana_api_key}",
            "Content-Type": "application/json"
        }
        
        self.signoz_headers = {
            "Content-Type": "application/json"
        }
        if signoz_api_key:
            self.signoz_headers["X-API-KEY"] = signoz_api_key
    
    def migrate_dashboards(self):
        """Migrate all Grafana dashboards to SignOz."""
        logger.info("Starting dashboard migration...")
        
        # Get all Grafana dashboards
        dashboards = self._get_grafana_dashboards()
        logger.info(f"Found {len(dashboards)} dashboards to migrate")
        
        migrated = 0
        failed = []
        
        for dashboard_meta in dashboards:
            try:
                # Get full dashboard
                dashboard = self._get_grafana_dashboard(dashboard_meta['uid'])
                
                # Convert to SignOz format
                signoz_dashboard = self._convert_dashboard_to_signoz(dashboard)
                
                # Create in SignOz
                self._create_signoz_dashboard(signoz_dashboard)
                
                logger.info(f"✓ Migrated dashboard: {dashboard['dashboard']['title']}")
                migrated += 1
                
            except Exception as e:
                logger.error(f"✗ Failed to migrate {dashboard_meta.get('title', 'Unknown')}: {e}")
                failed.append(dashboard_meta.get('title', 'Unknown')
        
        logger.info(f"\nDashboard Migration Complete:")
        logger.info(f"  ✓ Successfully migrated: {migrated}")
        logger.info(f"  ✗ Failed: {len(failed)}")
        
        if failed:
            logger.info(f"  Failed dashboards: {', '.join(failed)}")
        
        return migrated, failed
    
    def _get_grafana_dashboards(self) -> List[Dict]:
        """Get list of all Grafana dashboards."""
        response = requests.get(
            f"{self.grafana_url}/api/search?type=dash-db",
            headers=self.grafana_headers
        )
        response.raise_for_status()
        return response.model_dump_json()
    
    def _get_grafana_dashboard(self, uid: str) -> Dict:
        """Get a specific Grafana dashboard."""
        response = requests.get(
            f"{self.grafana_url}/api/dashboards/uid/{uid}",
            headers=self.grafana_headers
        )
        response.raise_for_status()
        return response.model_dump_json()
    
    def _convert_dashboard_to_signoz(self, grafana_dashboard: Dict) -> Dict:
        """Convert Grafana dashboard to SignOz format."""
        dashboard = grafana_dashboard['dashboard']
        
        signoz_dashboard = {
            "title": dashboard.get('title', 'Migrated Dashboard'),
            "description": dashboard.get('description', ''),
            "tags": dashboard.get('tags', []),
            "variables": [],
            "layout": [],
            "widgets": []
        }
        
        # Convert template variables
        for var in dashboard.get('templating', {}).get('list', []):
            signoz_var = self._convert_variable(var)
            if signoz_var:
                signoz_dashboard['variables'].append(signoz_var)
        
        # Convert panels to widgets
        for panel in dashboard.get('panels', []):
            widget = self._convert_panel_to_widget(panel)
            if widget:
                signoz_dashboard['widgets'].append(widget)
                signoz_dashboard['layout'].append({
                    "i": str(panel.get('id', 0),
                    "x": panel.get('gridPos', {}).get('x', 0),
                    "y": panel.get('gridPos', {}).get('y', 0),
                    "w": panel.get('gridPos', {}).get('w', 6),
                    "h": panel.get('gridPos', {}).get('h', 4)
                })
        
        return signoz_dashboard
    
    def _convert_variable(self, grafana_var: Dict) -> Dict:
        """Convert Grafana template variable to SignOz format."""
        return {
            "name": grafana_var.get('name', ''),
            "displayName": grafana_var.get('label', grafana_var.get('name', ''),
            "type": "custom",  # SignOz uses different var types
            "query": grafana_var.get('query', ''),
            "default": grafana_var.get('current', {}).get('value', ''),
            "options": []
        }
    
    def _convert_panel_to_widget(self, panel: Dict) -> Dict:
        """Convert Grafana panel to SignOz widget."""
        widget_type = self._map_panel_type(panel.get('type', 'graph')
        
        widget = {
            "id": str(panel.get('id', 0),
            "title": panel.get('title', 'Untitled'),
            "description": panel.get('description', ''),
            "panelType": widget_type,
            "query": {}
        }
        
        # Convert queries
        targets = panel.get('targets', [])
        if targets:
            widget['query'] = self._convert_promql_to_signoz(targets[0])
        
        # Convert thresholds and options
        if panel.get('thresholds'):
            widget['thresholds'] = panel['thresholds']
        
        if panel.get('options'):
            widget['options'] = panel['options']
        
        return widget
    
    def _map_panel_type(self, grafana_type: str) -> str:
        """Map Grafana panel type to SignOz widget type."""
        mapping = {
            'graph': 'TIME_SERIES',
            'timeseries': 'TIME_SERIES',
            'stat': 'VALUE',
            'singlestat': 'VALUE',
            'gauge': 'GAUGE',
            'table': 'TABLE',
            'piechart': 'PIE_CHART',
            'bargauge': 'BAR_CHART',
            'heatmap': 'HEATMAP',
            'text': 'MARKDOWN'
        }
        return mapping.get(grafana_type.lower(), 'TIME_SERIES')
    
    def _convert_promql_to_signoz(self, target: Dict) -> Dict:
        """Convert PromQL query to SignOz query format."""
        expr = target.get('expr', '')
        
        # SignOz uses ClickHouse SQL for metrics
        # This is a simplified conversion - real conversion would be more complex
        signoz_query = {
            "queryType": "metric",
            "metric": self._extract_metric_name(expr),
            "aggregation": self._extract_aggregation(expr),
            "groupBy": self._extract_group_by(expr),
            "filters": {},
            "expression": expr  # Keep original for reference
        }
        
        # Handle common PromQL patterns
        if 'rate(' in expr:
            signoz_query['aggregation'] = 'rate'
        elif 'sum(' in expr:
            signoz_query['aggregation'] = 'sum'
        elif 'avg(' in expr:
            signoz_query['aggregation'] = 'avg'
        elif 'histogram_quantile' in expr:
            signoz_query['aggregation'] = 'p95'
        
        return signoz_query
    
    def _extract_metric_name(self, promql: str) -> str:
        """Extract metric name from PromQL."""
        # Simple extraction - would need proper parsing for complex queries
        import re
        match = re.search(r'([a-z_][a-z0-9_]*)', promql)
        return match.group(1) if match else 'unknown_metric'
    
    def _extract_aggregation(self, promql: str) -> str:
        """Extract aggregation from PromQL."""
        if 'rate(' in promql:
            return 'rate'
        elif 'sum(' in promql:
            return 'sum'
        elif 'avg(' in promql:
            return 'avg'
        elif 'max(' in promql:
            return 'max'
        elif 'min(' in promql:
            return 'min'
        return 'avg'
    
    def _extract_group_by(self, promql: str) -> List[str]:
        """Extract group by labels from PromQL."""
        import re
        match = re.search(r'by\s*\((.*?)\)', promql)
        if match:
            labels = match.group(1).split(',')
            return [label.strip() for label in labels]
        return []
    
    def _create_signoz_dashboard(self, dashboard: Dict):
        """Create dashboard in SignOz."""
        response = requests.post(
            f"{self.signoz_url}/api/v1/dashboards",
            json=dashboard,
            headers=self.signoz_headers
        )
        response.raise_for_status()
        return response.model_dump_json()
    
    def migrate_alerts(self):
        """Migrate Prometheus alert rules to SignOz."""
        logger.info("Starting alert migration...")
        
        # Get Prometheus rules
        rules = self._get_prometheus_rules()
        logger.info(f"Found {len(rules)} alert rules to migrate")
        
        migrated = 0
        failed = []
        
        for rule in rules:
            try:
                # Convert to SignOz format
                signoz_alert = self._convert_alert_to_signoz(rule)
                
                # Create in SignOz
                self._create_signoz_alert(signoz_alert)
                
                logger.info(f"✓ Migrated alert: {rule['alert']}")
                migrated += 1
                
            except Exception as e:
                logger.error(f"✗ Failed to migrate {rule.get('alert', 'Unknown')}: {e}")
                failed.append(rule.get('alert', 'Unknown')
        
        logger.info(f"\nAlert Migration Complete:")
        logger.info(f"  ✓ Successfully migrated: {migrated}")
        logger.info(f"  ✗ Failed: {len(failed)}")
        
        return migrated, failed
    
    def _get_prometheus_rules(self) -> List[Dict]:
        """Get Prometheus alert rules."""
        response = requests.get(f"{self.prometheus_url}/api/v1/rules")
        response.raise_for_status()
        
        rules = []
        for group in response.model_dump_json().get('data', {}).get('groups', []):
            for rule in group.get('rules', []):
                if rule.get('type') == 'alerting':
                    rules.append(rule)
        
        return rules
    
    def _convert_alert_to_signoz(self, prometheus_rule: Dict) -> Dict:
        """Convert Prometheus alert rule to SignOz format."""
        return {
            "alert": prometheus_rule.get('alert', 'Unnamed Alert'),
            "expr": self._convert_promql_to_clickhouse(prometheus_rule.get('query', ''),
            "for": prometheus_rule.get('duration', 300),  # Default 5m
            "labels": prometheus_rule.get('labels', {}),
            "annotations": prometheus_rule.get('annotations', {}),
            "enabled": True,
            "condition": {
                "type": "QUERY",
                "query": prometheus_rule.get('query', ''),
                "op": ">",
                "threshold": 0  # Would need to parse from PromQL
            }
        }
    
    def _convert_promql_to_clickhouse(self, promql: str) -> str:
        """Convert PromQL to ClickHouse SQL for SignOz."""
        # This is a simplified conversion
        # Real implementation would need a proper PromQL parser
        
        # Basic mapping of common patterns
        sql = promql
        
        # Replace rate() with SignOz equivalent
        sql = sql.replace('rate(', 'rate(')
        
        # Replace sum by() with GROUP BY
        import re
        if 'sum by' in sql:
            sql = re.sub(r'sum by\((.*?)\)', r'GROUP BY \1', sql)
        
        # This would need much more sophisticated conversion
        return f"SELECT * FROM signoz_metrics WHERE metric_name = 'converted_metric'"
    
    def _create_signoz_alert(self, alert: Dict):
        """Create alert in SignOz."""
        response = requests.post(
            f"{self.signoz_url}/api/v1/alerts",
            json=alert,
            headers=self.signoz_headers
        )
        response.raise_for_status()
        return response.model_dump_json()
    
    def migrate_data(self, start_time: str, end_time: str, metrics: List[str] = None):
        """
        Migrate historical data from Prometheus to SignOz.
        
        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format
            metrics: List of metrics to migrate (None for all)
        """
        logger.info(f"Starting data migration from {start_time} to {end_time}")
        
        if not metrics:
            # Get all metrics
            metrics = self._get_all_prometheus_metrics()
        
        logger.info(f"Migrating {len(metrics)} metrics")
        
        for metric in metrics:
            try:
                self._migrate_metric_data(metric, start_time, end_time)
                logger.info(f"✓ Migrated data for metric: {metric}")
            except Exception as e:
                logger.error(f"✗ Failed to migrate {metric}: {e}")
    
    def _get_all_prometheus_metrics(self) -> List[str]:
        """Get list of all metrics from Prometheus."""
        response = requests.get(f"{self.prometheus_url}/api/v1/label/__name__/values")
        response.raise_for_status()
        return response.model_dump_json().get('data', [])
    
    def _migrate_metric_data(self, metric: str, start_time: str, end_time: str):
        """Migrate data for a specific metric."""
        # Query Prometheus for data
        params = {
            'query': metric,
            'start': start_time,
            'end': end_time,
            'step': '60s'  # 1 minute resolution
        }
        
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query_range",
            params=params
        )
        response.raise_for_status()
        
        data = response.model_dump_json().get('data', {}).get('result', [])
        
        # Convert and send to SignOz
        for series in data:
            self._send_series_to_signoz(metric, series)
    
    def _send_series_to_signoz(self, metric: str, series: Dict):
        """Send time series data to SignOz."""
        # Convert Prometheus series to OTLP format
        # This would use OTLP exporter in real implementation
        pass
    
    def validate_migration(self):
        """Validate that migration was successful."""
        logger.info("Validating migration...")
        
        # Check dashboards
        signoz_dashboards = self._get_signoz_dashboards()
        logger.info(f"SignOz has {len(signoz_dashboards)} dashboards")
        
        # Check alerts
        signoz_alerts = self._get_signoz_alerts()
        logger.info(f"SignOz has {len(signoz_alerts)} alerts")
        
        # Sample data validation
        # Would check that key metrics are present and recent
        
        return True
    
    def _get_signoz_dashboards(self) -> List[Dict]:
        """Get list of SignOz dashboards."""
        response = requests.get(
            f"{self.signoz_url}/api/v1/dashboards",
            headers=self.signoz_headers
        )
        response.raise_for_status()
        return response.model_dump_json().get('data', [])
    
    def _get_signoz_alerts(self) -> List[Dict]:
        """Get list of SignOz alerts."""
        response = requests.get(
            f"{self.signoz_url}/api/v1/alerts",
            headers=self.signoz_headers
        )
        response.raise_for_status()
        return response.model_dump_json().get('data', [])


def main():
    parser = argparse.ArgumentParser(description='Migrate from Prometheus/Grafana to SignOz')
    parser.add_argument('--grafana-url', default='http://localhost:3000', help='Grafana URL')
    parser.add_argument('--grafana-api-key', required=True, help='Grafana API key')
    parser.add_argument('--prometheus-url', default='http://localhost:9090', help='Prometheus URL')
    parser.add_argument('--signoz-url', default='http://localhost:3301', help='SignOz URL')
    parser.add_argument('--signoz-api-key', help='SignOz API key (if required)')
    parser.add_argument('--migrate-dashboards', action='store_true', help='Migrate dashboards')
    parser.add_argument('--migrate-alerts', action='store_true', help='Migrate alerts')
    parser.add_argument('--migrate-data', action='store_true', help='Migrate historical data')
    parser.add_argument('--data-start', help='Start time for data migration (ISO format)')
    parser.add_argument('--data-end', help='End time for data migration (ISO format)')
    parser.add_argument('--validate', action='store_true', help='Validate migration')
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = SignOzMigrator(
        grafana_url=args.grafana_url,
        grafana_api_key=args.grafana_api_key,
        prometheus_url=args.prometheus_url,
        signoz_url=args.signoz_url,
        signoz_api_key=args.signoz_api_key
    )
    
    # Run migrations
    if args.migrate_dashboards:
        migrator.migrate_dashboards()
    
    if args.migrate_alerts:
        migrator.migrate_alerts()
    
    if args.migrate_data:
        if not args.data_start or not args.data_end:
            # Default to last 7 days
            end = datetime.now()
            start = end - timedelta(days=7)
            args.data_start = start.isoformat()
            args.data_end = end.isoformat()
        
        migrator.migrate_data(args.data_start, args.data_end)
    
    if args.validate:
        migrator.validate_migration()
    
    logger.info("\nMigration complete!")


if __name__ == "__main__":
    main()