#!/usr/bin/env python3
"""
Security Hardening Implementation Script for DotMac Framework
Implements security measures in a production-safe way
"""

import subprocess
import os
import sys
from pathlib import Path
import json
import tempfile

class SecurityHardening:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.changes_made = []
        self.errors = []

    def run_command(self, cmd: str, description: str = "") -> bool:
        """Run command with proper error handling"""
        if self.dry_run:
            print(f"[DRY RUN] Would run: {cmd}")
            return True
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                if description:
                    self.changes_made.append(description)
                return True
            else:
                error_msg = f"Command failed: {cmd}\nError: {result.stderr}"
                print(f"❌ {error_msg}")
                self.errors.append(error_msg)
                return False
        except Exception as e:
            error_msg = f"Exception running command: {cmd}\nError: {e}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False

    def create_backup(self, file_path: str) -> str:
        """Create backup of configuration file"""
        backup_path = f"{file_path}.backup.{subprocess.run(['date', '+%Y%m%d_%H%M%S'], capture_output=True, text=True).stdout.strip()}"
        if os.path.exists(file_path):
            try:
                if not self.dry_run:
                    subprocess.run(f"cp {file_path} {backup_path}", shell=True, check=True)
                print(f"✅ Created backup: {backup_path}")
                return backup_path
            except Exception as e:
                print(f"⚠️  Could not create backup of {file_path}: {e}")
        return ""

    def configure_firewall(self):
        """Configure UFW firewall"""
        print("\n🔥 Configuring UFW Firewall...")
        
        # Check if UFW is installed
        if not self.run_command("which ufw > /dev/null", ""):
            print("⚠️  UFW not installed, installing...")
            if not self.run_command("apt-get update && apt-get install -y ufw", "UFW installation"):
                return False
        
        # Reset UFW to defaults (safe operation)
        self.run_command("ufw --force reset", "UFW reset to defaults")
        
        # Set default policies
        self.run_command("ufw default deny incoming", "Set default deny incoming")
        self.run_command("ufw default allow outgoing", "Set default allow outgoing")
        
        # Allow essential services
        essential_ports = {
            "22": "SSH",
            "80": "HTTP", 
            "443": "HTTPS",
            "8000": "Management Platform",
            "8001": "ISP Framework"
        }
        
        for port, service in essential_ports.items():
            self.run_command(f"ufw allow {port}", f"Allow {service} ({port})")
        
        # Enable UFW
        self.run_command("ufw --force enable", "Enable UFW")
        
        print("✅ UFW firewall configured")

    def harden_ssh(self):
        """Harden SSH configuration"""
        print("\n🔐 Hardening SSH Configuration...")
        
        ssh_config = "/etc/ssh/sshd_config"
        if not os.path.exists(ssh_config):
            print(f"⚠️  SSH config file not found: {ssh_config}")
            return
        
        # Create backup
        self.create_backup(ssh_config)
        
        # SSH hardening settings
        ssh_settings = {
            "PermitRootLogin": "no",
            "PasswordAuthentication": "yes",  # Keep enabled for now, can be disabled after key setup
            "PermitEmptyPasswords": "no",
            "X11Forwarding": "no",
            "MaxAuthTries": "3",
            "ClientAliveInterval": "300",
            "ClientAliveCountMax": "2",
            "Protocol": "2",
            "Port": "22"
        }
        
        if not self.dry_run:
            try:
                # Read current config
                with open(ssh_config, 'r') as f:
                    config_lines = f.readlines()
                
                # Create new config with hardened settings
                new_config = []
                settings_added = set()
                
                for line in config_lines:
                    line_strip = line.strip()
                    if line_strip and not line_strip.startswith('#'):
                        # Check if this line sets one of our hardening settings
                        for setting, value in ssh_settings.items():
                            if line_strip.lower().startswith(setting.lower()):
                                new_config.append(f"{setting} {value}\n")
                                settings_added.add(setting)
                                break
                        else:
                            new_config.append(line)
                    else:
                        new_config.append(line)
                
                # Add any settings that weren't found in the config
                for setting, value in ssh_settings.items():
                    if setting not in settings_added:
                        new_config.append(f"{setting} {value}\n")
                
                # Write new config
                with open(ssh_config, 'w') as f:
                    f.writelines(new_config)
                
                print("✅ SSH configuration hardened")
                self.changes_made.append("SSH hardening applied")
                
                # Test SSH config and restart if valid
                if self.run_command("sshd -t", "SSH config validation"):
                    self.run_command("systemctl restart ssh", "SSH service restart")
                else:
                    print("⚠️  SSH config test failed, not restarting service")
                    
            except Exception as e:
                print(f"❌ Error hardening SSH config: {e}")
                self.errors.append(f"SSH hardening failed: {e}")

    def install_fail2ban(self):
        """Install and configure fail2ban"""
        print("\n🛡️ Installing and Configuring fail2ban...")
        
        # Install fail2ban
        if not self.run_command("which fail2ban-server > /dev/null", ""):
            print("Installing fail2ban...")
            if not self.run_command("apt-get update && apt-get install -y fail2ban", "fail2ban installation"):
                return
        
        # Create fail2ban local jail configuration
        jail_local = "/etc/fail2ban/jail.local"
        jail_config = """[DEFAULT]
bantime = 600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
"""
        
        if not self.dry_run:
            try:
                with open(jail_local, 'w') as f:
                    f.write(jail_config)
                print(f"✅ Created fail2ban config: {jail_local}")
                self.changes_made.append("fail2ban jail configuration created")
            except Exception as e:
                print(f"❌ Error creating fail2ban config: {e}")
                self.errors.append(f"fail2ban config creation failed: {e}")
                return
        
        # Enable and start fail2ban
        self.run_command("systemctl enable fail2ban", "Enable fail2ban service")
        self.run_command("systemctl restart fail2ban", "Start fail2ban service")
        
        print("✅ fail2ban installed and configured")

    def setup_audit_logging(self):
        """Setup audit logging with auditd"""
        print("\n📝 Setting up Audit Logging...")
        
        # Install auditd
        if not self.run_command("which auditctl > /dev/null", ""):
            print("Installing auditd...")
            if not self.run_command("apt-get update && apt-get install -y auditd audispd-plugins", "auditd installation"):
                return
        
        # Create audit rules
        audit_rules = "/etc/audit/rules.d/dotmac.rules"
        rules_content = """# DotMac Framework Audit Rules
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k identity

# Monitor authentication files
-w /var/log/auth.log -p wa -k authentication
-w /var/log/secure -p wa -k authentication

# Monitor configuration changes
-w /etc/ssh/sshd_config -p wa -k ssh-config
-w /etc/nginx/ -p wa -k nginx-config
-w /etc/docker/ -p wa -k docker-config

# Monitor system calls
-a always,exit -F arch=b64 -S adjtimex -S settimeofday -k time-change
-a always,exit -F arch=b64 -S clock_settime -k time-change
-w /etc/localtime -p wa -k time-change

# Monitor network configuration
-w /etc/hosts -p wa -k network
-w /etc/network/ -p wa -k network

# Monitor privilege escalation
-w /bin/su -p x -k privileged
-w /usr/bin/sudo -p x -k privileged
-w /usr/bin/sudoedit -p x -k privileged

# Monitor file deletions
-a always,exit -F arch=b64 -S unlink -S unlinkat -S rename -S renameat -F success=1 -k delete
"""
        
        if not self.dry_run:
            try:
                os.makedirs("/etc/audit/rules.d", exist_ok=True)
                with open(audit_rules, 'w') as f:
                    f.write(rules_content)
                print(f"✅ Created audit rules: {audit_rules}")
                self.changes_made.append("Audit rules configured")
            except Exception as e:
                print(f"❌ Error creating audit rules: {e}")
                self.errors.append(f"Audit rules creation failed: {e}")
                return
        
        # Enable and start auditd
        self.run_command("systemctl enable auditd", "Enable auditd service")
        self.run_command("systemctl restart auditd", "Start auditd service")
        
        print("✅ Audit logging configured")

    def configure_docker_security(self):
        """Configure Docker security settings"""
        print("\n🐳 Configuring Docker Security...")
        
        # Create Docker daemon configuration
        docker_config_dir = "/etc/docker"
        docker_config_file = f"{docker_config_dir}/daemon.json"
        
        docker_security_config = {
            "live-restore": True,
            "userland-proxy": False,
            "no-new-privileges": True,
            "log-driver": "json-file",
            "log-opts": {
                "max-size": "10m",
                "max-file": "3"
            },
            "default-ulimits": {
                "nofile": {
                    "Name": "nofile",
                    "Hard": 64000,
                    "Soft": 64000
                },
                "nproc": {
                    "Name": "nproc", 
                    "Hard": 8192,
                    "Soft": 4096
                }
            }
        }
        
        if not self.dry_run:
            try:
                os.makedirs(docker_config_dir, exist_ok=True)
                
                # Backup existing config if it exists
                if os.path.exists(docker_config_file):
                    self.create_backup(docker_config_file)
                
                with open(docker_config_file, 'w') as f:
                    json.dump(docker_security_config, f, indent=2)
                
                print(f"✅ Created Docker security config: {docker_config_file}")
                self.changes_made.append("Docker security configuration applied")
                
                # Restart Docker daemon
                print("Restarting Docker daemon...")
                self.run_command("systemctl restart docker", "Docker daemon restart")
                
            except Exception as e:
                print(f"❌ Error configuring Docker security: {e}")
                self.errors.append(f"Docker security configuration failed: {e}")
        
        print("✅ Docker security configured")

    def setup_system_hardening(self):
        """Setup system-level security hardening"""
        print("\n⚙️ Applying System Hardening...")
        
        # Create sysctl security configuration
        sysctl_config = "/etc/sysctl.d/99-security.conf"
        sysctl_settings = """# DotMac Framework Security Settings

# Network security
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# IPv6 security (disable if not used)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1

# Kernel security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
kernel.core_pattern = /dev/null
fs.suid_dumpable = 0

# Memory protection
vm.mmap_min_addr = 4096
"""
        
        if not self.dry_run:
            try:
                with open(sysctl_config, 'w') as f:
                    f.write(sysctl_settings)
                
                print(f"✅ Created sysctl security config: {sysctl_config}")
                self.changes_made.append("System security parameters configured")
                
                # Apply sysctl settings
                self.run_command("sysctl -p /etc/sysctl.d/99-security.conf", "Apply sysctl security settings")
                
            except Exception as e:
                print(f"❌ Error creating sysctl config: {e}")
                self.errors.append(f"System hardening failed: {e}")
        
        print("✅ System hardening applied")

    def setup_log_security(self):
        """Setup secure logging configuration"""
        print("\n🔄 Configuring Secure Logging...")
        
        # Create DotMac specific logrotate configuration
        logrotate_config = "/etc/logrotate.d/dotmac"
        logrotate_settings = """/opt/dotmac/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 0644 root root
}

/var/log/audit/audit.log {
    weekly
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0600 root root
    postrotate
        /sbin/service auditd restart
    endscript
}

/var/log/fail2ban.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    copytruncate
    create 0644 root adm
}
"""
        
        if not self.dry_run:
            try:
                with open(logrotate_config, 'w') as f:
                    f.write(logrotate_settings)
                
                print(f"✅ Created logrotate config: {logrotate_config}")
                self.changes_made.append("Log rotation configured")
                
                # Test logrotate configuration
                self.run_command("logrotate -d /etc/logrotate.d/dotmac", "Test logrotate config")
                
            except Exception as e:
                print(f"❌ Error creating logrotate config: {e}")
                self.errors.append(f"Log rotation configuration failed: {e}")
        
        print("✅ Secure logging configured")

    def create_security_monitoring_script(self):
        """Create security monitoring script"""
        print("\n🔍 Creating Security Monitoring Script...")
        
        monitoring_script = "/usr/local/bin/dotmac-security-monitor"
        script_content = """#!/bin/bash
# DotMac Framework Security Monitoring Script

LOG_FILE="/var/log/dotmac-security-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting security check..." >> $LOG_FILE

# Check for failed SSH attempts
FAILED_SSH=$(journalctl --since="1 hour ago" | grep "Failed password" | wc -l)
if [ "$FAILED_SSH" -gt 10 ]; then
    echo "[$DATE] ALERT: $FAILED_SSH failed SSH attempts in the last hour" >> $LOG_FILE
fi

# Check Docker container status
UNHEALTHY_CONTAINERS=$(docker ps --filter health=unhealthy --format "{{.Names}}" | wc -l)
if [ "$UNHEALTHY_CONTAINERS" -gt 0 ]; then
    echo "[$DATE] ALERT: $UNHEALTHY_CONTAINERS unhealthy Docker containers" >> $LOG_FILE
fi

# Check disk usage
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "[$DATE] ALERT: Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check for unauthorized sudo attempts
SUDO_FAILURES=$(journalctl --since="1 hour ago" | grep "sudo.*authentication failure" | wc -l)
if [ "$SUDO_FAILURES" -gt 5 ]; then
    echo "[$DATE] ALERT: $SUDO_FAILURES failed sudo attempts in the last hour" >> $LOG_FILE
fi

echo "[$DATE] Security check completed" >> $LOG_FILE
"""
        
        if not self.dry_run:
            try:
                with open(monitoring_script, 'w') as f:
                    f.write(script_content)
                
                os.chmod(monitoring_script, 0o755)
                print(f"✅ Created security monitoring script: {monitoring_script}")
                self.changes_made.append("Security monitoring script created")
                
                # Create cron job for security monitoring
                cron_job = "*/15 * * * * root /usr/local/bin/dotmac-security-monitor"
                self.run_command(f'echo "{cron_job}" >> /etc/crontab', "Add security monitoring to cron")
                
            except Exception as e:
                print(f"❌ Error creating monitoring script: {e}")
                self.errors.append(f"Security monitoring setup failed: {e}")
        
        print("✅ Security monitoring configured")

    def apply_all_hardening(self):
        """Apply all security hardening measures"""
        print("🔒 Starting DotMac Framework Security Hardening")
        print("=" * 60)
        
        if self.dry_run:
            print("🧪 DRY RUN MODE - No changes will be made")
            print("=" * 60)
        
        # Apply security measures
        hardening_steps = [
            self.configure_firewall,
            self.harden_ssh,
            self.install_fail2ban,
            self.setup_audit_logging,
            self.configure_docker_security,
            self.setup_system_hardening,
            self.setup_log_security,
            self.create_security_monitoring_script,
        ]
        
        for step in hardening_steps:
            try:
                step()
            except Exception as e:
                print(f"❌ Error in hardening step {step.__name__}: {e}")
                self.errors.append(f"Step {step.__name__} failed: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("🔒 Security Hardening Summary")
        print(f"✅ Changes made: {len(self.changes_made)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.changes_made:
            print("\nChanges applied:")
            for change in self.changes_made:
                print(f"  • {change}")
        
        if self.errors:
            print("\nErrors encountered:")
            for error in self.errors:
                print(f"  • {error}")
        
        if len(self.errors) == 0:
            print("\n🎉 Security hardening completed successfully!")
            print("\nRecommended next steps:")
            print("1. Reboot the system to ensure all changes take effect")
            print("2. Run security validation: python3 scripts/validate_security.py")
            print("3. Test application functionality")
            print("4. Monitor security logs in /var/log/")
            return True
        else:
            print(f"\n⚠️  Security hardening completed with {len(self.errors)} errors")
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DotMac Framework Security Hardening")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true", help="Apply changes without confirmation")
    
    args = parser.parse_args()
    
    # Confirmation for non-dry-run mode
    if not args.dry_run and not args.force:
        print("⚠️  This script will make system-level security changes.")
        print("It is recommended to run with --dry-run first.")
        confirm = input("Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(1)
    
    # Run hardening
    hardening = SecurityHardening(dry_run=args.dry_run)
    success = hardening.apply_all_hardening()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()