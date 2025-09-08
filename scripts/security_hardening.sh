#!/bin/bash
# Security Hardening Script for DotMac Framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/var/log/dotmac-security-hardening.log"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }
print_header() { echo -e "${BLUE}$1${NC}" | tee -a "$LOG_FILE"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1" | tee -a "$LOG_FILE"; }

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    print_error "Security hardening failed at line $2 with exit code $1"
    exit $1
}

# Check if running with appropriate privileges
check_privileges() {
    if [[ $EUID -ne 0 && -z "$SUDO_USER" ]]; then
        print_error "This script requires root privileges for system-level security hardening"
        print_status "Please run with: sudo $0"
        exit 1
    fi
}

# System hardening
harden_system() {
    print_step "Hardening system-level security..."
    
    # Update system packages
    print_status "Updating system packages..."
    apt-get update -q
    apt-get upgrade -y -q
    
    # Install security packages
    print_status "Installing security packages..."
    apt-get install -y -q \
        fail2ban \
        ufw \
        rkhunter \
        lynis \
        aide \
        auditd \
        apparmor \
        apparmor-utils
    
    # Configure automatic security updates
    apt-get install -y -q unattended-upgrades
    cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF
    
    print_status "System security packages installed and configured"
}

# Configure firewall
configure_firewall() {
    print_step "Configuring UFW firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful not to lock yourself out)
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow DotMac application ports (with rate limiting)
    ufw limit 8000/tcp comment 'Management Platform'
    ufw limit 8001/tcp comment 'ISP Framework'
    
    # Allow monitoring ports (restrict to specific IPs in production)
    ufw allow from 127.0.0.1 to any port 9090 comment 'Prometheus'
    # Grafana not used
    
    # Enable UFW
    ufw --force enable
    
    print_status "Firewall configured with restrictive rules"
    print_warning "Ensure you can still access the system before logging out!"
}

