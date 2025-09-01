#!/bin/bash
# Generate secure secrets for Coolify deployment

echo "🔐 Generating secure secrets for DotMac Management Platform"
echo "=" * 60

# Generate SECRET_KEY (32+ characters)
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=${SECRET_KEY}"

# Generate JWT_SECRET_KEY (32+ characters)  
JWT_SECRET_KEY=$(openssl rand -hex 32)
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}"

# Generate ENCRYPTION_KEY (32 bytes, base64 encoded)
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo "ENCRYPTION_KEY=${ENCRYPTION_KEY}"

# Generate WEBHOOK_SECRET
WEBHOOK_SECRET=$(openssl rand -hex 24)
echo "WEBHOOK_SECRET=${WEBHOOK_SECRET}"

echo ""
echo "📋 Copy these into your Coolify environment variables:"
echo "SECRET_KEY=${SECRET_KEY}"
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}"
echo "ENCRYPTION_KEY=${ENCRYPTION_KEY}"
echo "WEBHOOK_SECRET=${WEBHOOK_SECRET}"

echo ""
echo "✅ All secrets generated! Keep these secure."