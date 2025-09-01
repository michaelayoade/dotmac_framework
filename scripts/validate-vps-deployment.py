#!/usr/bin/env python3
"""
VPS Deployment Validation Script
Comprehensive validation for customer VPS deployments
"""

import asyncio
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import httpx
import paramiko
import subprocess
import socket

@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    status: str  # pass, fail, warning, skip
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None


class VPSValidator:
    """Comprehensive VPS deployment validator"""
    
    def __init__(self, vps_ip: str, ssh_port: int = 22, ssh_user: str = "root", ssh_key: str = None):
        self.vps_ip = vps_ip
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key = ssh_key
        self.results: List[ValidationResult] = []
    
    def log_result(self, result: ValidationResult):
        """Log validation result"""
        self.results.append(result)
        
        # Color output
        colors = {
            "pass": "\033[92m✅",
            "fail": "\033[91m❌",
            "warning": "\033[93m⚠️",
            "skip": "\033[94mℹ️"
        }
        reset = "\033[0m"
        
        icon = colors.get(result.status, "")
        print(f"{icon} {result.name}: {result.message}{reset}")
        
        if result.details and result.status in ["fail", "warning"]:
            for key, value in result.details.items():
                print(f"   {key}: {value}")
    
    async def validate_ssh_connectivity(self) -> ValidationResult:
        """Test SSH connectivity to VPS"""
        start_time = datetime.now()
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.vps_ip,
                'port': self.ssh_port,
                'username': self.ssh_user,
                'timeout': 10
            }
            
            if self.ssh_key:
                connect_kwargs['key_filename'] = self.ssh_key
            
            ssh.connect(**connect_kwargs)
            
            # Test command execution
            stdin, stdout, stderr = ssh.exec_command('echo "SSH test successful"')
            output = stdout.read().decode().strip()
            
            ssh.close()
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if output == "SSH test successful":
                return ValidationResult(
                    name="SSH Connectivity",
                    status="pass", 
                    message=f"Connected to {self.vps_ip}:{self.ssh_port} as {self.ssh_user}",
                    details={"response_time_ms": execution_time},
                    execution_time_ms=execution_time
                )
            else:
                return ValidationResult(
                    name="SSH Connectivity",
                    status="fail",
                    message="SSH connection established but command execution failed",
                    details={"output": output}
                )
                
        except Exception as e:
            return ValidationResult(
                name="SSH Connectivity",
                status="fail",
                message="SSH connection failed",
                details={"error": str(e)}
            )
    
    async def validate_system_requirements(self) -> List[ValidationResult]:
        """Validate system meets minimum requirements"""
        results = []
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.vps_ip,
                'port': self.ssh_port,
                'username': self.ssh_user,
                'timeout': 30
            }
            
            if self.ssh_key:
                connect_kwargs['key_filename'] = self.ssh_key
                
            ssh.connect(**connect_kwargs)
            
            # Get system specifications
            commands = {
                'cpu_cores': 'nproc',
                'memory_gb': 'free -g | awk "NR==2{print $2}"',
                'disk_gb': 'df -BG / | awk "NR==2{print $4}" | sed "s/G//"',
                'os_info': 'lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d "\\"',
                'architecture': 'uname -m'
            }
            
            specs = {}
            for spec_name, command in commands.items():
                try:
                    stdin, stdout, stderr = ssh.exec_command(command)
                    output = stdout.read().decode().strip()
                    specs[spec_name] = output
                except:
                    specs[spec_name] = "unknown"
            
            ssh.close()
            
            # Validate CPU
            try:
                cpu_cores = int(specs.get('cpu_cores', '0'))
                if cpu_cores >= 2:
                    results.append(ValidationResult(
                        name="CPU Requirements",
                        status="pass",
                        message=f"{cpu_cores} cores available (minimum: 2)",
                        details={"cpu_cores": cpu_cores}
                    ))
                else:
                    results.append(ValidationResult(
                        name="CPU Requirements", 
                        status="fail",
                        message=f"Insufficient CPU cores: {cpu_cores} (minimum: 2)",
                        details={"cpu_cores": cpu_cores, "minimum_required": 2}
                    ))
            except:
                results.append(ValidationResult(
                    name="CPU Requirements",
                    status="warning",
                    message="Could not determine CPU count",
                    details={"raw_output": specs.get('cpu_cores')}
                ))
            
            # Validate Memory
            try:
                memory_gb = int(specs.get('memory_gb', '0'))
                if memory_gb >= 4:
                    results.append(ValidationResult(
                        name="Memory Requirements",
                        status="pass", 
                        message=f"{memory_gb}GB RAM available (minimum: 4GB)",
                        details={"memory_gb": memory_gb}
                    ))
                else:
                    results.append(ValidationResult(
                        name="Memory Requirements",
                        status="fail",
                        message=f"Insufficient RAM: {memory_gb}GB (minimum: 4GB)",
                        details={"memory_gb": memory_gb, "minimum_required": 4}
                    ))
            except:
                results.append(ValidationResult(
                    name="Memory Requirements",
                    status="warning",
                    message="Could not determine memory amount",
                    details={"raw_output": specs.get('memory_gb')}
                ))
            
            # Validate Disk Space
            try:
                disk_gb = int(specs.get('disk_gb', '0'))
                if disk_gb >= 50:
                    results.append(ValidationResult(
                        name="Disk Space Requirements",
                        status="pass",
                        message=f"{disk_gb}GB available (minimum: 50GB)",
                        details={"disk_gb": disk_gb}
                    ))
                else:
                    results.append(ValidationResult(
                        name="Disk Space Requirements",
                        status="fail", 
                        message=f"Insufficient disk space: {disk_gb}GB (minimum: 50GB)",
                        details={"disk_gb": disk_gb, "minimum_required": 50}
                    ))
            except:
                results.append(ValidationResult(
                    name="Disk Space Requirements",
                    status="warning",
                    message="Could not determine available disk space",
                    details={"raw_output": specs.get('disk_gb')}
                ))
            
            # Validate OS
            os_info = specs.get('os_info', '').lower()
            supported_os = ['ubuntu', 'debian', 'centos', 'rocky', 'rhel']
            
            if any(os_name in os_info for os_name in supported_os):
                results.append(ValidationResult(
                    name="Operating System",
                    status="pass",
                    message=f"Supported OS detected: {specs.get('os_info')}",
                    details={"os_info": specs.get('os_info')}
                ))
            else:
                results.append(ValidationResult(
                    name="Operating System",
                    status="warning",
                    message=f"OS not officially supported: {specs.get('os_info')}",
                    details={
                        "detected_os": specs.get('os_info'),
                        "supported_os": supported_os
                    }
                ))
                
        except Exception as e:
            results.append(ValidationResult(
                name="System Requirements",
                status="fail",
                message="Could not validate system requirements",
                details={"error": str(e)}
            ))
        
        return results
    
    async def validate_network_connectivity(self) -> List[ValidationResult]:
        """Test network connectivity and ports"""
        results = []
        
        # Test outbound internet connectivity
        try:
            ssh = paramiko.SSHClient() 
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.vps_ip,
                'port': self.ssh_port,
                'username': self.ssh_user,
                'timeout': 10
            }
            
            if self.ssh_key:
                connect_kwargs['key_filename'] = self.ssh_key
                
            ssh.connect(**connect_kwargs)
            
            # Test internet connectivity
            stdin, stdout, stderr = ssh.exec_command('curl -s --connect-timeout 10 http://httpbin.org/ip')
            output = stdout.read().decode().strip()
            
            if output and 'origin' in output:
                results.append(ValidationResult(
                    name="Internet Connectivity",
                    status="pass",
                    message="Outbound internet connectivity working",
                    details={"response": output[:100]}
                ))
            else:
                results.append(ValidationResult(
                    name="Internet Connectivity", 
                    status="warning",
                    message="Could not verify internet connectivity",
                    details={"output": output}
                ))
            
            ssh.close()
            
        except Exception as e:
            results.append(ValidationResult(
                name="Internet Connectivity",
                status="fail", 
                message="Failed to test internet connectivity",
                details={"error": str(e)}
            ))
        
        # Test required ports
        required_ports = [22, 80, 443, 8000, 8001]
        
        for port in required_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((self.vps_ip, port))
                sock.close()
                
                if result == 0:
                    results.append(ValidationResult(
                        name=f"Port {port} Connectivity",
                        status="pass",
                        message=f"Port {port} is accessible",
                        details={"port": port}
                    ))
                else:
                    # SSH is required, others may not be open yet
                    status = "fail" if port == 22 else "warning"
                    message = f"Port {port} is not accessible" + ("" if port == 22 else " (may open after deployment)")
                    
                    results.append(ValidationResult(
                        name=f"Port {port} Connectivity",
                        status=status,
                        message=message,
                        details={"port": port, "connection_result": result}
                    ))
                    
            except Exception as e:
                results.append(ValidationResult(
                    name=f"Port {port} Connectivity",
                    status="warning",
                    message=f"Could not test port {port}",
                    details={"port": port, "error": str(e)}
                ))
        
        return results
    
    async def validate_docker_installation(self) -> ValidationResult:
        """Check if Docker is installed and working"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.vps_ip,
                'port': self.ssh_port, 
                'username': self.ssh_user,
                'timeout': 15
            }
            
            if self.ssh_key:
                connect_kwargs['key_filename'] = self.ssh_key
                
            ssh.connect(**connect_kwargs)
            
            # Test Docker
            stdin, stdout, stderr = ssh.exec_command('docker --version && docker compose version')
            docker_output = stdout.read().decode().strip()
            docker_error = stderr.read().decode().strip()
            
            ssh.close()
            
            if docker_output and 'Docker version' in docker_output:
                return ValidationResult(
                    name="Docker Installation",
                    status="pass",
                    message="Docker is installed and accessible",
                    details={"docker_info": docker_output.split('\n')}
                )
            else:
                return ValidationResult(
                    name="Docker Installation",
                    status="warning",
                    message="Docker not found (will be installed during deployment)",
                    details={"output": docker_output, "error": docker_error}
                )
                
        except Exception as e:
            return ValidationResult(
                name="Docker Installation",
                status="warning", 
                message="Could not check Docker installation (will be installed during deployment)",
                details={"error": str(e)}
            )
    
    async def validate_deployment_readiness(self) -> ValidationResult:
        """Overall deployment readiness assessment"""
        
        # Count validation results
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        warnings = sum(1 for r in self.results if r.status == "warning")
        
        total_checks = len(self.results)
        pass_percentage = (passed / total_checks * 100) if total_checks > 0 else 0
        
        if failed == 0 and pass_percentage >= 80:
            status = "pass"
            message = f"VPS is ready for deployment ({passed}/{total_checks} checks passed)"
        elif failed == 0:
            status = "warning"
            message = f"VPS may be ready for deployment with cautions ({passed}/{total_checks} checks passed, {warnings} warnings)"
        else:
            status = "fail"
            message = f"VPS is not ready for deployment ({failed} critical failures)"
        
        return ValidationResult(
            name="Deployment Readiness",
            status=status,
            message=message,
            details={
                "total_checks": total_checks,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "pass_percentage": round(pass_percentage, 1)
            }
        )
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete VPS validation suite"""
        print(f"🔍 Starting VPS validation for {self.vps_ip}")
        print("=" * 60)
        
        # 1. SSH Connectivity
        result = await self.validate_ssh_connectivity()
        self.log_result(result)
        
        if result.status == "fail":
            print("\n❌ SSH connectivity failed - cannot proceed with other tests")
            return self.generate_report()
        
        # 2. System Requirements
        print("\n📋 Checking system requirements...")
        for result in await self.validate_system_requirements():
            self.log_result(result)
        
        # 3. Network Connectivity
        print("\n🌐 Testing network connectivity...")
        for result in await self.validate_network_connectivity():
            self.log_result(result)
        
        # 4. Docker Installation
        print("\n🐳 Checking Docker installation...")
        result = await self.validate_docker_installation()
        self.log_result(result)
        
        # 5. Overall Readiness
        print("\n🎯 Assessment...")
        readiness = await self.validate_deployment_readiness()
        self.log_result(readiness)
        
        print("\n" + "=" * 60)
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        
        # Summary statistics
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail") 
        warnings = sum(1 for r in self.results if r.status == "warning")
        total = len(self.results)
        
        # Overall status
        if failed == 0 and passed >= total * 0.8:
            overall_status = "ready"
        elif failed == 0:
            overall_status = "ready_with_warnings"
        else:
            overall_status = "not_ready"
        
        report = {
            "vps_ip": self.vps_ip,
            "validation_timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed, 
                "warnings": warnings,
                "pass_rate": round((passed / total * 100) if total > 0 else 0, 1)
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in self.results
            ],
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate deployment recommendations based on validation results"""
        recommendations = []
        
        failed_checks = [r for r in self.results if r.status == "fail"]
        warning_checks = [r for r in self.results if r.status == "warning"]
        
        if failed_checks:
            recommendations.append("❌ Fix critical issues before proceeding with deployment:")
            for check in failed_checks:
                recommendations.append(f"   - {check.name}: {check.message}")
        
        if warning_checks:
            recommendations.append("⚠️ Consider addressing these warnings:")
            for check in warning_checks:
                recommendations.append(f"   - {check.name}: {check.message}")
        
        if not failed_checks and not warning_checks:
            recommendations.append("✅ VPS meets all requirements - ready for deployment!")
            recommendations.append("   - Proceed with DotMac ISP Framework installation")
            recommendations.append("   - Configure monitoring and alerts")
            recommendations.append("   - Set up automated backups")
        
        return recommendations


async def main():
    parser = argparse.ArgumentParser(description='Validate VPS for DotMac deployment')
    parser.add_argument('vps_ip', help='VPS IP address')
    parser.add_argument('--ssh-port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--ssh-user', default='root', help='SSH username (default: root)')  
    parser.add_argument('--ssh-key', help='Path to SSH private key file')
    parser.add_argument('--output', help='Output report to JSON file')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    
    args = parser.parse_args()
    
    # Create validator
    validator = VPSValidator(
        vps_ip=args.vps_ip,
        ssh_port=args.ssh_port,
        ssh_user=args.ssh_user,
        ssh_key=args.ssh_key
    )
    
    # Run validation
    report = await validator.run_full_validation()
    
    # Output results
    if not args.quiet:
        print("\n📄 Validation Summary:")
        print(f"   Overall Status: {report['overall_status'].upper()}")
        print(f"   Pass Rate: {report['summary']['pass_rate']}%")
        print(f"   Checks: {report['summary']['passed']} passed, {report['summary']['failed']} failed, {report['summary']['warnings']} warnings")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   {rec}")
    
    # Save report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Report saved to: {args.output}")
    
    # Exit code based on validation status
    if report['overall_status'] == 'not_ready':
        sys.exit(1)
    elif report['overall_status'] == 'ready_with_warnings':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())