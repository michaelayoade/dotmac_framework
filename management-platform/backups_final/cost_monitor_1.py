#!/usr/bin/env python3
"""
Infrastructure Cost Monitoring and Optimization System.

This script provides comprehensive cost tracking, analysis, and optimization
recommendations for the DotMac Management Platform across multiple cloud providers.
"""

import os
import json
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
import asyncio

try:
    import boto3
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.costmanagement import CostManagementClient
    from google.cloud import billing
    import requests
except ImportError as e:
    print(f"Warning: Some cloud provider SDKs not installed: {e}")
    print("Install with: poetry install --with cloud")


@dataclass
class CostMetric:
    """Represents a cost metric for a specific resource."""
    resource_id: str
    resource_name: str
    resource_type: str
    cloud_provider: str
    region: str
    tenant_id: Optional[str]
    service_category: str
    cost_amount: Decimal
    currency: str
    time_period: str
    usage_quantity: Optional[float] = None
    usage_unit: Optional[str] = None
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class CostAlert:
    """Represents a cost alert or anomaly."""
    alert_id: str
    alert_type: str  # budget_exceeded, anomaly_detected, forecast_high
    severity: str    # low, medium, high, critical
    title: str
    description: str
    affected_resources: List[str]
    current_cost: Decimal
    threshold_cost: Optional[Decimal]
    projected_cost: Optional[Decimal]
    time_period: str
    recommendations: List[str]
    created_at: datetime


@dataclass
class OptimizationRecommendation:
    """Represents a cost optimization recommendation."""
    recommendation_id: str
    category: str  # rightsizing, scheduling, purchasing, architecture
    title: str
    description: str
    affected_resources: List[str]
    potential_savings: Decimal
    implementation_effort: str  # low, medium, high
    risk_level: str  # low, medium, high
    implementation_steps: List[str]
    estimated_hours: int


class CloudCostProvider:
    """Base class for cloud provider cost APIs."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
    
    async def get_costs(self, start_date: datetime, end_date: datetime)
                       tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Get cost metrics for the specified time period."""
        raise NotImplementedError
    
    async def get_usage_metrics(self, resource_id: str)
                               start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get usage metrics for a specific resource."""
        raise NotImplementedError


class AWSCostProvider(CloudCostProvider):
    """AWS Cost Explorer integration."""
    
    def __init__(self):
        super().__init__("aws")
        try:
            self.client = boto3.client('ce')  # Cost Explorer
            self.cloudwatch = boto3.client('cloudwatch')
        except Exception as e:
            self.logger.warning(f"Failed to initialize AWS client: {e}")
            self.client = None
    
    async def get_costs(self, start_date: datetime, end_date: datetime)
                       tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Get AWS costs using Cost Explorer API."""
        if not self.client:
            return []
        
        try:
            # Build time period
            time_period = {
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            }
            
            # Build group by criteria
            group_by = [
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'REGION'},
                {'Type': 'TAG', 'Key': 'TenantId'} if tenant_filter else {'Type': 'DIMENSION', 'Key': 'RESOURCE_ID'}
            ]
            
            # Filter by tenant if specified
            filter_expr = None
            if tenant_filter:
                filter_expr = {
                    'Tags': {
                        'Key': 'TenantId',
                        'Values': [tenant_filter]
                    }
                }
            
            response = self.client.get_cost_and_usage()
                TimePeriod=time_period,
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=group_by,
                Filter=filter_expr
            )
            
            costs = []
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                
                for group in result['Groups']:
                    keys = group['Keys']
                    metrics = group['Metrics']
                    
                    service = keys[0] if len(keys) > 0 else 'Unknown'
                    region = keys[1] if len(keys) > 1 else 'Unknown'
                    resource_id = keys[2] if len(keys) > 2 else 'Unknown'
                    
                    cost_amount = Decimal(metrics['BlendedCost']['Amount'])
                    usage_quantity = float(metrics['UsageQuantity']['Amount']) if 'UsageQuantity' in metrics else None
                    
                    if cost_amount > 0:  # Only include non-zero costs
                        costs.append(CostMetric()
                            resource_id=resource_id,
                            resource_name=resource_id,
                            resource_type=service,
                            cloud_provider='aws',
                            region=region,
                            tenant_id=tenant_filter,
                            service_category=service,
                            cost_amount=cost_amount,
                            currency='USD',
                            time_period=date,
                            usage_quantity=usage_quantity,
                            usage_unit=metrics['UsageQuantity']['Unit'] if 'UsageQuantity' in metrics else None
                        )
            
            return costs
            
        except Exception as e:
            self.logger.error(f"Failed to get AWS costs: {e}")
            return []
    
    async def get_usage_metrics(self, resource_id: str)
                               start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get CloudWatch metrics for resource usage analysis."""
        if not self.cloudwatch:
            return {}
        
        try:
            # Get CPU utilization for EC2 instances
            if 'i-' in resource_id:  # EC2 instance
                response = self.cloudwatch.get_metric_statistics()
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'InstanceId', 'Value': resource_id}],
                    StartTime=start_date,
                    EndTime=end_date,
                    Period=3600,  # 1 hour
                    Statistics=['Average', 'Maximum']
                )
                
                return {
                    'cpu_utilization': response['Datapoints'],
                    'avg_cpu': sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints']) if response['Datapoints'] else 0
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get AWS usage metrics for {resource_id}: {e}")
            return {}


class AzureCostProvider(CloudCostProvider):
    """Azure Cost Management integration."""
    
    def __init__(self):
        super().__init__("azure")
        try:
            credential = DefaultAzureCredential()
            self.client = CostManagementClient(credential)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Azure client: {e}")
            self.client = None
    
    async def get_costs(self, start_date: datetime, end_date: datetime)
                       tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Get Azure costs using Cost Management API."""
        if not self.client:
            return []
        
        # Azure cost implementation would go here
        # This is a placeholder implementation
        return []


