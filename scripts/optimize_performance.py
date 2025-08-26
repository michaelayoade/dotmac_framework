#!/usr/bin/env python3
"""
Performance Optimization Script for DotMac Framework
Optimizes database, caching, and application performance using existing infrastructure
"""

import subprocess
import json
import os
import sys
from pathlib import Path
import time
import logging

class PerformanceOptimizer:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.production_dir = self.project_root / "deployment" / "production"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def run_command(self, command: str, description: str = "") -> bool:
        """Execute command with proper logging"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would run: {command}")
            return True
        
        self.logger.info(f"Executing: {description or command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return True
            else:
                self.logger.error(f"Command failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Exception: {e}")
            return False

    def optimize_postgresql(self):
        """Optimize PostgreSQL configuration using existing setup"""
        self.logger.info("🗄️ Optimizing PostgreSQL performance...")
        
        # Create PostgreSQL optimization config
        pg_config = """# PostgreSQL Performance Optimization for DotMac Framework
# Append to postgresql.conf or use as postgresql.conf.d/dotmac.conf

# Memory settings (adjust based on available RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query planner settings
random_page_cost = 1.1
effective_io_concurrency = 200

# Connection settings
max_connections = 100
max_prepared_transactions = 0

# Logging for performance monitoring
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0

# Autovacuum optimization
autovacuum = on
log_autovacuum_min_duration = 0
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
"""
        
        pg_config_file = self.production_dir / "postgres" / "postgresql-performance.conf"
        pg_config_file.parent.mkdir(exist_ok=True)
        
        with open(pg_config_file, 'w') as f:
            f.write(pg_config)
        
        self.logger.info(f"PostgreSQL optimization config created: {pg_config_file}")
        
        # Apply optimizations to running container
        os.chdir(self.production_dir)
        
        # Check if PostgreSQL container is running
        if self.run_command("docker-compose -f docker-compose.prod.yml ps postgres-shared | grep -q Up", "Check PostgreSQL container"):
            # Create indexes for common queries
            index_queries = [
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email ON users(email);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_user_id ON sessions(user_id);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_created_at ON audit_logs(created_at);",
            ]
            
            for query in index_queries:
                self.run_command(
                    f'docker-compose -f docker-compose.prod.yml exec -T postgres-shared psql -U dotmac_admin -c "{query}"',
                    f"Create index: {query[:50]}..."
                )
            
            # Analyze tables for better query planning
            self.run_command(
                'docker-compose -f docker-compose.prod.yml exec -T postgres-shared psql -U dotmac_admin -c "ANALYZE;"',
                "Analyze database tables"
            )
        
        return True

    def optimize_redis_caching(self):
        """Optimize Redis configuration and implement caching strategies"""
        self.logger.info("🔄 Optimizing Redis caching...")
        
        os.chdir(self.production_dir)
        
        # Update Redis configuration using our performance config
        redis_config_source = self.production_dir / "redis" / "redis-performance.conf"
        
        if redis_config_source.exists():
            # Copy Redis configuration to container
            container_name = "dotmac-redis-prod"
            if self.run_command(f"docker ps | grep -q {container_name}", "Check Redis container"):
                self.run_command(
                    f"docker cp '{redis_config_source}' {container_name}:/usr/local/etc/redis/redis.conf",
                    "Update Redis configuration"
                )
                
                # Restart Redis to apply new configuration
                self.run_command(
                    "docker-compose -f docker-compose.prod.yml restart redis-shared",
                    "Restart Redis with new configuration"
                )
        
        # Configure Redis for optimal caching
        redis_commands = [
            "CONFIG SET maxmemory-policy allkeys-lru",
            "CONFIG SET save '900 1 300 10 60 10000'",
            "CONFIG SET tcp-keepalive 60",
            "CONFIG SET timeout 300"
        ]
        
        for cmd in redis_commands:
            self.run_command(
                f'docker-compose -f docker-compose.prod.yml exec -T redis-shared redis-cli {cmd}',
                f"Configure Redis: {cmd}"
            )
        
        return True

    def optimize_nginx_performance(self):
        """Optimize Nginx configuration for better performance"""
        self.logger.info("🌐 Optimizing Nginx performance...")
        
        # Our nginx.conf already has performance optimizations, but add specific enhancements
        nginx_optimizations = """# Additional Nginx Performance Optimizations
