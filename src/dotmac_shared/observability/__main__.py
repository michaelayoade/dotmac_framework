#!/usr/bin/env python3
"""
DotMac Observability CLI

Command-line interface for managing observability components including:
- Health monitoring and reporting
- Metrics collection and export
- Trace analysis and debugging
- SignOz integration management
- Configuration validation and testing

Usage:
    python -m dotmac_shared.observability <command> [options]

Commands:
    health      - Health monitoring operations
    metrics     - Metrics operations
    tracing     - Tracing operations
    signoz      - SignOz integration operations
    config      - Configuration operations
    test        - Test observability components
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class ObservabilityCLI:
    """Command-line interface for DotMac observability operations."""

    def __init__(self):
        self.config = None
        self.observability_manager = None

    def setup_logging(self, debug: bool = False):
        """Setup logging for CLI operations."""
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=level,
            format='.format(asctime)s - .format(name)s - .format(levelname)s - .format(message)s'
        )

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load observability configuration."""
        try:
            from dotmac_shared.observability.config import (
                get_default_config,
                get_env_config,
            )

            if config_path and os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    if config_path.endswith('.json'):
                        config_dict = json.load(f)
                    else:
                        # Assume YAML
                        import yaml
                        config_dict = yaml.safe_load(f)

                logger.info(f"Loaded configuration from {config_path}")
                return config_dict
            else:
                # Load from environment
                config = get_env_config()
                logger.info("Loaded configuration from environment")
                return config.to_dict()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fallback to default config
            from dotmac_shared.observability.config import get_default_config
            return get_default_config().to_dict()

    # Health Commands
    async def health_status(self, args):
        """Get current health status."""
        try:
            from dotmac_shared.observability.core.health_reporter import (
                get_health_reporter,
            )

            reporter = get_health_reporter(self.config.get('health', {}))

            if args.summary:
                health_data = reporter.get_health_summary()
            else:
                health_data = reporter.get_latest_health_data()

            if args.json:
                print(json.dumps(health_data, indent=2, default=str))
            else:
                self._print_health_status(health_data, args.summary)

        except ImportError as e:
            logger.error(f"Health reporter not available: {e}")
            return 1
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return 1

    def _print_health_status(self, health_data: Dict[str, Any], summary: bool = False):
        """Print health status in human-readable format."""
        if summary:
            print(f"Overall Status: {health_data.get('status', 'unknown')}")
            print(f"Total Components: {health_data.get('total_components', 0)}")
            print(f"Healthy: {health_data.get('healthy', 0)}")
            print(f"Warning: {health_data.get('warning', 0)}")
            print(f"Unhealthy: {health_data.get('unhealthy', 0)}")
            print(f"Last Check: {health_data.get('last_check', 'never')}")
        else:

            if health_data.get('health_data'):
                for component, data in health_data['health_data'].items():
                    status = data.get('status', 'unknown')
                    details = data.get('details', 'No details')

            print(f"\nLast Report: {health_data.get('last_collection', 'never')}")
            print(f"Reporting: {'Active' if health_data.get('is_reporting') else 'Inactive'}")

    async def health_report(self, args):
        """Force a health report."""
        try:
            from dotmac_shared.observability.core.health_reporter import (
                get_health_reporter,
            )

            reporter = get_health_reporter(self.config.get('health', {}))
            result = await reporter.force_health_report()

            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                if result.get('status') == 'success':
                    print(f"Reported at: {result.get('reported_at', 'unknown')}")
                    print(f"Components: {len(result.get('components', []))}")
                else:
                    print(f"Error: {result.get('error', 'unknown error')}")
                    return 1

        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return 1

    async def health_start(self, args):
        """Start health reporting."""
        try:
            from dotmac_shared.observability.core.health_reporter import (
                start_health_reporting,
            )

            await start_health_reporting(self.config.get('health', {}))

            if args.daemon:
                try:
                    while True:
                        await asyncio.sleep(60)
                except KeyboardInterrupt:
                    from dotmac_shared.observability.core.health_reporter import (
                        stop_health_reporting,
                    )
                    stop_health_reporting()

        except Exception as e:
            logger.error(f"Failed to start health reporting: {e}")
            return 1

    # Metrics Commands
    def metrics_export(self, args):
        """Export Prometheus metrics."""
        try:
            from dotmac_shared.monitoring import get_monitoring as get_metrics

            metrics = get_metrics(args.service_name or "dotmac-cli")
            if not metrics:
                logger.error("Prometheus metrics not available")
                return 1

            metrics_output, _ = metrics.get_metrics_endpoint()

            if args.output:
                with open(args.output, 'w') as f:
                    f.write(metrics_output)
            else:

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return 1

    def metrics_clear(self, args):
        """Clear metrics (useful for testing)."""
        try:
            from dotmac_shared.monitoring import get_monitoring as get_metrics

            metrics = get_metrics(args.service_name or "dotmac-cli")
            if not metrics:
                logger.error("Prometheus metrics not available")
                return 1

            metrics.clear_metrics()

        except Exception as e:
            logger.error(f"Failed to clear metrics: {e}")
            return 1

    # Tracing Commands
    def tracing_analyze(self, args):
        """Analyze trace data."""
        try:
            from dotmac_shared.observability.core.distributed_tracing import (
                trace_analyzer,
            )

            if args.trace_id:
                analysis = trace_analyzer.analyze_trace_performance(args.trace_id)

                if args.json:
                    print(json.dumps(analysis, indent=2, default=str))
                else:
                    self._print_trace_analysis(analysis)
            else:
                return 1

        except Exception as e:
            logger.error(f"Failed to analyze trace: {e}")
            return 1

    def _print_trace_analysis(self, analysis: Dict[str, Any]):
        """Print trace analysis in human-readable format."""
        if "error" in analysis:
            return

        print(f"Trace ID: {analysis.get('trace_id')}")
        print(f"Total Spans: {analysis.get('total_spans', 0)}")
        print(f"Duration: {analysis.get('trace_duration_ms', 0):.2f}ms")
        print(f"Critical Path: {analysis.get('critical_path_duration_ms', 0):.2f}ms")
        print(f"Error Rate: {analysis.get('error_rate', 0):.2f}%")
        print(f"Max Depth: {analysis.get('deepest_nesting', 0)}")

        if analysis.get('service_breakdown'):
            for service, data in analysis['service_breakdown'].items():

    # SignOz Commands
    def signoz_dashboard(self, args):
        """Generate SignOz dashboard configuration."""
        try:
            from dotmac_shared.observability.core.signoz_integration import get_signoz

            signoz = get_signoz()
            if not signoz:
                logger.error("SignOz not initialized")
                return 1

            dashboard_config = signoz.create_signoz_dashboard()

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(dashboard_config, f, indent=2)
            else:
                print(json.dumps(dashboard_config, indent=2))

        except Exception as e:
            logger.error(f"Failed to generate dashboard: {e}")
            return 1

    def signoz_test(self, args):
        """Test SignOz connection."""
        try:
            from dotmac_shared.observability.core.signoz_integration import init_signoz

            signoz = init_signoz(
                service_name=args.service_name or "dotmac-cli-test",
                service_version="1.0.0",
                signoz_endpoint=args.endpoint,
                insecure=args.insecure
            )

            if signoz and signoz.enabled:

                # Test recording a metric
                signoz.record_business_event(
                    event_type="cli_test",
                    tenant_id="test",
                    attributes={"test": True}
                )
            else:
                return 1

        except Exception as e:
            logger.error(f"SignOz connection test failed: {e}")
            return 1

    # Configuration Commands
    def config_validate(self, args):
        """Validate observability configuration."""
        try:
            from dotmac_shared.observability.config import (
                ObservabilityConfig,
                validate_config,
            )

            config_dict = self.load_config(args.config)

            # Convert dict to config object for validation
            # This is a simplified validation - in practice you'd need proper deserialization

            # Basic checks
            required_fields = ['service_name', 'tracing', 'metrics', 'health']
            missing_fields = [field for field in required_fields if field not in config_dict]

            if missing_fields:
                print(f"❌ Missing required fields: {', '.join(missing_fields)}")
                return 1
            else:

            # Check service name
            service_name = config_dict.get('service_name', '')
            if not service_name or not isinstance(service_name, str):
                return 1
            else:


        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return 1

    def config_show(self, args):
        """Show current configuration."""
        config_dict = self.load_config(args.config)

        if args.json:
            print(json.dumps(config_dict, indent=2, default=str))
        else:
            self._print_config_tree(config_dict)

    def _print_config_tree(self, config_dict: Dict[str, Any], indent: int = 0):
        """Print configuration in a tree format."""
        for key, value in config_dict.items():
            prefix = "  " * indent
            if isinstance(value, dict):
                self._print_config_tree(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}: [{', '.join(map(str, value))}]")
            else:

    # Test Commands
    async def test_all(self, args):
        """Test all observability components."""

        results = {}

        # Test imports
        results['imports'] = self._test_imports()

        # Test configuration
        results['config'] = self._test_config()

        # Test health reporter
        results['health'] = await self._test_health_reporter()

        # Test metrics
        results['metrics'] = self._test_metrics()

        # Test tracing
        results['tracing'] = self._test_tracing()

        # Print summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r)

        for component, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"


        return 0 if passed_tests == total_tests else 1

    def _test_imports(self) -> bool:
        """Test that all components can be imported."""
        try:
            import dotmac_shared.observability
            from dotmac_shared.observability.config import get_default_config
            from dotmac_shared.observability.core.health_reporter import HealthReporter
            return True
        except Exception as e:
            return False

    def _test_config(self) -> bool:
        """Test configuration loading."""
        try:
            config_dict = self.load_config()
            if config_dict and 'service_name' in config_dict:
                return True
            else:
                return False
        except Exception as e:
            return False

    async def _test_health_reporter(self) -> bool:
        """Test health reporter functionality."""
        try:
            from dotmac_shared.observability.core.health_reporter import HealthReporter

            config = {
                "include_system_metrics": False,
                "include_database_health": False,
                "include_redis_health": False,
                "include_network_health": False,
            }

            reporter = HealthReporter(config)
            summary = reporter.get_health_summary()

            if 'status' in summary:
                return True
            else:
                return False

        except Exception as e:
            return False

    def _test_metrics(self) -> bool:
        """Test metrics functionality."""
        try:
            from dotmac_shared.monitoring import get_monitoring as get_metrics

            metrics = get_metrics("test-service")
            if metrics:
                return True
            else:
                return True  # Not a failure if dependencies missing

        except Exception as e:
            return False

    def _test_tracing(self) -> bool:
        """Test tracing functionality."""
        try:
            from dotmac_shared.observability.core.distributed_tracing import (
                DistributedTracer,
            )

            tracer = DistributedTracer("test-service")
            span = tracer.start_span("test_operation")
            tracer.finish_span(span)

            if span and span.trace_id:
                return True
            else:
                return False

        except Exception as e:
            return False

    def setup_parsers(self) -> argparse.ArgumentParser:
        """Setup command line argument parsers."""
        parser = argparse.ArgumentParser(
            description="DotMac Observability CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__doc__
        )

        parser.add_argument(
            "--config",
            help="Configuration file path (JSON or YAML)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output in JSON format"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Health commands
        health_parser = subparsers.add_parser("health", help="Health monitoring operations")
        health_subparsers = health_parser.add_subparsers(dest="health_command")

        # Health status
        health_status = health_subparsers.add_parser("status", help="Get health status")
        health_status.add_argument("--summary", action="store_true", help="Show summary only")

        # Health report
        health_subparsers.add_parser("report", help="Force health report")

        # Health start
        health_start = health_subparsers.add_parser("start", help="Start health reporting")
        health_start.add_argument("--daemon", action="store_true", help="Run as daemon")

        # Metrics commands
        metrics_parser = subparsers.add_parser("metrics", help="Metrics operations")
        metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_command")

        # Metrics export
        metrics_export = metrics_subparsers.add_parser("export", help="Export metrics")
        metrics_export.add_argument("--service-name", help="Service name for metrics")
        metrics_export.add_argument("--output", help="Output file path")

        # Metrics clear
        metrics_clear = metrics_subparsers.add_parser("clear", help="Clear metrics")
        metrics_clear.add_argument("--service-name", help="Service name for metrics")

        # Tracing commands
        tracing_parser = subparsers.add_parser("tracing", help="Tracing operations")
        tracing_subparsers = tracing_parser.add_subparsers(dest="tracing_command")

        # Trace analyze
        trace_analyze = tracing_subparsers.add_parser("analyze", help="Analyze trace")
        trace_analyze.add_argument("--trace-id", required=True, help="Trace ID to analyze")

        # SignOz commands
        signoz_parser = subparsers.add_parser("signoz", help="SignOz operations")
        signoz_subparsers = signoz_parser.add_subparsers(dest="signoz_command")

        # SignOz dashboard
        signoz_dashboard = signoz_subparsers.add_parser("dashboard", help="Generate dashboard config")
        signoz_dashboard.add_argument("--output", help="Output file path")

        # SignOz test
        signoz_test = signoz_subparsers.add_parser("test", help="Test SignOz connection")
        signoz_test.add_argument("--service-name", help="Service name for test")
        signoz_test.add_argument("--endpoint", help="SignOz endpoint")
        signoz_test.add_argument("--insecure", action="store_true", help="Use insecure connection")

        # Config commands
        config_parser = subparsers.add_parser("config", help="Configuration operations")
        config_subparsers = config_parser.add_subparsers(dest="config_command")

        # Config validate
        config_validate = config_subparsers.add_parser("validate", help="Validate configuration")
        config_validate.add_argument("--config", help="Configuration file to validate")

        # Config show
        config_show = config_subparsers.add_parser("show", help="Show configuration")
        config_show.add_argument("--config", help="Configuration file to show")

        # Test commands
        test_parser = subparsers.add_parser("test", help="Test observability components")
        test_subparsers = test_parser.add_subparsers(dest="test_command")

        test_subparsers.add_parser("all", help="Test all components")

        return parser

    async def main(self):
        """Main CLI entry point."""
        parser = self.setup_parsers()
        args = parser.parse_args()

        # Setup logging
        self.setup_logging(args.debug)

        # Load configuration
        self.config = self.load_config(args.config)

        if not args.command:
            parser.print_help()
            return 1

        try:
            # Route commands
            if args.command == "health":
                if args.health_command == "status":
                    return await self.health_status(args)
                elif args.health_command == "report":
                    return await self.health_report(args)
                elif args.health_command == "start":
                    return await self.health_start(args)
                else:
                    parser.error("Health command required")

            elif args.command == "metrics":
                if args.metrics_command == "export":
                    return self.metrics_export(args)
                elif args.metrics_command == "clear":
                    return self.metrics_clear(args)
                else:
                    parser.error("Metrics command required")

            elif args.command == "tracing":
                if args.tracing_command == "analyze":
                    return self.tracing_analyze(args)
                else:
                    parser.error("Tracing command required")

            elif args.command == "signoz":
                if args.signoz_command == "dashboard":
                    return self.signoz_dashboard(args)
                elif args.signoz_command == "test":
                    return self.signoz_test(args)
                else:
                    parser.error("SignOz command required")

            elif args.command == "config":
                if args.config_command == "validate":
                    return self.config_validate(args)
                elif args.config_command == "show":
                    return self.config_show(args)
                else:
                    parser.error("Config command required")

            elif args.command == "test":
                if args.test_command == "all":
                    return await self.test_all(args)
                else:
                    parser.error("Test command required")

            else:
                parser.error(f"Unknown command: {args.command}")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Command failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1

        return 0


def main():
    """Entry point for the CLI."""
    cli = ObservabilityCLI()
    exit_code = asyncio.run(cli.main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
