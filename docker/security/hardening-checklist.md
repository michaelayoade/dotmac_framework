# Docker Security Hardening Checklist

## Base Image Security
- [ ] Use official, minimal base images (alpine, distroless)
- [ ] Regularly update base images
- [ ] Scan base images for vulnerabilities
- [ ] Use specific image tags, not 'latest'

## User Security
- [ ] Run containers as non-root user
- [ ] Use numeric user IDs in USER instruction
- [ ] Set appropriate file permissions
- [ ] Remove shell access where possible

## Network Security
- [ ] Use custom networks instead of default bridge
- [ ] Implement network segmentation
- [ ] Expose only necessary ports
- [ ] Use internal networks for service communication

## File System Security
- [ ] Use read-only file systems where possible
- [ ] Mount sensitive directories as read-only
- [ ] Use tmpfs for temporary data
- [ ] Implement proper volume permissions

## Secret Management
- [ ] Use Docker secrets or external secret management
- [ ] Never embed secrets in images
- [ ] Use .dockerignore to exclude sensitive files
- [ ] Rotate secrets regularly

## Runtime Security
- [ ] Use security profiles (AppArmor, SELinux)
- [ ] Implement resource limits
- [ ] Use health checks
- [ ] Enable logging and monitoring

## Build Security
- [ ] Use multi-stage builds
- [ ] Minimize attack surface
- [ ] Verify package signatures
- [ ] Use dependency scanning

## Compliance
- [ ] Follow CIS Docker Benchmark
- [ ] Implement vulnerability scanning
- [ ] Regular security assessments
- [ ] Document security measures
