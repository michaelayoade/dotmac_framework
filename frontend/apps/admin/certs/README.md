# SSL Certificates

SSL certificates have been moved to `/home/dotmac_framework/certs/dev/` for security reasons.

## Development Setup

```bash
# Certificates are now located at:
# /home/dotmac_framework/certs/dev/cert.pem
# /home/dotmac_framework/certs/dev/key.pem

# Update your docker-compose or application configuration to reference:
# - Certificate: ../../certs/dev/cert.pem
# - Private Key: ../../certs/dev/key.pem
```

## Production Setup

For production, use proper SSL certificate management:
- Let's Encrypt for automatic certificate provisioning
- External certificate management service
- Never commit certificates to repository

## Security Note

SSL certificates and private keys should NEVER be committed to version control.