class GCPCostProvider(CloudCostProvider):
    """Google Cloud Platform cost integration."""
    
    def __init__(self):
        super().__init__("gcp")
        try:
            self.client = billing.CloudBillingClient()
        except Exception as e:
            self.logger.warning(f"Failed to initialize GCP client: {e}")
            self.client = None
    
    async def get_costs(self, start_date: datetime, end_date: datetime)
                       tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Get GCP costs using Cloud Billing API."""
        if not self.client:
            return []
        
        # GCP cost implementation would go here
        # This is a placeholder implementation
        return []


class DigitalOceanCostProvider(CloudCostProvider):
    """DigitalOcean cost integration."""
    
    def __init__(self):
        super().__init__("digitalocean")
        self.api_token = os.getenv('DO_API_TOKEN')
        
    async def get_costs(self, start_date: datetime, end_date: datetime)
                       tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Get DigitalOcean costs using API."""
        if not self.api_token:
            return []
        
        try:
            headers = {'Authorization': f'Bearer {self.api_token}'}
            
            # Get droplets
            response = requests.get('https://api.digitalocean.com/v2/droplets', headers=headers)
            droplets = response.model_dump_json().get('droplets', [])
            
            costs = []
            for droplet in droplets:
                # Calculate cost based on size and runtime
                size_costs = {
                    's-1vcpu-1gb': 5.0,
                    's-1vcpu-2gb': 10.0,
                    's-2vcpu-2gb': 15.0,
                    's-2vcpu-4gb': 20.0,
                    # Add more sizes as needed
                }
                
                monthly_cost = size_costs.get(droplet['size']['slug'], 0)
                daily_cost = monthly_cost / 30  # Approximate daily cost
                
                # Filter by tenant if specified
                tenant_id = None
                for tag in droplet.get('tags', []):
                    if tag.startswith('tenant-'):
                        tenant_id = tag.replace('tenant-', '')
                        break
                
                if tenant_filter and tenant_id != tenant_filter:
                    continue
                
                costs.append(CostMetric()
                    resource_id=str(droplet['id']),
                    resource_name=droplet['name'],
                    resource_type='droplet',
                    cloud_provider='digitalocean',
                    region=droplet['region']['name'],
                    tenant_id=tenant_id,
                    service_category='compute',
                    cost_amount=Decimal(str(daily_cost))
                    currency='USD',
                    time_period=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                    usage_quantity=1,
                    usage_unit='instance'
                )
            
            return costs
            
        except Exception as e:
            self.logger.error(f"Failed to get DigitalOcean costs: {e}")
            return []


