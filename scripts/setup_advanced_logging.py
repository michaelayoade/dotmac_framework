#!/usr/bin/env python3
"""
Advanced Logging and Audit Trail Setup for DotMac Framework
Sets up comprehensive logging using existing infrastructure
"""

import subprocess
import json
import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any

class AdvancedLoggingSetup:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.production_dir = self.project_root / "deployment" / "production"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def run_command(self, command: str, description: str = "") -> bool:
        """Execute command with proper logging"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would run: {command}")
            return True
        
        self.logger.info(f"Executing: {description or command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return True
            else:
                self.logger.error(f"Command failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Exception: {e}")
            return False

    def create_logging_config(self):
        """Create centralized logging configuration"""
        self.logger.info("📝 Creating advanced logging configuration...")
        
        # Python logging configuration
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s"
                },
                "audit": {
                    "format": "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
                },
                "json": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                },
                "file_info": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": "/opt/dotmac/logs/application.log",
                    "maxBytes": 50000000,  # 50MB
                    "backupCount": 10
                },
                "file_error": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": "/opt/dotmac/logs/errors.log",
                    "maxBytes": 50000000,  # 50MB
                    "backupCount": 5
                },
                "audit_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "INFO",
                    "formatter": "audit",
                    "filename": "/opt/dotmac/logs/audit.log",
                    "when": "midnight",
                    "backupCount": 365,
                    "interval": 1
                },
                "json_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "json",
                    "filename": "/opt/dotmac/logs/structured.log",
                    "maxBytes": 100000000,  # 100MB
                    "backupCount": 20
                }
            },
            "loggers": {
                "dotmac_isp": {
                    "handlers": ["console", "file_info", "file_error", "json_file"],
                    "level": "INFO",
                    "propagate": False
                },
                "management_platform": {
                    "handlers": ["console", "file_info", "file_error", "json_file"],
                    "level": "INFO",
                    "propagate": False
                },
                "audit": {
                    "handlers": ["audit_file", "json_file"],
                    "level": "INFO",
                    "propagate": False
                },
                "security": {
                    "handlers": ["console", "file_error", "audit_file"],
                    "level": "WARNING",
                    "propagate": False
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["console", "file_info"]
            }
        }
        
        # Save logging configuration
        logging_config_dir = self.production_dir / "configs"
        logging_config_dir.mkdir(exist_ok=True)
        
        config_file = logging_config_dir / "logging_config.json"
        with open(config_file, 'w') as f:
            json.dump(logging_config, f, indent=2)
        
        self.logger.info(f"Logging configuration created: {config_file}")

    def create_audit_system(self):
        """Create comprehensive audit logging system"""
        self.logger.info("🔍 Setting up audit logging system...")
        
        # Audit logging Python module
        audit_module = """#!/usr/bin/env python3
\"\"\"
Audit Logging System for DotMac Framework
Provides comprehensive audit trail functionality
\"\"\"

