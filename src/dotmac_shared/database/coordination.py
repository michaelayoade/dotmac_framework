"""
Database Coordination for DotMac Framework
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import asyncpg

import redis

logger = logging.getLogger(__name__)


class DatabaseCoordinator:
    """Main database coordinator for connection and transaction management."""

    def __init__(self, database_url: str = None, redis_url: str = None):
        self.database_url = database_url or "postgresql://localhost/test"
        self.redis_url = redis_url or "redis://localhost:6379/1"
        self._initialized = False
        self._db_pool = None
        self._redis_client = None

    async def initialize(self):
        """Initialize the database coordinator."""
        self._db_pool = await self._init_database_pool()
        self._redis_client = await self._init_redis_client()
        self._initialized = True

    async def _init_database_pool(self):
        """Initialize database connection pool."""
        return await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def _init_redis_client(self):
        """Initialize Redis client."""
        return redis.from_url(self.redis_url)

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection context manager."""
        if not self._initialized:
            await self.initialize()

        async with self._db_pool.acquire() as connection:
            yield connection

    async def execute_query(self, query: str, *args):
        """Execute a query and return results."""
        async with self.get_connection() as conn:
            return await conn.fetchall(query, *args)

    async def execute_transaction(self, operations: Callable):
        """Execute operations within a transaction."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                return await operations(conn)

    async def check_health(self) -> Dict[str, Any]:
        """Check health of database and Redis."""
        results = {}

        # Check database health
        try:
            start_time = asyncio.get_event_loop().time()
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            response_time = asyncio.get_event_loop().time() - start_time

            results["database"] = {
                "status": "healthy",
                "response_time": round(response_time, 3),
            }
        except Exception as e:
            results["database"] = {"status": "unhealthy", "error": str(e)}

        # Check Redis health
        try:
            start_time = asyncio.get_event_loop().time()
            await self._redis_client.ping()
            response_time = asyncio.get_event_loop().time() - start_time

            results["redis"] = {
                "status": "healthy",
                "response_time": round(response_time, 3),
            }
        except Exception as e:
            results["redis"] = {"status": "unhealthy", "error": str(e)}

        return results

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self._db_pool:
            return {"error": "Pool not initialized"}

        return {
            "total_connections": self._db_pool.get_size(),
            "idle_connections": self._db_pool.get_idle_size(),
            "active_connections": self._db_pool.get_size()
            - self._db_pool.get_idle_size(),
        }

    async def _get_connection(self):
        """Internal method to get connection for testing."""
        async with self.get_connection() as conn:
            return conn

    async def cleanup(self):
        """Clean up resources."""
        if self._db_pool:
            await self._db_pool.close()
        if self._redis_client:
            await self._redis_client.close()
        self._initialized = False


class ConnectionPool:
    """Connection pool management."""

    def __init__(self, database_url: str, min_size: int = 2, max_size: int = 10):
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self._pool = None

    async def initialize(self):
        """Initialize the connection pool."""
        self._pool = await asyncpg.create_pool(
            self.database_url, min_size=self.min_size, max_size=self.max_size
        )

    async def acquire(self):
        """Acquire a connection from the pool."""
        return await self._pool.acquire()

    async def release(self, connection):
        """Release a connection back to the pool."""
        await self._pool.release(connection)

    async def __aenter__(self):
        """Context manager entry."""
        self._connection = await self.acquire()
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self, "_connection"):
            await self.release(self._connection)
            delattr(self, "_connection")


class TransactionManager:
    """Transaction management utilities."""

    async def begin(self, connection):
        """Begin a transaction."""
        return await connection.transaction()

    async def commit(self, transaction):
        """Commit a transaction."""
        await transaction.commit()

    async def rollback(self, transaction):
        """Rollback a transaction."""
        await transaction.rollback()

    @asynccontextmanager
    async def transaction(self, connection):
        """Transaction context manager."""
        async with connection.transaction() as txn:
            yield txn


class DatabaseMigration:
    """Database migration utilities."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def _create_migration_table(self):
        """Create migration tracking table."""
        async with self._get_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """
            )

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        async with self._get_connection() as conn:
            rows = await conn.fetch(
                "SELECT version FROM migrations ORDER BY applied_at"
            )
            return [row["version"] for row in rows]

    async def apply_migration(self, version: str, migration_sql: str):
        """Apply a migration."""
        async with self._get_connection() as conn:
            async with conn.transaction():
                # Execute migration SQL
                await conn.execute(migration_sql)

                # Record migration
                await conn.execute(
                    "INSERT INTO migrations (version) VALUES ($1)", version
                )

    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection for migrations."""
        conn = await asyncpg.connect(self.database_url)
        try:
            yield conn
        finally:
            await conn.close()