class CostMonitor:
    """Main cost monitoring and optimization system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.providers = {
            'aws': AWSCostProvider(),
            'azure': AzureCostProvider(),
            'gcp': GCPCostProvider(),
            'digitalocean': DigitalOceanCostProvider()
        }
        
        # Cost thresholds and budgets
        self.tenant_budgets = {}  # tenant_id -> monthly_budget
        self.service_budgets = {}  # service -> monthly_budget
        self.anomaly_threshold = 0.5  # 50% increase triggers anomaly
    
    async def collect_all_costs(self, start_date: datetime, end_date: datetime)
                               tenant_filter: Optional[str] = None) -> List[CostMetric]:
        """Collect costs from all cloud providers."""
        all_costs = []
        
        tasks = []
        for provider_name, provider in self.providers.items():
            tasks.append(provider.get_costs(start_date, end_date, tenant_filter)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider_name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to get costs from {provider_name}: {result}")
            else:
                all_costs.extend(result)
        
        return all_costs
    
    def analyze_cost_trends(self, costs: List[CostMetric]) -> Dict[str, Any]:
        """Analyze cost trends and patterns."""
        analysis = {
            'total_cost': Decimal('0'),
            'cost_by_provider': {},
            'cost_by_tenant': {},
            'cost_by_service': {},
            'cost_by_region': {},
            'daily_trends': {},
            'growth_rate': 0.0
        }
        
        # Aggregate costs
        for cost in costs:
            analysis['total_cost'] += cost.cost_amount
            
            # By provider
            if cost.cloud_provider not in analysis['cost_by_provider']:
                analysis['cost_by_provider'][cost.cloud_provider] = Decimal('0')
            analysis['cost_by_provider'][cost.cloud_provider] += cost.cost_amount
            
            # By tenant
            tenant_key = cost.tenant_id or 'untagged'
            if tenant_key not in analysis['cost_by_tenant']:
                analysis['cost_by_tenant'][tenant_key] = Decimal('0')
            analysis['cost_by_tenant'][tenant_key] += cost.cost_amount
            
            # By service
            if cost.service_category not in analysis['cost_by_service']:
                analysis['cost_by_service'][cost.service_category] = Decimal('0')
            analysis['cost_by_service'][cost.service_category] += cost.cost_amount
            
            # By region
            if cost.region not in analysis['cost_by_region']:
                analysis['cost_by_region'][cost.region] = Decimal('0')
            analysis['cost_by_region'][cost.region] += cost.cost_amount
            
            # Daily trends
            if cost.time_period not in analysis['daily_trends']:
                analysis['daily_trends'][cost.time_period] = Decimal('0')
            analysis['daily_trends'][cost.time_period] += cost.cost_amount
        
        # Calculate growth rate
        if len(analysis['daily_trends']) > 1:
            dates = sorted(analysis['daily_trends'].keys()
            first_day = analysis['daily_trends'][dates[0]]
            last_day = analysis['daily_trends'][dates[-1]]
            if first_day > 0:
                analysis['growth_rate'] = float((last_day - first_day) / first_day * 100)
        
        return analysis
    
    def detect_cost_anomalies(self, costs: List[CostMetric]) -> List[CostAlert]:
        """Detect cost anomalies and budget overruns."""
        alerts = []
        
        # Group costs by tenant and service for anomaly detection
        tenant_costs = {}
        service_costs = {}
        
        for cost in costs:
            tenant_key = cost.tenant_id or 'untagged'
            if tenant_key not in tenant_costs:
                tenant_costs[tenant_key] = []
            tenant_costs[tenant_key].append(cost)
            
            if cost.service_category not in service_costs:
                service_costs[cost.service_category] = []
            service_costs[cost.service_category].append(cost)
        
        # Check tenant budget overruns
        for tenant_id, tenant_cost_list in tenant_costs.items():
            total_cost = sum(c.cost_amount for c in tenant_cost_list)
            budget = self.tenant_budgets.get(tenant_id, Decimal('10000')  # Default budget
            
            if total_cost > budget:
                alerts.append(CostAlert()
                    alert_id=f"budget_overrun_{tenant_id}_{int(datetime.now(timezone.utc).timestamp())}",
                    alert_type="budget_exceeded",
                    severity="high",
                    title=f"Budget Exceeded for Tenant {tenant_id}",
                    description=f"Tenant {tenant_id} has exceeded budget by ${total_cost - budget:.2f}",
                    affected_resources=[c.resource_id for c in tenant_cost_list],
                    current_cost=total_cost,
                    threshold_cost=budget,
                    projected_cost=None,
                    time_period="monthly",
                    recommendations=[
                        "Review resource usage and optimize underutilized instances",
                        "Consider implementing auto-scaling policies",
                        "Evaluate if reserved instances would provide savings"
                    ],
                    created_at=datetime.now(timezone.utc)
                )
        
        return alerts
    
    def generate_optimization_recommendations(self, costs: List[CostMetric]) -> List[OptimizationRecommendation]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        # Group costs by resource type for analysis
        resource_analysis = {}
        for cost in costs:
            if cost.resource_type not in resource_analysis:
                resource_analysis[cost.resource_type] = []
            resource_analysis[cost.resource_type].append(cost)
        
        # Analyze compute resources for rightsizing opportunities
        if 'EC2-Instance' in resource_analysis:
            ec2_costs = resource_analysis['EC2-Instance']
            high_cost_instances = [c for c in ec2_costs if c.cost_amount > Decimal('100')]
            
            if high_cost_instances:
                recommendations.append(OptimizationRecommendation()
                    recommendation_id=f"rightsizing_ec2_{int(datetime.now(timezone.utc).timestamp())}",
                    category="rightsizing",
                    title="EC2 Instance Rightsizing Opportunity",
                    description="High-cost EC2 instances detected that may benefit from rightsizing",
                    affected_resources=[c.resource_id for c in high_cost_instances],
                    potential_savings=sum(c.cost_amount for c in high_cost_instances) * Decimal('0.3'),
                    implementation_effort="medium",
                    risk_level="low",
                    implementation_steps=[
                        "Analyze CPU and memory utilization over 30 days",
                        "Identify instances with < 50% average utilization",
                        "Test application performance with smaller instance types",
                        "Gradually resize instances during maintenance windows"
                    ],
                    estimated_hours=8
                )
        
        # Look for unused resources
        zero_usage_resources = [c for c in costs if c.usage_quantity == 0]
        if zero_usage_resources:
            recommendations.append(OptimizationRecommendation()
                recommendation_id=f"cleanup_unused_{int(datetime.now(timezone.utc).timestamp())}",
                category="scheduling",
                title="Unused Resource Cleanup",
                description="Resources with zero usage detected",
                affected_resources=[c.resource_id for c in zero_usage_resources],
                potential_savings=sum(c.cost_amount for c in zero_usage_resources),
                implementation_effort="low",
                risk_level="low",
                implementation_steps=[
                    "Verify resources are truly unused",
                    "Check for dependencies or scheduled usage",
                    "Create snapshots/backups before deletion",
                    "Terminate unused resources"
                ],
                estimated_hours=2
            )
        
        return recommendations
    
    async def generate_cost_report(self, days: int = 30, tenant_filter: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive cost report."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        self.logger.info(f"Generating cost report for {days} days (tenant: {tenant_filter or 'all'})")
        
        # Collect costs
        costs = await self.collect_all_costs(start_date, end_date, tenant_filter)
        
        # Analyze trends
        analysis = self.analyze_cost_trends(costs)
        
        # Detect anomalies
        alerts = self.detect_cost_anomalies(costs)
        
        # Generate recommendations
        recommendations = self.generate_optimization_recommendations(costs)
        
        # Build report
        report = {
            'report_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'tenant_filter': tenant_filter,
                'total_resources': len(costs)
            },
            'cost_summary': {
                'total_cost': str(analysis['total_cost']),
                'currency': 'USD',
                'average_daily_cost': str(analysis['total_cost'] / days) if days > 0 else '0',
                'growth_rate_percent': analysis['growth_rate']
            },
            'cost_breakdown': {
                'by_provider': {k: str(v) for k, v in analysis['cost_by_provider'].items()},
                'by_tenant': {k: str(v) for k, v in analysis['cost_by_tenant'].items()},
                'by_service': {k: str(v) for k, v in analysis['cost_by_service'].items()},
                'by_region': {k: str(v) for k, v in analysis['cost_by_region'].items()}
            },
            'daily_trends': {k: str(v) for k, v in analysis['daily_trends'].items()},
            'alerts': [asdict(alert) for alert in alerts],
            'optimization_recommendations': [asdict(rec) for rec in recommendations],
            'potential_savings': str(sum(rec.potential_savings for rec in recommendations)
        )
        
        return report


async def main():
    """Main entry point for cost monitoring script."""
    parser = argparse.ArgumentParser(description='DotMac Cost Monitoring and Optimization')
    parser.add_argument('--analyze', action='store_true', help='Run cost analysis')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--tenant', type=str, help='Filter by specific tenant ID')
    parser.add_argument('--output', type=str, default='cost-report.json', help='Output file path')
    parser.add_argument('--alert-threshold', type=float, default=0.5, help='Anomaly detection threshold')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig()
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting DotMac Cost Monitor")
    
    if args.analyze:
        monitor = CostMonitor()
        monitor.anomaly_threshold = args.alert_threshold
        
        try:
            report = await monitor.generate_cost_report(args.days, args.tenant)
            
            # Save report
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Cost report saved to {args.output}")
            
            # Print summary
            print(f"\nCost Analysis Summary ({args.days} days):")
            print(f"Total Cost: ${report['cost_summary']['total_cost']}")
            print(f"Growth Rate: {report['cost_summary']['growth_rate_percent']:.1f}%")
            print(f"Alerts: {len(report['alerts'])}")
            print(f"Optimization Opportunities: {len(report['optimization_recommendations'])}")
            print(f"Potential Savings: ${report['potential_savings']}")
            
            # Show top cost drivers
            if report['cost_breakdown']['by_service']:
                print("\nTop Cost Drivers:")
                for service, cost in sorted()
                    report['cost_breakdown']['by_service'].items(),
                    key=lambda x: float(x[1]),
                    reverse=True
                )[:5]:
                    print(f"  {service}: ${cost}")
            
        except Exception as e:
            logger.error(f"Cost analysis failed: {e}")
            return 1
    
    else:
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(asyncio.run(main())