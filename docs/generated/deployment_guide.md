# Deployment Guide

## Health Checks

The application provides the following health check endpoints:

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /health/startup` - Startup probe

## Container Deployment

Build the container:

```bash
docker build -t dotmac-platform .
```

## Database Setup

The application uses PostgreSQL. Ensure database is configured with:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```

*Auto-generated on 2025-08-29 12:59:00*
