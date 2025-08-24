Troubleshooting Guide
====================

This comprehensive troubleshooting guide covers common issues, diagnostic procedures, and solutions for the DotMac platform.

.. contents::
   :local:
   :depth: 3

Common Issues
-------------

Application Startup Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Application fails to start with database connection errors

.. code-block:: console

   ERROR: Connection to database failed: could not connect to server
   DETAIL: FATAL: password authentication failed for user "dotmac"

**Diagnosis**:

.. code-block:: bash

   # Check database connectivity
   pg_isready -h localhost -p 5432 -U dotmac
   
   # Test authentication
   psql -h localhost -p 5432 -U dotmac -d dotmac_db

**Solutions**:

1. **Verify database credentials**:
   
   .. code-block:: bash
   
      # Check environment variables
      echo $DATABASE_URL
      echo $DB_PASSWORD
      
      # Verify .env file
      grep -E "^DB_|^DATABASE_" .env

2. **Reset database password**:
   
   .. code-block:: sql
   
      -- Connect as postgres superuser
      ALTER USER dotmac WITH PASSWORD 'new_secure_password';
      GRANT ALL PRIVILEGES ON DATABASE dotmac_db TO dotmac;

3. **Check network connectivity**:
   
   .. code-block:: bash
   
      # Test port connectivity
      telnet localhost 5432
      
      # Check firewall rules
      sudo ufw status

**Symptom**: Redis connection failures

.. code-block:: console

   ERROR: Redis connection failed: [Errno 111] Connection refused

**Diagnosis**:

.. code-block:: bash

   # Check Redis status
   redis-cli ping
   
   # Verify Redis is running
   sudo systemctl status redis

**Solutions**:

1. **Start Redis service**:
   
   .. code-block:: bash
   
      sudo systemctl start redis
      sudo systemctl enable redis

2. **Check Redis configuration**:
   
   .. code-block:: bash
   
      # Check Redis config
      redis-cli CONFIG GET "*"
      
      # Test connection with auth
      redis-cli -a your_redis_password ping

Authentication & Authorization Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Users cannot log in with valid credentials

.. code-block:: console

   HTTP 401: Invalid email or password

**Diagnosis**:

.. code-block:: python

   # Debug user authentication
   from dotmac_isp.modules.identity.services.auth_service import AuthService
   
   # Check user exists and is active
   user = db.query(User).filter(User.email == "user@example.com").first()
   print(f"User found: {user is not None}")
   print(f"User active: {user.is_active if user else 'N/A'}")
   print(f"User locked: {user.is_locked if user else 'N/A'}")

**Solutions**:

1. **Reset user account**:
   
   .. code-block:: python
   
      # Reset failed login attempts
      user.failed_login_attempts = "0"
      user.locked_until = None
      user.is_active = True
      db.commit()

2. **Verify password hashing**:
   
   .. code-block:: python
   
      from dotmac_isp.shared.auth import verify_password, hash_password
      
      # Test password verification
      is_valid = verify_password("user_password", user.password_hash)
      print(f"Password valid: {is_valid}")

**Symptom**: JWT token validation failures

.. code-block:: console

   HTTP 403: Invalid or expired token

**Diagnosis**:

.. code-block:: bash

   # Check JWT configuration
   echo $JWT_SECRET_KEY
   echo $JWT_ALGORITHM
   echo $JWT_EXPIRE_MINUTES

**Solutions**:

1. **Regenerate JWT secret**:
   
   .. code-block:: bash
   
      # Generate new secret key
      python -c "import secrets; print(secrets.token_urlsafe(32))"

2. **Verify token expiration**:
   
   .. code-block:: python
   
      import jwt
      from datetime import datetime
      
      try:
          decoded = jwt.decode(token, secret, algorithms=["HS256"])
          exp_time = datetime.fromtimestamp(decoded['exp'])
          print(f"Token expires: {exp_time}")
      except jwt.ExpiredSignatureError:
          print("Token has expired")

Performance Issues
~~~~~~~~~~~~~~~~~~

**Symptom**: Slow API response times

.. code-block:: console

   WARNING: Request took 5.2s to complete
   Endpoint: /api/customers

**Diagnosis**:

.. code-block:: python

   # Check database query performance
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   
   # Enable SQL query logging
   SQLALCHEMY_ECHO = True

.. code-block:: bash

   # Check database performance
   sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   
   # Check slow queries
   sudo -u postgres psql -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

**Solutions**:

1. **Add database indexes**:
   
   .. code-block:: sql
   
      -- Common indexes for customer queries
      CREATE INDEX idx_customers_email ON customers(email);
      CREATE INDEX idx_customers_tenant_id ON customers(tenant_id);
      CREATE INDEX idx_customers_status ON customers(status);
      CREATE INDEX idx_customers_created_at ON customers(created_at);