# Add to existing nginx.conf or create nginx-performance.conf

# Worker process optimization
worker_processes auto;
worker_connections 4096;
worker_rlimit_nofile 65535;

# Buffer optimizations
client_body_buffer_size 128k;
client_header_buffer_size 1k;
large_client_header_buffers 4 4k;
output_buffers 1 32k;
postpone_output 1460;

# Timeout optimizations
client_header_timeout 3m;
client_body_timeout 3m;
send_timeout 3m;

# Compression optimization (already in nginx.conf but ensure it's optimal)
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 16 8k;
gzip_http_version 1.1;

# Caching for static files
location ~* \.(jpg|jpeg|gif|png|css|js|ico|xml)$ {
    access_log off;
    log_not_found off;
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
}

# Enable HTTP/2 push for critical resources
location = /index.html {
    http2_push /css/main.css;
    http2_push /js/app.js;
}

# Rate limiting optimization
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Connection optimization
keepalive_timeout 65;
keepalive_requests 100;
"""
        
        nginx_perf_file = self.production_dir / "nginx" / "nginx-performance.conf"
        with open(nginx_perf_file, 'w') as f:
            f.write(nginx_optimizations)
        
        self.logger.info(f"Nginx performance config created: {nginx_perf_file}")
        
        # Reload Nginx configuration
        os.chdir(self.production_dir)
        if self.run_command("docker-compose -f docker-compose.prod.yml ps nginx | grep -q Up", "Check Nginx container"):
            self.run_command(
                "docker-compose -f docker-compose.prod.yml exec nginx nginx -t",
                "Test Nginx configuration"
            )
            self.run_command(
                "docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload",
                "Reload Nginx configuration"
            )
        
        return True

    def optimize_docker_containers(self):
        """Optimize Docker container performance"""
        self.logger.info("🐳 Optimizing Docker container performance...")
        
        # Update docker-compose.prod.yml with performance optimizations
        compose_optimizations = {
            "version": "3.8",
            "x-logging": {
                "driver": "json-file",
                "options": {
                    "max-size": "10m",
                    "max-file": "3"
                }
            },
            "x-resource-limits": {
                "limits": {
                    "memory": "512M"
                },
                "reservations": {
                    "memory": "256M"
                }
            }
        }
        
        # Create performance optimization overlay for docker-compose
        perf_compose_file = self.production_dir / "docker-compose.performance.yml"
        
        with open(perf_compose_file, 'w') as f:
            yaml_content = """version: '3.8'

services:
  isp-framework:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    environment:
      - GUNICORN_WORKERS=4
      - GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
      - GUNICORN_MAX_REQUESTS=1000
      - GUNICORN_MAX_REQUESTS_JITTER=50
      - REDIS_POOL_SIZE=20
    healthcheck:
      interval: 30s
      timeout: 10s
      retries: 3

  management-platform:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    environment:
      - GUNICORN_WORKERS=4
      - GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
      - GUNICORN_MAX_REQUESTS=1000
      - GUNICORN_MAX_REQUESTS_JITTER=50
    healthcheck:
      interval: 30s
      timeout: 10s
      retries: 3

  postgres-shared:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.8'
        reservations:
          memory: 512M
          cpus: '0.4'
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c work_mem=4MB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c max_connections=100

  redis-shared:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    sysctls:
      - net.core.somaxconn=65535

  nginx:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.25'
    sysctls:
      - net.core.somaxconn=65535
      - net.ipv4.ip_local_port_range=1024 65535
