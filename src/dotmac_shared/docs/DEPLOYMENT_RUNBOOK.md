# Deployment Runbook (Consolidated)

This document has been consolidated into the canonical runbook at `docs/PRODUCTION_DEPLOYMENT_RUNBOOK.md`.

Quick CI/CD reference (GitHub Actions):

```bash
# Trigger: push to main
git checkout main && git pull && git merge feature/your-feature && git push origin main

# Manual trigger / watch / rollback
gh workflow run intelligent-deployment.yml
gh run list --workflow=intelligent-deployment.yml --limit=5
gh run watch
gh workflow run rollback.yml -f rollback_to=previous
```

For Kubernetes/Docker deployments, troubleshooting, verification checklists, and escalation paths, see the canonical runbook above.

