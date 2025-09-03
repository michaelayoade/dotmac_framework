# GitHub Repository Secrets Setup Guide

## Required Secrets for CI/CD Pipeline

Your CI/CD pipeline requires these secrets to be configured in your GitHub repository:

### 🔐 **Required Secrets**

#### 1. `AUTH_ADMIN_EMAIL`
- **Purpose**: Email address for the initial admin user during bootstrap
- **Format**: Valid email address
- **Example**: `admin@yourdomain.com`
- **Usage**: Used by `dotmac-admin bootstrap --check-only` command

#### 2. `AUTH_INITIAL_ADMIN_PASSWORD`
- **Purpose**: Secure password for the initial admin user
- **Format**: Strong password (min 12 chars, mixed case, numbers, symbols)
- **Example**: `SecureAdm1n!Pass2024`
- **Security**: This should be a unique, strong password

#### 3. `CODECOV_TOKEN` (Optional)
- **Purpose**: Authentication token for Codecov coverage reporting
- **Format**: UUID-style token from Codecov
- **Example**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **Note**: Optional - CI will continue without it but coverage won't be uploaded

## 📝 **Step-by-Step Setup Instructions**

### Method 1: GitHub Web Interface

1. **Navigate to your repository on GitHub**
   - Go to `https://github.com/YOUR_USERNAME/dotmac-framework`

2. **Access Settings**
   - Click on the "Settings" tab (you need admin access)

3. **Go to Secrets and Variables**
   - In the left sidebar, click "Secrets and variables"
   - Select "Actions"

4. **Add Repository Secrets**
   - Click "New repository secret" button
   - Add each secret one by one:

   **For AUTH_ADMIN_EMAIL:**
   ```
   Name: AUTH_ADMIN_EMAIL
   Secret: admin@yourdomain.com
   ```

   **For AUTH_INITIAL_ADMIN_PASSWORD:**
   ```
   Name: AUTH_INITIAL_ADMIN_PASSWORD
   Secret: YourSecurePassword123!
   ```

   **For CODECOV_TOKEN (optional):**
   ```
   Name: CODECOV_TOKEN
   Secret: your-codecov-token-here
   ```

### Method 2: GitHub CLI

If you have GitHub CLI installed, you can add secrets via command line:

```bash
# Set admin email
gh secret set AUTH_ADMIN_EMAIL --body "admin@yourdomain.com"

# Set admin password (will prompt securely)
gh secret set AUTH_INITIAL_ADMIN_PASSWORD

# Set codecov token (optional)
gh secret set CODECOV_TOKEN --body "your-codecov-token-here"
```

## 🔍 **Getting Your Codecov Token**

1. **Sign up/Login to Codecov**
   - Go to https://codecov.io/
   - Sign in with your GitHub account

2. **Add Your Repository**
   - Click "Add new repository"
   - Find and select your `dotmac-framework` repository

3. **Get Your Token**
   - Codecov will display your repository token
   - Copy this token to use as `CODECOV_TOKEN` secret

## ✅ **Verification**

After adding the secrets, you can verify they're working by:

1. **Check Secrets List**
   - Go to Settings → Secrets and variables → Actions
   - You should see your secrets listed (values are hidden)

2. **Trigger a CI Run**
   - Push a commit or create a pull request
   - Check the "Security Bootstrap Validation" step in the CI logs
   - It should now run instead of being skipped

3. **Expected CI Output**
   ```
   ✅ Security bootstrap environment validated
   ```

## 🛡️ **Security Best Practices**

### For AUTH_INITIAL_ADMIN_PASSWORD:
- Use a unique password (not used elsewhere)
- Minimum 12 characters
- Include uppercase, lowercase, numbers, and symbols
- Consider using a password manager
- This is only for CI validation - use a different password in production

### General Secret Management:
- Never commit secrets to code
- Rotate secrets regularly
- Use different secrets for different environments
- Limit access to secrets (only repository admins)

## 🚨 **Troubleshooting**

### If CI Still Skips Bootstrap Validation:
1. Check secret names match exactly (case-sensitive)
2. Ensure you have admin access to the repository
3. Verify secrets are added to the correct repository
4. Re-run the CI pipeline after adding secrets

### If Bootstrap Command Fails:
1. Check that the admin email format is valid
2. Ensure password meets complexity requirements
3. Verify the `dotmac-admin bootstrap --check-only` command exists
4. Check CI logs for specific error messages

## 📋 **Quick Checklist**

- [ ] Added `AUTH_ADMIN_EMAIL` secret
- [ ] Added `AUTH_INITIAL_ADMIN_PASSWORD` secret  
- [ ] Added `CODECOV_TOKEN` secret (optional)
- [ ] Verified secrets appear in GitHub Settings
- [ ] Tested CI pipeline runs bootstrap validation
- [ ] Confirmed coverage uploads work (if using Codecov)

---

**Need Help?** Check the CI logs for detailed error messages or create an issue in the repository.