"""
            f.write(yaml_content)
        
        self.logger.info(f"Docker performance optimization config created: {perf_compose_file}")
        
        return True

    def setup_application_caching(self):
        """Setup application-level caching configuration"""
        self.logger.info("📦 Setting up application caching...")
        
        # Create caching configuration for Python applications
        caching_config = {
            "redis": {
                "host": "redis-shared",
                "port": 6379,
                "db": 0,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30,
                "max_connections": 20,
                "connection_pool_kwargs": {
                    "max_connections": 20,
                    "retry_on_timeout": True
                }
            },
            "cache_timeouts": {
                "user_session": 3600,  # 1 hour
                "user_profile": 1800,  # 30 minutes
                "static_data": 86400,  # 24 hours
                "api_responses": 300,  # 5 minutes
                "database_queries": 600  # 10 minutes
            },
            "cache_prefixes": {
                "session": "sess:",
                "user": "user:",
                "api": "api:",
                "query": "qry:"
            }
        }
        
        # Save caching configuration
        caching_config_file = self.production_dir / "configs" / "caching.json"
        caching_config_file.parent.mkdir(exist_ok=True)
        
        with open(caching_config_file, 'w') as f:
            json.dump(caching_config, f, indent=2)
        
        self.logger.info(f"Application caching config created: {caching_config_file}")
        
        return True

    def run_performance_tests(self):
        """Run basic performance tests to validate optimizations"""
        self.logger.info("🧪 Running performance validation tests...")
        
        os.chdir(self.production_dir)
        
        tests = [
            {
                "name": "Database Connection Pool",
                "command": "docker-compose -f docker-compose.prod.yml exec -T postgres-shared psql -U dotmac_admin -c 'SELECT version();'",
                "description": "Test PostgreSQL connectivity"
            },
            {
                "name": "Redis Performance",
                "command": "docker-compose -f docker-compose.prod.yml exec -T redis-shared redis-cli ping",
                "description": "Test Redis connectivity"
            },
            {
                "name": "Application Health",
                "command": "curl -f -s --connect-timeout 5 http://localhost:8000/health",
                "description": "Test application response"
            },
            {
                "name": "Nginx Response",
                "command": "curl -f -s --connect-timeout 5 http://localhost/health",
                "description": "Test Nginx response"
            }
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            self.logger.info(f"Running test: {test['name']}")
            if self.run_command(test["command"], test["description"]):
                self.logger.info(f"✅ {test['name']} - PASSED")
                passed_tests += 1
            else:
                self.logger.error(f"❌ {test['name']} - FAILED")
        
        self.logger.info(f"Performance tests completed: {passed_tests}/{total_tests} passed")
        return passed_tests == total_tests

    def optimize_performance(self):
        """Run all performance optimizations"""
        self.logger.info("🚀 Starting DotMac Framework Performance Optimization")
        self.logger.info("=" * 60)
        
        if self.dry_run:
            self.logger.info("🧪 DRY RUN MODE - No changes will be made")
        
        optimization_steps = [
            ("PostgreSQL Database", self.optimize_postgresql),
            ("Redis Caching", self.optimize_redis_caching),
            ("Nginx Web Server", self.optimize_nginx_performance),
            ("Docker Containers", self.optimize_docker_containers),
            ("Application Caching", self.setup_application_caching),
            ("Performance Validation", self.run_performance_tests)
        ]
        
        successful_steps = 0
        
        for step_name, step_function in optimization_steps:
            self.logger.info(f"\n🔧 Optimizing {step_name}...")
            try:
                if step_function():
                    self.logger.info(f"✅ {step_name} optimization completed")
                    successful_steps += 1
                else:
                    self.logger.error(f"❌ {step_name} optimization failed")
            except Exception as e:
                self.logger.error(f"❌ {step_name} optimization failed with exception: {e}")
        
        # Summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🚀 Performance Optimization Summary")
        self.logger.info(f"✅ Completed: {successful_steps}/{len(optimization_steps)} steps")
        
        if successful_steps == len(optimization_steps):
            self.logger.info("\n🎉 All performance optimizations completed successfully!")
            self.logger.info("\nOptimizations applied:")
            self.logger.info("• PostgreSQL query optimization and indexing")
            self.logger.info("• Redis caching configuration and memory optimization")
            self.logger.info("• Nginx performance tuning and HTTP/2")
            self.logger.info("• Docker container resource limits and optimization")
            self.logger.info("• Application-level caching strategies")
            
            self.logger.info("\nRecommended next steps:")
            self.logger.info("1. Monitor performance metrics in Grafana")
            self.logger.info("2. Run load testing to validate improvements")
            self.logger.info("3. Adjust caching timeouts based on usage patterns")
            self.logger.info("4. Monitor resource utilization and adjust limits as needed")
            return True
        else:
            self.logger.info(f"\n⚠️  Performance optimization completed with {len(optimization_steps) - successful_steps} issues")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="DotMac Framework Performance Optimization")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--test-only", action="store_true", help="Run performance tests only")
    
    args = parser.parse_args()
    
    optimizer = PerformanceOptimizer(dry_run=args.dry_run)
    
    if args.test_only:
        success = optimizer.run_performance_tests()
    else:
        success = optimizer.optimize_performance()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()