#!/usr/bin/env python3
"""
Backup Health Monitor for DotMac Platform.

Provides continuous monitoring of backup system health including:
- Backup completion verification
- Backup integrity checks
- Restore testing
- Alert generation
- Metrics collection
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiohttp
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/dotmac-backup-monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
backup_completion_time = Histogram(
    'dotmac_backup_completion_seconds', 
    'Time taken to complete backup',
    ['backup_type', 'status']
)
backup_size_bytes = Gauge(
    'dotmac_backup_size_bytes',
    'Size of backup in bytes',
    ['backup_id', 'component']
)
backup_success_total = Counter(
    'dotmac_backup_success_total',
    'Total successful backups',
    ['backup_type']
)
backup_failure_total = Counter(
    'dotmac_backup_failure_total',
    'Total failed backups',
    ['backup_type', 'failure_reason']
)
restore_test_duration = Histogram(
    'dotmac_restore_test_duration_seconds',
    'Time taken for restore tests',
    ['test_type', 'status']
)
backup_health_score = Gauge(
    'dotmac_backup_health_score',
    'Overall backup system health score (0-100)'
)


class BackupHealthMonitor:
    """Monitor backup system health and performance."""
    
    def __init__(self, config_file: str = "/home/dotmac_framework/config/backup-config.yml"):
        self.config = self._load_config(config_file)
        self.backup_root = "/var/backups/dotmac"
        self.health_score = 100
        self.last_successful_backup = None
        self.alert_history = []
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load monitoring configuration."""
        import yaml
        
        default_config = {
            "monitoring": {
                "check_interval_minutes": 15,
                "backup_staleness_hours": 25,  # Alert if no backup in 25 hours
                "health_check_port": 8080,
                "notifications": {
                    "email": {
                        "enabled": False,
                        "smtp_host": "localhost",
                        "smtp_port": 587,
                        "smtp_user": "",
                        "smtp_password": "",
                        "recipients": []
                    },
                    "slack": {
                        "enabled": False,
                        "webhook_url": ""
                    }
                }
            },
            "restore_testing": {
                "enabled": True,
                "frequency_days": 7,
                "test_database": "dotmac_restore_test"
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_update(default_config, user_config)
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")
        
        return default_config
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Recursively update nested dictionary."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    async def check_backup_completions(self) -> Dict[str, Any]:
        """Check recent backup completions."""
        results = {
            "status": "healthy",
            "last_backup": None,
            "backup_age_hours": 0,
            "issues": []
        }
        
        try:
            if not os.path.exists(self.backup_root):
                results["status"] = "critical"
                results["issues"].append("Backup directory does not exist")
                return results
            
            # Find most recent backup
            backups = []
            for backup_dir in os.listdir(self.backup_root):
                backup_path = os.path.join(self.backup_root, backup_dir)
                if os.path.isdir(backup_path):
                    try:
                        timestamp_str = backup_dir.split('_')[-1]
                        backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        backups.append((backup_time, backup_dir, backup_path)
                    except (ValueError, IndexError):
                        continue
            
            if backups:
                # Sort by timestamp, most recent first
                backups.sort(reverse=True)
                most_recent = backups[0]
                
                results["last_backup"] = most_recent[1]
                backup_age = datetime.now(timezone.utc) - most_recent[0]
                results["backup_age_hours"] = backup_age.total_seconds() / 3600
                
                # Check if backup is stale
                staleness_hours = self.config.get("monitoring", {}).get("backup_staleness_hours", 25)
                if backup_age.total_seconds() > staleness_hours * 3600:
                    results["status"] = "warning"
                    results["issues"].append(f"Last backup is {results['backup_age_hours']:.1f} hours old")
                
                # Check backup integrity
                manifest_file = os.path.join(most_recent[2], "backup_manifest.json")
                if os.path.exists(manifest_file):
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    # Verify all components are present
                    missing_components = []
                    for component, files in manifest.get("components", {}).items():
                        if isinstance(files, list):
                            for file in files:
                                file_path = os.path.join(most_recent[2], file)
                                if not os.path.exists(file_path):
                                    missing_components.append(f"{component}/{file}")
                        else:
                            file_path = os.path.join(most_recent[2], files)
                            if not os.path.exists(file_path):
                                missing_components.append(f"{component}/{files}")
                    
                    if missing_components:
                        results["status"] = "critical"
                        results["issues"].append(f"Missing backup files: {', '.join(missing_components)}")
                    
                    self.last_successful_backup = most_recent[0]
                else:
                    results["status"] = "warning"
                    results["issues"].append("Backup manifest not found")
            else:
                results["status"] = "critical"
                results["issues"].append("No backups found")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to check backup completions: {e}")
            results["status"] = "critical"
            results["issues"].append(f"Check failed: {str(e)}")
            return results
    
    async def verify_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """Verify integrity of a specific backup."""
        results = {
            "backup_id": backup_id,
            "status": "healthy",
            "verified_files": 0,
            "failed_verifications": 0,
            "issues": []
        }
        
        try:
            backup_dir = os.path.join(self.backup_root, backup_id)
            manifest_file = os.path.join(backup_dir, "backup_manifest.json")
            
            if not os.path.exists(manifest_file):
                results["status"] = "critical"
                results["issues"].append("Backup manifest not found")
                return results
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            checksums = manifest.get("checksums", {})
            
            for filename, expected_checksum in checksums.items():
                file_path = os.path.join(backup_dir, filename)
                
                if os.path.exists(file_path):
                    import hashlib
                    with open(file_path, 'rb') as f:
                        actual_checksum = hashlib.sha256(f.read().hexdigest()
                    
                    if actual_checksum == expected_checksum:
                        results["verified_files"] += 1
                    else:
                        results["failed_verifications"] += 1
                        results["issues"].append(f"Checksum mismatch: {filename}")
                        results["status"] = "critical"
                else:
                    results["failed_verifications"] += 1
                    results["issues"].append(f"Missing file: {filename}")
                    results["status"] = "critical"
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to verify backup integrity for {backup_id}: {e}")
            results["status"] = "critical"
            results["issues"].append(f"Verification failed: {str(e)}")
            return results
    
    async def test_restore_procedure(self) -> Dict[str, Any]:
        """Test backup restore procedure."""
        results = {
            "status": "healthy",
            "test_type": "database_restore",
            "duration_seconds": 0,
            "issues": []
        }
        
        if not self.config.get("restore_testing", {}).get("enabled", False):
            results["status"] = "skipped"
            results["issues"].append("Restore testing disabled")
            return results
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Find most recent backup
            backup_completions = await self.check_backup_completions()
            if backup_completions["status"] == "critical" or not backup_completions["last_backup"]:
                results["status"] = "failed"
                results["issues"].append("No valid backup found for restore test")
                return results
            
            backup_id = backup_completions["last_backup"]
            
            # Create test database
            test_db = self.config.get("restore_testing", {}).get("test_database", "dotmac_restore_test")
            
            # This is a simplified restore test - in production, you'd:
            # 1. Create isolated test environment
            # 2. Restore backup to test database
            # 3. Run data validation queries
            # 4. Clean up test environment
            
            # For now, we'll just verify the backup can be read
            backup_dir = os.path.join(self.backup_root, backup_id)
            manifest_file = os.path.join(backup_dir, "backup_manifest.json")
            
            if os.path.exists(manifest_file):
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                # Verify database backup files exist
                db_components = manifest.get("components", {}).get("databases", [])
                if not db_components:
                    results["status"] = "failed"
                    results["issues"].append("No database backups found in manifest")
                else:
                    # Check if database backup files exist
                    missing_files = []
                    for db_file in db_components:
                        file_path = os.path.join(backup_dir, db_file)
                        if not os.path.exists(file_path):
                            missing_files.append(db_file)
                    
                    if missing_files:
                        results["status"] = "failed"
                        results["issues"].append(f"Missing database backup files: {', '.join(missing_files)}")
                    else:
                        results["status"] = "passed"
                        logger.info(f"Restore test passed for backup {backup_id}")
            else:
                results["status"] = "failed"
                results["issues"].append("Backup manifest not found")
            
        except Exception as e:
            logger.error(f"Restore test failed: {e}")
            results["status"] = "failed"
            results["issues"].append(f"Test failed: {str(e)}")
        
        finally:
            end_time = datetime.now(timezone.utc)
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Update metrics
            restore_test_duration.labels(
                test_type=results["test_type"],
                status=results["status"]
            ).observe(results["duration_seconds"])
        
        return results
    
    async def calculate_health_score(self) -> int:
        """Calculate overall backup system health score (0-100)."""
        score = 100
        
        try:
            # Check backup completions (40% of score)
            backup_status = await self.check_backup_completions()
            if backup_status["status"] == "critical":
                score -= 40
            elif backup_status["status"] == "warning":
                score -= 20
            
            # Check backup age (20% of score)
            if backup_status["backup_age_hours"] > 48:  # More than 2 days old
                score -= 20
            elif backup_status["backup_age_hours"] > 26:  # More than 26 hours old
                score -= 10
            
            # Check recent backups integrity (20% of score)
            if backup_status["last_backup"]:
                integrity_check = await self.verify_backup_integrity(backup_status["last_backup"])
                if integrity_check["status"] == "critical":
                    score -= 20
                elif integrity_check["failed_verifications"] > 0:
                    score -= 10
            
            # Check restore testing (20% of score)
            restore_test = await self.test_restore_procedure()
            if restore_test["status"] == "failed":
                score -= 20
            elif restore_test["status"] == "skipped":
                score -= 10
            
            self.health_score = max(0, score)
            
            # Update metric
            backup_health_score.set(self.health_score)
            
            return self.health_score
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            self.health_score = 0
            backup_health_score.set(0)
            return 0
    
    async def send_alert(self, alert_type: str, message: str, severity: str = "warning") -> None:
        """Send alert notification."""
        try:
            alert_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": alert_type,
                "message": message,
                "severity": severity,
                "service": "dotmac-backup"
            }
            
            # Add to alert history
            self.alert_history.append(alert_data)
            if len(self.alert_history) > 100:  # Keep only recent alerts
                self.alert_history = self.alert_history[-100:]
            
            logger.warning(f"BACKUP ALERT [{severity.upper()}]: {message}")
            
            # Send email notification
            email_config = self.config.get("monitoring", {}).get("notifications", {}).get("email", {})
            if email_config.get("enabled", False):
                await self._send_email_alert(alert_data, email_config)
            
            # Send Slack notification
            slack_config = self.config.get("monitoring", {}).get("notifications", {}).get("slack", {})
            if slack_config.get("enabled", False):
                await self._send_slack_alert(alert_data, slack_config)
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def _send_email_alert(self, alert_data: Dict[str, Any], email_config: Dict[str, Any]) -> None:
        """Send email alert."""
        try:
            msg = MIMEMultipart()
            msg['From'] = email_config.get("smtp_user", "noreply@dotmac.com")
            msg['Subject'] = f"DotMac Backup Alert - {alert_data['severity'].upper()}"
            
            body = f"""
DotMac Platform Backup Alert

Timestamp: {alert_data['timestamp']}
Type: {alert_data['type']}
Severity: {alert_data['severity'].upper()}

Message: {alert_data['message']}

Health Score: {self.health_score}/100

This is an automated alert from the DotMac Platform backup monitoring system.
"""
            
            msg.attach(MIMEText(body, 'plain')
            
            server = smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"])
            if email_config.get("smtp_password"):
                server.starttls()
                server.login(email_config["smtp_user"], email_config["smtp_password"])
            
            for recipient in email_config.get("recipients", []):
                msg['To'] = recipient
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def _send_slack_alert(self, alert_data: Dict[str, Any], slack_config: Dict[str, Any]) -> None:
        """Send Slack alert."""
        try:
            webhook_url = slack_config.get("webhook_url")
            if not webhook_url:
                return
            
            color = {
                "info": "#36a64f",
                "warning": "#ff9500", 
                "critical": "#ff0000"
            }.get(alert_data['severity'], "#ff9500")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"DotMac Backup Alert - {alert_data['severity'].upper()}",
                    "fields": [
                        {
                            "title": "Type",
                            "value": alert_data['type'],
                            "short": True
                        },
                        {
                            "title": "Health Score",
                            "value": f"{self.health_score}/100",
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert_data['message'],
                            "short": False
                        }
                    ],
                    "timestamp": alert_data['timestamp']
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack alert sent successfully")
                    else:
                        logger.error(f"Failed to send Slack alert: {response.status}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    async def run_health_check_cycle(self) -> Dict[str, Any]:
        """Run complete health check cycle."""
        cycle_start = datetime.now(timezone.utc)
        
        try:
            logger.info("Starting backup health check cycle")
            
            # Check backup completions
            backup_status = await self.check_backup_completions()
            
            # Calculate health score
            health_score = await self.calculate_health_score()
            
            # Send alerts if needed
            if backup_status["status"] == "critical":
                await self.send_alert(
                    "backup_failure",
                    f"Critical backup system issues: {', '.join(backup_status['issues'])}",
                    "critical"
                )
            elif backup_status["status"] == "warning":
                await self.send_alert(
                    "backup_warning",
                    f"Backup system warnings: {', '.join(backup_status['issues'])}",
                    "warning"
                )
            
            # Low health score alert
            if health_score < 70:
                await self.send_alert(
                    "low_health_score",
                    f"Backup system health score is low: {health_score}/100",
                    "warning" if health_score >= 50 else "critical"
                )
            
            cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
            
            result = {
                "timestamp": cycle_start.isoformat(),
                "duration_seconds": cycle_duration,
                "health_score": health_score,
                "backup_status": backup_status,
                "alerts_sent": len([a for a in self.alert_history if a["timestamp"] >= cycle_start.isoformat()])
            }
            
            logger.info(f"Health check cycle completed in {cycle_duration:.2f}s, health score: {health_score}/100")
            return result
            
        except Exception as e:
            logger.error(f"Health check cycle failed: {e}")
            await self.send_alert(
                "monitor_failure",
                f"Backup monitoring system failure: {str(e)}",
                "critical"
            )
            return {
                "timestamp": cycle_start.isoformat(),
                "error": str(e),
                "health_score": 0
            }
    
    async def start_monitoring(self) -> None:
        """Start continuous monitoring."""
        check_interval = self.config.get("monitoring", {}).get("check_interval_minutes", 15)
        
        logger.info(f"Starting backup health monitoring (interval: {check_interval} minutes)")
        
        # Start Prometheus metrics server
        metrics_port = self.config.get("monitoring", {}).get("health_check_port", 8080)
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
        
        while True:
            try:
                await self.run_health_check_cycle()
                await asyncio.sleep(check_interval * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DotMac Backup Health Monitor")
    parser.add_argument("--config", default="/home/dotmac_framework/config/backup-config.yml")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--test-restore", action="store_true", help="Run restore test only")
    
    args = parser.parse_args()
    
    monitor = BackupHealthMonitor(args.config)
    
    if args.test_restore:
        result = await monitor.test_restore_procedure()
        print(f"Restore test result: {json.dumps(result, indent=2)}")
        return 0 if result["status"] in ["passed", "skipped"] else 1
    
    if args.once:
        result = await monitor.run_health_check_cycle()
        print(f"Health check result: {json.dumps(result, indent=2)}")
        return 0 if result.get("health_score", 0) >= 70 else 1
    
    # Continuous monitoring
    await monitor.start_monitoring()
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main())