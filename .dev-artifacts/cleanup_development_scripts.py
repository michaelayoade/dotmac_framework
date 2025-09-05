#!/usr/bin/env python3
"""
Development Script Cleanup

Remove temporary development scripts and keep only operational tools.
"""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Scripts to remove (development artifacts)
DEVELOPMENT_ARTIFACTS = [
    'scripts/comprehensive_cleanup.py',  # Meta-cleanup script
    'scripts/dry_test_orchestration_final.py',  # Temporary test orchestration
    'scripts/fresh_test_architecture.py',  # Architecture experiment
    'scripts/dependency_cleanup.py',  # One-time cleanup
]

# Keep these operational scripts
OPERATIONAL_SCRIPTS = [
    'scripts/production_readiness_check.py',
    'scripts/security_validation.py', 
    'scripts/validate-vps-deployment.py',
    'scripts/deployment_validation.py',
    'scripts/run_comprehensive_tests.py',  # CI/CD testing
    'scripts/module_scaffolding/',  # Developer tooling
    'deployment/scripts/disaster_recovery.py',
    'examples/',  # Living documentation
]

def main():
    """Remove development artifacts while preserving operational tools."""
    
    logger.info("Starting cleanup of development artifacts")
    
    removed_count = 0
    
    for artifact in DEVELOPMENT_ARTIFACTS:
        artifact_path = Path(artifact)
        
        if artifact_path.exists():
            try:
                if artifact_path.is_file():
                    artifact_path.unlink()
                    logger.info(f"Removed file: {artifact}")
                    removed_count += 1
                elif artifact_path.is_dir():
                    import shutil
                    shutil.rmtree(artifact_path)
                    logger.info(f"Removed directory: {artifact}")
                    removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove {artifact}: {e}")
        else:
            logger.debug(f"Artifact not found: {artifact}")
    
    logger.info(f"Cleanup completed. Removed {removed_count} development artifacts")
    
    # Log what was kept for reference
    logger.info("Operational scripts preserved:")
    for script in OPERATIONAL_SCRIPTS:
        if Path(script).exists():
            logger.info(f"  ✓ {script}")

if __name__ == "__main__":
    main()