import logging
import json
import datetime
from datetime import timezone
import uuid
from typing import Dict, Any, Optional
from functools import wraps
import inspect

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        
    def log_event(self, event_type: str, user_id: str = None, resource_type: str = None, 
                  resource_id: str = None, action: str = None, details: Dict[str, Any] = None,
                  ip_address: str = None, user_agent: str = None, status: str = 'success'):
        \"\"\"Log an audit event\"\"\"
        
        audit_record = {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'event_id': str(uuid.uuid4(),
            'event_type': event_type,
            'user_id': user_id,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action': action,
            'status': status,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details or {}
        }
        
        self.logger.info(json.dumps(audit_record)
    
    def log_authentication(self, user_id: str, action: str, status: str, 
                          ip_address: str = None, details: Dict[str, Any] = None):
        \"\"\"Log authentication events\"\"\"
        self.log_event(
            event_type='authentication',
            user_id=user_id,
            action=action,
            status=status,
            ip_address=ip_address,
            details=details
        )
    
    def log_authorization(self, user_id: str, resource_type: str, resource_id: str,
                         action: str, status: str, details: Dict[str, Any] = None):
        \"\"\"Log authorization events\"\"\"
        self.log_event(
            event_type='authorization',
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details
        )
    
    def log_data_access(self, user_id: str, resource_type: str, resource_id: str,
                       action: str, details: Dict[str, Any] = None):
        \"\"\"Log data access events\"\"\"
        self.log_event(
            event_type='data_access',
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details
        )
    
    def log_system_event(self, action: str, status: str, details: Dict[str, Any] = None):
        \"\"\"Log system events\"\"\"
        self.log_event(
            event_type='system',
            action=action,
            status=status,
            details=details
        )
    
    def log_security_event(self, event_type: str, severity: str, description: str,
                          user_id: str = None, ip_address: str = None, 
                          details: Dict[str, Any] = None):
        \"\"\"Log security events\"\"\"
        security_details = {
            'severity': severity,
            'description': description,
            **(details or {})
        }
        
        self.log_event(
            event_type=f'security_{event_type}',
            user_id=user_id,
            action=event_type,
            status='alert' if severity in ['high', 'critical'] else 'warning',
            ip_address=ip_address,
            details=security_details
        )

# Decorators for automatic audit logging
def audit_api_call(resource_type: str = None, action: str = None):
    \"\"\"Decorator to automatically audit API calls\"\"\"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit = AuditLogger()
            
            # Extract user info from request context (FastAPI)
            user_id = None
            ip_address = None
            
            try:
                # Attempt to get user info from FastAPI request
                for arg in args:
                    if hasattr(arg, 'state') and hasattr(arg.state, 'user'):
                        user_id = getattr(arg.state.user, 'id', None)
                    if hasattr(arg, 'client') and hasattr(arg.client, 'host'):
                        ip_address = arg.client.host
                        break
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log successful API call
                audit.log_event(
                    event_type='api_call',
                    user_id=user_id,
                    resource_type=resource_type or func.__name__,
                    action=action or func.__name__,
                    status='success',
                    ip_address=ip_address,
                    details={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed API call
                audit.log_event(
                    event_type='api_call',
                    user_id=user_id,
                    resource_type=resource_type or func.__name__,
                    action=action or func.__name__,
                    status='error',
                    ip_address=ip_address,
                    details={
                        'function': func.__name__,
                        'module': func.__module__,
                        'error': str(e)
                    }
                )
                raise
                
        return wrapper
    return decorator

def audit_database_operation(operation_type: str):
    \"\"\"Decorator to audit database operations\"\"\"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit = AuditLogger()
            
            try:
                result = func(*args, **kwargs)
                
                audit.log_event(
                    event_type='database_operation',
                    action=operation_type,
                    status='success',
                    details={
                        'function': func.__name__,
                        'operation': operation_type
                    }
                )
                
                return result
                
            except Exception as e:
                audit.log_event(
                    event_type='database_operation',
                    action=operation_type,
                    status='error',
                    details={
                        'function': func.__name__,
                        'operation': operation_type,
                        'error': str(e)
                    }
                )
                raise
                
        return wrapper
    return decorator

# Global audit logger instance
audit_logger = AuditLogger()
"""
        
        # Save audit module
        shared_dir = self.project_root / "shared"
        shared_dir.mkdir(exist_ok=True)
        
        audit_file = shared_dir / "audit_logger.py"
        with open(audit_file, 'w') as f:
            f.write(audit_module)
        
        self.logger.info(f"Audit logging module created: {audit_file}")

    def create_log_monitoring_script(self):
        """Create log monitoring and alerting script"""
        self.logger.info("📊 Creating log monitoring script...")
        
        monitoring_script = """#!/usr/bin/env python3
\"\"\"
Log Monitoring and Analysis Script for DotMac Framework
Monitors logs for errors, security events, and performance issues
\"\"\"

import json
import re
import os
import time
from pathlib import Path
from collections import defaultdict, Counter
import subprocess
import logging
from datetime import timezone

class LogMonitor:
    def __init__(self, log_dir: str = '/opt/dotmac/logs'):
        self.log_dir = Path(log_dir)
        self.alert_file = self.log_dir / 'alerts.log'
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_error_patterns(self, log_file: Path, time_window: int = 3600):
        \"\"\"Check for error patterns in logs\"\"\"
        if not log_file.exists():
            return []
        
        alerts = []
        error_patterns = [
            (r'ERROR.*database.*connection', 'Database connection error'),
            (r'ERROR.*authentication.*failed', 'Authentication failure'),
            (r'ERROR.*permission.*denied', 'Permission denied'),
            (r'CRITICAL.*', 'Critical error'),
            (r'Exception.*', 'Application exception'),
            (r'500.*Internal Server Error', 'HTTP 500 error'),
            (r'Failed.*login.*attempt', 'Failed login attempt')
        ]
        
        try:
            # Read recent log entries
            current_time = time.time()
            recent_errors = []
            
            with open(log_file, 'r') as f:
                for line in f.readlines()[-1000:]:  # Check last 1000 lines
                    for pattern, description in error_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            recent_errors.append({
                                'pattern': description,
                                'line': line.strip(),
                                'file': str(log_file)
                            })
            
            # Group errors by pattern
            error_counts = Counter(error['pattern'] for error in recent_errors)
            
            for pattern, count in error_counts.items():
                if count > 5:  # Alert if more than 5 occurrences
                    alerts.append({
                        'type': 'error_pattern',
                        'severity': 'high' if count > 20 else 'medium',
                        'message': f'{pattern}: {count} occurrences',
                        'count': count,
                        'pattern': pattern
                    })
        
        except Exception as e:
            self.logger.error(f'Error checking patterns in {log_file}: {e}')
        
        return alerts
    
    def check_security_events(self, audit_log: Path):
        \"\"\"Check for security events in audit logs\"\"\"
        if not audit_log.exists():
            return []
        
        alerts = []
        
        try:
            with open(audit_log, 'r') as f:
                for line in f.readlines()[-500:]:  # Check recent entries
                    if 'AUDIT' in line:
                        try:
                            # Parse audit log entry
                            audit_data = json.loads(line.split('AUDIT - INFO - ')[1])
                            
                            # Check for security events
                            if audit_data.get('event_type', '').startswith('security_'):
                                severity = audit_data.get('details', {}).get('severity', 'medium')
                                
                                alerts.append({
                                    'type': 'security_event',
                                    'severity': severity,
                                    'message': f'Security event: {audit_data.get("action", "unknown")}',
                                    'event_type': audit_data.get('event_type'),
                                    'user_id': audit_data.get('user_id'),
                                    'ip_address': audit_data.get('ip_address')
                                })
                        except (json.JSONDecodeError, IndexError):
                            continue
        
        except Exception as e:
            self.logger.error(f'Error checking security events: {e}')
        
        return alerts
    
    def check_performance_issues(self, app_log: Path):
        \"\"\"Check for performance issues\"\"\"
        if not app_log.exists():
            return []
        
        alerts = []
        
        try:
            slow_requests = []
            memory_warnings = []
            
            with open(app_log, 'r') as f:
                for line in f.readlines()[-1000:]:
                    # Check for slow requests
                    if 'slow' in line.lower() or 'timeout' in line.lower():
                        slow_requests.append(line.strip()
                    
                    # Check for memory issues
                    if 'memory' in line.lower() and ('high' in line.lower() or 'exceeded' in line.lower():
                        memory_warnings.append(line.strip()
            
            if len(slow_requests) > 10:
                alerts.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'message': f'{len(slow_requests)} slow requests detected',
                    'count': len(slow_requests)
                })
            
            if len(memory_warnings) > 5:
                alerts.append({
                    'type': 'performance',
                    'severity': 'high',
                    'message': f'{len(memory_warnings)} memory warnings',
                    'count': len(memory_warnings)
                })
        
        except Exception as e:
            self.logger.error(f'Error checking performance issues: {e}')
        
        return alerts
    
    def send_alert(self, alert):
        \"\"\"Send alert notification\"\"\"
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        alert_message = f'[{timestamp}] {alert["severity"].upper()}: {alert["message"]}'
        
        # Log alert
        with open(self.alert_file, 'a') as f:
            f.write(f'{alert_message}\\n')
        
        # Send to monitoring system if configured
        try:
            # Use existing notification system if available
            notify_script = '/usr/local/bin/dotmac-backup-notify'
            if os.path.exists(notify_script):
                subprocess.run([
                    notify_script, 
                    alert['severity'], 
                    f'Log Alert: {alert["message"]}'
                ], check=False)
        except Exception as e:
            self.logger.error(f'Failed to send alert notification: {e}')
    
    def monitor_logs(self):
        \"\"\"Main monitoring function\"\"\"
        self.logger.info('Starting log monitoring...')
        
        # Log files to monitor
        log_files = {
            'application': self.log_dir / 'application.log',
            'errors': self.log_dir / 'errors.log',
            'audit': self.log_dir / 'audit.log',
            'structured': self.log_dir / 'structured.log'
        }
        
        all_alerts = []
        
        # Check each log file
        for log_type, log_file in log_files.items():
            if log_type == 'audit':
                alerts = self.check_security_events(log_file)
            elif log_type == 'errors':
                alerts = self.check_error_patterns(log_file)
            elif log_type == 'application':
                alerts = self.check_performance_issues(log_file)
            else:
                alerts = self.check_error_patterns(log_file)
            
            all_alerts.extend(alerts)
        
        # Process alerts
        for alert in all_alerts:
            if alert['severity'] in ['high', 'critical']:
                self.send_alert(alert)
                self.logger.warning(f'Alert: {alert["message"]}')
            elif alert['severity'] == 'medium':
                self.logger.info(f'Warning: {alert["message"]}')
        
        self.logger.info(f'Log monitoring completed. {len(all_alerts)} alerts processed.')
        
        # Generate monitoring report
        self.generate_monitoring_report(all_alerts)
    
    def generate_monitoring_report(self, alerts):
        \"\"\"Generate monitoring summary report\"\"\"
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_alerts': len(alerts),
            'alerts_by_severity': Counter(alert['severity'] for alert in alerts),
            'alerts_by_type': Counter(alert['type'] for alert in alerts),
            'alerts': alerts
        }
        
        report_file = self.log_dir / f'monitoring_report_{int(time.time()}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f'Monitoring report saved: {report_file}')

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor DotMac Framework logs')
    parser.add_argument('--log-dir', default='/opt/dotmac/logs', help='Log directory path')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    monitor = LogMonitor(args.log_dir)
    
    if args.continuous:
        print(f'Starting continuous monitoring (interval: {args.interval}s)...')
        while True:
            monitor.monitor_logs()
            time.sleep(args.interval)
    else:
        monitor.monitor_logs()

if __name__ == '__main__':
    main()
"""
        
        # Save monitoring script
        monitoring_script_file = self.project_root / "scripts" / "monitor_logs.py"
        with open(monitoring_script_file, 'w') as f:
            f.write(monitoring_script)
        
        os.chmod(monitoring_script_file, 0o755)
        self.logger.info(f"Log monitoring script created: {monitoring_script_file}")

    def setup_log_rotation(self):
        """Setup advanced log rotation with logrotate"""
        self.logger.info("🔄 Setting up log rotation...")
        
        logrotate_config = """# DotMac Framework Log Rotation Configuration

/opt/dotmac/logs/application.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 root root
    postrotate
        # Reload application if needed
        docker-compose -f /home/dotmac_framework/deployment/production/docker-compose.prod.yml kill -s USR1 isp-framework management-platform 2>/dev/null || true
    endscript
}

/opt/dotmac/logs/errors.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 root root
}

/opt/dotmac/logs/audit.log {
    daily
    rotate 365
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 root root
}

/opt/dotmac/logs/structured.log {
    daily
    rotate 60
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 root root
}

/opt/dotmac/logs/alerts.log {
    weekly
    rotate 52
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 root root
}

/opt/dotmac/logs/monitoring_report_*.json {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
"""
        
        if not self.dry_run:
            # Create logrotate configuration
            logrotate_file = "/etc/logrotate.d/dotmac-advanced-logs"
            
            try:
                with open(logrotate_file, 'w') as f:
                    f.write(logrotate_config)
                
                os.chmod(logrotate_file, 0o644)
                self.logger.info(f"Logrotate configuration created: {logrotate_file}")
                
                # Test logrotate configuration
                self.run_command(f"logrotate -d {logrotate_file}", "Test logrotate configuration")
                
            except Exception as e:
                self.logger.error(f"Failed to create logrotate config: {e}")
        
        return True

    def setup_advanced_logging(self) -> bool:
        """Setup complete advanced logging system"""
        self.logger.info("🚀 Setting up Advanced Logging and Audit Trail System")
        self.logger.info("=" * 60)
        
        if self.dry_run:
            self.logger.info("🧪 DRY RUN MODE - No changes will be made")
        
        setup_steps = [
            ("Logging Configuration", self.create_logging_config),
            ("Audit System", self.create_audit_system),
            ("Log Monitoring", self.create_log_monitoring_script),
            ("Log Rotation", self.setup_log_rotation)
        ]
        
        successful_steps = 0
        
        for step_name, step_function in setup_steps:
            self.logger.info(f"\n📋 Setting up {step_name}...")
            try:
                if step_function():
                    self.logger.info(f"✅ {step_name} setup completed")
                    successful_steps += 1
                else:
                    self.logger.error(f"❌ {step_name} setup failed")
            except Exception as e:
                self.logger.error(f"❌ {step_name} setup failed with exception: {e}")
        
        # Ensure log directory exists
        log_dir = Path("/opt/dotmac/logs")
        if not self.dry_run:
            log_dir.mkdir(parents=True, exist_ok=True)
            os.chown(log_dir, 0, 0)  # root:root
            os.chmod(log_dir, 0o755)
            self.logger.info(f"Log directory created: {log_dir}")
        
        # Summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📝 Advanced Logging Setup Summary")
        self.logger.info(f"✅ Completed: {successful_steps}/{len(setup_steps)} steps")
        
        if successful_steps == len(setup_steps):
            self.logger.info("\n🎉 Advanced logging system setup completed successfully!")
            self.logger.info("\nFeatures implemented:")
            self.logger.info("• Centralized logging configuration")
            self.logger.info("• Comprehensive audit trail system")
            self.logger.info("• Automated log monitoring and alerting")
            self.logger.info("• Advanced log rotation and retention")
            self.logger.info("• Structured logging with JSON format")
            self.logger.info("• Security event tracking")
            
            self.logger.info("\nUsage:")
            self.logger.info("1. Import audit_logger in your applications:")
            self.logger.info("   from shared.audit_logger import audit_logger")
            
            self.logger.info("2. Use audit decorators:")
            self.logger.info("   @audit_api_call(resource_type='user', action='create')")
            
            self.logger.info("3. Manual audit logging:")
            self.logger.info("   audit_logger.log_authentication(user_id, 'login', 'success')")
            
            self.logger.info("4. Monitor logs:")
            self.logger.info("   python3 scripts/monitor_logs.py")
            
            self.logger.info("\nFiles created:")
            self.logger.info("• shared/audit_logger.py - Audit logging module")
            self.logger.info("• deployment/production/configs/logging_config.json - Logging config")
            self.logger.info("• scripts/monitor_logs.py - Log monitoring script")
            self.logger.info("• /etc/logrotate.d/dotmac-advanced-logs - Log rotation config")
            
            return True
        else:
            self.logger.error(f"⚠️  Advanced logging setup completed with {len(setup_steps) - successful_steps} issues")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup advanced logging and audit trail for DotMac Framework")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    setup = AdvancedLoggingSetup(dry_run=args.dry_run)
    success = setup.setup_advanced_logging()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()