# Configure Fail2Ban
configure_fail2ban() {
    print_step "Configuring Fail2Ban intrusion prevention..."
    
    # Create custom jail for DotMac applications
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Ban hosts for 1 hour (3600 seconds)
bantime = 3600

# A host is banned if it has generated "maxretry" during the "findtime"
findtime = 600
maxretry = 5

# Destination email for action_mw (mail with whois)
destemail = admin@localhost
sender = fail2ban@localhost

# Default action: ban and send email with whois and log lines
action = %(action_mw)s

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 600

[dotmac-auth]
enabled = true
port = 8000,8001
logpath = /opt/dotmac/logs/*/auth.log
maxretry = 5
bantime = 1800
findtime = 300
EOF
    
    # Restart Fail2Ban
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    print_status "Fail2Ban configured with custom rules for DotMac"
}

# Harden SSH configuration
harden_ssh() {
    print_step "Hardening SSH configuration..."
    
    # Backup original SSH config
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    # Apply hardened SSH configuration
    cat > /etc/ssh/sshd_config.d/99-dotmac-hardening.conf << 'EOF'
# DotMac SSH Security Hardening

# Disable root login
PermitRootLogin no

# Disable password authentication (use key-based only)
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes

# Limit login attempts
MaxAuthTries 3
MaxSessions 4

# Timeout settings
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 60

# Protocol and encryption
Protocol 2
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha2-256,hmac-sha2-512
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512

# Disable unused features
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
PermitTunnel no

# Logging
SyslogFacility AUTHPRIV
LogLevel VERBOSE

# Banner
Banner /etc/ssh/banner
EOF
    
    # Create SSH banner
    cat > /etc/ssh/banner << 'EOF'
***************************************************************************
                    AUTHORIZED ACCESS ONLY
                    
This system is for authorized users only. All activity is monitored
and logged. Unauthorized access is prohibited and may be subject to
legal action.
***************************************************************************
EOF
    
    # Test SSH configuration
    sshd -t
    
    # Restart SSH service
    systemctl restart sshd
    
    print_status "SSH configuration hardened"
    print_warning "Ensure you have SSH key access before logging out!"
}

# Configure audit logging
configure_audit_logging() {
    print_step "Configuring system audit logging..."
    
    # Configure auditd rules
    cat > /etc/audit/rules.d/99-dotmac.rules << 'EOF'
# DotMac Audit Rules

# Delete all existing rules
-D

# Set buffer size
-b 8192

# Failure mode (0=silent 1=printk 2=panic)
-f 1

# Monitor authentication events
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/gshadow -p wa -k identity

# Monitor login/logout events
-w /var/log/lastlog -p wa -k logins
-w /var/run/faillock -p wa -k logins

# Monitor sudo usage
-w /etc/sudoers -p wa -k scope
-w /etc/sudoers.d/ -p wa -k scope

# Monitor network configuration
-w /etc/hosts -p wa -k network
-w /etc/network/ -p wa -k network

# Monitor Docker daemon
-w /usr/bin/docker -p x -k docker
-w /var/lib/docker -p wa -k docker

# Monitor DotMac application directories
-w /opt/dotmac -p wa -k dotmac
-w /var/log/dotmac -p wa -k dotmac

# Monitor critical system files
-w /etc/ssh/sshd_config -p wa -k sshd
-w /etc/fail2ban -p wa -k fail2ban

# System calls to monitor
-a always,exit -F arch=b64 -S execve -k commands
-a always,exit -F arch=b32 -S execve -k commands

# File access monitoring
-a always,exit -F arch=b64 -S open,openat,creat -F exit=-EACCES -k access
-a always,exit -F arch=b64 -S open,openat,creat -F exit=-EPERM -k access

# Make the rules immutable
-e 2
EOF
    
    # Restart auditd
    systemctl enable auditd
    systemctl restart auditd
    
    print_status "System audit logging configured"
}

# Secure Docker installation
secure_docker() {
    print_step "Securing Docker installation..."
    
    # Create Docker daemon configuration
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << 'EOF'
{
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
EOF
    
    # Download Docker's default seccomp profile
    curl -sSL https://raw.githubusercontent.com/moby/moby/master/profiles/seccomp/default.json \
        -o /etc/docker/seccomp.json
    
    # Create Docker security options
    mkdir -p /etc/systemd/system/docker.service.d
    cat > /etc/systemd/system/docker.service.d/security.conf << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd --containerd=/run/containerd/containerd.sock --icc=false --userland-proxy=false
EOF
    
    # Add current user to docker group (if not root)
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
    fi
    
    # Restart Docker
    systemctl daemon-reload
    systemctl restart docker
    
    print_status "Docker installation secured"
}

# Set up file integrity monitoring
setup_file_integrity_monitoring() {
    print_step "Setting up file integrity monitoring with AIDE..."
    
    # Initialize AIDE database
    aideinit
    
    # Move database to expected location
    mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db
    
    # Create custom AIDE configuration
    cat >> /etc/aide/aide.conf << 'EOF'

# DotMac specific monitoring
/opt/dotmac FIPSR
/etc/docker FIPSR
/etc/fail2ban FIPSR
/etc/ssh FIPSR
EOF
    
    # Set up daily AIDE check
    cat > /etc/cron.daily/aide-check << 'EOF'
#!/bin/bash
# Daily AIDE file integrity check

AIDE_LOG="/var/log/aide.log"
AIDE_REPORT="/tmp/aide-report.txt"

# Run AIDE check
aide --check > "$AIDE_REPORT" 2>&1

# If changes detected, log and alert
if [ $? -ne 0 ]; then
    echo "$(date): AIDE detected file system changes" >> "$AIDE_LOG"
    cat "$AIDE_REPORT" >> "$AIDE_LOG"
    
    # Send alert (customize based on your notification system)
    echo "File integrity violations detected. Check $AIDE_LOG for details." | \
        mail -s "AIDE Alert - File System Changes Detected" admin@localhost
fi

# Clean up
rm -f "$AIDE_REPORT"
EOF
    
    chmod +x /etc/cron.daily/aide-check
    
    print_status "File integrity monitoring configured"
}

# Configure security limits
configure_security_limits() {
    print_step "Configuring system security limits..."
    
    # Configure system limits
    cat > /etc/security/limits.d/99-dotmac-security.conf << 'EOF'
# DotMac Security Limits

# Limit core dumps
* soft core 0
* hard core 0

# Limit number of processes
* soft nproc 1000
* hard nproc 2000

# Limit number of open files
* soft nofile 4096
* hard nofile 8192

# Limit memory usage (in KB)
* soft rss 1048576
* hard rss 2097152
EOF
    
    # Disable core dumps system-wide
    echo "* hard core 0" >> /etc/security/limits.conf
    echo "fs.suid_dumpable = 0" >> /etc/sysctl.conf
    
    # Configure kernel security parameters
    cat >> /etc/sysctl.conf << 'EOF'

# DotMac Security Hardening
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
kernel.randomize_va_space = 2
EOF
    
    # Apply sysctl settings
    sysctl -p
    
    print_status "Security limits and kernel parameters configured"
}

# Set up log rotation
setup_log_rotation() {
    print_step "Configuring log rotation for DotMac logs..."
    
    cat > /etc/logrotate.d/dotmac << 'EOF'
/opt/dotmac/logs/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        /usr/bin/docker-compose -f /opt/dotmac/deployment/production/docker-compose.prod.yml restart nginx > /dev/null 2>&1 || true
    endscript
}

/var/log/dotmac*.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF
    
    print_status "Log rotation configured"
}

# Generate security report
generate_security_report() {
    print_step "Generating security hardening report..."
    
    local report_file="/var/log/dotmac-security-report-$(date +%Y%m%d).txt"
    
    cat > "$report_file" << EOF
DotMac Framework Security Hardening Report
Generated: $(date)
==========================================

System Information:
- OS: $(lsb_release -d | cut -f2)
- Kernel: $(uname -r)
- Hostname: $(hostname)

Security Measures Implemented:
- [✓] System packages updated
- [✓] Security packages installed
- [✓] UFW firewall configured
- [✓] Fail2Ban intrusion prevention
- [✓] SSH hardening applied
- [✓] Audit logging configured
- [✓] Docker security enhanced
- [✓] File integrity monitoring (AIDE)
- [✓] Security limits configured
- [✓] Log rotation set up

Active Security Services:
EOF
    
    # Check service status
    for service in ufw fail2ban auditd docker; do
        if systemctl is-active --quiet "$service"; then
            echo "- [✓] $service: ACTIVE" >> "$report_file"
        else
            echo "- [✗] $service: INACTIVE" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << 'EOF'

Next Steps:
1. Review and test all security configurations
2. Set up monitoring and alerting for security events
3. Configure backup encryption
4. Implement additional application-level security measures
5. Schedule regular security assessments

For detailed configuration files and logs, check:
- /var/log/dotmac-security-hardening.log
- /etc/security/
- /etc/audit/
- /etc/fail2ban/
EOF
    
    print_status "Security report generated: $report_file"
    
    # Display summary
    print_header "\n🔒 SECURITY HARDENING COMPLETED"
    print_header "=" * 50
    print_status "Security report: $report_file"
    print_status "All security measures have been implemented"
    print_warning "Please review the configuration and test system access"
    print_warning "Ensure you can still access the system before logging out!"
}

# Main execution
main() {
    print_header "🔒 DotMac Framework Security Hardening"
    print_header "=" * 60
    
    echo "$(date): Starting security hardening" | tee -a "$LOG_FILE"
    
    # Check privileges
    check_privileges
    
    # Perform hardening steps
    harden_system
    configure_firewall
    configure_fail2ban
    harden_ssh
    configure_audit_logging
    secure_docker
    setup_file_integrity_monitoring
    configure_security_limits
    setup_log_rotation
    generate_security_report
    
    echo "$(date): Security hardening completed" | tee -a "$LOG_FILE"
}

# Handle command line options
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo "  --help, -h    Show this help message"
        echo "  --version, -v Show version information"
        exit 0
        ;;
    --version|-v)
        echo "DotMac Security Hardening Script v1.0.0"
        exit 0
        ;;
esac

# Run main function
main "$@"