2. **Optimize queries**:
   
   .. code-block:: python
   
      # Use database joins instead of multiple queries
      customers = db.query(Customer)\
          .join(ServiceInstance)\
          .filter(Customer.tenant_id == tenant_id)\
          .all()
      
      # Add query limits
      customers = db.query(Customer)\
          .filter(Customer.tenant_id == tenant_id)\
          .limit(100)\
          .offset(page * 100)\
          .all()

3. **Enable query caching**:
   
   .. code-block:: python
   
      # Use Redis caching for expensive queries
      from dotmac_isp.core.cache import cache_manager
      
      @cache_manager.cached(timeout=300)
      async def get_customer_analytics(tenant_id: str):
          return await expensive_analytics_query(tenant_id)

**Symptom**: High memory usage

.. code-block:: console

   WARNING: Memory usage at 90% (7.2GB / 8GB)

**Diagnosis**:

.. code-block:: bash

   # Check memory usage by process
   ps aux --sort=-%mem | head -10
   
   # Monitor Python memory usage
   python -m memory_profiler your_script.py
   
   # Check for memory leaks
   sudo valgrind --tool=memcheck python app.py

**Solutions**:

1. **Optimize database connections**:
   
   .. code-block:: python
   
      # Use connection pooling
      SQLALCHEMY_ENGINE_OPTIONS = {
          "pool_size": 10,
          "max_overflow": 20,
          "pool_pre_ping": True,
          "pool_recycle": 3600
      }

2. **Implement pagination**:
   
   .. code-block:: python
   
      # Paginate large result sets
      def get_customers_paginated(page: int = 0, size: int = 50):
          return db.query(Customer)\
              .limit(size)\
              .offset(page * size)\
              .all()

Network & Connectivity Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: External API integration failures

.. code-block:: console

   ERROR: HTTP 503 Service Unavailable
   Failed to connect to payment-processor.com

**Diagnosis**:

.. code-block:: bash

   # Test external connectivity
   curl -I https://payment-processor.com/api/health
   
   # Check DNS resolution
   nslookup payment-processor.com
   
   # Test with different DNS
   nslookup payment-processor.com 8.8.8.8

**Solutions**:

1. **Implement retry logic**:
   
   .. code-block:: python
   
      import asyncio
      from tenacity import retry, stop_after_attempt, wait_exponential
      
      @retry(
          stop=stop_after_attempt(3),
          wait=wait_exponential(multiplier=1, min=4, max=10)
      )
      async def call_external_api(url: str):
          async with httpx.AsyncClient() as client:
              response = await client.get(url, timeout=30.0)
              response.raise_for_status()
              return response.json()

2. **Add circuit breaker**:
   
   .. code-block:: python
   
      from circuit_breaker import CircuitBreaker
      
      payment_api_breaker = CircuitBreaker(
          failure_threshold=5,
          recovery_timeout=30,
          expected_exception=httpx.RequestError
      )
      
      @payment_api_breaker
      async def process_payment(payment_data):
          return await payment_api.charge(payment_data)

File System Issues
~~~~~~~~~~~~~~~~~~

**Symptom**: File upload failures

.. code-block:: console

   ERROR: Permission denied: '/app/uploads/invoice_123.pdf'

**Diagnosis**:

.. code-block:: bash

   # Check file permissions
   ls -la /app/uploads/
   
   # Check disk space
   df -h /app/uploads/
   
   # Check inode usage
   df -i /app/uploads/

**Solutions**:

