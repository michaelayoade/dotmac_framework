#!/usr/bin/env python3
"""
Automated Backup and Disaster Recovery System for DotMac Platform.

Features:
- Database backup with encryption
- Configuration backup with versioning
- Plugin state backup
- Container image backup
- Cross-region replication
- Automated restore procedures
- Backup verification and integrity checks
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import psycopg2
import yaml
from cryptography.fernet import Fernet

import docker
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/dotmac-backup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BackupEncryption:
    """Handle backup encryption and decryption."""

    def __init__(self, key_path: Optional[str] = None):
        self.key_path = key_path or os.getenv("BACKUP_ENCRYPTION_KEY_PATH", "/etc/dotmac/backup.key")
        self.cipher = self._load_or_create_key()

    def _load_or_create_key(self) -> Fernet:
        """Load existing encryption key or create new one."""
        try:
            if os.path.exists(self.key_path):
                with open(self.key_path, 'rb') as f:
                    key = f.read()
                logger.info(f"Loaded encryption key from {self.key_path}")
            else:
                # Create new key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
                with open(self.key_path, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_path, 0o600)  # Secure permissions
                logger.info(f"Created new encryption key at {self.key_path}")

            return Fernet(key)

        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise

    def encrypt_file(self, file_path: str, encrypted_path: str) -> str:
        """Encrypt a file."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()

            encrypted_data = self.cipher.encrypt(data)

            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)

            # Calculate checksum
            checksum = hashlib.sha256(encrypted_data).hexdigest()
            logger.info(f"Encrypted {file_path} -> {encrypted_path} (checksum: {checksum[:16]}...)")
            return checksum

        except Exception as e:
            logger.error(f"Failed to encrypt {file_path}: {e}")
            raise

    def decrypt_file(self, encrypted_path: str, decrypted_path: str) -> bool:
        """Decrypt a file."""
        try:
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)

            with open(decrypted_path, 'wb') as f:
                f.write(decrypted_data)

            logger.info(f"Decrypted {encrypted_path} -> {decrypted_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to decrypt {encrypted_path}: {e}")
            return False


