# DotMac Framework Security Configuration

This directory contains security scanning configuration that handles legitimate secret templates while maintaining strong security posture.

## 🛡️ Security Scanning Approach

### Template-Aware Scanning

Our security tools are configured to:
- ✅ **Allow legitimate templates**: `${SECRET:name}` patterns  
- ❌ **Block hardcoded secrets**: Real passwords, API keys, tokens
- 🔍 **Context-aware rules**: Different rules for different file types
- 📋 **Document requirements**: All templates must be documented

## 📁 Configuration Files

| File | Tool | Purpose |
|------|------|---------|
| `security-scan-config.yaml` | Generic | Master configuration for all tools |
| `gitleaks.toml` | GitLeaks | Git-based secret detection |
| `trufflehog-exclude.txt` | TruffleHog | Pattern exclusions |
| `.semgrep.yml` | Semgrep | Static analysis rules |

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The `security-scanning.yml` workflow provides:

1. **Multi-tool scanning**: GitLeaks, TruffleHog, Semgrep
2. **Template recognition**: Ignores `${SECRET:*}` patterns
3. **Custom validation**: Additional Python-based checks
4. **Documentation verification**: Ensures templates are documented
5. **PR comments**: Results posted to pull requests

### Running Locally

```bash
# Run GitLeaks with our config
gitleaks detect --config=.security/gitleaks.toml

# Run TruffleHog with exclusions
trufflehog git file://. --exclude-paths=.security/trufflehog-exclude.txt

# Run custom template-aware scan
python3 .security/template-aware-scan.py
```

## 📋 Legitimate Template Patterns

### ✅ Safe Patterns (Allowed)

```python
# Secret injection templates
password = "${SECRET:database_password}"
api_key = "${SECRET:stripe_secret_key}"

# Template validation code
if config.jwt_secret.startswith("${SECRET:"):
    # validation logic

# Template detection logic  
if "${SECRET:" in value:
    # detection logic
```

### ❌ Dangerous Patterns (Blocked)

```python
# Hardcoded credentials (will trigger alerts)
password = "my_real_password123"
api_key = "sk_live_abc123xyz789"
secret = "hardcoded_secret_value"
```

## 🏗️ Adding New Templates

When adding new secret templates:

1. **Use standard format**: `${SECRET:descriptive_name}`
2. **Add to documentation**: Update relevant docs
3. **Test scanning**: Verify it's recognized as safe
4. **Add comments**: Include inline documentation

Example:
```python
# Safe template with documentation
database_url = "${SECRET:postgres_connection_string}"  # Injected at deployment
```

## 🚨 Security Policy Enforcement

### CI/CD Rules

- ✅ **Templates allowed**: `${SECRET:*}` patterns pass
- ❌ **Hardcoded secrets**: Block PR merge
- 📋 **Documentation required**: All templates must be explained
- 🔍 **Multiple tools**: Layered detection approach

### Policy Violations

If security scan fails:

1. **Review violations**: Check scan output
2. **Verify legitimacy**: Is it really a hardcoded secret?
3. **Fix or document**: Either remove secret or add to allowlist
4. **Re-run scan**: Verify fixes work

## 🔧 Maintenance

### Regular Tasks

- Review allowlist patterns monthly
- Update exclusions as needed  
- Test new security tool versions
- Audit template documentation

### Tool Updates

When updating security tools:
1. Test with current codebase
2. Verify template patterns still work
3. Update configurations if needed
4. Document any changes

## 📞 Support

For security scanning issues:
1. Check this documentation first
2. Review CI/CD workflow logs
3. Test locally with provided commands
4. Update configurations as needed

## 🎯 Best Practices

### For Developers

- ✅ Use `${SECRET:name}` for all secrets
- ✅ Add descriptive names to templates
- ✅ Include inline comments explaining templates
- ❌ Never commit real secrets, even temporarily
- ❌ Don't bypass security scans without review

### For DevOps

- 🔍 Review security scan results regularly
- 📋 Maintain template documentation
- 🔄 Update configurations as tools evolve
- 🛡️ Monitor for new threat patterns

This approach ensures **strong security** while allowing **legitimate development practices**.