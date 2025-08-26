#!/usr/bin/env python3
"""
Disaster Recovery Script for DotMac Framework
Comprehensive disaster recovery automation with multiple recovery strategies
"""

import subprocess
import json
import os
import sys
import argparse
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

class RecoveryType(Enum):
    FULL_SYSTEM = "full_system"
    DATABASE_ONLY = "database_only"
    CONFIGURATION = "configuration"
    APPLICATION_DATA = "application_data"
    EMERGENCY = "emergency"

class RecoveryStatus(Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class RecoveryPlan:
    recovery_type: RecoveryType
    backup_path: str
    target_timestamp: str
    components: List[str]
    estimated_duration: int  # minutes
    risk_level: str  # low, medium, high
    rollback_strategy: str

class DisasterRecovery:
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent.parent
        self.production_dir = self.project_root / "deployment" / "production"
        self.backup_base_dir = Path("/opt/dotmac/backups")
        self.recovery_log_dir = Path("/opt/dotmac/recovery")
        
        # Setup logging
        self.setup_logging()
        
        # Recovery state
        self.current_status = RecoveryStatus.PLANNING
        self.recovery_steps = []
        self.failed_steps = []
        self.rollback_commands = []
        
        # System state backup
        self.pre_recovery_backup = None

    def setup_logging(self):
        """Setup comprehensive logging"""
        self.recovery_log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = self.recovery_log_dir / f"disaster_recovery_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.DEBUG if self.verbose else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Disaster recovery logging initialized: {log_file}")

    def run_command(self, command: str, description: str = "", check: bool = True) -> subprocess.CompletedProcess:
        """Execute command with proper logging and error handling"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: {command}")
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        
        self.logger.info(f"Executing: {description or command}")
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=300,
                check=check
            )
            
            if result.stdout and self.verbose:
                self.logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr and result.returncode != 0:
                self.logger.error(f"STDERR: {result.stderr}")
                
            return result
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout: {command}")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Return code: {e.returncode}")
            self.logger.error(f"Error output: {e.stderr}")
            raise

    def discover_backups(self) -> List[Dict[str, Any]]:
        """Discover available backups"""
        self.logger.info("Discovering available backups...")
        
        backups = []
        
        if not self.backup_base_dir.exists():
            self.logger.warning(f"Backup directory not found: {self.backup_base_dir}")
            return backups
        
        # Find backup directories and compressed backups
        for item in self.backup_base_dir.iterdir():
            backup_info = None
            
            if item.is_dir() and item.name.startswith("20"):  # Timestamp format
                # Directory backup
                info_file = item / "backup_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            backup_info = json.load(f)
                        backup_info['path'] = str(item)
                        backup_info['format'] = 'directory'
                    except Exception as e:
                        self.logger.warning(f"Could not read backup info: {info_file}: {e}")
                        
            elif item.name.startswith("dotmac_backup_") and item.name.endswith(".tar.gz"):
                # Compressed backup
                timestamp = item.name.replace("dotmac_backup_", "").replace(".tar.gz", "")
                info_file = self.backup_base_dir / f"backup_{timestamp}_info.json"
                
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            backup_info = json.load(f)
                        backup_info['path'] = str(item)
                        backup_info['format'] = 'compressed'
                        backup_info['timestamp'] = timestamp
                    except Exception as e:
                        self.logger.warning(f"Could not read backup info: {info_file}: {e}")
            
            if backup_info:
                # Add computed fields
                backup_info['size'] = self.get_path_size(item)
                backup_info['age_hours'] = self.get_backup_age_hours(backup_info.get('timestamp', '')
                backups.append(backup_info)
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        self.logger.info(f"Found {len(backups)} available backups")
        return backups

    def get_path_size(self, path: Path) -> str:
        """Get human-readable size of path"""
        try:
            result = self.run_command(f"du -sh '{path}'", check=False)
            if result.returncode == 0:
                return result.stdout.split('\t')[0]
        except:
            pass
        return "unknown"

    def get_backup_age_hours(self, timestamp: str) -> float:
        """Calculate backup age in hours"""
        try:
            backup_time = time.strptime(timestamp, "%Y%m%d_%H%M%S")
            backup_seconds = time.mktime(backup_time)
            current_seconds = time.time()
            return (current_seconds - backup_seconds) / 3600
        except:
            return 0

    def analyze_backup(self, backup_path: str) -> Dict[str, Any]:
        """Analyze backup contents and create recovery plan"""
        self.logger.info(f"Analyzing backup: {backup_path}")
        
        backup = Path(backup_path)
        analysis = {
            'path': backup_path,
            'components': [],
            'size': self.get_path_size(backup),
            'format': 'directory' if backup.is_dir() else 'compressed',
            'extractable': True,
            'integrity_ok': True
        }
        
        # Extract or access backup contents
        if backup.name.endswith('.tar.gz'):
            # Test compressed backup integrity
            try:
                self.run_command(f"tar -tzf '{backup}' > /dev/null", "Test archive integrity")
                analysis['integrity_ok'] = True
            except:
                analysis['integrity_ok'] = False
                analysis['extractable'] = False
                return analysis
        
        # Analyze components (for directory backups or after extraction)
        if backup.is_dir():
            content_dir = backup
        else:
            # Would need to extract compressed backup for full analysis
            content_dir = None
        
        if content_dir:
            components = []
            
            # Check for database backups
            db_dir = content_dir / "databases"
            if db_dir.exists():
                db_files = list(db_dir.glob("*.sql") + list(db_dir.glob("*.rdb")
                if db_files:
                    components.append("databases")
            
            # Check for configuration backups
            config_dir = content_dir / "configs"
            if config_dir.exists() and list(config_dir.iterdir():
                components.append("configurations")
            
            # Check for application data
            data_dir = content_dir / "data"
            if data_dir.exists() and list(data_dir.iterdir():
                components.append("application_data")
            
            # Check for logs
            logs_dir = content_dir / "logs"
            if logs_dir.exists() and list(logs_dir.iterdir():
                components.append("logs")
            
            analysis['components'] = components
        
        self.logger.info(f"Backup analysis complete: {len(analysis['components'])} components found")
        return analysis

    def create_recovery_plan(self, backup_path: str, recovery_type: RecoveryType, 
                           components: List[str] = None) -> RecoveryPlan:
        """Create detailed recovery plan"""
        self.logger.info(f"Creating recovery plan for {recovery_type.value}")
        
        backup_analysis = self.analyze_backup(backup_path)
        available_components = backup_analysis['components']
        
        # Determine components to recover
        if components is None:
            if recovery_type == RecoveryType.FULL_SYSTEM:
                components = available_components
            elif recovery_type == RecoveryType.DATABASE_ONLY:
                components = ['databases']
            elif recovery_type == RecoveryType.CONFIGURATION:
                components = ['configurations']
            elif recovery_type == RecoveryType.APPLICATION_DATA:
                components = ['application_data']
            elif recovery_type == RecoveryType.EMERGENCY:
                components = ['databases', 'configurations']
        
        # Validate requested components are available
        missing_components = set(components) - set(available_components)
        if missing_components:
            self.logger.warning(f"Requested components not found in backup: {missing_components}")
            components = [c for c in components if c in available_components]
        
        # Estimate duration and risk
        duration_map = {
            'databases': 30,
            'configurations': 5,
            'application_data': 15,
            'logs': 5
        }
        
        estimated_duration = sum(duration_map.get(c, 10) for c in components)
        
        # Determine risk level
        if 'databases' in components and len(components) > 1:
            risk_level = "high"
        elif 'databases' in components:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        plan = RecoveryPlan(
            recovery_type=recovery_type,
            backup_path=backup_path,
            target_timestamp=backup_analysis.get('timestamp', 'unknown'),
            components=components,
            estimated_duration=estimated_duration,
            risk_level=risk_level,
            rollback_strategy="emergency_backup" if risk_level == "high" else "configuration_restore"
        )
        
        self.logger.info(f"Recovery plan created: {len(components)} components, "
                        f"{estimated_duration} min estimated duration, {risk_level} risk")
        
        return plan

    def create_emergency_backup(self) -> Optional[str]:
        """Create emergency backup of current state before recovery"""
        self.logger.info("Creating emergency backup of current state...")
        
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            emergency_backup_path = self.backup_base_dir / f"emergency_recovery_{timestamp}"
            
            # Run emergency backup
            backup_script = self.project_root / "deployment" / "scripts" / "backup.sh"
            if backup_script.exists():
                result = self.run_command(
                    f"bash '{backup_script}' --type emergency",
                    "Create emergency backup"
                )
                
                # Find the created backup
                for item in self.backup_base_dir.iterdir():
                    if item.name.startswith(timestamp):
                        self.logger.info(f"Emergency backup created: {item}")
                        return str(item)
            
            self.logger.warning("Could not create emergency backup - backup script not found")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create emergency backup: {e}")
            return None

    def stop_services(self, services: List[str] = None):
        """Stop application services gracefully"""
        self.logger.info("Stopping application services...")
        
        if services is None:
            services = [
                "nginx", "isp-framework", "management-platform", 
                "mgmt-celery-worker", "mgmt-celery-beat"
            ]
        
        os.chdir(self.production_dir)
        
        for service in services:
            try:
                self.run_command(
                    f"docker-compose -f docker-compose.prod.yml stop {service}",
                    f"Stop {service} service",
                    check=False
                )
                self.rollback_commands.append(f"docker-compose -f docker-compose.prod.yml start {service}")
            except Exception as e:
                self.logger.warning(f"Failed to stop {service}: {e}")

    def start_services(self, services: List[str] = None):
        """Start application services"""
        self.logger.info("Starting application services...")
        
        if services is None:
            services = [
                "postgres-shared", "redis-shared", "openbao-shared",
                "isp-framework", "management-platform", 
                "mgmt-celery-worker", "mgmt-celery-beat", "nginx"
            ]
        
        os.chdir(self.production_dir)
        
        for service in services:
            try:
                self.run_command(
                    f"docker-compose -f docker-compose.prod.yml start {service}",
                    f"Start {service} service"
                )
            except Exception as e:
                self.logger.error(f"Failed to start {service}: {e}")
                raise

    def extract_backup(self, backup_path: str) -> str:
        """Extract compressed backup to temporary directory"""
        backup = Path(backup_path)
        
        if backup.is_dir():
            return backup_path
        
        if not backup.name.endswith('.tar.gz'):
            raise ValueError(f"Unsupported backup format: {backup}")
        
        self.logger.info(f"Extracting compressed backup: {backup}")
        
        # Create temporary extraction directory
        temp_dir = tempfile.mkdtemp(prefix="dotmac_recovery_")
        
        try:
            self.run_command(
                f"tar -xzf '{backup}' -C '{temp_dir}'",
                "Extract backup archive"
            )
            
            # Find extracted directory
            extracted_items = list(Path(temp_dir).iterdir()
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                extracted_path = str(extracted_items[0])
            else:
                extracted_path = temp_dir
            
            self.logger.info(f"Backup extracted to: {extracted_path}")
            return extracted_path
            
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def restore_databases(self, backup_dir: str):
        """Restore database backups"""
        self.logger.info("Restoring databases...")
        
        backup_path = Path(backup_dir)
        db_backup_dir = backup_path / "databases"
        
        if not db_backup_dir.exists():
            self.logger.warning("No database backups found")
            return
        
        os.chdir(self.production_dir)
        
        # Ensure database services are running
        try:
            self.run_command(
                "docker-compose -f docker-compose.prod.yml up -d postgres-shared redis-shared",
                "Start database services"
            )
            time.sleep(10)  # Wait for services to be ready
        except Exception as e:
            self.logger.error(f"Failed to start database services: {e}")
            raise
        
        # Restore PostgreSQL
        postgres_backup = db_backup_dir / "postgres_full_backup.sql"
        if postgres_backup.exists():
            self.logger.info("Restoring PostgreSQL databases...")
            try:
                self.run_command(
                    f"docker-compose -f docker-compose.prod.yml exec -T postgres-shared "
                    f"psql -U dotmac_admin < '{postgres_backup}'",
                    "Restore PostgreSQL backup"
                )
                self.logger.info("PostgreSQL restoration completed")
            except Exception as e:
                self.logger.error(f"PostgreSQL restoration failed: {e}")
                raise
        
        # Restore Redis
        redis_backup = db_backup_dir / "redis_backup.rdb"
        if redis_backup.exists():
            self.logger.info("Restoring Redis data...")
            try:
                container_name = "dotmac-redis-prod"
                self.run_command(
                    f"docker cp '{redis_backup}' {container_name}:/data/dump.rdb",
                    "Copy Redis backup to container"
                )
                self.run_command(
                    "docker-compose -f docker-compose.prod.yml restart redis-shared",
                    "Restart Redis to load backup"
                )
                self.logger.info("Redis restoration completed")
            except Exception as e:
                self.logger.error(f"Redis restoration failed: {e}")
                raise
        
        # Restore OpenBao
        openbao_backup = db_backup_dir / "openbao_data"
        if Path(openbao_backup).exists():
            self.logger.info("Restoring OpenBao data...")
            try:
                container_name = "dotmac-openbao-prod"
                self.run_command(
                    f"docker cp '{openbao_backup}' {container_name}:/openbao/data",
                    "Copy OpenBao backup to container"
                )
                self.run_command(
                    "docker-compose -f docker-compose.prod.yml restart openbao-shared",
                    "Restart OpenBao to load backup"
                )
                self.logger.info("OpenBao restoration completed")
            except Exception as e:
                self.logger.warning(f"OpenBao restoration failed: {e}")

    def restore_configurations(self, backup_dir: str):
        """Restore configuration files"""
        self.logger.info("Restoring configurations...")
        
        backup_path = Path(backup_dir)
        config_backup_dir = backup_path / "configs"
        
        if not config_backup_dir.exists():
            self.logger.warning("No configuration backups found")
            return
        
        # Restore production environment
        env_backup = config_backup_dir / ".env.production"
        if env_backup.exists():
            env_target = self.production_dir / ".env.production"
            if env_target.exists():
                # Create backup of current config
                backup_current = f"{env_target}.pre_recovery_{int(time.time()}"
                shutil.copy(env_target, backup_current)
                self.rollback_commands.append(f"cp '{backup_current}' '{env_target}'")
            
            shutil.copy(env_backup, env_target)
            self.logger.info("Production environment configuration restored")
        
        # Restore Docker Compose configuration
        compose_backup = config_backup_dir / "docker-compose.prod.yml"
        if compose_backup.exists():
            compose_target = self.production_dir / "docker-compose.prod.yml"
            if compose_target.exists():
                backup_current = f"{compose_target}.pre_recovery_{int(time.time()}"
                shutil.copy(compose_target, backup_current)
                self.rollback_commands.append(f"cp '{backup_current}' '{compose_target}'")
            
            shutil.copy(compose_backup, compose_target)
            self.logger.info("Docker Compose configuration restored")
        
        # Restore Nginx configuration
        nginx_backup_dir = config_backup_dir / "nginx"
        if nginx_backup_dir.exists():
            nginx_target_dir = self.production_dir / "nginx"
            if nginx_target_dir.exists():
                backup_current = f"{nginx_target_dir}.pre_recovery_{int(time.time()}"
                shutil.copytree(nginx_target_dir, backup_current)
                self.rollback_commands.append(f"rm -rf '{nginx_target_dir}' && mv '{backup_current}' '{nginx_target_dir}'")
                shutil.rmtree(nginx_target_dir)
            
            shutil.copytree(nginx_backup_dir, nginx_target_dir)
            self.logger.info("Nginx configuration restored")
        
        # Restore SSL certificates
        ssl_backup_dir = config_backup_dir / "ssl"
        if ssl_backup_dir.exists():
            ssl_target_dir = Path("/opt/dotmac/ssl")
            if ssl_target_dir.exists():
                backup_current = f"{ssl_target_dir}.pre_recovery_{int(time.time()}"
                shutil.copytree(ssl_target_dir, backup_current)
                self.rollback_commands.append(f"rm -rf '{ssl_target_dir}' && mv '{backup_current}' '{ssl_target_dir}'")
                shutil.rmtree(ssl_target_dir)
            
            shutil.copytree(ssl_backup_dir, ssl_target_dir)
            self.logger.info("SSL certificates restored")

    def restore_application_data(self, backup_dir: str):
        """Restore application data files"""
        self.logger.info("Restoring application data...")
        
        backup_path = Path(backup_dir)
        data_backup_dir = backup_path / "data"
        
        if not data_backup_dir.exists():
            self.logger.warning("No application data backups found")
            return
        
        # Restore uploaded files and data
        data_mappings = {
            "uploads_data": "/opt/dotmac/data/isp/uploads",
            "mgmt_data": "/opt/dotmac/data/mgmt/uploads",
            "shared_data": "/opt/dotmac/data/shared"
        }
        
        for backup_name, target_path in data_mappings.items():
            data_backup = data_backup_dir / backup_name
            if data_backup.exists():
                target = Path(target_path)
                
                if target.exists():
                    backup_current = f"{target}.pre_recovery_{int(time.time()}"
                    shutil.copytree(target, backup_current)
                    self.rollback_commands.append(f"rm -rf '{target}' && mv '{backup_current}' '{target}'")
                    shutil.rmtree(target)
                
                shutil.copytree(data_backup, target)
                self.logger.info(f"Application data restored: {target_path}")

    def verify_recovery(self):
        """Verify that recovery was successful"""
        self.logger.info("Verifying recovery...")
        
        verification_results = {
            'services_running': False,
            'databases_accessible': False,
            'configurations_valid': False,
            'endpoints_responding': False
        }
        
        # Check services are running
        try:
            os.chdir(self.production_dir)
            result = self.run_command(
                "docker-compose -f docker-compose.prod.yml ps --services --filter status=running",
                "Check running services",
                check=False
            )
            
            running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
            essential_services = ["postgres-shared", "redis-shared", "isp-framework", "management-platform"]
            
            if all(service in running_services for service in essential_services):
                verification_results['services_running'] = True
                self.logger.info("✓ Essential services are running")
            else:
                self.logger.error("✗ Not all essential services are running")
                
        except Exception as e:
            self.logger.error(f"Service verification failed: {e}")
        
        # Check database connectivity
        try:
            self.run_command(
                "docker-compose -f docker-compose.prod.yml exec -T postgres-shared pg_isready -U dotmac_admin",
                "Check PostgreSQL connectivity",
                check=False
            )
            
            self.run_command(
                "docker-compose -f docker-compose.prod.yml exec -T redis-shared redis-cli ping",
                "Check Redis connectivity", 
                check=False
            )
            
            verification_results['databases_accessible'] = True
            self.logger.info("✓ Databases are accessible")
            
        except Exception as e:
            self.logger.error(f"Database verification failed: {e}")
        
        # Check configuration validity
        try:
            env_file = self.production_dir / ".env.production"
            if env_file.exists():
                verification_results['configurations_valid'] = True
                self.logger.info("✓ Configuration files are present")
            else:
                self.logger.error("✗ Configuration files are missing")
                
        except Exception as e:
            self.logger.error(f"Configuration verification failed: {e}")
        
        # Check endpoint responsiveness
        try:
            import time
            time.sleep(30)  # Wait for services to fully start
            
            endpoints = [
                "http://localhost:8000/health",
                "http://localhost:8001/health"
            ]
            
            for endpoint in endpoints:
                try:
                    result = self.run_command(
                        f"curl -f -s --connect-timeout 10 '{endpoint}'",
                        f"Check endpoint {endpoint}",
                        check=False
                    )
                    if result.returncode == 0:
                        self.logger.info(f"✓ Endpoint responding: {endpoint}")
                    else:
                        self.logger.warning(f"⚠ Endpoint not responding: {endpoint}")
                except:
                    self.logger.warning(f"⚠ Could not check endpoint: {endpoint}")
            
            verification_results['endpoints_responding'] = True
            
        except Exception as e:
            self.logger.error(f"Endpoint verification failed: {e}")
        
        # Overall verification result
        passed_checks = sum(1 for result in verification_results.values() if result)
        total_checks = len(verification_results)
        
        if passed_checks >= 3:  # Require at least 3 out of 4 checks to pass
            self.logger.info(f"✅ Recovery verification successful ({passed_checks}/{total_checks} checks passed)")
            return True
        else:
            self.logger.error(f"❌ Recovery verification failed ({passed_checks}/{total_checks} checks passed)")
            return False

    def execute_recovery(self, plan: RecoveryPlan) -> bool:
        """Execute the recovery plan"""
        self.logger.info(f"Executing recovery plan: {plan.recovery_type.value}")
        self.current_status = RecoveryStatus.IN_PROGRESS
        
        try:
            # Create emergency backup if high risk
            if plan.risk_level == "high":
                self.pre_recovery_backup = self.create_emergency_backup()
            
            # Extract backup if needed
            working_backup_dir = self.extract_backup(plan.backup_path)
            
            # Stop services for safe recovery
            if 'databases' in plan.components or 'configurations' in plan.components:
                self.stop_services()
            
            # Execute recovery components
            if 'databases' in plan.components:
                self.restore_databases(working_backup_dir)
                self.recovery_steps.append("databases")
            
            if 'configurations' in plan.components:
                self.restore_configurations(working_backup_dir)
                self.recovery_steps.append("configurations")
            
            if 'application_data' in plan.components:
                self.restore_application_data(working_backup_dir)
                self.recovery_steps.append("application_data")
            
            # Start services
            self.start_services()
            
            # Verify recovery
            if not self.verify_recovery():
                raise Exception("Recovery verification failed")
            
            self.current_status = RecoveryStatus.COMPLETED
            self.logger.info("✅ Disaster recovery completed successfully!")
            
            # Cleanup temporary extraction directory if created
            if working_backup_dir != plan.backup_path and working_backup_dir.startswith('/tmp'):
                shutil.rmtree(working_backup_dir, ignore_errors=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disaster recovery failed: {e}")
            self.current_status = RecoveryStatus.FAILED
            
            # Attempt rollback
            if self.rollback_commands and plan.risk_level == "high":
                self.logger.info("Attempting rollback...")
                try:
                    self.rollback()
                    self.current_status = RecoveryStatus.ROLLED_BACK
                except Exception as rollback_error:
                    self.logger.error(f"Rollback also failed: {rollback_error}")
            
            return False

    def rollback(self):
        """Rollback changes made during recovery"""
        self.logger.info("Performing rollback...")
        
        # Execute rollback commands in reverse order
        for command in reversed(self.rollback_commands):
            try:
                self.run_command(command, "Rollback command")
            except Exception as e:
                self.logger.error(f"Rollback command failed: {command}: {e}")
        
        # Restart services
        try:
            self.start_services()
        except Exception as e:
            self.logger.error(f"Service restart during rollback failed: {e}")
        
        self.logger.info("Rollback completed")

def main():
    parser = argparse.ArgumentParser(description="DotMac Framework Disaster Recovery")
    parser.add_argument("--list-backups", action="store_true", help="List available backups")
    parser.add_argument("--backup", help="Backup path to recover from")
    parser.add_argument("--type", choices=["full", "database", "config", "data", "emergency"], 
                       default="full", help="Recovery type")
    parser.add_argument("--components", nargs="+", 
                       choices=["databases", "configurations", "application_data", "logs"],
                       help="Specific components to recover")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--force", action="store_true", help="Skip confirmations")
    
    args = parser.parse_args()
    
    # Initialize disaster recovery
    dr = DisasterRecovery(dry_run=args.dry_run, verbose=args.verbose)
    
    try:
        if args.list_backups:
            backups = dr.discover_backups()
            
            print("\n🔍 Available Backups:")
            print("=" * 80)
            
            if not backups:
                print("No backups found.")
                sys.exit(0)
            
            for i, backup in enumerate(backups, 1):
                print(f"\n{i}. Timestamp: {backup.get('timestamp', 'unknown')}")
                print(f"   Path: {backup['path']}")
                print(f"   Size: {backup['size']}")
                print(f"   Age: {backup['age_hours']:.1f} hours")
                print(f"   Components: {', '.join(backup.get('components', [])}")
                print(f"   Format: {backup.get('format', 'unknown')}")
            
            print()
            sys.exit(0)
        
        if not args.backup:
            print("Error: --backup is required for recovery operations")
            sys.exit(1)
        
        # Map recovery types
        type_mapping = {
            "full": RecoveryType.FULL_SYSTEM,
            "database": RecoveryType.DATABASE_ONLY,
            "config": RecoveryType.CONFIGURATION,
            "data": RecoveryType.APPLICATION_DATA,
            "emergency": RecoveryType.EMERGENCY
        }
        
        recovery_type = type_mapping[args.type]
        
        # Create recovery plan
        plan = dr.create_recovery_plan(args.backup, recovery_type, args.components)
        
        # Display plan
        print("\n🚨 DISASTER RECOVERY PLAN")
        print("=" * 60)
        print(f"Recovery Type: {plan.recovery_type.value}")
        print(f"Backup Path: {plan.backup_path}")
        print(f"Target Timestamp: {plan.target_timestamp}")
        print(f"Components: {', '.join(plan.components)}")
        print(f"Estimated Duration: {plan.estimated_duration} minutes")
        print(f"Risk Level: {plan.risk_level.upper()}")
        print(f"Rollback Strategy: {plan.rollback_strategy}")
        
        if args.dry_run:
            print("\n🧪 DRY RUN MODE - No changes will be made")
            sys.exit(0)
        
        # Confirmation
        if not args.force and plan.risk_level in ["medium", "high"]:
            print(f"\n⚠️  This is a {plan.risk_level} risk recovery operation.")
            print("Current system state will be modified and may cause downtime.")
            if plan.risk_level == "high":
                print("An emergency backup will be created before proceeding.")
            
            confirm = input("\nDo you want to proceed? (yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                print("Recovery cancelled.")
                sys.exit(0)
        
        # Execute recovery
        success = dr.execute_recovery(plan)
        
        if success:
            print("\n🎉 Disaster recovery completed successfully!")
            print("\nNext steps:")
            print("1. Verify all application functionality")
            print("2. Check logs for any issues")
            print("3. Monitor system performance")
            print("4. Update monitoring and alerting if needed")
            sys.exit(0)
        else:
            print("\n💥 Disaster recovery failed!")
            print("Check the logs for detailed error information.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nRecovery interrupted by user.")
        sys.exit(1)
    except Exception as e:
        dr.logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()