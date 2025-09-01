# 🚀 Coolify Setup Walkthrough - DotMac Management Platform

## Prerequisites Checklist
- ✅ Coolify server running and accessible
- ✅ Domain name pointed to your server
- ✅ Docker registry access (if using private images)

## Step 1: Create New Project in Coolify

1. **Login to your Coolify dashboard**
2. **Create new project**: 
   - Name: `dotmac-management-platform`
   - Description: `DotMac ISP Management Platform`

## Step 2: Add Required Services

### 2.1 Create PostgreSQL Database
1. **Add Service** → **Database** → **PostgreSQL**
2. **Configuration**:
   - Name: `dotmac-postgres` 
   - Database: `dotmac_management`
   - Username: `dotmac_user`
   - Password: `[Generate strong password]`
   - Version: `15` (recommended)

### 2.2 Create Redis Cache  
1. **Add Service** → **Database** → **Redis**
2. **Configuration**:
   - Name: `dotmac-redis`
   - Password: `[Generate strong password]`
   - Version: `7` (recommended)

## Step 3: Deploy Management Application

### 3.1 Create Application Service
1. **Add Service** → **Application** 
2. **Source Configuration**:
   - **Git Repository**: `https://github.com/yourusername/dotmac-framework.git`
   - **Branch**: `main` (or your production branch)
   - **Build Pack**: `Docker`
   - **Dockerfile**: Use existing `Dockerfile`

### 3.2 Set Environment Variables

Copy these into Coolify's Environment Variables section:

```bash
# === CORE APPLICATION ===
ENVIRONMENT=production
SERVICE_TYPE=management
DEBUG=false
LOG_LEVEL=info

# === DATABASE (Auto-filled by Coolify) ===
# Coolify will auto-populate DATABASE_URL from your PostgreSQL service
# DATABASE_URL=postgresql://dotmac_user:password@dotmac-postgres:5432/dotmac_management

# === CACHE (Auto-filled by Coolify) ===  
# Coolify will auto-populate REDIS_URL from your Redis service
# REDIS_URL=redis://:password@dotmac-redis:6379/0

# === SECURITY (IMPORTANT: Generate these!) ===
SECRET_KEY=your-super-secret-key-min-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-also-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-base64-encoded-32-byte-encryption-key

# === API CONFIGURATION ===
API_V1_STR=/api/v1
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# === MANAGEMENT APP SPECIFIC ===
MANAGEMENT_API_VERSION=v1
ADMIN_EMAIL=admin@yourdomain.com
WEBHOOK_SECRET=your-webhook-secret-for-integrations

# === PERFORMANCE ===
WEB_CONCURRENCY=4
MAX_WORKERS=4
KEEPALIVE=2
GRACEFUL_TIMEOUT=30

# === FEATURES ===
ENABLE_METRICS=true
ENABLE_TRACING=true
CONTAINER_ORCHESTRATION_ENABLED=true
TENANT_ISOLATION_ENABLED=true
```

### 3.3 Port Configuration
- **Port**: `8001` (as defined in docker-compose.coolify.yml)
- **Expose**: `8001:8001`

### 3.4 Health Check
- **Path**: `/health`
- **Port**: `8001`
- **Interval**: `30s`

## Step 4: Domain Configuration

### 4.1 Set Domain
1. Go to **Domains** section of your application
2. Add your domain: `management.yourdomain.com`
3. **Enable HTTPS** (Let's Encrypt)

### 4.2 Configure DNS
Point your domain to your Coolify server:
```
management.yourdomain.com → A record → [Your Server IP]
```

## Step 5: Deploy!

1. **Click "Deploy"** in Coolify
2. **Monitor logs** for any issues
3. **Wait for successful deployment** (usually 2-5 minutes)

## Step 6: Verify Deployment

### 6.1 Check Health Endpoints
```bash
curl https://management.yourdomain.com/health
# Should return: {"status": "healthy"}
```

### 6.2 Check API Documentation  
Visit: `https://management.yourdomain.com/docs`

### 6.3 Test Database Migration
Check logs for successful migration:
```
[INFO] Database migrations completed successfully
[INFO] Management platform started on port 8001
```

## Step 7: Create First Admin User

### 7.1 Access Admin Creation Endpoint
```bash
# POST to create first admin
curl -X POST https://management.yourdomain.com/api/v1/admin/setup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "your-secure-password",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

### 7.2 Login and Test
```bash
# Test login
curl -X POST https://management.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com", 
    "password": "your-secure-password"
  }'
```

## 🎉 Success!

Your DotMac Management Platform is now running on Coolify!

**Next Steps:**
1. **Create first tenant** via API or admin panel
2. **Configure ISP instance deployment** for tenants
3. **Test complete tenant provisioning flow**

## 🔧 Troubleshooting

### Common Issues:

**1. Database Connection Failed**
- Check PostgreSQL service is running
- Verify DATABASE_URL environment variable
- Check network connectivity between services

**2. Redis Connection Failed**  
- Check Redis service is running
- Verify REDIS_URL environment variable
- Check Redis password

**3. Build Failures**
- Check Docker build logs in Coolify
- Verify Dockerfile exists and is correct
- Check for missing dependencies

**4. Health Check Failures**
- Verify application is binding to `0.0.0.0:8001` not `localhost:8001`
- Check logs for startup errors
- Ensure health endpoint returns 200 status

### Log Access
- **Application logs**: Coolify → Your App → Logs
- **Database logs**: Coolify → PostgreSQL Service → Logs  
- **Build logs**: Coolify → Your App → Deployments → View logs

## 📞 Need Help?

If you encounter issues:
1. Check the logs in Coolify dashboard
2. Verify all environment variables are set
3. Ensure services are running and connected
4. Test database connectivity

Let me know if you need assistance with any specific step!