class DatabaseBackup:
    """Handle PostgreSQL database backups."""

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.host = db_config.get("host", "localhost")
        self.port = db_config.get("port", "5432")
        self.user = db_config.get("user", "postgres")
        self.password = db_config.get("password", "")
        self.databases = db_config.get("databases", ["dotmac_db", "identity_db", "billing_db"])

    async def create_backup(self, backup_dir: str, tenant_id: Optional[str] = None) -> List[str]:
        """Create database backup with optional tenant filtering."""
        backup_files = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        try:
            for database in self.databases:
                backup_file = os.path.join(
                    backup_dir,
                    f"{database}_{tenant_id}_{timestamp}.sql" if tenant_id else f"{database}_{timestamp}.sql"
                )

                # Build pg_dump command
                dump_cmd = [
                    "pg_dump",
                    f"--host={self.host}",
                    f"--port={self.port}",
                    f"--username={self.user}",
                    "--verbose",
                    "--clean",
                    "--no-owner",
                    "--no-privileges",
                    "--format=custom",
                    f"--file={backup_file}",
                    database
                ]

                # Add tenant filtering if specified
                if tenant_id:
                    dump_cmd.extend([
                        "--where", f"tenant_id = '{tenant_id}'"
                    ])

                # Set password environment variable
                env = os.environ.copy()
                env["PGPASSWORD"] = self.password

                # Execute backup
                logger.info(f"Creating backup for database {database}...")
                result = await asyncio.create_subprocess_exec(
                    *dump_cmd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await result.communicate()

                if result.returncode == 0:
                    backup_files.append(backup_file)
                    file_size = os.path.getsize(backup_file)
                    logger.info(f"Database backup created: {backup_file} ({file_size} bytes)")
                else:
                    logger.error(f"Database backup failed for {database}: {stderr.decode()}")
                    raise Exception(f"pg_dump failed: {stderr.decode()}")

            return backup_files

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise

    async def restore_backup(self, backup_file: str, target_database: str) -> bool:
        """Restore database from backup."""
        try:
            logger.info(f"Restoring database {target_database} from {backup_file}...")

            restore_cmd = [
                "pg_restore",
                f"--host={self.host}",
                f"--port={self.port}",
                f"--username={self.user}",
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                f"--dbname={target_database}",
                backup_file
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = self.password

            result = await asyncio.create_subprocess_exec(
                *restore_cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                logger.info(f"Database restore completed: {target_database}")
                return True
            else:
                logger.error(f"Database restore failed: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False


class ConfigurationBackup:
    """Handle configuration and plugin state backups."""

    def __init__(self, config_dirs: List[str]):
        self.config_dirs = config_dirs
        self.docker_client = docker.from_env()

    async def create_backup(self, backup_dir: str) -> str:
        """Create configuration backup."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"config_backup_{timestamp}.tar.gz")

        try:
            with tarfile.open(backup_file, "w:gz") as tar:
                for config_dir in self.config_dirs:
                    if os.path.exists(config_dir):
                        tar.add(config_dir, arcname=os.path.basename(config_dir))
                        logger.info(f"Added {config_dir} to configuration backup")

                # Add Docker Compose files
                compose_files = [
                    "/home/dotmac_framework/docker-compose.unified.yml",
                    "/home/dotmac_framework/docker-compose.override.yml"
                ]

                for compose_file in compose_files:
                    if os.path.exists(compose_file):
                        tar.add(compose_file, arcname=os.path.basename(compose_file))
                        logger.info(f"Added {compose_file} to configuration backup")

                # Add environment files
                env_files = [
                    "/home/dotmac_framework/.env",
                    "/home/dotmac_framework/.env.production"
                ]

                for env_file in env_files:
                    if os.path.exists(env_file):
                        tar.add(env_file, arcname=os.path.basename(env_file))
                        logger.info(f"Added {env_file} to configuration backup")

            file_size = os.path.getsize(backup_file)
            logger.info(f"Configuration backup created: {backup_file} ({file_size} bytes)")
            return backup_file

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            raise

    async def backup_plugin_states(self, backup_dir: str) -> str:
        """Backup plugin configurations and states."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        plugin_backup_file = os.path.join(backup_dir, f"plugin_states_{timestamp}.json")

        try:
            plugin_states = {
                "timestamp": timestamp,
                "plugin_configurations": {},
                "plugin_licenses": {},
                "plugin_usage_metrics": {}
            }

            # Connect to Redis to get plugin states
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                decode_responses=True
            )

            # Get plugin configurations
            plugin_keys = redis_client.keys("plugin:config:*")
            for key in plugin_keys:
                plugin_id = key.split(":")[-1]
                config_data = redis_client.get(key)
                if config_data:
                    plugin_states["plugin_configurations"][plugin_id] = json.loads(config_data)

            # Get plugin licenses
            license_keys = redis_client.keys("plugin:license:*")
            for key in license_keys:
                plugin_id = key.split(":")[-1]
                license_data = redis_client.get(key)
                if license_data:
                    plugin_states["plugin_licenses"][plugin_id] = json.loads(license_data)

            # Save plugin states
            with open(plugin_backup_file, 'w') as f:
                json.dump(plugin_states, f, indent=2, default=str)

            logger.info(f"Plugin states backed up: {plugin_backup_file}")
            return plugin_backup_file

        except Exception as e:
            logger.error(f"Plugin state backup failed: {e}")
            raise


class ContainerBackup:
    """Handle Docker container and image backups."""

    def __init__(self):
        self.docker_client = docker.from_env()

    async def backup_images(self, backup_dir: str, image_tags: List[str]) -> List[str]:
        """Backup Docker images."""
        backup_files = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        try:
            for image_tag in image_tags:
                try:
                    image = self.docker_client.images.get(image_tag)
                    backup_file = os.path.join(
                        backup_dir,
                        f"image_{image_tag.replace(':', '_').replace('/', '_')}_{timestamp}.tar"
                    )

                    logger.info(f"Backing up image {image_tag}...")

                    # Save image to tar file
                    with open(backup_file, 'wb') as f:
                        for chunk in image.save():
                            f.write(chunk)

                    file_size = os.path.getsize(backup_file)
                    backup_files.append(backup_file)
                    logger.info(f"Image backup created: {backup_file} ({file_size} bytes)")

                except docker.errors.ImageNotFound:
                    logger.warning(f"Image not found: {image_tag}")
                except Exception as e:
                    logger.error(f"Failed to backup image {image_tag}: {e}")

            return backup_files

        except Exception as e:
            logger.error(f"Container image backup failed: {e}")
            raise

    async def backup_volumes(self, backup_dir: str, volume_names: List[str]) -> List[str]:
        """Backup Docker volumes."""
        backup_files = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        try:
            for volume_name in volume_names:
                try:
                    backup_file = os.path.join(backup_dir, f"volume_{volume_name}_{timestamp}.tar.gz")

                    # Create temporary container to access volume
                    container = self.docker_client.containers.run(
                        "alpine:latest",
                        command="tar czf /backup.tar.gz -C /data .",
                        volumes={volume_name: {'bind': '/data', 'mode': 'ro'}},
                        detach=True,
                        remove=True
                    )

                    # Wait for container to complete
                    result = container.wait()

                    if result['StatusCode'] == 0:
                        # Copy backup from container
                        with tempfile.NamedTemporaryFile() as temp_file:
                            bits, _ = container.get_archive('/backup.tar.gz')
                            for chunk in bits:
                                temp_file.write(chunk)
                            temp_file.flush()

                            shutil.copy2(temp_file.name, backup_file)

                        backup_files.append(backup_file)
                        file_size = os.path.getsize(backup_file)
                        logger.info(f"Volume backup created: {backup_file} ({file_size} bytes)")
                    else:
                        logger.error(f"Volume backup failed for {volume_name}")

                except Exception as e:
                    logger.error(f"Failed to backup volume {volume_name}: {e}")

            return backup_files

        except Exception as e:
            logger.error(f"Volume backup failed: {e}")
            raise


class CloudStorageUpload:
    """Handle upload to cloud storage (AWS S3, Azure, GCP)."""

    def __init__(self, provider: str = "aws"):
        self.provider = provider
        self.s3_client = None

        if provider == "aws":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            self.bucket_name = os.getenv("BACKUP_S3_BUCKET", "dotmac-backups")

    async def upload_backup(self, local_file: str, remote_key: str) -> bool:
        """Upload backup file to cloud storage."""
        try:
            if self.provider == "aws" and self.s3_client:
                logger.info(f"Uploading {local_file} to S3://{self.bucket_name}/{remote_key}")

                # Upload with server-side encryption
                self.s3_client.upload_file(
                    local_file,
                    self.bucket_name,
                    remote_key,
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'StorageClass': 'STANDARD_IA'  # Infrequent Access for cost optimization
                    }
                )

                logger.info(f"Upload completed: {remote_key}")
                return True
            else:
                logger.warning(f"Cloud provider {self.provider} not configured")
                return False

        except Exception as e:
            logger.error(f"Failed to upload {local_file}: {e}")
            return False

    async def list_backups(self, prefix: str) -> List[Dict[str, Any]]:
        """List available backups in cloud storage."""
        try:
            if self.provider == "aws" and self.s3_client:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )

                backups = []
                for obj in response.get('Contents', []):
                    backups.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'storage_class': obj.get('StorageClass', 'STANDARD')
                    })

                return sorted(backups, key=lambda x: x['last_modified'], reverse=True)
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []


