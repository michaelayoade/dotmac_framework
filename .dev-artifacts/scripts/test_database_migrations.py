#!/usr/bin/env python3
"""
Database Migration Testing Script

This script validates Alembic migrations can be applied and rolled back cleanly.
Used in CI/CD pipeline for Gate B validation.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationTester:
    def __init__(self, alembic_cfg_path: str = "alembic.ini"):
        self.alembic_cfg = alembic_cfg_path
        self.migrations_applied = []
        
    def run_alembic_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run alembic command and return success status and output."""
        try:
            full_cmd = ["alembic", "-c", self.alembic_cfg] + cmd
            result = subprocess.run(
                full_cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=60
            )
            return True, result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            return False, f"Command failed: {e.stdout + e.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 60 seconds"
            
    def get_current_revision(self) -> str:
        """Get current database revision."""
        success, output = self.run_alembic_command(["current"])
        if success:
            # Parse revision from output
            for line in output.split('\n'):
                if 'Rev:' in line:
                    return line.split('Rev:')[1].strip().split()[0]
        return "unknown"
    
    def get_migration_history(self) -> List[str]:
        """Get list of available migrations."""
        success, output = self.run_alembic_command(["history"])
        revisions = []
        if success:
            for line in output.split('\n'):
                if 'Rev:' in line:
                    rev = line.split('Rev:')[1].strip().split()[0]
                    if rev not in revisions:
                        revisions.append(rev)
        return revisions
        
    def test_upgrade_to_head(self) -> bool:
        """Test upgrading to latest migration."""
        logger.info("Testing upgrade to head...")
        success, output = self.run_alembic_command(["upgrade", "head"])
        if success:
            logger.info("✅ Upgrade to head successful")
            return True
        else:
            logger.error(f"❌ Upgrade to head failed: {output}")
            return False
            
    def test_downgrade_rollback(self) -> bool:
        """Test downgrading one step and upgrading back."""
        logger.info("Testing downgrade/rollback...")
        
        # Get current revision before downgrade
        initial_rev = self.get_current_revision()
        logger.info(f"Current revision: {initial_rev}")
        
        # Downgrade one step
        success, output = self.run_alembic_command(["downgrade", "-1"])
        if not success:
            logger.error(f"❌ Downgrade failed: {output}")
            return False
            
        downgraded_rev = self.get_current_revision()
        logger.info(f"Downgraded to revision: {downgraded_rev}")
        
        # Upgrade back to head
        success, output = self.run_alembic_command(["upgrade", "head"])
        if not success:
            logger.error(f"❌ Re-upgrade failed: {output}")
            return False
            
        final_rev = self.get_current_revision()
        logger.info(f"Final revision: {final_rev}")
        
        if final_rev == initial_rev:
            logger.info("✅ Downgrade/rollback test successful")
            return True
        else:
            logger.error(f"❌ Rollback failed - expected {initial_rev}, got {final_rev}")
            return False
            
    def test_migration_consistency(self) -> bool:
        """Test that migrations can be applied from scratch."""
        logger.info("Testing migration consistency from scratch...")
        
        # Downgrade to base
        success, output = self.run_alembic_command(["downgrade", "base"])
        if not success:
            logger.warning(f"Could not downgrade to base: {output}")
            
        # Upgrade to head
        success, output = self.run_alembic_command(["upgrade", "head"])
        if success:
            logger.info("✅ Migration consistency test successful")
            return True
        else:
            logger.error(f"❌ Migration consistency test failed: {output}")
            return False
            
    def validate_alembic_config(self) -> bool:
        """Validate alembic configuration is correct."""
        logger.info("Validating Alembic configuration...")
        
        if not Path(self.alembic_cfg).exists():
            logger.error(f"❌ Alembic config file not found: {self.alembic_cfg}")
            return False
            
        # Check if we can get current revision
        success, output = self.run_alembic_command(["current"])
        if success:
            logger.info("✅ Alembic configuration valid")
            return True
        else:
            logger.error(f"❌ Alembic configuration invalid: {output}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all migration tests."""
        logger.info("🧪 Starting database migration tests...")
        
        tests = [
            ("Configuration Validation", self.validate_alembic_config),
            ("Upgrade to Head", self.test_upgrade_to_head),
            ("Downgrade/Rollback", self.test_downgrade_rollback),
            ("Migration Consistency", self.test_migration_consistency)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n📊 Migration Test Summary:")
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status}: {test_name}")
            if not passed:
                all_passed = False
                
        if all_passed:
            logger.info("🎉 All migration tests passed!")
        else:
            logger.error("💥 Some migration tests failed!")
            
        return all_passed

def main():
    """Main entry point."""
    # Check for required environment variables
    required_vars = ["DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Find alembic.ini file
    alembic_paths = ["alembic.ini", "alembic/alembic.ini", "../alembic.ini"]
    alembic_cfg = None
    
    for path in alembic_paths:
        if Path(path).exists():
            alembic_cfg = path
            break
            
    if not alembic_cfg:
        logger.error("Could not find alembic.ini configuration file")
        sys.exit(1)
        
    logger.info(f"Using Alembic config: {alembic_cfg}")
    
    # Run migration tests
    tester = MigrationTester(alembic_cfg)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()