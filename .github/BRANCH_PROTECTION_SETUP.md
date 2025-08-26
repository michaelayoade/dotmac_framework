# Branch Protection Setup Guide

## 🛡️ Main Branch Protection Configuration

To protect the main branch and ensure code quality, follow these steps to configure branch protection rules:

## GitHub Web Interface Setup

### 1. Navigate to Branch Protection Settings
1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Branches** in the left sidebar
4. Click **Add rule** next to "Branch protection rules"

### 2. Configure Protection Rule

#### Branch Name Pattern
- **Branch name pattern**: `main`

#### Protection Settings (Check these boxes):

**Protect matching branches:**
- ✅ **Restrict pushes that create files larger than 100 MB**
- ✅ **Restrict force pushes**
- ✅ **Allow deletions** (uncheck this - we don't want deletions)

**Require a pull request before merging:**
- ✅ **Require a pull request before merging**
- ✅ **Require approvals** (set to at least 1)
- ✅ **Dismiss stale PR approvals when new commits are pushed**
- ✅ **Require review from code owners** (if you have CODEOWNERS file)

**Require status checks to pass before merging:**
- ✅ **Require status checks to pass before merging**
- ✅ **Require branches to be up to date before merging**

**Required Status Checks** (Add these):
- `deployment-readiness` (from our GitHub Actions workflow)
- `legacy-tests` (from our GitHub Actions workflow)
- `frontend-readiness` (from our GitHub Actions workflow)

**Restrict who can push to matching branches:**
- ✅ **Restrict pushes that create files larger than 100 MB**
- Consider adding specific users/teams if needed

**Rules applied to everyone including administrators:**
- ✅ **Include administrators** (recommended for consistency)

## 3. Save Protection Rule
Click **Create** to save the branch protection rule.

## Alternative: GitHub CLI Setup

If you prefer using GitHub CLI, you can set up branch protection with these commands:

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Login to GitHub
gh auth login

# Enable branch protection on main branch
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["deployment-readiness","legacy-tests","frontend-readiness"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

## 4. Verification

After setting up branch protection, verify it's working:

1. Try to push directly to main (should be blocked)
2. Create a test PR and verify status checks are required
3. Check that force pushes are blocked

## 🔧 Recommended Additional Files

### CODEOWNERS File
Create `.github/CODEOWNERS` to specify code review requirements:

```
# Global code owners
* @your-username

# Platform-specific owners
/isp-framework/ @isp-team
/management-platform/ @platform-team
/scripts/ @devops-team
/.github/ @devops-team

# Critical files require admin review
docker-compose*.yml @admin-team
.github/workflows/ @admin-team
*/requirements*.txt @admin-team
```

### Pull Request Template
Create `.github/pull_request_template.md`:

```markdown
## 🎯 Purpose
<!-- Briefly describe what this PR accomplishes -->

## 🧪 Testing
- [ ] All validation scripts pass (`python3 scripts/run_all_tests.py`)
- [ ] Manual testing completed
- [ ] No breaking changes introduced

## 📋 Checklist
- [ ] Code follows project conventions
- [ ] Documentation updated if needed
- [ ] Environment variables documented if added
- [ ] Database migrations included if schema changed
- [ ] Tests added for new functionality

## 🚀 Deployment Notes
<!-- Any special deployment considerations -->
```

## 📊 Status Check Integration

Our GitHub Actions workflow is already configured to work with branch protection:

- **deployment-readiness**: Must pass for merge approval
- **legacy-tests**: Additional validation
- **frontend-readiness**: Frontend validation (if applicable)

## 🚨 Important Notes

1. **Emergency Procedures**: Even with protection, repository admins can bypass rules if needed for hotfixes
2. **Status Check Names**: Ensure the status check names in branch protection match your GitHub Actions job names
3. **Review Requirements**: Adjust the number of required reviews based on your team size
4. **Admin Inclusion**: Including administrators in rules ensures consistency but allows override when needed

## 🔄 Updating Protection Rules

To modify branch protection rules:
1. Go to Settings → Branches
2. Click **Edit** next to the main branch rule
3. Update settings as needed
4. Click **Save changes**

## 📋 Quick Setup Checklist

- [ ] Navigate to repository Settings → Branches
- [ ] Add branch protection rule for `main`
- [ ] Enable "Require a pull request before merging"
- [ ] Set required approvals (minimum 1)
- [ ] Enable "Require status checks to pass before merging"
- [ ] Add status checks: `deployment-readiness`, `legacy-tests`, `frontend-readiness`
- [ ] Disable force pushes and deletions
- [ ] Include administrators in rules
- [ ] Create CODEOWNERS file (optional)
- [ ] Create PR template (optional)
- [ ] Test the protection by attempting direct push

This setup ensures code quality and prevents accidental damage to the main branch while maintaining the deployment readiness validation we've implemented.