"""
Chaos test runner - CLI and programmatic interface for chaos engineering
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import time
import logging
import argparse

from .chaos_pipeline import (
    ChaosPipelineScheduler, PipelineConfig, ScheduleType, ResilienceLevel
)
from .chaos_scenarios import DotMacChaosScenarios
from .resilience_validator import ResilienceValidator
from .chaos_monitoring import ChaosMonitor

logger = logging.getLogger(__name__)


class ChaosTestRunner:
    """Main interface for running chaos engineering tests"""
    
    def __init__(self):
        self.scheduler = ChaosPipelineScheduler()
        self.chaos_scenarios = DotMacChaosScenarios()
        self.resilience_validator = ResilienceValidator()
        self.chaos_monitor = ChaosMonitor()
        
    async def run_single_scenario(self, scenario_name: str, tenant_id: str = None) -> Dict[str, Any]:
        """Run a single chaos scenario"""
        logger.info(f"Running single scenario: {scenario_name}")
        
        # Start monitoring
        await self.chaos_monitor.start()
        
        try:
            if scenario_name == "tenant_isolation":
                tenant = tenant_id or "test-tenant"
                result = await self.chaos_scenarios.run_tenant_isolation_scenario(tenant)
                
            elif scenario_name == "isp_disruption":
                result = await self.chaos_scenarios.run_isp_service_disruption_scenario()
                
            elif scenario_name == "billing_resilience":
                result = await self.chaos_scenarios.run_billing_resilience_scenario()
                
            elif scenario_name == "database_partition":
                tenants = [tenant_id] if tenant_id else ["tenant-1", "tenant-2"]
                result = await self.chaos_scenarios.run_multi_tenant_database_partition_scenario(tenants)
                
            elif scenario_name == "comprehensive":
                tenant = tenant_id or "test-tenant"
                result = await self.chaos_scenarios.run_comprehensive_resilience_test(tenant)
                
            elif scenario_name == "load_chaos":
                result = await self.chaos_scenarios.run_load_and_chaos_scenario(100, 5)
                
            else:
                raise ValueError(f"Unknown scenario: {scenario_name}")
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "result": result,
                "system_health": self.chaos_monitor.get_system_health()
            }
            
        finally:
            await self.chaos_monitor.stop()
    
    async def run_resilience_validation(self, level: str = "basic") -> Dict[str, Any]:
        """Run resilience validation tests"""
        logger.info(f"Running resilience validation: {level}")
        
        level_enum = ResilienceLevel(level.lower())
        
        await self.chaos_monitor.start()
        
        try:
            results = await self.resilience_validator.validate_resilience(level_enum)
            report = self.resilience_validator.generate_resilience_report(results)
            
            return {
                "validation_level": level,
                "results": [r.__dict__ for r in results],
                "report": report,
                "system_health": self.chaos_monitor.get_system_health()
            }
            
        finally:
            await self.chaos_monitor.stop()
    
    async def create_pipeline(self, config_dict: Dict[str, Any]) -> str:
        """Create a new chaos testing pipeline"""
        
        # Convert schedule_time string to time object if provided
        if "schedule_time" in config_dict and config_dict["schedule_time"]:
            time_str = config_dict["schedule_time"]
            hour, minute = map(int, time_str.split(":"))
            config_dict["schedule_time"] = time(hour, minute)
        
        # Convert string enums
        if "schedule_type" in config_dict:
            config_dict["schedule_type"] = ScheduleType(config_dict["schedule_type"])
        
        if "resilience_level" in config_dict:
            config_dict["resilience_level"] = ResilienceLevel(config_dict["resilience_level"])
        
        config = PipelineConfig(**config_dict)
        pipeline = self.scheduler.register_pipeline(config)
        
        logger.info(f"Created pipeline: {config.name}")
        return config.name
    
    async def start_scheduler(self):
        """Start the pipeline scheduler"""
        await self.scheduler.start_scheduler()
    
    async def stop_scheduler(self):
        """Stop the pipeline scheduler"""
        await self.scheduler.stop_scheduler()
    
    async def trigger_pipeline(self, pipeline_name: str) -> str:
        """Trigger a pipeline manually"""
        return await self.scheduler.trigger_pipeline(pipeline_name)
    
    def get_pipeline_status(self, pipeline_name: str = None) -> Dict[str, Any]:
        """Get pipeline status"""
        if pipeline_name:
            status = self.scheduler.get_pipeline_status(pipeline_name)
            return status if status else {"error": f"Pipeline {pipeline_name} not found"}
        else:
            # Return all pipelines
            return {
                name: self.scheduler.get_pipeline_status(name)
                for name in self.scheduler.pipelines.keys()
            }


async def run_cli_command(args):
    """Run chaos testing from command line"""
    runner = ChaosTestRunner()
    
    if args.command == "scenario":
        result = await runner.run_single_scenario(args.scenario, args.tenant)
        print(json.dumps(result, indent=2, default=str))
        
    elif args.command == "validate":
        result = await runner.run_resilience_validation(args.level)
        print(json.dumps(result, indent=2, default=str))
        
    elif args.command == "pipeline":
        if args.action == "create":
            config = json.loads(args.config)
            pipeline_name = await runner.create_pipeline(config)
            print(f"Created pipeline: {pipeline_name}")
            
        elif args.action == "trigger":
            run_id = await runner.trigger_pipeline(args.name)
            print(f"Triggered pipeline: {args.name}, run ID: {run_id}")
            
        elif args.action == "status":
            status = runner.get_pipeline_status(args.name)
            print(json.dumps(status, indent=2, default=str))
            
        elif args.action == "start":
            await runner.start_scheduler()
            print("Pipeline scheduler started")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                await runner.stop_scheduler()


def create_sample_configs():
    """Create sample configuration files"""
    configs_dir = Path(".dev-artifacts/chaos-configs")
    configs_dir.mkdir(parents=True, exist_ok=True)
    
    # Basic pipeline config
    basic_config = {
        "name": "basic_resilience_daily",
        "description": "Daily basic resilience testing",
        "resilience_level": "basic",
        "schedule_type": "daily",
        "schedule_time": "02:00",
        "target_environment": "staging",
        "max_concurrent_experiments": 2,
        "abort_on_critical_failure": True,
        "max_error_rate": 0.05,
        "max_response_time_p99": 3000,
        "min_availability": 0.99
    }
    
    # Production pipeline config
    production_config = {
        "name": "production_resilience_weekly",
        "description": "Weekly production resilience validation",
        "resilience_level": "production", 
        "schedule_type": "weekly",
        "schedule_time": "01:00",
        "target_environment": "production",
        "max_concurrent_experiments": 1,
        "abort_on_critical_failure": True,
        "max_error_rate": 0.01,
        "max_response_time_p99": 2000,
        "min_availability": 0.999,
        "notification_webhooks": ["https://hooks.slack.com/services/YOUR/WEBHOOK/URL"]
    }
    
    # Comprehensive testing config
    comprehensive_config = {
        "name": "comprehensive_chaos_monthly",
        "description": "Monthly comprehensive chaos engineering",
        "resilience_level": "advanced",
        "schedule_type": "monthly",
        "schedule_time": "00:00",
        "target_environment": "staging",
        "max_concurrent_experiments": 3,
        "abort_on_critical_failure": False,
        "include_scenarios": [
            "tenant_isolation_scenario",
            "isp_service_disruption_scenario",
            "billing_resilience_scenario",
            "multi_tenant_database_partition_scenario"
        ],
        "max_error_rate": 0.15,
        "max_response_time_p99": 10000,
        "min_availability": 0.95
    }
    
    configs = {
        "basic_daily.json": basic_config,
        "production_weekly.json": production_config,
        "comprehensive_monthly.json": comprehensive_config
    }
    
    for filename, config in configs.items():
        config_file = configs_dir / filename
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Created sample config: {config_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="DotMac Chaos Engineering Test Runner")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scenario command
    scenario_parser = subparsers.add_parser("scenario", help="Run a single chaos scenario")
    scenario_parser.add_argument("scenario", choices=[
        "tenant_isolation", "isp_disruption", "billing_resilience", 
        "database_partition", "comprehensive", "load_chaos"
    ], help="Scenario to run")
    scenario_parser.add_argument("--tenant", help="Tenant ID for tenant-specific tests")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Run resilience validation")
    validate_parser.add_argument("--level", default="basic", choices=["basic", "intermediate", "advanced", "production"],
                                help="Validation level")
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Manage chaos pipelines")
    pipeline_subparsers = pipeline_parser.add_subparsers(dest="action", help="Pipeline actions")
    
    # Pipeline create
    create_parser = pipeline_subparsers.add_parser("create", help="Create a new pipeline")
    create_parser.add_argument("config", help="Pipeline configuration JSON")
    
    # Pipeline trigger
    trigger_parser = pipeline_subparsers.add_parser("trigger", help="Trigger a pipeline")
    trigger_parser.add_argument("name", help="Pipeline name")
    
    # Pipeline status
    status_parser = pipeline_subparsers.add_parser("status", help="Get pipeline status")
    status_parser.add_argument("--name", help="Pipeline name (optional, shows all if not specified)")
    
    # Pipeline start scheduler
    pipeline_subparsers.add_parser("start", help="Start pipeline scheduler")
    
    # Sample configs command
    subparsers.add_parser("sample-configs", help="Create sample configuration files")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if args.command == "sample-configs":
        create_sample_configs()
        return
    
    # Run async command
    try:
        asyncio.run(run_cli_command(args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Command failed")
        sys.exit(1)


if __name__ == "__main__":
    main()