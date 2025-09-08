#!/usr/bin/env python3
"""
Implementation Progress Tracker for DotMac Framework Gap Resolution
"""
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class ImplementationTracker:
    """Track implementation progress across all phases."""
    
    def __init__(self):
        self.progress_file = Path(".dev-artifacts/implementation_progress.json")
        
        # Define phase requirements first (needed for validation)
        self._setup_phase_requirements()
        
        # Then load progress
        self.load_progress()
    
    def _setup_phase_requirements(self):
        """Setup phase requirements structure."""
        self.phase_requirements = {
            "Phase 1": {
                "name": "Critical Security Fixes",
                "duration_weeks": 2,
                "tasks": [
                    "remove_hardcoded_secrets",
                    "fix_sql_injection", 
                    "implement_input_validation",
                    "setup_security_pipeline"
                ],
                "success_metrics": {
                    "hardcoded_secrets": 0,
                    "sql_injection_vulns": 0,
                    "validated_endpoints_percent": 100,
                    "security_scan_failures": 0
                }
            },
            "Phase 2": {
                "name": "Architecture Standardization", 
                "duration_weeks": 4,
                "tasks": [
                    "create_base_repository",
                    "create_base_service",
                    "migrate_repositories",
                    "migrate_services",
                    "standardize_middleware"
                ],
                "success_metrics": {
                    "repositories_using_base_percent": 90,
                    "services_using_base_percent": 90,
                    "middleware_standardized": True,
                    "bare_except_clauses": 0
                }
            },
            "Phase 3": {
                "name": "Testing & Observability",
                "duration_weeks": 4, 
                "tasks": [
                    "setup_integration_tests",
                    "implement_health_checks",
                    "setup_monitoring_dashboard",
                    "optimize_n_plus_one_queries",
                    "fix_async_patterns"
                ],
                "success_metrics": {
                    "test_coverage_percent": 70,
                    "health_check_coverage_percent": 100,
                    "monitoring_dashboard_operational": True,
                    "n_plus_one_issues_fixed": 130
                }
            },
            "Phase 4": {
                "name": "Performance & Documentation",
                "duration_weeks": 3,
                "tasks": [
                    "establish_performance_baseline",
                    "refactor_complex_functions", 
                    "complete_api_documentation",
                    "create_developer_guides"
                ],
                "success_metrics": {
                    "api_response_time_p95_ms": 100,
                    "functions_over_50_lines": 200,  # Reduced from 915
                    "api_functions_documented_percent": 100,
                    "developer_setup_time_minutes": 5
                }
            }
        }
    
    def load_progress(self):
        """Load progress from file or initialize."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    self.progress = json.load(f)
                    
                # Basic schema validation
                self._validate_progress_schema()
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Invalid progress file format: {e}")
                print("Initializing fresh progress tracking...")
                self._initialize_progress()
        else:
            self._initialize_progress()
    
    def _initialize_progress(self):
        """Initialize fresh progress structure."""
        self.progress = {
            "started_at": datetime.now().isoformat(),
            "phases": {}
        }
    
    def _validate_progress_schema(self):
        """Validate progress file has expected structure."""
        required_keys = ["started_at", "phases"]
        for key in required_keys:
            if key not in self.progress:
                raise KeyError(f"Missing required key: {key}")
        
        # Validate phase structure
        for phase_name, phase_data in self.progress["phases"].items():
            if phase_name not in self.phase_requirements:
                print(f"Warning: Unknown phase in progress file: {phase_name}")
            
            if not isinstance(phase_data, dict):
                raise ValueError(f"Phase {phase_name} data must be a dict")
            
            if "tasks" in phase_data and not isinstance(phase_data["tasks"], dict):
                raise ValueError(f"Phase {phase_name} tasks must be a dict")
    
    def save_progress(self):
        """Save progress to file."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def start_phase(self, phase: str):
        """Mark phase as started."""
        if phase not in self.progress["phases"]:
            self.progress["phases"][phase] = {
                "started_at": datetime.now().isoformat(),
                "status": "in_progress",
                "tasks": {},
                "metrics": {}
            }
        self.save_progress()
        
        print(f"✅ Started {phase}: {self.phase_requirements[phase]['name']}")
        print(f"   Duration: {self.phase_requirements[phase]['duration_weeks']} weeks")
        print(f"   Tasks: {len(self.phase_requirements[phase]['tasks'])}")
    
    def record_task_completion(
        self,
        phase: str,
        task_id: str,
        completion_details: Dict[str, Any]
    ):
        """Record task completion with validation."""
        if phase not in self.progress["phases"]:
            self.start_phase(phase)
        
        self.progress["phases"][phase]["tasks"][task_id] = {
            "completed_at": datetime.now().isoformat(),
            "details": completion_details,
            "validated": False
        }
        
        self.save_progress()
        print(f"✅ Completed task: {task_id} in {phase}")
    
    def update_metrics(self, phase: str, metrics: Dict[str, Any]):
        """Update phase metrics."""
        if phase not in self.progress["phases"]:
            self.start_phase(phase)
            
        self.progress["phases"][phase]["metrics"].update(metrics)
        self.progress["phases"][phase]["last_metric_update"] = datetime.now().isoformat()
        self.save_progress()
        
        print(f"📊 Updated metrics for {phase}:")
        for metric, value in metrics.items():
            print(f"   {metric}: {value}")
    
    def validate_phase_completion(self, phase: str) -> bool:
        """Validate that phase requirements are met."""
        if phase not in self.progress["phases"]:
            return False
            
        phase_data = self.progress["phases"][phase]
        requirements = self.phase_requirements[phase]
        
        # Check task completion
        required_tasks = set(requirements["tasks"])
        completed_tasks = set(phase_data["tasks"].keys())
        missing_tasks = required_tasks - completed_tasks
        
        if missing_tasks:
            print(f"❌ {phase} validation failed - Missing tasks: {missing_tasks}")
            return False
        
        # Check success metrics
        current_metrics = phase_data.get("metrics", {})
        required_metrics = requirements["success_metrics"]
        
        failed_metrics = []
        for metric, target_value in required_metrics.items():
            current_value = current_metrics.get(metric)
            
            if current_value is None:
                failed_metrics.append(f"{metric}: not measured")
                continue
                
            # Different validation logic for different metric types
            if isinstance(target_value, bool):
                if current_value != target_value:
                    failed_metrics.append(f"{metric}: {current_value} (expected: {target_value})")
            elif isinstance(target_value, int):
                if "percent" in metric:
                    if current_value < target_value:
                        failed_metrics.append(f"{metric}: {current_value}% (target: ≥{target_value}%)")
                elif "time_ms" in metric or "time_minutes" in metric:
                    if current_value > target_value:
                        failed_metrics.append(f"{metric}: {current_value} (target: ≤{target_value})")
                else:  # For counts like issues_fixed
                    if current_value < target_value:
                        failed_metrics.append(f"{metric}: {current_value} (target: ≥{target_value})")
        
        if failed_metrics:
            print(f"❌ {phase} validation failed - Metric failures:")
            for failure in failed_metrics:
                print(f"   {failure}")
            return False
        
        # Mark phase as completed
        self.progress["phases"][phase]["status"] = "completed"
        self.progress["phases"][phase]["completed_at"] = datetime.now().isoformat()
        self.save_progress()
        
        print(f"✅ {phase} validation passed - All requirements met!")
        return True
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall implementation progress percentage using weighted average."""
        total_weight = 0
        weighted_progress = 0
        
        for phase_name, phase_requirements in self.phase_requirements.items():
            weight = phase_requirements["duration_weeks"]  # Weight by duration
            total_weight += weight
            
            phase_status = self._get_phase_status(phase_name)
            phase_progress = phase_status["progress_percent"] / 100  # Convert to 0-1
            
            weighted_progress += phase_progress * weight
        
        if total_weight == 0:
            return 0.0
            
        return (weighted_progress / total_weight) * 100
    
    def _get_phase_status(self, phase: str) -> Dict[str, Any]:
        """Get detailed status for a phase."""
        if phase not in self.progress["phases"]:
            return {
                "status": "not_started",
                "progress_percent": 0,
                "tasks_completed": 0,
                "tasks_total": len(self.phase_requirements[phase]["tasks"])
            }
        
        phase_data = self.progress["phases"][phase]
        requirements = self.phase_requirements[phase]
        
        completed_tasks = len(phase_data["tasks"])
        total_tasks = len(requirements["tasks"])
        progress_percent = (completed_tasks / total_tasks) * 100
        
        return {
            "status": phase_data.get("status", "in_progress"),
            "started_at": phase_data.get("started_at"),
            "completed_at": phase_data.get("completed_at"),
            "progress_percent": progress_percent,
            "tasks_completed": completed_tasks,
            "tasks_total": total_tasks,
            "metrics": phase_data.get("metrics", {}),
            "next_tasks": [
                task for task in requirements["tasks"] 
                if task not in phase_data["tasks"]
            ]
        }
    
    def generate_progress_report(self) -> Dict[str, Any]:
        """Generate comprehensive progress report."""
        overall_progress = self._calculate_overall_progress()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "overall_progress_percent": overall_progress,
            "estimated_completion_date": self._estimate_completion_date(),
            "phase_status": {},
            "critical_blockers": [],
            "next_actions": [],
            "risk_assessment": self._assess_risks()
        }
        
        for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
            report["phase_status"][phase] = self._get_phase_status(phase)
            
            # Identify blockers and next actions
            phase_status = report["phase_status"][phase]
            if phase_status["status"] == "in_progress" and phase_status["next_tasks"]:
                report["next_actions"].extend([
                    f"{phase}: {task}" for task in phase_status["next_tasks"][:2]
                ])
        
        return report
    
    def _estimate_completion_date(self) -> str:
        """Estimate project completion date based on current progress."""
        if not self.progress["phases"]:
            # No progress yet, estimate from start date
            start_date = datetime.fromisoformat(self.progress["started_at"])
            total_weeks = sum(req["duration_weeks"] for req in self.phase_requirements.values())
            completion_date = start_date + timedelta(weeks=total_weeks)
            return completion_date.isoformat()
        
        # Calculate based on actual progress
        current_date = datetime.now()
        
        # Find current phase
        current_phase = None
        for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
            phase_data = self.progress["phases"].get(phase_name, {})
            if phase_data.get("status") != "completed":
                current_phase = phase_name
                break
        
        if current_phase is None:
            # All phases completed
            return datetime.now().isoformat()
        
        # Estimate remaining time
        remaining_weeks = 0
        for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
            if phase_name == current_phase:
                # Add remaining time for current phase
                phase_data = self.progress["phases"].get(phase_name, {})
                if phase_data:
                    started_at = datetime.fromisoformat(phase_data["started_at"])
                    weeks_elapsed = (current_date - started_at).days / 7
                    phase_duration = self.phase_requirements[phase_name]["duration_weeks"]
                    remaining_weeks += max(0, phase_duration - weeks_elapsed)
                else:
                    remaining_weeks += self.phase_requirements[phase_name]["duration_weeks"]
            elif self.progress["phases"].get(phase_name, {}).get("status") != "completed":
                # Add full duration for future phases
                remaining_weeks += self.phase_requirements[phase_name]["duration_weeks"]
        
        completion_date = current_date + timedelta(weeks=remaining_weeks)
        return completion_date.isoformat()
    
    def _assess_risks(self) -> Dict[str, List[str]]:
        """Assess current implementation risks."""
        risks = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        # Check for overdue phases
        for phase_name, phase_data in self.progress["phases"].items():
            if phase_data.get("status") == "in_progress":
                started_at = datetime.fromisoformat(phase_data["started_at"])
                expected_duration = self.phase_requirements[phase_name]["duration_weeks"]
                weeks_elapsed = (datetime.now() - started_at).days / 7
                
                if weeks_elapsed > expected_duration * 1.5:
                    risks["high"].append(f"{phase_name} significantly overdue ({weeks_elapsed:.1f} weeks elapsed, {expected_duration} expected)")
                elif weeks_elapsed > expected_duration:
                    risks["medium"].append(f"{phase_name} slightly overdue ({weeks_elapsed:.1f} weeks elapsed, {expected_duration} expected)")
        
        # Check for incomplete critical security fixes
        phase1_data = self.progress["phases"].get("Phase 1", {})
        if phase1_data.get("status") != "completed":
            critical_tasks = ["remove_hardcoded_secrets", "fix_sql_injection"]
            missing_critical = [
                task for task in critical_tasks 
                if task not in phase1_data.get("tasks", {})
            ]
            if missing_critical:
                risks["high"].extend([
                    f"Critical security task incomplete: {task}" for task in missing_critical
                ])
        
        return risks
    
    def print_status_summary(self):
        """Print a formatted status summary."""
        report = self.generate_progress_report()
        
        print("\n" + "=" * 60)
        print("DOTMAC FRAMEWORK IMPLEMENTATION STATUS")
        print("=" * 60)
        print(f"Overall Progress: {report['overall_progress_percent']:.1f}%")
        print(f"Estimated Completion: {report['estimated_completion_date'][:10]}")
        print()
        
        for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
            status = report["phase_status"][phase_name]
            status_icon = {
                "completed": "✅",
                "in_progress": "🚧", 
                "not_started": "⏳"
            }.get(status["status"], "❓")
            
            print(f"{status_icon} {phase_name}: {status['progress_percent']:.0f}% ({status['tasks_completed']}/{status['tasks_total']} tasks)")
        
        print()
        
        # Show next actions
        if report["next_actions"]:
            print("🎯 NEXT ACTIONS:")
            for action in report["next_actions"][:5]:
                print(f"   • {action}")
            print()
        
        # Show risks
        if report["risk_assessment"]["high"]:
            print("🚨 HIGH RISKS:")
            for risk in report["risk_assessment"]["high"]:
                print(f"   • {risk}")
            print()
        
        if report["risk_assessment"]["medium"]:
            print("⚠️  MEDIUM RISKS:")  
            for risk in report["risk_assessment"]["medium"]:
                print(f"   • {risk}")
            print()


def main():
    """Main CLI interface for progress tracking."""
    import argparse
    import sys
    
    tracker = ImplementationTracker()
    valid_phases = list(tracker.phase_requirements.keys())
    
    parser = argparse.ArgumentParser(
        description="DotMac Framework Implementation Progress Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {sys.argv[0]} status                                    # Show current status
  {sys.argv[0]} start-phase "Phase 1"                     # Start Phase 1
  {sys.argv[0]} complete-task "Phase 1" fix_sql_injection # Mark task complete
  {sys.argv[0]} update-metrics "Phase 1" sql_injection_vulns=0 hardcoded_secrets=0
  {sys.argv[0]} validate-phase "Phase 1"                  # Validate phase completion
  {sys.argv[0]} report                                    # Generate JSON report

Valid phases: {', '.join(valid_phases)}
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command (default)
    subparsers.add_parser('status', help='Show current implementation status')
    
    # Start phase command
    start_parser = subparsers.add_parser('start-phase', help='Start a new phase')
    start_parser.add_argument('phase', choices=valid_phases, help='Phase to start')
    
    # Complete task command
    task_parser = subparsers.add_parser('complete-task', help='Mark task as completed')
    task_parser.add_argument('phase', choices=valid_phases, help='Phase containing the task')
    task_parser.add_argument('task', help='Task ID to mark complete')
    task_parser.add_argument('--details', help='JSON string with completion details')
    
    # Update metrics command
    metrics_parser = subparsers.add_parser('update-metrics', help='Update phase metrics')
    metrics_parser.add_argument('phase', choices=valid_phases, help='Phase to update')
    metrics_parser.add_argument('metrics', nargs='+', help='Metrics in key=value format')
    
    # Validate phase command
    validate_parser = subparsers.add_parser('validate-phase', help='Validate phase completion')
    validate_parser.add_argument('phase', choices=valid_phases, help='Phase to validate')
    
    # Report command
    subparsers.add_parser('report', help='Generate detailed JSON report')
    
    args = parser.parse_args()
    
    # Default to status if no command
    command = args.command or 'status'
    
    try:
        if command == "status":
            tracker.print_status_summary()
            sys.exit(0)
            
        elif command == "start-phase":
            tracker.start_phase(args.phase)
            sys.exit(0)
        
        elif command == "complete-task":
            details = {"manual_completion": True}
            if args.details:
                try:
                    import json
                    details.update(json.loads(args.details))
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON in --details: {args.details}")
            
            # Validate task exists for phase
            valid_tasks = tracker.phase_requirements[args.phase]["tasks"]
            if args.task not in valid_tasks:
                print(f"Error: Task '{args.task}' not found in {args.phase}")
                print(f"Valid tasks: {', '.join(valid_tasks)}")
                sys.exit(1)
            
            tracker.record_task_completion(args.phase, args.task, details)
            sys.exit(0)
        
        elif command == "update-metrics":
            metrics = {}
            for metric_arg in args.metrics:
                if "=" not in metric_arg:
                    print(f"Error: Invalid metric format '{metric_arg}'. Use key=value")
                    sys.exit(1)
                    
                key, value = metric_arg.split("=", 1)
                
                # Improved metric parsing
                try:
                    # Handle percentages
                    if value.endswith('%'):
                        metrics[key] = float(value[:-1])
                    # Handle booleans
                    elif value.lower() in ("true", "false", "yes", "no", "on", "off"):
                        metrics[key] = value.lower() in ("true", "yes", "on")
                    # Handle negative numbers
                    elif value.startswith('-') and value[1:].replace('.', '').isdigit():
                        if '.' in value:
                            metrics[key] = float(value)
                        else:
                            metrics[key] = int(value)
                    # Handle positive numbers
                    elif value.replace('.', '').replace(',', '').isdigit():
                        # Remove commas for large numbers
                        clean_value = value.replace(',', '')
                        if '.' in clean_value:
                            metrics[key] = float(clean_value)
                        else:
                            metrics[key] = int(clean_value)
                    else:
                        # Keep as string
                        metrics[key] = value
                        
                except ValueError as e:
                    print(f"Warning: Could not parse metric '{key}={value}': {e}")
                    metrics[key] = value
                    
            tracker.update_metrics(args.phase, metrics)
            sys.exit(0)
        
        elif command == "validate-phase":
            success = tracker.validate_phase_completion(args.phase)
            sys.exit(0 if success else 1)
        
        elif command == "report":
            report = tracker.generate_progress_report()
            print(json.dumps(report, indent=2))
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()