class DisasterRecoveryManager:
    """Main disaster recovery orchestrator."""

    def __init__(self, config_file: str = "/etc/dotmac/backup-config.yml"):
        self.config = self._load_config(config_file)
        self.encryption = BackupEncryption()
        self.db_backup = DatabaseBackup(self.config.get("database", {}))
        self.config_backup = ConfigurationBackup(self.config.get("config_dirs", []))
        self.container_backup = ContainerBackup()
        self.cloud_storage = CloudStorageUpload(self.config.get("cloud_provider", "aws"))

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load backup configuration."""
        default_config = {
            "database": {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", ""),
                "databases": ["dotmac_db", "identity_db", "billing_db"]
            },
            "config_dirs": [
                "/home/dotmac_framework/config",
                "/home/dotmac_framework/shared/communication",
                "/home/dotmac_framework/signoz"
            ],
            "backup_retention_days": 30,
            "backup_schedule": "daily",
            "cloud_provider": "aws",
            "container_images": [
                "dotmac/isp-framework:latest",
                "dotmac/management-platform:latest"
            ],
            "docker_volumes": [
                "dotmac_postgres_data",
                "dotmac_redis_data",
                "dotmac_signoz_data"
            ]
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")

        return default_config

    async def create_full_backup(self, backup_type: str = "scheduled") -> Dict[str, Any]:
        """Create a complete system backup."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{backup_type}_{timestamp}"

        # Create backup directory
        backup_dir = f"/var/backups/dotmac/{backup_id}"
        os.makedirs(backup_dir, exist_ok=True)

        backup_manifest = {
            "backup_id": backup_id,
            "timestamp": timestamp,
            "backup_type": backup_type,
            "components": {},
            "checksums": {},
            "cloud_locations": {}
        }

        try:
            logger.info(f"Starting full backup: {backup_id}")

            # 1. Database backup
            logger.info("Creating database backups...")
            db_files = await self.db_backup.create_backup(backup_dir)
            encrypted_db_files = []

            for db_file in db_files:
                encrypted_file = f"{db_file}.encrypted"
                checksum = self.encryption.encrypt_file(db_file, encrypted_file)
                encrypted_db_files.append(encrypted_file)
                backup_manifest["checksums"][os.path.basename(encrypted_file)] = checksum
                os.remove(db_file)  # Remove unencrypted file

            backup_manifest["components"]["databases"] = [
                os.path.basename(f) for f in encrypted_db_files
            ]

            # 2. Configuration backup
            logger.info("Creating configuration backup...")
            config_file = await self.config_backup.create_backup(backup_dir)
            encrypted_config = f"{config_file}.encrypted"
            checksum = self.encryption.encrypt_file(config_file, encrypted_config)
            backup_manifest["checksums"][os.path.basename(encrypted_config)] = checksum
            backup_manifest["components"]["configuration"] = os.path.basename(encrypted_config)
            os.remove(config_file)  # Remove unencrypted file

            # 3. Plugin state backup
            logger.info("Creating plugin state backup...")
            plugin_file = await self.config_backup.backup_plugin_states(backup_dir)
            encrypted_plugin = f"{plugin_file}.encrypted"
            checksum = self.encryption.encrypt_file(plugin_file, encrypted_plugin)
            backup_manifest["checksums"][os.path.basename(encrypted_plugin)] = checksum
            backup_manifest["components"]["plugin_states"] = os.path.basename(encrypted_plugin)
            os.remove(plugin_file)  # Remove unencrypted file

            # 4. Container images backup (optional, for air-gapped environments)
            if self.config.get("backup_container_images", False):
                logger.info("Creating container image backups...")
                image_files = await self.container_backup.backup_images(
                    backup_dir,
                    self.config.get("container_images", [])
                )
                backup_manifest["components"]["container_images"] = [
                    os.path.basename(f) for f in image_files
                ]

            # 5. Docker volumes backup
            logger.info("Creating Docker volume backups...")
            volume_files = await self.container_backup.backup_volumes(
                backup_dir,
                self.config.get("docker_volumes", [])
            )
            encrypted_volumes = []

            for volume_file in volume_files:
                encrypted_file = f"{volume_file}.encrypted"
                checksum = self.encryption.encrypt_file(volume_file, encrypted_file)
                encrypted_volumes.append(encrypted_file)
                backup_manifest["checksums"][os.path.basename(encrypted_file)] = checksum
                os.remove(volume_file)  # Remove unencrypted file

            backup_manifest["components"]["docker_volumes"] = [
                os.path.basename(f) for f in encrypted_volumes
            ]

            # 6. Save backup manifest
            manifest_file = os.path.join(backup_dir, "backup_manifest.json")
            with open(manifest_file, 'w') as f:
                json.dump(backup_manifest, f, indent=2, default=str)

            # 7. Upload to cloud storage
            if self.config.get("cloud_backup_enabled", True):
                logger.info("Uploading backup to cloud storage...")

                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        local_path = os.path.join(root, file)
                        relative_path = os.path.relpath(local_path, backup_dir)
                        cloud_key = f"dotmac-backups/{backup_id}/{relative_path}"

                        if await self.cloud_storage.upload_backup(local_path, cloud_key):
                            backup_manifest["cloud_locations"][relative_path] = cloud_key
                        else:
                            logger.error(f"Failed to upload {relative_path} to cloud")

            # 8. Update manifest with cloud locations
            with open(manifest_file, 'w') as f:
                json.dump(backup_manifest, f, indent=2, default=str)

            backup_size = sum(
                os.path.getsize(os.path.join(root, file))
                for root, dirs, files in os.walk(backup_dir)
                for file in files
            )

            logger.info(f"Full backup completed: {backup_id} ({backup_size} bytes)")
            return backup_manifest

        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            raise

    async def restore_from_backup(self, backup_id: str, components: List[str] = None) -> bool:
        """Restore system from backup."""
        try:
            logger.info(f"Starting restore from backup: {backup_id}")

            # Load backup manifest
            backup_dir = f"/var/backups/dotmac/{backup_id}"
            manifest_file = os.path.join(backup_dir, "backup_manifest.json")

            if not os.path.exists(manifest_file):
                logger.error(f"Backup manifest not found: {manifest_file}")
                return False

            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            components = components or list(manifest["components"].keys())

            for component in components:
                logger.info(f"Restoring component: {component}")

                if component == "databases":
                    # Restore databases
                    for encrypted_db_file in manifest["components"]["databases"]:
                        encrypted_path = os.path.join(backup_dir, encrypted_db_file)

                        if os.path.exists(encrypted_path):
                            # Decrypt database file
                            decrypted_path = encrypted_path.replace('.encrypted', '')

                            if self.encryption.decrypt_file(encrypted_path, decrypted_path):
                                # Extract database name from filename
                                db_name = os.path.basename(decrypted_path).split('_')[0]

                                # Restore database
                                if await self.db_backup.restore_backup(decrypted_path, db_name):
                                    logger.info(f"Database {db_name} restored successfully")
                                else:
                                    logger.error(f"Failed to restore database {db_name}")

                                # Clean up decrypted file
                                os.remove(decrypted_path)
                            else:
                                logger.error(f"Failed to decrypt {encrypted_db_file}")
                        else:
                            logger.error(f"Backup file not found: {encrypted_db_file}")

                elif component == "configuration":
                    # Restore configuration
                    encrypted_config = manifest["components"]["configuration"]
                    encrypted_path = os.path.join(backup_dir, encrypted_config)

                    if os.path.exists(encrypted_path):
                        decrypted_path = encrypted_path.replace('.encrypted', '')

                        if self.encryption.decrypt_file(encrypted_path, decrypted_path):
                            # Extract configuration files
                            with tarfile.open(decrypted_path, "r:gz") as tar:
                                tar.extractall("/tmp/dotmac_config_restore")

                            logger.info("Configuration files restored to /tmp/dotmac_config_restore")
                            os.remove(decrypted_path)
                        else:
                            logger.error("Failed to decrypt configuration backup")
                    else:
                        logger.error(f"Configuration backup not found: {encrypted_config}")

            logger.info(f"Restore completed for backup: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def cleanup_old_backups(self) -> None:
        """Remove backups older than retention period."""
        try:
            retention_days = self.config.get("backup_retention_days", 30)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            backup_root = "/var/backups/dotmac"
            if not os.path.exists(backup_root):
                return

            removed_count = 0
            for backup_dir in os.listdir(backup_root):
                backup_path = os.path.join(backup_root, backup_dir)

                if os.path.isdir(backup_path):
                    # Extract timestamp from backup directory name
                    try:
                        timestamp_str = backup_dir.split('_')[-1]
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        if backup_date < cutoff_date:
                            logger.info(f"Removing old backup: {backup_dir}")
                            shutil.rmtree(backup_path)
                            removed_count += 1
                    except (ValueError, IndexError):
                        logger.warning(f"Invalid backup directory name: {backup_dir}")

            logger.info(f"Cleanup completed: removed {removed_count} old backups")

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    async def verify_backup_integrity(self, backup_id: str) -> bool:
        """Verify backup integrity using checksums."""
        try:
            backup_dir = f"/var/backups/dotmac/{backup_id}"
            manifest_file = os.path.join(backup_dir, "backup_manifest.json")

            if not os.path.exists(manifest_file):
                logger.error(f"Backup manifest not found: {manifest_file}")
                return False

            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            checksums = manifest.get("checksums", {})

            for filename, expected_checksum in checksums.items():
                file_path = os.path.join(backup_dir, filename)

                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        actual_checksum = hashlib.sha256(f.read()).hexdigest()

                    if actual_checksum == expected_checksum:
                        logger.debug(f"Checksum verified: {filename}")
                    else:
                        logger.error(f"Checksum mismatch for {filename}")
                        return False
                else:
                    logger.error(f"Backup file missing: {filename}")
                    return False

            logger.info(f"Backup integrity verified: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False


async def main():
    """Main backup script entry point."""
    import argparse

from dotmac_shared.api.exception_handlers import standard_exception_handler

    parser = argparse.ArgumentParser(description="DotMac Platform Backup & Disaster Recovery")
    parser.add_argument("action", choices=["backup", "restore", "verify", "cleanup", "list"])
    parser.add_argument("--backup-id", help="Backup ID for restore/verify operations")
    parser.add_argument("--backup-type", default="manual", help="Backup type (scheduled/manual)")
    parser.add_argument("--components", nargs="+", help="Components to restore")
    parser.add_argument("--config", default="/etc/dotmac/backup-config.yml", help="Config file path")

    args = parser.parse_args()

    dr_manager = DisasterRecoveryManager(args.config)

    try:
        if args.action == "backup":
            manifest = await dr_manager.create_full_backup(args.backup_type)
            print(f"Backup completed: {manifest['backup_id']}")

        elif args.action == "restore":
            if not args.backup_id:
                print("--backup-id is required for restore operation")
                return

            success = await dr_manager.restore_from_backup(args.backup_id, args.components)
            print(f"Restore {'completed' if success else 'failed'}")

        elif args.action == "verify":
            if not args.backup_id:
                print("--backup-id is required for verify operation")
                return

            valid = await dr_manager.verify_backup_integrity(args.backup_id)
            print(f"Backup verification {'passed' if valid else 'failed'}")

        elif args.action == "cleanup":
            await dr_manager.cleanup_old_backups()
            print("Cleanup completed")

        elif args.action == "list":
            backup_root = "/var/backups/dotmac"
            if os.path.exists(backup_root):
                backups = []
                for backup_dir in sorted(os.listdir(backup_root)):
                    backup_path = os.path.join(backup_root, backup_dir)
                    if os.path.isdir(backup_path):
                        size = sum(
                            os.path.getsize(os.path.join(root, file))
                            for root, dirs, files in os.walk(backup_path)
                            for file in files
                        )
                        backups.append(f"{backup_dir} ({size} bytes)")

                print("Available backups:")
                for backup in backups:
                    print(f"  {backup}")
            else:
                print("No backups found")

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main())
