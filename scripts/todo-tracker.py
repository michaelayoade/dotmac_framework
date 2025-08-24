#!/usr/bin/env python3
"""
TODO Resolution Tracking Script

This script helps track and manage the systematic resolution of TODOs
across the DotMac platform according to the strategic plan.
"""

import os
import re
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class TodoStatus(Enum):
    PLANNED = "📋 Planned"
    IN_PROGRESS = "🔄 In Progress"
    COMPLETE = "✅ Complete"
    BLOCKED = "⚠️ Blocked"
    CRITICAL = "🔥 Critical"

class Priority(Enum):
    P0_CRITICAL = "P0 - Critical"
    P1_HIGH = "P1 - High"
    P2_MEDIUM = "P2 - Medium"
    P3_LOW = "P3 - Low"

@dataclass
class TodoItem:
    file_path: str
    line_number: int
    description: str
    priority: Priority
    phase: int
    assignee: str
    due_date: str
    status: TodoStatus = TodoStatus.PLANNED
    dependencies: List[str] = None
    created_date: str = None
    completed_date: str = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()

class TodoTracker:
    def __init__(self, project_root: str = "/home/dotmac_framework"):
        self.project_root = project_root
        self.todos_file = os.path.join(project_root, "todos_database.json")
        self.todos: List[TodoItem] = []
        self.load_todos()
    
    def scan_codebase(self) -> List[Tuple[str, int, str]]:
        """Scan codebase for TODO comments."""
        todos = []
        
        # Use ripgrep for fast scanning
        try:
            result = subprocess.run([
                'rg', '--line-number', '--no-heading', 'TODO', 
                self.project_root,
                '--type', 'py', '--type', 'js', '--type', 'ts', '--type', 'tsx'
            ], capture_output=True, text=True)
            
            for line in result.stdout.strip().split('\n'):
                if ':' in line and 'TODO' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path = parts[0].replace(self.project_root, '')
                        line_num = int(parts[1])
                        description = parts[2].strip()
                        todos.append((file_path, line_num, description))
                        
        except Exception as e:
            print(f"Error scanning codebase: {e}")
            
        return todos

    def categorize_todo(self, file_path: str, description: str) -> Tuple[Priority, int, str]:
        """Categorize TODO by file path and description."""
        
        # Critical Priority (P0) - Revenue blocking
        if any(keyword in file_path.lower() for keyword in ['auth', 'billing', 'payment']):
            if 'billing_service.py' in file_path or 'billing_tasks.py' in file_path:
                return Priority.P0_CRITICAL, 1, "Backend Dev"
            if 'ManagementAuthProvider' in file_path:
                return Priority.P0_CRITICAL, 1, "Frontend Dev"
        
        # High Priority (P1) - Platform stability  
        if any(keyword in file_path.lower() for keyword in ['deployment', 'plugin']):
            if 'deployment_service.py' in file_path or 'deployment_tasks.py' in file_path:
                return Priority.P1_HIGH, 2, "DevOps"
            if 'plugin_service.py' in file_path or 'plugin_tasks.py' in file_path:
                return Priority.P1_HIGH, 2, "Backend Dev"
        
        # Medium Priority (P2) - Operational
        if any(keyword in file_path.lower() for keyword in ['monitoring', 'notification']):
            if 'monitoring_service.py' in file_path or 'monitoring_tasks.py' in file_path:
                return Priority.P2_MEDIUM, 3, "DevOps"
            if 'notification_tasks.py' in file_path:
                return Priority.P2_MEDIUM, 3, "Backend Dev"
        
        # Low Priority (P3) - Enhancement
        if 'commissions/page.tsx' in file_path or 'tenant_service.py' in file_path:
            return Priority.P3_LOW, 4, "Frontend Dev"
            
        # Default categorization
        return Priority.P2_MEDIUM, 3, "Backend Dev"

    def generate_due_date(self, priority: Priority, phase: int) -> str:
        """Generate due date based on priority and phase."""
        base_date = datetime.now()
        
        if priority == Priority.P0_CRITICAL:
            due_date = base_date + timedelta(weeks=1)
        elif priority == Priority.P1_HIGH:
            due_date = base_date + timedelta(weeks=2)
        elif priority == Priority.P2_MEDIUM:
            due_date = base_date + timedelta(weeks=4)
        else:  # P3_LOW
            due_date = base_date + timedelta(weeks=6)
            
        return due_date.strftime("%Y-%m-%d")

    def initialize_todos(self):
        """Initialize TODO database from codebase scan."""
        scanned_todos = self.scan_codebase()
        
        for file_path, line_num, description in scanned_todos:
            # Skip if already tracked
            if any(t.file_path == file_path and t.line_number == line_num for t in self.todos):
                continue
                
            priority, phase, assignee = self.categorize_todo(file_path, description)
            due_date = self.generate_due_date(priority, phase)
            
            # Clean description
            clean_desc = description.replace('#', '').replace('TODO:', '').replace('TODO', '').strip()
            
            todo = TodoItem(
                file_path=file_path,
                line_number=line_num,
                description=clean_desc,
                priority=priority,
                phase=phase,
                assignee=assignee,
                due_date=due_date,
                status=TodoStatus.CRITICAL if priority == Priority.P0_CRITICAL else TodoStatus.PLANNED
            )
            
            self.todos.append(todo)
        
        self.save_todos()
        print(f"Initialized {len(scanned_todos)} TODOs")

    def load_todos(self):
        """Load TODOs from JSON file."""
        if os.path.exists(self.todos_file):
            try:
                with open(self.todos_file, 'r') as f:
                    data = json.load(f)
                    self.todos = []
                    for item in data:
                        todo = TodoItem(**item)
                        todo.priority = Priority(item['priority'])
                        todo.status = TodoStatus(item['status'])
                        self.todos.append(todo)
            except Exception as e:
                print(f"Error loading TODOs: {e}")
                self.todos = []

    def save_todos(self):
        """Save TODOs to JSON file."""
        try:
            data = []
            for todo in self.todos:
                item = asdict(todo)
                item['priority'] = todo.priority.value
                item['status'] = todo.status.value
                data.append(item)
                
            with open(self.todos_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving TODOs: {e}")

    def update_todo_status(self, file_path: str, line_number: int, status: TodoStatus):
        """Update the status of a specific TODO."""
        for todo in self.todos:
            if todo.file_path == file_path and todo.line_number == line_number:
                todo.status = status
                if status == TodoStatus.COMPLETE:
                    todo.completed_date = datetime.now().isoformat()
                break
        self.save_todos()

    def get_phase_summary(self) -> Dict:
        """Get summary by phase."""
        phases = {1: "Revenue Protection", 2: "Platform Stability", 
                 3: "Operational Excellence", 4: "Experience Enhancement"}
        
        summary = {}
        for phase_num, phase_name in phases.items():
            phase_todos = [t for t in self.todos if t.phase == phase_num]
            completed = len([t for t in phase_todos if t.status == TodoStatus.COMPLETE])
            
            summary[phase_num] = {
                "name": phase_name,
                "total": len(phase_todos),
                "completed": completed,
                "percentage": round((completed / len(phase_todos)) * 100, 1) if phase_todos else 0,
                "todos": phase_todos
            }
            
        return summary

    def get_priority_summary(self) -> Dict:
        """Get summary by priority."""
        summary = {}
        for priority in Priority:
            priority_todos = [t for t in self.todos if t.priority == priority]
            completed = len([t for t in priority_todos if t.status == TodoStatus.COMPLETE])
            
            summary[priority.value] = {
                "total": len(priority_todos),
                "completed": completed,
                "percentage": round((completed / len(priority_todos)) * 100, 1) if priority_todos else 0,
                "todos": priority_todos
            }
            
        return summary

    def get_overdue_todos(self) -> List[TodoItem]:
        """Get list of overdue TODOs."""
        today = datetime.now().date()
        overdue = []
        
        for todo in self.todos:
            if todo.status != TodoStatus.COMPLETE:
                due_date = datetime.strptime(todo.due_date, "%Y-%m-%d").date()
                if due_date < today:
                    overdue.append(todo)
                    
        return overdue

    def generate_status_report(self) -> str:
        """Generate comprehensive status report."""
        total_todos = len(self.todos)
        completed_todos = len([t for t in self.todos if t.status == TodoStatus.COMPLETE])
        completion_rate = round((completed_todos / total_todos) * 100, 1) if total_todos else 0
        
        phase_summary = self.get_phase_summary()
        priority_summary = self.get_priority_summary()
        overdue_todos = self.get_overdue_todos()
        
        report = f"""
# TODO Resolution Status Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Progress
- **Total TODOs**: {total_todos}
- **Completed**: {completed_todos}
- **Remaining**: {total_todos - completed_todos}
- **Completion Rate**: {completion_rate}%
- **Overdue**: {len(overdue_todos)}

## Progress by Phase
"""
        
        for phase_num, phase_data in phase_summary.items():
            report += f"### Phase {phase_num}: {phase_data['name']}\n"
            report += f"- Progress: {phase_data['completed']}/{phase_data['total']} ({phase_data['percentage']}%)\n"
            report += f"- Status: {'✅ Complete' if phase_data['percentage'] == 100 else '🔄 In Progress' if phase_data['completed'] > 0 else '📋 Not Started'}\n\n"
        
        report += "## Progress by Priority\n"
        for priority, data in priority_summary.items():
            report += f"### {priority}\n"
            report += f"- Progress: {data['completed']}/{data['total']} ({data['percentage']}%)\n\n"
        
        if overdue_todos:
            report += f"## ⚠️ Overdue TODOs ({len(overdue_todos)})\n"
            for todo in overdue_todos[:10]:  # Show first 10
                report += f"- **{todo.file_path}:{todo.line_number}** - {todo.description[:50]}... (Due: {todo.due_date})\n"
        
        return report

    def export_to_markdown(self, filename: str = None):
        """Export TODOs to markdown format."""
        if not filename:
            filename = os.path.join(self.project_root, "TODO_STATUS_EXPORT.md")
            
        report = self.generate_status_report()
        
        with open(filename, 'w') as f:
            f.write(report)
            
        print(f"Status report exported to {filename}")

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TODO Resolution Tracker")
    parser.add_argument('--init', action='store_true', help='Initialize TODO database')
    parser.add_argument('--status', action='store_true', help='Show status report')
    parser.add_argument('--export', action='store_true', help='Export status to markdown')
    parser.add_argument('--phase', type=int, help='Show TODOs for specific phase')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'], help='Show TODOs for specific priority')
    parser.add_argument('--overdue', action='store_true', help='Show overdue TODOs')
    
    args = parser.parse_args()
    
    tracker = TodoTracker()
    
    if args.init:
        tracker.initialize_todos()
        
    elif args.status:
        print(tracker.generate_status_report())
        
    elif args.export:
        tracker.export_to_markdown()
        
    elif args.phase:
        phase_summary = tracker.get_phase_summary()
        if args.phase in phase_summary:
            phase_data = phase_summary[args.phase]
            print(f"\nPhase {args.phase}: {phase_data['name']}")
            print(f"Progress: {phase_data['completed']}/{phase_data['total']} ({phase_data['percentage']}%)")
            print("\nTODOs:")
            for todo in phase_data['todos']:
                print(f"  {todo.status.value} {todo.file_path}:{todo.line_number} - {todo.description}")
                
    elif args.priority:
        priority_map = {'P0': Priority.P0_CRITICAL, 'P1': Priority.P1_HIGH, 
                       'P2': Priority.P2_MEDIUM, 'P3': Priority.P3_LOW}
        priority = priority_map[args.priority]
        todos = [t for t in tracker.todos if t.priority == priority]
        
        print(f"\n{args.priority} TODOs ({len(todos)} total):")
        for todo in todos:
            print(f"  {todo.status.value} {todo.file_path}:{todo.line_number} - {todo.description}")
            
    elif args.overdue:
        overdue = tracker.get_overdue_todos()
        print(f"\nOverdue TODOs ({len(overdue)} total):")
        for todo in overdue:
            print(f"  {todo.status.value} {todo.file_path}:{todo.line_number} - Due: {todo.due_date}")
            
    else:
        # Default: show quick summary
        total = len(tracker.todos)
        completed = len([t for t in tracker.todos if t.status == TodoStatus.COMPLETE])
        print(f"\nTODO Summary: {completed}/{total} completed ({round(completed/total*100, 1) if total else 0}%)")
        print("Use --help for more options")

if __name__ == "__main__":
    main()