1. **Fix permissions**:
   
   .. code-block:: bash
   
      # Set correct ownership
      sudo chown -R app:app /app/uploads/
      
      # Set proper permissions
      chmod 755 /app/uploads/
      chmod 644 /app/uploads/*.pdf

2. **Clean up old files**:
   
   .. code-block:: bash
   
      # Remove files older than 30 days
      find /app/uploads/ -type f -mtime +30 -delete
   
      # Remove empty directories
      find /app/uploads/ -type d -empty -delete

Module-Specific Issues
----------------------

Billing Module Issues
~~~~~~~~~~~~~~~~~~~~

**Issue**: Payment processing failures

**Symptoms**:
- Credit card charges fail unexpectedly
- Webhook processing errors
- Duplicate payment attempts

**Diagnosis Steps**:

.. code-block:: python

   # Check payment processor logs
   from dotmac_isp.modules.billing.services.payment_service import PaymentService
   
   payment_service = PaymentService(db, tenant_id)
   payment_logs = await payment_service.get_payment_logs(
       start_date=yesterday,
       end_date=today,
       status="failed"
   )
   
   for log in payment_logs:
       print(f"Payment {log.id}: {log.error_message}")

**Common Solutions**:

1. **Invalid payment methods**:
   
   .. code-block:: python
   
      # Validate payment method before processing
      if not await payment_service.validate_payment_method(payment_method_id):
          raise PaymentError("Invalid payment method")

2. **Webhook signature validation**:
   
   .. code-block:: python
   
      # Ensure webhook signatures are properly verified
      def verify_webhook_signature(payload, signature, secret):
          expected_sig = hmac.new(
              secret.encode(),
              payload,
              hashlib.sha256
          ).hexdigest()
          return hmac.compare_digest(signature, f"sha256={expected_sig}")

Identity Module Issues
~~~~~~~~~~~~~~~~~~~~~

**Issue**: Customer Portal ID conflicts

**Symptoms**:
- Duplicate Portal ID generation
- Customer login failures
- Portal ID validation errors

**Diagnosis**:

.. code-block:: python

   # Check for Portal ID duplicates
   from sqlalchemy import func
   
   duplicates = db.query(Customer.portal_id, func.count(Customer.portal_id))\
       .group_by(Customer.portal_id)\
       .having(func.count(Customer.portal_id) > 1)\
       .all()
   
   for portal_id, count in duplicates:
       print(f"Duplicate Portal ID {portal_id}: {count} occurrences")

**Solution**:

.. code-block:: python

   # Regenerate Portal IDs for duplicates
   from dotmac_isp.modules.identity.portal_id_generator import PortalIDGenerator
   
   generator = PortalIDGenerator()
   
   for portal_id, count in duplicates:
       customers = db.query(Customer).filter(Customer.portal_id == portal_id).all()
       for i, customer in enumerate(customers[1:], 1):  # Keep first, regenerate others
           new_portal_id = generator.generate_unique_id(db, tenant_id)
           customer.portal_id = new_portal_id
           print(f"Updated customer {customer.id} to Portal ID {new_portal_id}")
   
   db.commit()

Network Monitoring Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: SNMP polling failures

**Symptoms**:
- Device status showing as unknown
- Missing network metrics
- Monitoring alerts not triggering

**Diagnosis**:

.. code-block:: python

   # Test SNMP connectivity
   from dotmac_isp.modules.network_monitoring.snmp_client import SNMPClient
   
   snmp_client = SNMPClient()
   
   try:
       result = await snmp_client.get_device_info("192.168.1.1")
       print(f"Device info: {result}")
   except SNMPError as e:
       print(f"SNMP Error: {e}")

**Solutions**:

1. **Verify SNMP credentials**:
   
   .. code-block:: python
   
      # Test different SNMP versions
      for version in [1, 2, 3]:
          try:
              result = await snmp_client.get(
                  target="192.168.1.1",
                  community="public",
                  version=version
              )
              print(f"SNMP v{version} works")
              break
          except Exception as e:
              print(f"SNMP v{version} failed: {e}")

2. **Check firewall rules**:
   
   .. code-block:: bash
   
      # Allow SNMP traffic
      sudo ufw allow from 192.168.1.0/24 to any port 161
      
      # Test SNMP walk
      snmpwalk -v2c -c public 192.168.1.1 1.3.6.1.2.1.1

Diagnostic Tools
----------------

Database Diagnostics
~~~~~~~~~~~~~~~~~~~~

**Connection Health Check**:

.. code-block:: python

   from dotmac_isp.core.database import get_db
   from sqlalchemy import text
   
   async def check_database_health():
       db = get_db()
       try:
           # Test basic connectivity
           result = db.execute(text("SELECT 1")).scalar()
           assert result == 1
           
           # Check critical tables
           tables = ["customers", "invoices", "payments", "users"]
           for table in tables:
               count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
               print(f"{table}: {count} records")
           
           # Check database size
           size_query = text("""
               SELECT pg_size_pretty(pg_database_size(current_database())) as size
           """)
           size = db.execute(size_query).scalar()
           print(f"Database size: {size}")
           
           return True
       except Exception as e:
           print(f"Database health check failed: {e}")
           return False

**Performance Monitoring**:

.. code-block:: python

   async def monitor_database_performance():
       slow_queries = text("""
           SELECT query, mean_time, calls, total_time
           FROM pg_stat_statements 
           WHERE mean_time > 1000
           ORDER BY mean_time DESC 
           LIMIT 10
       """)
       
       results = db.execute(slow_queries).fetchall()
       for query, mean_time, calls, total_time in results:
           print(f"Slow query ({mean_time:.2f}ms avg): {query[:100]}...")

Application Health Checks
~~~~~~~~~~~~~~~~~~~~~~~~~

**Service Status Check**:

.. code-block:: python

   from fastapi import FastAPI
   from dotmac_isp.core.health import HealthChecker
   
   app = FastAPI()
   health_checker = HealthChecker()
   
   @app.get("/health")
   async def health_check():
       results = await health_checker.check_all([
           health_checker.check_database,
           health_checker.check_redis,
           health_checker.check_external_apis,
           health_checker.check_file_system
       ])
       
       overall_status = "healthy" if all(results.values()) else "unhealthy"
       
       return {
           "status": overall_status,
           "checks": results,
           "timestamp": datetime.utcnow().isoformat()
       }

**Memory and Resource Monitoring**:

.. code-block:: python

   import psutil
   import asyncio
   
   async def monitor_system_resources():
       while True:
           # CPU usage
           cpu_percent = psutil.cpu_percent(interval=1)
           
           # Memory usage
           memory = psutil.virtual_memory()
           memory_percent = memory.percent
           
           # Disk usage
           disk = psutil.disk_usage('/')
           disk_percent = disk.percent
           
           print(f"CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
           
           # Alert if resources are high
           if memory_percent > 85:
               print("WARNING: High memory usage!")
           
           if disk_percent > 90:
               print("CRITICAL: Low disk space!")
           
           await asyncio.sleep(60)  # Check every minute

Log Analysis Tools
~~~~~~~~~~~~~~~~~~

**Automated Log Analysis**:

.. code-block:: python

   import re
   from collections import defaultdict
   
   def analyze_application_logs(log_file_path: str):
       error_patterns = {
           'database_errors': r'ERROR.*database',
           'auth_failures': r'HTTP 401|authentication failed',
           'payment_failures': r'payment.*failed|HTTP 402',
           'timeout_errors': r'timeout|timed out',
           'memory_errors': r'MemoryError|out of memory'
       }
       
       error_counts = defaultdict(int)
       recent_errors = []
       
       with open(log_file_path, 'r') as f:
           for line in f:
               for error_type, pattern in error_patterns.items():
                   if re.search(pattern, line, re.IGNORECASE):
                       error_counts[error_type] += 1
                       recent_errors.append((error_type, line.strip()))
       
       print("Error Summary:")
       for error_type, count in error_counts.items():
           print(f"  {error_type}: {count}")
       
       print("\nRecent Errors:")
       for error_type, line in recent_errors[-10:]:
           print(f"  [{error_type}] {line}")

Emergency Procedures
--------------------

Database Recovery
~~~~~~~~~~~~~~~~

**Backup and Restore**:

.. code-block:: bash

   # Create database backup
   pg_dump -h localhost -U dotmac -d dotmac_db > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Restore from backup
   psql -h localhost -U dotmac -d dotmac_db < backup_20240201_120000.sql

**Point-in-Time Recovery**:

.. code-block:: bash

   # Stop the application
   sudo systemctl stop dotmac-app
   
   # Restore to specific point in time
   pg_basebackup -h localhost -D /var/lib/postgresql/recovery -U dotmac -v -P -W
   
   # Start PostgreSQL in recovery mode
   echo "restore_command = 'cp /path/to/wal/%f %p'" >> /var/lib/postgresql/recovery/recovery.conf
   echo "recovery_target_time = '2024-02-01 12:00:00'" >> /var/lib/postgresql/recovery/recovery.conf

Application Rollback
~~~~~~~~~~~~~~~~~~~~

**Quick Rollback Procedure**:

.. code-block:: bash

   # Stop current application
   sudo systemctl stop dotmac-app
   
   # Rollback to previous version
   cd /opt/dotmac
   sudo git checkout HEAD~1
   
   # Restore previous database migration
   alembic downgrade -1
   
   # Restart application
   sudo systemctl start dotmac-app
   
   # Verify health
   curl http://localhost:8000/health

**Docker Rollback**:

.. code-block:: bash

   # Stop current containers
   docker-compose down
   
   # Rollback to previous image
   docker tag dotmac:latest dotmac:broken
   docker tag dotmac:v1.0.0 dotmac:latest
   
   # Start with previous version
   docker-compose up -d
   
   # Monitor logs
   docker-compose logs -f

Contact Information
-------------------

**Emergency Contacts**:

- **Platform Team Lead**: platform-lead@dotmac.com
- **Database Administrator**: dba@dotmac.com  
- **Security Team**: security@dotmac.com
- **On-call Engineer**: +1-555-DOTMAC-1

**Escalation Procedures**:

1. **Severity 1 (Service Down)**: Contact on-call engineer immediately
2. **Severity 2 (Performance Issues)**: Create ticket and notify team lead
3. **Severity 3 (Minor Issues)**: Create ticket for next business day

**Support Channels**:

- **Internal Slack**: #dotmac-support
- **Monitoring Dashboard**: https://monitor.dotmac.com
- **Status Page**: https://status.dotmac.com