#!/usr/bin/env python3
"""
Security Validation Script for DotMac Framework
Validates that security hardening measures are properly implemented
"""

import subprocess
import socket
import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

class SecurityValidator:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def run_command(self, cmd: str) -> Tuple[str, int]:
        """Run shell command and return output and exit code"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "Command timed out", 1
        except Exception as e:
            return f"Error: {e}", 1

    def check_service(self, service: str) -> bool:
        """Check if a service is active"""
        output, code = self.run_command(f"systemctl is-active {service}")
        return code == 0 and output == "active"

    def validate_firewall(self) -> Dict[str, Any]:
        """Validate UFW firewall configuration"""
        print("🔥 Validating firewall configuration...")
        
        results = {}
        
        # Check if UFW is installed
        output, code = self.run_command("which ufw")
        if code != 0:
            results["ufw_installed"] = {"status": "fail", "message": "UFW not installed"}
            return results
        
        results["ufw_installed"] = {"status": "pass", "message": "UFW is installed"}
        
        # Check UFW status
        output, code = self.run_command("ufw status")
        if "Status: active" in output:
            results["ufw_active"] = {"status": "pass", "message": "UFW is active"}
            
            # Check default policies
            if "deny (incoming)" in output.lower():
                results["default_deny_incoming"] = {"status": "pass", "message": "Default deny incoming policy"}
            else:
                results["default_deny_incoming"] = {"status": "fail", "message": "Default deny incoming not set"}
                
            if "allow (outgoing)" in output.lower():
                results["default_allow_outgoing"] = {"status": "pass", "message": "Default allow outgoing policy"}
            else:
                results["default_allow_outgoing"] = {"status": "warn", "message": "Outgoing policy check failed"}
                
            # Check for essential ports
            essential_ports = ["22/tcp", "80/tcp", "443/tcp"]
            for port in essential_ports:
                if port in output:
                    results[f"port_{port.replace('/', '_')}"] = {"status": "pass", "message": f"Port {port} allowed"}
                else:
                    results[f"port_{port.replace('/', '_')}"] = {"status": "warn", "message": f"Port {port} may not be configured"}
        else:
            results["ufw_active"] = {"status": "fail", "message": "UFW is not active"}
        
        return results

    def validate_ssh_hardening(self) -> Dict[str, Any]:
        """Validate SSH hardening configuration"""
        print("🔐 Validating SSH hardening...")
        
        results = {}
        ssh_config_file = "/etc/ssh/sshd_config"
        
        if not os.path.exists(ssh_config_file):
            results["ssh_config_exists"] = {"status": "fail", "message": "SSH config file not found"}
            return results
        
        results["ssh_config_exists"] = {"status": "pass", "message": "SSH config file exists"}
        
        # Read SSH config
        try:
            with open(ssh_config_file, 'r') as f:
                ssh_config = f.read()
        except Exception as e:
            results["ssh_config_readable"] = {"status": "fail", "message": f"Cannot read SSH config: {e}"}
            return results
        
        # Check hardening settings
        hardening_checks = {
            "root_login_disabled": ("PermitRootLogin no", "Root login is disabled"),
            "password_auth_disabled": ("PasswordAuthentication no", "Password authentication disabled"),
            "empty_passwords_disabled": ("PermitEmptyPasswords no", "Empty passwords not permitted"),
            "x11_forwarding_disabled": ("X11Forwarding no", "X11 forwarding disabled"),
            "protocol_2": ("Protocol 2", "SSH Protocol 2 enforced"),
            "max_auth_tries": ("MaxAuthTries", "Max authentication tries configured"),
        }
        
        for check, (pattern, message) in hardening_checks.items():
            if pattern.lower() in ssh_config.lower():
                results[check] = {"status": "pass", "message": message}
            else:
                results[check] = {"status": "warn", "message": f"{message} - not found in config"}
        
        # Check if SSH service is running
        if self.check_service("ssh") or self.check_service("sshd"):
            results["ssh_service_running"] = {"status": "pass", "message": "SSH service is running"}
        else:
            results["ssh_service_running"] = {"status": "fail", "message": "SSH service not running"}
        
        return results

    def validate_fail2ban(self) -> Dict[str, Any]:
        """Validate fail2ban configuration"""
        print("🛡️ Validating fail2ban configuration...")
        
        results = {}
        
        # Check if fail2ban is installed
        output, code = self.run_command("which fail2ban-server")
        if code != 0:
            results["fail2ban_installed"] = {"status": "warn", "message": "fail2ban not installed"}
            return results
        
        results["fail2ban_installed"] = {"status": "pass", "message": "fail2ban is installed"}
        
        # Check if fail2ban service is running
        if self.check_service("fail2ban"):
            results["fail2ban_active"] = {"status": "pass", "message": "fail2ban service is active"}
            
            # Check jail status
            output, code = self.run_command("fail2ban-client status")
            if code == 0:
                results["fail2ban_status"] = {"status": "pass", "message": f"fail2ban status: {output}"}
                
                # Check for SSH jail
                output, code = self.run_command("fail2ban-client status sshd")
                if code == 0:
                    results["sshd_jail"] = {"status": "pass", "message": "SSH jail is active"}
                else:
                    results["sshd_jail"] = {"status": "warn", "message": "SSH jail not found"}
            else:
                results["fail2ban_status"] = {"status": "fail", "message": "Cannot get fail2ban status"}
        else:
            results["fail2ban_active"] = {"status": "fail", "message": "fail2ban service not active"}
        
        return results

    def validate_audit_logging(self) -> Dict[str, Any]:
        """Validate audit logging configuration"""
        print("📝 Validating audit logging...")
        
        results = {}
        
        # Check if auditd is installed
        output, code = self.run_command("which auditctl")
        if code != 0:
            results["auditd_installed"] = {"status": "warn", "message": "auditd not installed"}
            return results
        
        results["auditd_installed"] = {"status": "pass", "message": "auditd is installed"}
        
        # Check if auditd service is running
        if self.check_service("auditd"):
            results["auditd_active"] = {"status": "pass", "message": "auditd service is active"}
            
            # Check audit rules
            output, code = self.run_command("auditctl -l")
            if code == 0 and output.strip():
                results["audit_rules"] = {"status": "pass", "message": f"Audit rules configured ({len(output.splitlines()} rules)"}
            else:
                results["audit_rules"] = {"status": "warn", "message": "No audit rules found"}
                
            # Check audit log file
            audit_log = "/var/log/audit/audit.log"
            if os.path.exists(audit_log):
                results["audit_log_exists"] = {"status": "pass", "message": "Audit log file exists"}
            else:
                results["audit_log_exists"] = {"status": "warn", "message": "Audit log file not found"}
        else:
            results["auditd_active"] = {"status": "fail", "message": "auditd service not active"}
        
        return results

    def validate_docker_security(self) -> Dict[str, Any]:
        """Validate Docker security configuration"""
        print("🐳 Validating Docker security...")
        
        results = {}
        
        # Check if Docker is installed
        output, code = self.run_command("docker --version")
        if code != 0:
            results["docker_installed"] = {"status": "warn", "message": "Docker not installed"}
            return results
        
        results["docker_installed"] = {"status": "pass", "message": f"Docker is installed: {output}"}
        
        # Check Docker daemon configuration
        docker_config = "/etc/docker/daemon.json"
        if os.path.exists(docker_config):
            results["docker_config_exists"] = {"status": "pass", "message": "Docker daemon config exists"}
            
            try:
                with open(docker_config, 'r') as f:
                    config = json.load(f)
                    
                # Check security settings
                if config.get("live-restore"):
                    results["live_restore"] = {"status": "pass", "message": "Live restore enabled"}
                else:
                    results["live_restore"] = {"status": "warn", "message": "Live restore not configured"}
                    
                if config.get("userland-proxy") == False:
                    results["userland_proxy"] = {"status": "pass", "message": "Userland proxy disabled"}
                else:
                    results["userland_proxy"] = {"status": "warn", "message": "Userland proxy not disabled"}
                    
                if "default-ulimits" in config:
                    results["ulimits"] = {"status": "pass", "message": "Resource limits configured"}
                else:
                    results["ulimits"] = {"status": "warn", "message": "Resource limits not configured"}
                    
            except Exception as e:
                results["docker_config_parse"] = {"status": "fail", "message": f"Cannot parse Docker config: {e}"}
        else:
            results["docker_config_exists"] = {"status": "warn", "message": "Docker daemon config not found"}
        
        # Check running containers for security
        output, code = self.run_command("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
        if code == 0:
            containers = [line for line in output.split('\n') if line and not line.startswith('NAMES')]
            results["container_status"] = {"status": "pass", "message": f"{len(containers)} containers running"}
        else:
            results["container_status"] = {"status": "warn", "message": "Cannot check Docker containers"}
        
        return results

    def validate_file_integrity(self) -> Dict[str, Any]:
        """Validate file integrity monitoring"""
        print("🔍 Validating file integrity monitoring...")
        
        results = {}
        
        # Check if AIDE is installed
        output, code = self.run_command("which aide")
        if code != 0:
            results["aide_installed"] = {"status": "warn", "message": "AIDE not installed"}
            return results
        
        results["aide_installed"] = {"status": "pass", "message": "AIDE is installed"}
        
        # Check AIDE configuration
        aide_config = "/etc/aide/aide.conf"
        if os.path.exists(aide_config):
            results["aide_config_exists"] = {"status": "pass", "message": "AIDE config exists"}
        else:
            results["aide_config_exists"] = {"status": "warn", "message": "AIDE config not found"}
        
        # Check if AIDE database exists
        aide_db_paths = ["/var/lib/aide/aide.db", "/var/lib/aide/aide.db.new"]
        for db_path in aide_db_paths:
            if os.path.exists(db_path):
                results[f"aide_db_{os.path.basename(db_path)}"] = {"status": "pass", "message": f"AIDE database {db_path} exists"}
                break
        else:
            results["aide_database"] = {"status": "warn", "message": "AIDE database not found - run 'aide --init'"}
        
        return results

    def validate_system_limits(self) -> Dict[str, Any]:
        """Validate system security limits"""
        print("⚙️ Validating system security limits...")
        
        results = {}
        
        # Check limits configuration
        limits_file = "/etc/security/limits.conf"
        if os.path.exists(limits_file):
            results["limits_config_exists"] = {"status": "pass", "message": "Security limits config exists"}
            
            try:
                with open(limits_file, 'r') as f:
                    limits_content = f.read()
                    
                # Check for common security limits
                security_patterns = ["nofile", "nproc", "core"]
                for pattern in security_patterns:
                    if pattern in limits_content:
                        results[f"limit_{pattern}"] = {"status": "pass", "message": f"{pattern} limits configured"}
                    else:
                        results[f"limit_{pattern}"] = {"status": "warn", "message": f"{pattern} limits not configured"}
                        
            except Exception as e:
                results["limits_config_readable"] = {"status": "fail", "message": f"Cannot read limits config: {e}"}
        else:
            results["limits_config_exists"] = {"status": "warn", "message": "Security limits config not found"}
        
        # Check sysctl security parameters
        sysctl_file = "/etc/sysctl.d/99-security.conf"
        if os.path.exists(sysctl_file):
            results["sysctl_security_exists"] = {"status": "pass", "message": "Security sysctl config exists"}
            
            try:
                with open(sysctl_file, 'r') as f:
                    sysctl_content = f.read()
                    
                # Check for key security parameters
                security_params = [
                    "net.ipv4.ip_forward",
                    "net.ipv4.icmp_echo_ignore_broadcasts",
                    "net.ipv4.icmp_ignore_bogus_error_responses",
                    "kernel.dmesg_restrict"
                ]
                
                for param in security_params:
                    if param in sysctl_content:
                        results[f"sysctl_{param.replace('.', '_')}"] = {"status": "pass", "message": f"{param} configured"}
                    else:
                        results[f"sysctl_{param.replace('.', '_')}"] = {"status": "warn", "message": f"{param} not configured"}
                        
            except Exception as e:
                results["sysctl_security_readable"] = {"status": "fail", "message": f"Cannot read sysctl config: {e}"}
        else:
            results["sysctl_security_exists"] = {"status": "warn", "message": "Security sysctl config not found"}
        
        return results

    def validate_log_rotation(self) -> Dict[str, Any]:
        """Validate log rotation configuration"""
        print("🔄 Validating log rotation...")
        
        results = {}
        
        # Check if logrotate is installed
        output, code = self.run_command("which logrotate")
        if code != 0:
            results["logrotate_installed"] = {"status": "fail", "message": "logrotate not installed"}
            return results
        
        results["logrotate_installed"] = {"status": "pass", "message": "logrotate is installed"}
        
        # Check main logrotate config
        logrotate_config = "/etc/logrotate.conf"
        if os.path.exists(logrotate_config):
            results["logrotate_config_exists"] = {"status": "pass", "message": "logrotate config exists"}
        else:
            results["logrotate_config_exists"] = {"status": "fail", "message": "logrotate config not found"}
        
        # Check logrotate.d directory
        logrotate_d = "/etc/logrotate.d"
        if os.path.exists(logrotate_d):
            config_files = os.listdir(logrotate_d)
            results["logrotate_d_exists"] = {"status": "pass", "message": f"logrotate.d with {len(config_files)} configs"}
        else:
            results["logrotate_d_exists"] = {"status": "fail", "message": "logrotate.d directory not found"}
        
        # Check if logrotate cron job exists
        cron_paths = ["/etc/cron.daily/logrotate", "/etc/cron.hourly/logrotate"]
        for cron_path in cron_paths:
            if os.path.exists(cron_path):
                results["logrotate_cron"] = {"status": "pass", "message": f"logrotate cron job: {cron_path}"}
                break
        else:
            results["logrotate_cron"] = {"status": "warn", "message": "logrotate cron job not found"}
        
        return results

    def print_results(self, category: str, results: Dict[str, Any]):
        """Print validation results for a category"""
        for check, result in results.items():
            status = result["status"]
            message = result["message"]
            
            if status == "pass":
                print(f"  ✅ {message}")
                self.passed += 1
            elif status == "fail":
                print(f"  ❌ {message}")
                self.failed += 1
            elif status == "warn":
                print(f"  ⚠️  {message}")
                self.warnings += 1
        
        self.results[category] = results

    def run_validation(self) -> bool:
        """Run all security validations"""
        print("🔒 Starting DotMac Framework Security Validation")
        print("=" * 60)
        
        # Run all validation checks
        validation_categories = [
            ("Firewall", self.validate_firewall),
            ("SSH Hardening", self.validate_ssh_hardening),
            ("Fail2ban", self.validate_fail2ban),
            ("Audit Logging", self.validate_audit_logging),
            ("Docker Security", self.validate_docker_security),
            ("File Integrity", self.validate_file_integrity),
            ("System Limits", self.validate_system_limits),
            ("Log Rotation", self.validate_log_rotation),
        ]
        
        for category_name, validation_func in validation_categories:
            print(f"\n{category_name}:")
            try:
                results = validation_func()
                self.print_results(category_name.lower().replace(" ", "_"), results)
            except Exception as e:
                print(f"  ❌ Error during {category_name} validation: {e}")
                self.failed += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print("🔒 Security Validation Summary")
        print(f"✅ Passed: {self.passed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print(f"❌ Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n🎉 Security validation completed successfully!")
            return True
        else:
            print(f"\n⚠️  Security validation completed with {self.failed} failures and {self.warnings} warnings")
            return False

    def generate_report(self, output_file: str = "security_validation_report.json"):
        """Generate detailed validation report"""
        report = {
            "timestamp": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
            "summary": {
                "passed": self.passed,
                "warnings": self.warnings,
                "failed": self.failed,
                "total": self.passed + self.warnings + self.failed
            },
            "results": self.results
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")

def main():
    """Main function"""
    validator = SecurityValidator()
    
    # Run validation
    success = validator.run_validation()
    
    # Generate report
    validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()