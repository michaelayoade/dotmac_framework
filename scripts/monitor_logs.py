#!/usr/bin/env python3
"""
Log Monitoring and Analysis Script for DotMac Framework
Monitors logs for errors, security events, and performance issues
"""

import json
import re
import os
import time
from pathlib import Path
from collections import defaultdict, Counter
import subprocess
import logging

class LogMonitor:
    def __init__(self, log_dir: str = '/opt/dotmac/logs'):
        self.log_dir = Path(log_dir)
        self.alert_file = self.log_dir / 'alerts.log'
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_error_patterns(self, log_file: Path, time_window: int = 3600):
        """Check for error patterns in logs"""
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
        """Check for security events in audit logs"""
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
        """Check for performance issues"""
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
        """Send alert notification"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        alert_message = f'[{timestamp}] {alert["severity"].upper()}: {alert["message"]}'
        
        # Log alert
        with open(self.alert_file, 'a') as f:
            f.write(f'{alert_message}\n')
        
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
        """Main monitoring function"""
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
        """Generate monitoring summary report"""
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
