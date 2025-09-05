#!/bin/bash
# DotMac Website Backend - Credential Setup Script
# Run this script to generate service credentials for the website backend

set -e

echo "🔐 DotMac Website Backend - Credential Setup"
echo "============================================="

# Check if .env exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Copy from example
cp .env.example .env

echo ""
echo "📝 Configuration Required:"
echo ""
echo "1. PAYSTACK CONFIGURATION:"
echo "   - Get your Paystack secret key from: https://dashboard.paystack.com/settings/developer"
echo "   - Create webhook endpoint in Paystack dashboard"
echo "   - Add webhook URL: https://yourwebsite.com/webhooks/paystack"
echo "   - Copy webhook signing secret"
echo ""
echo "2. HCAPTCHA CONFIGURATION:"
echo "   - Sign up at: https://www.hcaptcha.com/"
echo "   - Create new site and get secret key"
echo ""
echo "3. MANAGEMENT PLATFORM INTEGRATION:"
echo "   - Generate service token in Management Platform admin"
echo "   - Use full URL including https://"
echo ""
echo "4. UPDATE .env FILE:"
echo "   - Edit .env with your actual credentials"
echo "   - Never commit .env to version control"
echo ""

# Generate a secure service token format for reference
SERVICE_TOKEN="dmgmt_$(openssl rand -hex 32)"
echo "Example service token format: $SERVICE_TOKEN"
echo ""

echo "📋 Next Steps:"
echo "1. Edit .env file with your actual credentials"
echo "2. Test with: python backend.py"
echo "3. Deploy with: docker-compose up -d"
echo "4. Set up cron job for demo cleanup: docker-compose --profile cron run demo-cleanup"
echo ""
echo "🔒 Security Reminder:"
echo "- .env file contains sensitive credentials"
echo "- Add .env to .gitignore"
echo "- Use environment variables in production"
echo "- Rotate credentials regularly"
echo ""
echo "✅ Setup complete! Edit .env file to continue."