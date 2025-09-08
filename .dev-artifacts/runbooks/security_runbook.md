# Security Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Security Monitoring

### Daily Security Checks
```bash
# Check for failed authentication attempts
sudo grep -i "authentication" /var/log/dotmac/*.log

# Monitor unusual access patterns
sudo tail -100 /var/log/nginx/access.log | grep -E "40[0-9]|50[0-9]"

# Check for suspicious activity
sudo grep -i "unauthorized\|forbidden" /var/log/dotmac/*.log
```

### Access Control Review
```bash
# Check user permissions
sudo cat /etc/sudoers | grep dotmac
ls -la /opt/dotmac/.env.production

# Review database access
sudo docker exec -it dotmac-postgres psql -U postgres
\du
```

### Security Updates
```bash
# Check for security updates
sudo apt list --upgradable | grep -i security

# Update critical security patches
sudo apt upgrade -y
```

## Incident Response

### Security Incident Procedure
1. **Isolate affected systems**
2. **Preserve evidence**
3. **Notify security team**
4. **Implement fixes**
5. **Monitor for further activity**

### Emergency Response
```bash
# Block suspicious IP
sudo ufw insert 1 deny from SUSPICIOUS_IP

# Enable maintenance mode
sudo cp /etc/nginx/maintenance.html /var/www/html/

# Capture system state
sudo docker logs dotmac-management > /tmp/incident-logs.txt
sudo netstat -tlnp > /tmp/network-state.txt
```