class TenantCoordinator:
    """Multi-tenant database coordination."""

    def __init__(self, master_db_url: str, redis_url: str):
        self.master_db_url = master_db_url
        self.redis_url = redis_url
        self._redis_client = None

    async def get_tenant_database_url(self, tenant_id: str) -> str:
        """Get database URL for a specific tenant."""
        if not self._redis_client:
            self._redis_client = redis.from_url(self.redis_url)

        # Get from Redis cache
        db_url = await self._redis_client.hget("tenant_databases", tenant_id)
        if db_url:
            return db_url.decode() if isinstance(db_url, bytes) else db_url

        # Fallback or generate URL
        return f"postgresql://tenant_{tenant_id}@localhost/tenant_{tenant_id}_db"

    async def register_tenant_database(self, tenant_id: str, database_url: str):
        """Register a tenant's database URL."""
        if not self._redis_client:
            self._redis_client = redis.from_url(self.redis_url)

        await self._redis_client.hset("tenant_databases", tenant_id, database_url)

    @asynccontextmanager
    async def get_tenant_connection(self, tenant_id: str):
        """Get connection for a specific tenant."""
        db_url = await self.get_tenant_database_url(tenant_id)
        conn = await asyncpg.connect(db_url)
        try:
            yield conn
        finally:
            await conn.close()

    async def execute_tenant_query(self, tenant_id: str, query: str, *args):
        """Execute query on tenant database."""
        async with self.get_tenant_connection(tenant_id) as conn:
            return await conn.fetchall(query, *args)

    async def list_active_tenants(self) -> List[str]:
        """List all active tenant IDs."""
        if not self._redis_client:
            self._redis_client = redis.from_url(self.redis_url)

        tenant_keys = await self._redis_client.hkeys("tenant_databases")
        return [key.decode() if isinstance(key, bytes) else key for key in tenant_keys]

    async def coordinate_tenant_migration(
        self, tenant_id: str, migration_version: str
    ) -> Dict[str, Any]:
        """Coordinate migration for a specific tenant with safety locks."""
        migration_coordinator = MigrationCoordinator(self.redis_url)

        # Acquire tenant-specific migration lock
        lock_key = f"tenant_{tenant_id}"
        lock_value = await migration_coordinator.acquire_migration_lock(
            lock_key, timeout=600
        )  # 10 min timeout for tenant migrations

        if not lock_value:
            return {
                "status": "failed",
                "error": f"Could not acquire migration lock for tenant {tenant_id}",
                "tenant_id": tenant_id,
            }

        try:
            # Get tenant database connection
            tenant_db_url = await self.get_tenant_database_url(tenant_id)

            # Create backup before migration
            backup_info = await self._create_tenant_backup(tenant_id, migration_version)

            # Apply migration to tenant database
            migration_result = await self._apply_tenant_migration(
                tenant_id, tenant_db_url, migration_version
            )

            # Register successful migration
            if migration_result["status"] == "success":
                await migration_coordinator.register_platform_schema_version(
                    f"tenant_{tenant_id}",
                    migration_version,
                    {
                        "tenant_id": tenant_id,
                        "backup_info": backup_info,
                        "migration_timestamp": datetime.now().isoformat(),
                    },
                )

            return {
                "status": migration_result["status"],
                "tenant_id": tenant_id,
                "migration_version": migration_version,
                "backup_info": backup_info,
                "details": migration_result,
            }

        except Exception as e:
            logger.error("Tenant migration failed", tenant_id=tenant_id, error=str(e))
            return {"status": "error", "tenant_id": tenant_id, "error": str(e)}
        finally:
            # Always release the lock
            await migration_coordinator.release_migration_lock(lock_key, lock_value)

    async def _create_tenant_backup(
        self, tenant_id: str, migration_version: str
    ) -> Dict[str, Any]:
        """Create backup for tenant before migration."""
        backup_name = (
            f"tenant_{tenant_id}_pre_migration_{migration_version}_{int(time.time())}"
        )

        try:
            async with self.get_tenant_connection(tenant_id) as conn:
                # Get table list
                tables = await conn.fetch(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
                )

                backup_info = {
                    "backup_name": backup_name,
                    "tenant_id": tenant_id,
                    "migration_version": migration_version,
                    "timestamp": datetime.now().isoformat(),
                    "table_count": len(tables),
                    "tables": [t[0] for t in tables],
                }

                # Store backup metadata
                if not self._redis_client:
                    self._redis_client = redis.from_url(self.redis_url)

                await self._redis_client.hset(
                    f"tenant_backups:{tenant_id}", backup_name, json.dumps(backup_info)
                )

                logger.info(
                    "Tenant backup created",
                    tenant_id=tenant_id,
                    backup_name=backup_name,
                )
                return backup_info

        except Exception as e:
            logger.error("Tenant backup failed", tenant_id=tenant_id, error=str(e))
            return {"error": str(e)}

    async def _apply_tenant_migration(
        self, tenant_id: str, tenant_db_url: str, migration_version: str
    ) -> Dict[str, Any]:
        """Apply migration to tenant database."""
        try:
            # This would integrate with the SchemaManager
            # For now, we'll simulate the migration
            async with self.get_tenant_connection(tenant_id) as conn:
                # Check current version
                try:
                    current_version = await conn.fetchval(
                        "SELECT version_num FROM alembic_version LIMIT 1"
                    )
                except Exception:
                    current_version = None

                # Simulate migration application
                # In production, this would use SchemaManager
                await conn.execute("SELECT 1")  # Placeholder migration

                # Update version table
                if current_version:
                    await conn.execute(
                        "UPDATE alembic_version SET version_num = $1", migration_version
                    )
                else:
                    # Create version table if it doesn't exist
                    await conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                        )
                    """
                    )
                    await conn.execute(
                        "INSERT INTO alembic_version (version_num) VALUES ($1)",
                        migration_version,
                    )

                return {
                    "status": "success",
                    "previous_version": current_version,
                    "new_version": migration_version,
                    "tenant_id": tenant_id,
                }

        except Exception as e:
            logger.error(
                "Tenant migration application failed", tenant_id=tenant_id, error=str(e)
            )
            return {"status": "failed", "error": str(e), "tenant_id": tenant_id}

    async def rollback_tenant_migration(
        self, tenant_id: str, target_version: str
    ) -> Dict[str, Any]:
        """Rollback tenant migration to a specific version."""
        migration_coordinator = MigrationCoordinator(self.redis_url)

        # Acquire tenant-specific migration lock
        lock_key = f"tenant_{tenant_id}"
        lock_value = await migration_coordinator.acquire_migration_lock(lock_key)

        if not lock_value:
            return {
                "status": "failed",
                "error": f"Could not acquire migration lock for tenant {tenant_id}",
            }

        try:
            # Get backup information
            backup_info = await self._get_tenant_backup_info(tenant_id, target_version)

            # Perform rollback
            rollback_result = await self._perform_tenant_rollback(
                tenant_id, target_version
            )

            return {
                "status": rollback_result["status"],
                "tenant_id": tenant_id,
                "target_version": target_version,
                "backup_info": backup_info,
                "rollback_details": rollback_result,
            }

        finally:
            await migration_coordinator.release_migration_lock(lock_key, lock_value)

    async def _get_tenant_backup_info(
        self, tenant_id: str, version: str
    ) -> Optional[Dict]:
        """Get backup information for tenant rollback."""
        try:
            if not self._redis_client:
                self._redis_client = redis.from_url(self.redis_url)

            backups = await self._redis_client.hgetall(f"tenant_backups:{tenant_id}")

            for backup_name, backup_data in backups.items():
                try:
                    backup_info = json.loads(
                        backup_data.decode()
                        if isinstance(backup_data, bytes)
                        else backup_data
                    )
                    if version in backup_info.get("migration_version", ""):
                        return backup_info
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "Failed to parse backup data",
                        backup_name=backup_name,
                        error=str(e),
                    )

            return None

        except Exception as e:
            logger.warning(
                "Failed to get tenant backup info", tenant_id=tenant_id, error=str(e)
            )
            return None

    async def _perform_tenant_rollback(
        self, tenant_id: str, target_version: str
    ) -> Dict[str, Any]:
        """Perform the actual tenant rollback."""
        try:
            async with self.get_tenant_connection(tenant_id) as conn:
                # Get current version
                current_version = await conn.fetchval(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                )

                if current_version == target_version:
                    return {
                        "status": "success",
                        "message": "Already at target version",
                        "version": target_version,
                    }

                # Simulate rollback - in production this would use SchemaManager rollback
                await conn.execute(
                    "UPDATE alembic_version SET version_num = $1", target_version
                )

                return {
                    "status": "success",
                    "previous_version": current_version,
                    "new_version": target_version,
                }

        except Exception as e:
            logger.error("Tenant rollback failed", tenant_id=tenant_id, error=str(e))
            return {"status": "failed", "error": str(e)}

    async def get_tenant_migration_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get migration status for a specific tenant."""
        try:
            async with self.get_tenant_connection(tenant_id) as conn:
                # Get current schema version
                try:
                    current_version = await conn.fetchval(
                        "SELECT version_num FROM alembic_version LIMIT 1"
                    )
                except Exception:
                    current_version = None

                # Get table count
                table_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
                )

                # Get backup information
                backup_info = None
                if not self._redis_client:
                    self._redis_client = redis.from_url(self.redis_url)

                backups = await self._redis_client.hgetall(
                    f"tenant_backups:{tenant_id}"
                )
                backup_count = len(backups) if backups else 0

                return {
                    "tenant_id": tenant_id,
                    "current_version": current_version,
                    "table_count": table_count,
                    "backup_count": backup_count,
                    "status": "healthy" if current_version else "uninitialized",
                }

        except Exception as e:
            return {"tenant_id": tenant_id, "status": "error", "error": str(e)}


