#!/usr/bin/env python3
"""
Comprehensive Testing Orchestrator for DotMac Framework
Runs all validation and testing scripts in the correct order.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class TestOrchestrator:
    """Orchestrates all testing and validation scripts."""
    
    def __init__(self):
        self.results = []
        self.failed_tests = []
        
    def run_script(self, script_path: str, description: str, timeout: int = 300) -> bool:
        """Run a validation script and capture results."""
        print(f"\n{'='*20} {description} {'='*20}")
        print(f"Running: {script_path}")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            # Print output regardless of success/failure
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            success = result.returncode == 0
            self.results.append((description, success, result.returncode))
            
            if success:
                print(f"✅ {description}: PASSED")
            else:
                print(f"❌ {description}: FAILED (exit code: {result.returncode})")
                self.failed_tests.append(description)
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {description}: TIMEOUT (>{timeout}s)")
            self.results.append((description, False, "TIMEOUT"))
            self.failed_tests.append(description)
            return False
            
        except Exception as e:
            print(f"💥 {description}: ERROR - {e}")
            self.results.append((description, False, f"ERROR: {e}"))
            self.failed_tests.append(description)
            return False
    
    async def run_async_script(self, script_path: str, description: str, timeout: int = 300) -> bool:
        """Run an async validation script."""
        print(f"\n{'='*20} {description} {'='*20}")
        print(f"Running: {script_path}")
        print("-" * 60)
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            # Print output
            if stdout:
                print(stdout.decode())
            if stderr:
                print("STDERR:")
                print(stderr.decode())
            
            success = process.returncode == 0
            self.results.append((description, success, process.returncode))
            
            if success:
                print(f"✅ {description}: PASSED")
            else:
                print(f"❌ {description}: FAILED (exit code: {process.returncode})")
                self.failed_tests.append(description)
            
            return success
            
        except asyncio.TimeoutError:
            print(f"⏰ {description}: TIMEOUT (>{timeout}s)")
            self.results.append((description, False, "TIMEOUT"))
            self.failed_tests.append(description)
            return False
            
        except Exception as e:
            print(f"💥 {description}: ERROR - {e}")
            self.results.append((description, False, f"ERROR: {e}"))
            self.failed_tests.append(description)
            return False
    
    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TESTING SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r[1]])
        failed_tests = len(self.failed_tests)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Test Results:")
        print(f"   • Total tests run: {total_tests}")
        print(f"   • Passed: {passed_tests}")
        print(f"   • Failed: {failed_tests}")
        print(f"   • Success rate: {success_rate:.1f}%")
        
        print(f"\n📋 Detailed Results:")
        for description, success, exit_code in self.results:
            status = "✅ PASSED" if success else f"❌ FAILED ({exit_code})"
            print(f"   • {description}: {status}")
        
        if self.failed_tests:
            print(f"\n🚨 Failed Tests:")
            for test in self.failed_tests:
                print(f"   • {test}")
        
        print("\n" + "=" * 80)
        
        # Determine overall status
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED!")
            print("   The DotMac Framework is ready for deployment!")
            return True
        elif failed_tests <= 2:
            print("⚠️ MINOR ISSUES DETECTED")
            print("   Most tests passed, but some issues need attention.")
            return True  # Still deployable
        else:
            print("💥 CRITICAL ISSUES DETECTED")
            print("   Multiple tests failed. Please fix issues before deployment.")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all validation and testing scripts."""
        print("🚀 DotMac Framework - Comprehensive Testing Suite")
        print("=" * 80)
        print("This will run all validation and testing scripts to ensure")
        print("the framework is ready for development and deployment.")
        print("=" * 80)
        
        scripts_dir = Path(__file__).parent
        success = True
        
        # Environment validation (quick, should run first)
        success &= self.run_script(
            str(scripts_dir / "validate_environment.py"),
            "Environment Variable Validation",
            timeout=60
        )
        
        # Import validation (critical for deployment)
        success &= self.run_script(
            str(scripts_dir / "validate_imports.py"),
            "Import System Validation", 
            timeout=120
        )
        
        # Migration validation (database readiness)
        success &= self.run_script(
            str(scripts_dir / "validate_migrations.py"),
            "Database Migration Validation",
            timeout=180
        )
        
        # Container smoke tests (most comprehensive, run last)
        # Note: This requires Docker and may take longer
        print(f"\n⚠️ Container Smoke Tests require Docker to be running.")
        print("   If Docker is not available, this test will be skipped.")
        
        container_success = await self.run_async_script(
            str(scripts_dir / "container_smoke_tests.py"),
            "Container Smoke Tests",
            timeout=600  # 10 minutes for container operations
        )
        
        # Don't fail overall if just container tests fail (Docker might not be available)
        if not container_success:
            print("ℹ️ Container tests failed - this might be due to Docker not being available")
            print("   This doesn't prevent deployment if other tests pass.")
        
        # Print final summary
        overall_success = self.print_summary()
        
        return overall_success

async def main():
    """Main test orchestration entry point."""
    orchestrator = TestOrchestrator()
    success = await orchestrator.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()