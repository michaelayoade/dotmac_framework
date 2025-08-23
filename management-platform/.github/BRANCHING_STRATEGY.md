# Git Branching Strategy

## Overview

This repository follows a **GitFlow-inspired** branching strategy optimized for continuous deployment and security-first development.

## Branch Types

### Main Branches

#### `main`
- **Purpose**: Production-ready code
- **Protection**: Highest level protection with mandatory reviews
- **Deployment**: Automatically deploys to production environment
- **Merge Policy**: Only from `develop` via pull request with 2+ approvals
- **Commit Signing**: Required
- **Status Checks**: All CI/CD pipeline stages must pass

#### `develop`
- **Purpose**: Integration branch for features
- **Protection**: Medium level protection
- **Deployment**: Automatically deploys to staging environment
- **Merge Policy**: From feature branches via pull request with 1+ approval
- **Status Checks**: Tests, security scans, and code quality checks must pass

### Supporting Branches

#### Feature Branches (`feature/`)
- **Naming**: `feature/TICKET-ID-short-description`
- **Example**: `feature/SEC-123-implement-2fa`
- **Source**: Branch from `develop`
- **Merge Target**: `develop`
- **Lifetime**: Short-lived (1-2 weeks maximum)
- **Purpose**: Develop new features or enhancements

#### Bugfix Branches (`bugfix/`)
- **Naming**: `bugfix/TICKET-ID-short-description`
- **Example**: `bugfix/BUG-456-fix-auth-timeout`
- **Source**: Branch from `develop`
- **Merge Target**: `develop`
- **Lifetime**: Short-lived (1-5 days)
- **Purpose**: Fix bugs in development

#### Hotfix Branches (`hotfix/`)
- **Naming**: `hotfix/TICKET-ID-short-description`
- **Example**: `hotfix/CRITICAL-789-security-patch`
- **Source**: Branch from `main`
- **Merge Target**: Both `main` and `develop`
- **Lifetime**: Very short-lived (hours to 1 day)
- **Purpose**: Critical fixes for production issues

#### Release Branches (`release/`)
- **Naming**: `release/v1.2.3`
- **Example**: `release/v2.1.0`
- **Source**: Branch from `develop`
- **Merge Target**: `main` and `develop`
- **Lifetime**: Short-lived (1-3 days)
- **Purpose**: Prepare releases, final testing, and version bumping

## Workflow

### Feature Development
1. Create feature branch from `develop`
2. Implement feature with tests
3. Run local quality checks (`make check`)
4. Push and create pull request to `develop`
5. Code review and approval
6. Merge to `develop` (triggers staging deployment)

### Release Process
1. Create release branch from `develop`
2. Version bump and final testing
3. Create pull request to `main`
4. Release approval and merge
5. Tag release and deploy to production
6. Merge release branch back to `develop`

### Hotfix Process
1. Create hotfix branch from `main`
2. Implement critical fix
3. Emergency review and testing
4. Merge to `main` (triggers production deployment)
5. Merge to `develop` to include fix

## Branch Protection Rules

### `main` Branch
- Require pull request reviews (2 reviewers minimum)
- Require status checks to pass
- Require branches to be up to date
- Require signed commits
- Restrict pushes to administrators only
- Require linear history

### `develop` Branch
- Require pull request reviews (1 reviewer minimum)
- Require status checks to pass
- Require branches to be up to date
- Require signed commits
- Allow force pushes for administrators

### Feature/Bugfix Branches
- No special protection (developers can push directly)
- CI/CD pipeline runs on push
- Pre-commit hooks enforce code quality

## Commit Standards

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `ci`: CI/CD changes
- `chore`: Maintenance tasks
- `security`: Security-related changes

### Examples
```
feat(auth): implement two-factor authentication

Add TOTP-based 2FA support for enhanced security.
Includes SMS backup and recovery codes.

Closes #123
```

```
security(api): fix SQL injection vulnerability

Sanitize user input in search endpoints to prevent
SQL injection attacks.

BREAKING CHANGE: Search API now requires authentication
```

## Security Considerations

### Mandatory Security Checks
- All commits must be signed with GPG
- Pre-commit hooks scan for secrets and vulnerabilities
- Security scans required before merge to protected branches
- Dependency vulnerability checks on all PRs

### Secret Management
- Never commit secrets to any branch
- Use environment variables and secure vaults
- Rotate credentials immediately if accidentally committed
- Use `.env.example` files for configuration templates

### Code Review Security Focus
- Review for security vulnerabilities
- Validate input sanitization
- Check authentication and authorization
- Verify secure configuration practices

## Integration with CI/CD

### Branch-based Deployments
- `main` → Production environment
- `develop` → Staging environment
- Feature branches → Preview environments (optional)

### Pipeline Triggers
- Push to any branch: Run tests and security scans
- PR to `develop`: Full CI pipeline including integration tests
- PR to `main`: Complete pipeline with performance tests
- Tag creation: Release pipeline with deployment

## Emergency Procedures

### Critical Security Issues
1. Create emergency hotfix branch from `main`
2. Implement minimal fix with security review
3. Fast-track approval process (1 reviewer minimum)
4. Deploy immediately to production
5. Follow up with comprehensive fix in regular cycle

### Rollback Procedures
1. Identify last known good commit
2. Create rollback branch from that commit
3. Emergency deployment process
4. Investigation and proper fix in separate branch

## Best Practices

### Developer Guidelines
- Keep branches small and focused
- Rebase feature branches before merging
- Use descriptive commit messages
- Run `make check` before pushing
- Tag team members for security-sensitive changes

### Code Quality
- 80% minimum test coverage
- All security scans must pass
- Code complexity limits enforced
- Documentation required for new features

### Collaboration
- Use draft PRs for work in progress
- Request specific reviewers for expertise areas
- Link issues and tickets in commit messages
- Provide clear PR descriptions

This branching strategy ensures secure, reliable code delivery while maintaining development velocity and collaboration efficiency.