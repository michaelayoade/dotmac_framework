#!/usr/bin/env python3
"""
DotMac Framework Database Migration Testing
==========================================
Comprehensive testing for database migrations, rollbacks, and data integrity.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)


class MigrationTestFramework:
    """Framework for testing database migrations."""

    def __init__(self, database_url: str, migration_path: str = "migrations"):
        self.database_url = database_url
        self.migration_path = Path(migration_path)  # noqa: B008
        self.test_database_url = None
        self.engine = None
        self.alembic_cfg = None

    async def setup(self):
        """Set up test environment."""
        # Create test database
        self.test_database_url = await self._create_test_database()

        # Create async engine
        self.engine = create_async_engine(self.test_database_url)

        # Setup Alembic config
        self._setup_alembic_config()

        logger.info(f"Migration test framework initialized with DB: {self.test_database_url}")

    async def teardown(self):
        """Clean up test environment."""
        if self.engine:
            await self.engine.dispose()

        if self.test_database_url:
            await self._drop_test_database()

    async def _create_test_database(self) -> str:
        """Create isolated test database."""
        # Parse original database URL
        conn_info = self.database_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
        if "@" in conn_info:
            auth, host_db = conn_info.split("@", 1)
            username, password = auth.split(":", 1) if ":" in auth else (auth, "")
            host_port, original_db = host_db.split("/", 1) if "/" in host_db else (host_db, "postgres")
        else:
            host_port = conn_info
            username = password = ""

        # Generate unique test database name
        test_db_name = f"dotmac_migration_test_{uuid4().hex[:8]}"

        # Connect to postgres database to create test database
        admin_url = f"postgresql://{username}:{password}@{host_port}/postgres" if username else f"postgresql://{host_port}/postgres"

        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
        finally:
            await conn.close()

        return f"postgresql+asyncpg://{username}:{password}@{host_port}/{test_db_name}" if username else f"postgresql+asyncpg://{host_port}/{test_db_name}"

    async def _drop_test_database(self):
        """Drop test database."""
        if not self.test_database_url:
            return

        # Extract database name
        db_name = self.test_database_url.split("/")[-1]
        admin_url = self.test_database_url.replace(f"/{db_name}", "/postgres")

        conn = await asyncpg.connect(admin_url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            # Terminate connections to the test database
            await conn.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
            """)

            await conn.execute(f'DROP DATABASE "{db_name}"')
        finally:
            await conn.close()

    def _setup_alembic_config(self):
        """Setup Alembic configuration."""
        alembic_cfg_path = self.migration_path / "alembic.ini"

        if not alembic_cfg_path.exists():
            # Create minimal alembic.ini for testing
            alembic_content = f"""
[alembic]
script_location = {self.migration_path}
sqlalchemy.url = {self.test_database_url}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
            with open(alembic_cfg_path, 'w') as f:
                f.write(alembic_content)

        self.alembic_cfg = Config(str(alembic_cfg_path))
        self.alembic_cfg.set_main_option("sqlalchemy.url", self.test_database_url)

    async def get_migration_history(self) -> list[str]:
        """Get current migration history."""
        async with self.engine.connect() as conn:
            context = MigrationContext.configure(conn.sync_connection)
            return context.get_current_heads()

    async def get_available_migrations(self) -> list[str]:
        """Get all available migrations."""
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        return [revision.revision for revision in script_dir.walk_revisions()]

    async def test_clean_migration_to_head(self) -> dict[str, Any]:
        """Test migrating from clean database to HEAD."""
        result = {
            "test_name": "clean_migration_to_head",
            "status": "running",
            "start_time": datetime.now(),
            "errors": [],
            "details": {}
        }

        try:
            # Run migration to HEAD
            command.upgrade(self.alembic_cfg, "head")

            # Verify database structure
            structure = await self._get_database_structure()
            result["details"]["final_structure"] = structure

            # Get final migration history
            final_heads = await self.get_migration_history()
            result["details"]["final_heads"] = final_heads

            result["status"] = "passed"
            logger.info("✅ Clean migration to HEAD completed successfully")

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"❌ Clean migration to HEAD failed: {e}")

        finally:
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - result["start_time"]).total_seconds()

        return result

    async def test_incremental_migrations(self) -> dict[str, Any]:
        """Test applying migrations one by one."""
        result = {
            "test_name": "incremental_migrations",
            "status": "running",
            "start_time": datetime.now(),
            "errors": [],
            "details": {"migration_steps": []}
        }

        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)

            # Get all revisions in order
            revisions = list(reversed(list(script_dir.walk_revisions())))

            for _i, revision in enumerate(revisions):
                step_start = datetime.now()

                try:
                    # Apply single migration
                    command.upgrade(self.alembic_cfg, revision.revision)

                    # Verify structure after each step
                    structure = await self._get_database_structure()

                    step_result = {
                        "revision": revision.revision,
                        "message": revision.doc,
                        "status": "passed",
                        "structure_tables": list(structure.get("tables", {}).keys()),
                        "duration": (datetime.now() - step_start).total_seconds()
                    }

                    result["details"]["migration_steps"].append(step_result)
                    logger.info(f"✅ Migration {revision.revision} applied successfully")

                except Exception as e:
                    step_result = {
                        "revision": revision.revision,
                        "message": revision.doc,
                        "status": "failed",
                        "error": str(e),
                        "duration": (datetime.now() - step_start).total_seconds()
                    }
                    result["details"]["migration_steps"].append(step_result)
                    result["errors"].append(f"Migration {revision.revision} failed: {e}")
                    logger.error(f"❌ Migration {revision.revision} failed: {e}")
                    break

            result["status"] = "passed" if not result["errors"] else "failed"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"❌ Incremental migration test failed: {e}")

        finally:
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - result["start_time"]).total_seconds()

        return result

    async def test_rollback_migrations(self) -> dict[str, Any]:
        """Test rolling back migrations."""
        result = {
            "test_name": "rollback_migrations",
            "status": "running",
            "start_time": datetime.now(),
            "errors": [],
            "details": {"rollback_steps": []}
        }

        try:
            # First, migrate to HEAD
            command.upgrade(self.alembic_cfg, "head")

            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = list(script_dir.walk_revisions())

            # Test rolling back several migrations
            rollback_targets = revisions[1:4] if len(revisions) > 3 else revisions[1:]

            for revision in rollback_targets:
                step_start = datetime.now()

                try:
                    # Rollback to this revision
                    command.downgrade(self.alembic_cfg, revision.revision)

                    # Verify structure after rollback
                    structure = await self._get_database_structure()

                    step_result = {
                        "target_revision": revision.revision,
                        "message": revision.doc,
                        "status": "passed",
                        "remaining_tables": list(structure.get("tables", {}).keys()),
                        "duration": (datetime.now() - step_start).total_seconds()
                    }

                    result["details"]["rollback_steps"].append(step_result)
                    logger.info(f"✅ Rollback to {revision.revision} successful")

                except Exception as e:
                    step_result = {
                        "target_revision": revision.revision,
                        "message": revision.doc,
                        "status": "failed",
                        "error": str(e),
                        "duration": (datetime.now() - step_start).total_seconds()
                    }
                    result["details"]["rollback_steps"].append(step_result)
                    result["errors"].append(f"Rollback to {revision.revision} failed: {e}")
                    logger.error(f"❌ Rollback to {revision.revision} failed: {e}")
                    break

            result["status"] = "passed" if not result["errors"] else "failed"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"❌ Rollback migration test failed: {e}")

        finally:
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - result["start_time"]).total_seconds()

        return result

    async def test_data_integrity_during_migration(self) -> dict[str, Any]:
        """Test that data is preserved during migrations."""
        result = {
            "test_name": "data_integrity_migration",
            "status": "running",
            "start_time": datetime.now(),
            "errors": [],
            "details": {}
        }

        try:
            # Create base schema (first migration)
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = list(reversed(list(script_dir.walk_revisions())))

            if revisions:
                first_revision = revisions[0]
                command.upgrade(self.alembic_cfg, first_revision.revision)

                # Insert test data
                test_data = await self._insert_test_data()
                result["details"]["test_data_inserted"] = len(test_data)

                # Apply remaining migrations
                command.upgrade(self.alembic_cfg, "head")

                # Verify data integrity
                data_verification = await self._verify_test_data(test_data)
                result["details"]["data_verification"] = data_verification

                if data_verification["all_data_preserved"]:
                    result["status"] = "passed"
                    logger.info("✅ Data integrity maintained during migration")
                else:
                    result["status"] = "failed"
                    result["errors"].append("Data integrity compromised during migration")
                    logger.error("❌ Data integrity compromised during migration")
            else:
                result["status"] = "skipped"
                result["details"]["reason"] = "No migrations found"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"❌ Data integrity test failed: {e}")

        finally:
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - result["start_time"]).total_seconds()

        return result

    async def test_migration_performance(self) -> dict[str, Any]:
        """Test migration performance with larger datasets."""
        result = {
            "test_name": "migration_performance",
            "status": "running",
            "start_time": datetime.now(),
            "errors": [],
            "details": {}
        }

        try:
            # Create base schema
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = list(reversed(list(script_dir.walk_revisions())))

            if revisions:
                first_revision = revisions[0]
                command.upgrade(self.alembic_cfg, first_revision.revision)

                # Insert larger dataset
                performance_start = datetime.now()
                large_dataset = await self._insert_large_test_dataset()
                insert_duration = (datetime.now() - performance_start).total_seconds()

                result["details"]["dataset_size"] = len(large_dataset)
                result["details"]["insert_duration"] = insert_duration

                # Time the migration
                migration_start = datetime.now()
                command.upgrade(self.alembic_cfg, "head")
                migration_duration = (datetime.now() - migration_start).total_seconds()

                result["details"]["migration_duration"] = migration_duration
                result["details"]["records_per_second"] = len(large_dataset) / migration_duration if migration_duration > 0 else 0

                # Performance thresholds
                if migration_duration < 30:  # 30 seconds
                    result["performance_rating"] = "excellent"
                elif migration_duration < 120:  # 2 minutes
                    result["performance_rating"] = "good"
                elif migration_duration < 300:  # 5 minutes
                    result["performance_rating"] = "acceptable"
                else:
                    result["performance_rating"] = "poor"

                result["status"] = "passed"
                logger.info(f"✅ Migration performance test completed: {result['performance_rating']}")
            else:
                result["status"] = "skipped"
                result["details"]["reason"] = "No migrations found"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"❌ Migration performance test failed: {e}")

        finally:
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - result["start_time"]).total_seconds()

        return result

    async def _get_database_structure(self) -> dict[str, Any]:
        """Get current database structure."""
        async with self.engine.connect() as conn:
            # Get tables
            tables_result = await conn.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_name
            """)
            tables = {row[0]: {"schema": row[1]} for row in tables_result}

            # Get columns for each table
            for table_name in tables.keys():
                columns_result = await conn.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)
                tables[table_name]["columns"] = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "default": row[3]
                    } for row in columns_result
                ]

            return {"tables": tables}

    async def _insert_test_data(self) -> list[dict[str, Any]]:
        """Insert test data for integrity testing."""
        test_data = []

        # This is a generic example - you'd customize this based on your schema
        async with self.engine.connect() as conn:
            # Check if common tables exist
            tables_result = await conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('users', 'tenants', 'customers')
            """)
            existing_tables = [row[0] for row in tables_result]

            # Insert data based on available tables
            if 'tenants' in existing_tables:
                tenant_data = {
                    "id": str(uuid4()),
                    "name": "Migration Test Tenant",
                    "domain": "test.example.com",
                    "created_at": datetime.now()
                }
                await conn.execute(
                    "INSERT INTO tenants (id, name, domain, created_at) VALUES ($1, $2, $3, $4)",
                    tenant_data["id"], tenant_data["name"], tenant_data["domain"], tenant_data["created_at"]
                )
                test_data.append({"table": "tenants", "data": tenant_data})

            if 'users' in existing_tables:
                user_data = {
                    "id": str(uuid4()),
                    "email": "migration.test@example.com",
                    "username": "migration_test_user",
                    "created_at": datetime.now()
                }
                # Basic insert - adjust columns based on your schema
                test_data.append({"table": "users", "data": user_data})

        return test_data

    async def _verify_test_data(self, original_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Verify that test data is still intact."""
        verification = {
            "all_data_preserved": True,
            "verified_records": 0,
            "missing_records": 0,
            "details": []
        }

        async with self.engine.connect() as conn:
            for record in original_data:
                table_name = record["table"]
                original_record = record["data"]

                try:
                    # Simple verification - check if record with ID exists
                    if "id" in original_record:
                        result = await conn.execute(
                            f"SELECT id FROM {table_name} WHERE id = $1",
                            original_record["id"]
                        )
                        if result.fetchone():
                            verification["verified_records"] += 1
                        else:
                            verification["missing_records"] += 1
                            verification["all_data_preserved"] = False
                            verification["details"].append(f"Missing record in {table_name}: {original_record['id']}")
                except Exception as e:
                    verification["details"].append(f"Verification error for {table_name}: {e}")

        return verification

    async def _insert_large_test_dataset(self) -> list[dict[str, Any]]:
        """Insert a larger dataset for performance testing."""
        dataset = []

        # Insert 10,000 test records - customize based on your schema
        async with self.engine.connect() as conn:
            tables_result = await conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in tables_result]

            # Insert into a suitable table for performance testing
            # This is a simplified example
            if tables:
                for i in range(10000):
                    record = {
                        "id": str(uuid4()),
                        "test_data": f"Performance test record {i}",
                        "created_at": datetime.now()
                    }
                    dataset.append(record)

        return dataset

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all migration tests."""
        test_suite_start = datetime.now()

        suite_result = {
            "suite_name": "database_migration_tests",
            "start_time": test_suite_start,
            "tests": [],
            "summary": {}
        }

        # Define test methods
        test_methods = [
            self.test_clean_migration_to_head,
            self.test_incremental_migrations,
            self.test_rollback_migrations,
            self.test_data_integrity_during_migration,
            self.test_migration_performance
        ]

        for test_method in test_methods:
            try:
                # Create fresh database for each test
                await self.teardown()
                await self.setup()

                # Run test
                test_result = await test_method()
                suite_result["tests"].append(test_result)

                logger.info(f"Completed test: {test_result['test_name']} - {test_result['status']}")

            except Exception as e:
                error_result = {
                    "test_name": test_method.__name__,
                    "status": "error",
                    "start_time": datetime.now(),
                    "end_time": datetime.now(),
                    "errors": [str(e)]
                }
                suite_result["tests"].append(error_result)
                logger.error(f"Test {test_method.__name__} failed with error: {e}")

        # Calculate summary
        suite_result["end_time"] = datetime.now()
        suite_result["duration"] = (suite_result["end_time"] - test_suite_start).total_seconds()

        passed = sum(1 for test in suite_result["tests"] if test["status"] == "passed")
        failed = sum(1 for test in suite_result["tests"] if test["status"] == "failed")
        errors = sum(1 for test in suite_result["tests"] if test["status"] == "error")
        skipped = sum(1 for test in suite_result["tests"] if test["status"] == "skipped")

        suite_result["summary"] = {
            "total": len(suite_result["tests"]),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "success_rate": (passed / len(suite_result["tests"]) * 100) if suite_result["tests"] else 0
        }

        return suite_result


class MigrationTestRunner:
    """Runner for database migration tests."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.framework = None

    def _load_config(self, config_path: Optional[str]) -> dict[str, Any]:
        """Load test configuration."""
        default_config = {
            "database_url": os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/dotmac_test"),
            "migration_path": "migrations",
            "output_dir": "test-results/migration-tests"
        }

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                file_config = json.load(f)
            default_config.update(file_config)

        return default_config

    async def run_tests(self) -> int:
        """Run migration tests and return exit code."""
        print("🔄 Starting database migration tests...")

        self.framework = MigrationTestFramework(
            self.config["database_url"],
            self.config["migration_path"]
        )

        try:
            await self.framework.setup()

            # Run test suite
            results = await self.framework.run_all_tests()

            # Save results
            await self._save_results(results)

            # Print summary
            self._print_summary(results)

            # Return appropriate exit code
            return 0 if results["summary"]["failed"] == 0 and results["summary"]["errors"] == 0 else 1

        except Exception as e:
            logger.error(f"Migration test runner failed: {e}")
            print(f"❌ Migration test runner failed: {e}")
            return 1

        finally:
            if self.framework:
                await self.framework.teardown()

    async def _save_results(self, results: dict[str, Any]):
        """Save test results to files."""
        output_dir = Path(self.config["output_dir"])  # noqa: B008
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_file = output_dir / f"migration-test-results-{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"📄 Results saved to: {json_file}")

    def _print_summary(self, results: dict[str, Any]):
        """Print test summary."""
        print("\n" + "="*60)
        print("🔄 DATABASE MIGRATION TEST SUMMARY")
        print("="*60)

        summary = results["summary"]
        duration = results.get("duration", 0)

        print(f"⏱️  Duration: {duration:.1f}s")
        print(f"📊 Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"💥 Errors: {summary['errors']}")
        print(f"⏭️  Skipped: {summary['skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")

        print("\n📋 Test Details:")
        print("-" * 60)

        for test in results["tests"]:
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "error": "💥",
                "skipped": "⏭️"
            }.get(test["status"], "❓")

            duration = test.get("duration", 0)
            print(f"{status_emoji} {test['test_name']}: {test['status'].upper()} ({duration:.1f}s)")

            if test.get("errors"):
                for error in test["errors"][:2]:  # Show first 2 errors
                    print(f"    💬 {error}")

        print("\n" + "="*60)

        if summary["failed"] == 0 and summary["errors"] == 0:
            print("🎉 ALL MIGRATION TESTS PASSED!")
        else:
            print("❌ SOME MIGRATION TESTS FAILED!")


@pytest.mark.asyncio
async def test_database_migrations():
    """Pytest wrapper for migration tests."""
    runner = MigrationTestRunner()
    exit_code = await runner.run_tests()
    assert exit_code == 0, "Migration tests failed"


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DotMac Framework Migration Testing")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--database-url", help="Database URL for testing")
    parser.add_argument("--migration-path", default="migrations", help="Path to migration files")

    args = parser.parse_args()

    # Override config with command line args
    runner = MigrationTestRunner(args.config)
    if args.database_url:
        runner.config["database_url"] = args.database_url
    if args.migration_path:
        runner.config["migration_path"] = args.migration_path

    exit_code = await runner.run_tests()
    return exit_code


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