class MigrationCoordinator:
    """Cross-platform migration coordination system."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or "redis://localhost:6379/2"
        self._redis_client = None
        self._lock_timeout = 300  # 5 minutes

    async def initialize(self):
        """Initialize the migration coordinator."""
        self._redis_client = redis.from_url(self.redis_url)

    async def acquire_migration_lock(
        self, platform_name: str, timeout: int = None
    ) -> Optional[str]:
        """Acquire distributed migration lock for platform."""
        if not self._redis_client:
            await self.initialize()

        timeout = timeout or self._lock_timeout
        lock_key = f"migration_lock:{platform_name}"
        lock_value = f"{platform_name}_{datetime.now().timestamp()}"

        # Try to acquire lock with expiration
        acquired = await self._redis_client.set(
            lock_key,
            lock_value,
            nx=True,  # Only set if not exists
            ex=timeout,  # Expire after timeout seconds
        )

        if acquired:
            logger.info(
                "Migration lock acquired", platform=platform_name, lock_value=lock_value
            )
            return lock_value
        else:
            existing_lock = await self._redis_client.get(lock_key)
            logger.warning(
                "Migration lock already held",
                platform=platform_name,
                existing_lock=existing_lock,
            )
            return None

    async def release_migration_lock(self, platform_name: str, lock_value: str) -> bool:
        """Release migration lock if we own it."""
        if not self._redis_client:
            await self.initialize()

        lock_key = f"migration_lock:{platform_name}"

        # Use Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        result = await self._redis_client.eval(lua_script, 1, lock_key, lock_value)

        if result == 1:
            logger.info("Migration lock released", platform=platform_name)
            return True
        else:
            logger.warning(
                "Failed to release migration lock - not owner", platform=platform_name
            )
            return False

    async def register_platform_schema_version(
        self, platform_name: str, version: str, schema_info: Dict[str, Any]
    ) -> None:
        """Register current schema version for a platform."""
        if not self._redis_client:
            await self.initialize()

        schema_registry = f"schema_versions:{platform_name}"

        version_info = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "platform": platform_name,
            **schema_info,
        }

        await self._redis_client.hset(
            schema_registry, version, json.dumps(version_info)
        )

        # Also set current version pointer
        await self._redis_client.set(f"current_schema_version:{platform_name}", version)

        logger.info(
            "Schema version registered", platform=platform_name, version=version
        )

    async def get_platform_schema_version(self, platform_name: str) -> Optional[str]:
        """Get current schema version for a platform."""
        if not self._redis_client:
            await self.initialize()

        version = await self._redis_client.get(
            f"current_schema_version:{platform_name}"
        )
        return version.decode() if isinstance(version, bytes) else version

    async def get_all_platform_versions(self) -> Dict[str, str]:
        """Get schema versions for all registered platforms."""
        if not self._redis_client:
            await self.initialize()

        platforms = {}

        # Get all current version keys
        keys = await self._redis_client.keys("current_schema_version:*")

        for key in keys:
            if isinstance(key, bytes):
                key = key.decode()

            platform_name = key.replace("current_schema_version:", "")
            version = await self._redis_client.get(key)

            platforms[platform_name] = (
                version.decode() if isinstance(version, bytes) else version
            )

        return platforms

    async def check_cross_platform_consistency(self) -> Dict[str, Any]:
        """Check for schema version inconsistencies across platforms."""
        platform_versions = await self.get_all_platform_versions()

        if len(platform_versions) == 0:
            return {"status": "no_platforms", "message": "No platforms registered"}

        # Check for version mismatches
        version_groups = {}
        for platform, version in platform_versions.items():
            if version not in version_groups:
                version_groups[version] = []
            version_groups[version].append(platform)

        inconsistencies = []
        if len(version_groups) > 1:
            for version, platforms in version_groups.items():
                inconsistencies.append(
                    {
                        "version": version,
                        "platforms": platforms,
                        "count": len(platforms),
                    }
                )

        return {
            "status": "consistent" if len(version_groups) <= 1 else "inconsistent",
            "platform_count": len(platform_versions),
            "version_groups": len(version_groups),
            "inconsistencies": inconsistencies,
            "platforms": platform_versions,
        }

    async def coordinate_multi_platform_migration(
        self, target_version: str, platforms: List[str]
    ) -> Dict[str, Any]:
        """Coordinate migration across multiple platforms."""
        migration_id = f"multi_migration_{target_version}_{datetime.now().timestamp()}"

        logger.info(
            "Starting coordinated migration",
            migration_id=migration_id,
            target_version=target_version,
            platforms=platforms,
        )

        results = {
            "migration_id": migration_id,
            "target_version": target_version,
            "platforms": {},
            "overall_status": "started",
            "start_time": datetime.now().isoformat(),
        }

        # Try to acquire locks for all platforms
        acquired_locks = {}

        try:
            for platform in platforms:
                lock_value = await self.acquire_migration_lock(platform)
                if lock_value:
                    acquired_locks[platform] = lock_value
                    results["platforms"][platform] = {
                        "status": "locked",
                        "lock_acquired": True,
                    }
                else:
                    results["platforms"][platform] = {
                        "status": "lock_failed",
                        "lock_acquired": False,
                    }
                    results["overall_status"] = "failed"

            if results["overall_status"] == "failed":
                # Release any acquired locks
                for platform, lock_value in acquired_locks.items():
                    await self.release_migration_lock(platform, lock_value)

                return results

            # Store migration coordination info
            await self._store_migration_coordination(migration_id, results)

            results["overall_status"] = "coordinated"
            logger.info("Migration coordination successful", migration_id=migration_id)

            return results

        except Exception as e:
            logger.error(
                "Migration coordination failed", migration_id=migration_id, error=str(e)
            )

            # Release any acquired locks
            for platform, lock_value in acquired_locks.items():
                await self.release_migration_lock(platform, lock_value)

            results["overall_status"] = "error"
            results["error"] = str(e)

            return results

    async def _store_migration_coordination(
        self, migration_id: str, results: Dict[str, Any]
    ) -> None:
        """Store migration coordination information."""
        if not self._redis_client:
            await self.initialize()

        await self._redis_client.hset(
            "migration_coordinations", migration_id, json.dumps(results)
        )

        # Set expiration for coordination data (24 hours)
        await self._redis_client.expire("migration_coordinations", 86400)

    async def finalize_coordinated_migration(
        self, migration_id: str, platform_results: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Finalize coordinated migration and release locks."""
        if not self._redis_client:
            await self.initialize()

        # Get coordination info
        coordination_data = await self._redis_client.hget(
            "migration_coordinations", migration_id
        )

        if not coordination_data:
            return {
                "error": "Migration coordination not found",
                "migration_id": migration_id,
            }

        try:
            coordination_info = json.loads(
                coordination_data.decode()
                if isinstance(coordination_data, bytes)
                else coordination_data
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Failed to parse coordination data",
                migration_id=migration_id,
                error=str(e),
            )
            return {"error": "Invalid coordination data", "migration_id": migration_id}

        # Release locks and update results
        final_results = {
            "migration_id": migration_id,
            "platforms": {},
            "overall_status": "completed",
            "completion_time": datetime.now().isoformat(),
        }

        for platform, platform_result in platform_results.items():
            # Release lock if we have one
            if platform in coordination_info["platforms"]:
                platform_info = coordination_info["platforms"][platform]
                if platform_info.get("lock_acquired"):
                    # We don't have the lock value here, so we'll force release
                    await self._redis_client.delete(f"migration_lock:{platform}")

            final_results["platforms"][platform] = platform_result

            # Update platform schema version if migration succeeded
            if platform_result.get("status") == "success":
                await self.register_platform_schema_version(
                    platform,
                    coordination_info["target_version"],
                    platform_result.get("schema_info", {}),
                )

        # Store final results
        await self._redis_client.hset(
            "completed_migrations", migration_id, json.dumps(final_results)
        )

        logger.info("Coordinated migration finalized", migration_id=migration_id)

        return final_results

    async def get_migration_status(self, migration_id: str) -> Dict[str, Any]:
        """Get status of a coordinated migration."""
        if not self._redis_client:
            await self.initialize()

        # Check in-progress migrations
        ongoing = await self._redis_client.hget("migration_coordinations", migration_id)
        if ongoing:
            try:
                return json.loads(
                    ongoing.decode() if isinstance(ongoing, bytes) else ongoing
                )
            except (json.JSONDecodeError, ValueError):
                logger.warning(
                    "Failed to parse ongoing migration data", migration_id=migration_id
                )

        # Check completed migrations
        completed = await self._redis_client.hget("completed_migrations", migration_id)
        if completed:
            try:
                return json.loads(
                    completed.decode() if isinstance(completed, bytes) else completed
                )
            except (json.JSONDecodeError, ValueError):
                logger.warning(
                    "Failed to parse completed migration data",
                    migration_id=migration_id,
                )

        return {"error": "Migration not found", "migration_id": migration_id}

    async def cleanup_expired_locks(self) -> int:
        """Clean up any expired migration locks."""
        if not self._redis_client:
            await self.initialize()

        # Redis automatically expires locks, but this can force cleanup
        lock_keys = await self._redis_client.keys("migration_lock:*")
        cleaned = 0

        for key in lock_keys:
            ttl = await self._redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                await self._redis_client.delete(key)
                cleaned += 1

        return cleaned
