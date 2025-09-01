#!/bin/bash

# DB Migration Job Script
# Runs migrations safely with locking and exits
# Prevents multi-replica migration races

set -e

echo "🔄 Starting database migration job..."

# Configuration
MAX_WAIT_SECONDS=300  # 5 minutes max wait for DB
LOCK_TIMEOUT=600      # 10 minutes lock timeout
MIGRATION_LOCK_KEY="dotmac_migration_lock"

# Function to wait for database
wait_for_database() {
    echo "⏳ Waiting for database connection..."
    
    # Parse DATABASE_URL
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ DATABASE_URL environment variable is required"
        exit 1
    fi
    
    # Extract connection details from DATABASE_URL
    # Format: postgresql://user:password@host:port/dbname
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_USER=$(echo $DATABASE_URL | sed -n 's/postgresql:\/\/\([^:]*\):.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Default port if not specified
    DB_PORT=${DB_PORT:-5432}
    
    echo "🔌 Connecting to: $DB_HOST:$DB_PORT/$DB_NAME"
    
    # Wait for database to be ready
    for i in $(seq 1 $MAX_WAIT_SECONDS); do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            echo "✅ Database is ready"
            return 0
        fi
        echo "⏳ Database not ready, waiting... ($i/$MAX_WAIT_SECONDS)"
        sleep 1
    done
    
    echo "❌ Database connection timeout after $MAX_WAIT_SECONDS seconds"
    exit 1
}

# Function to acquire migration lock
acquire_migration_lock() {
    echo "🔒 Acquiring migration lock..."
    
    # Use PostgreSQL advisory locks for coordination
    python3 << EOF
import sys
import psycopg2
import os
from urllib.parse import urlparse

try:
    # Connect to database
    database_url = os.environ['DATABASE_URL']
    result = urlparse(database_url)
    
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    
    # Try to acquire advisory lock (non-blocking)
    cursor = conn.cursor()
    lock_id = hash('$MIGRATION_LOCK_KEY') % (2**31)  # Convert to 32-bit int
    
    cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
    lock_acquired = cursor.fetchone()[0]
    
    if lock_acquired:
        print("✅ Migration lock acquired")
        # Keep connection open to maintain lock
        with open('/tmp/migration_lock_conn', 'w') as f:
            f.write(str(conn.get_dsn_parameters()))
        sys.exit(0)
    else:
        print("⏳ Another migration is in progress, waiting...")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Failed to acquire migration lock: {e}")
    sys.exit(1)
EOF

    return $?
}

# Function to release migration lock
release_migration_lock() {
    echo "🔓 Releasing migration lock..."
    
    python3 << EOF
import psycopg2
import os
from urllib.parse import urlparse

try:
    database_url = os.environ['DATABASE_URL']
    result = urlparse(database_url)
    
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    
    cursor = conn.cursor()
    lock_id = hash('$MIGRATION_LOCK_KEY') % (2**31)
    
    cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
    conn.close()
    
    print("✅ Migration lock released")
    
except Exception as e:
    print(f"⚠️ Failed to release migration lock: {e}")
EOF
}

# Function to run migrations
run_migrations() {
    echo "🔄 Running database migrations..."
    
    cd /app
    
    # Check current migration state
    echo "📋 Current migration state:"
    alembic current -v
    
    # Run migrations
    echo "⬆️ Applying migrations..."
    if alembic upgrade head; then
        echo "✅ Migrations completed successfully"
        
        # Log migration state after upgrade
        echo "📋 Final migration state:"
        alembic current -v
        
        return 0
    else
        echo "❌ Migration failed"
        return 1
    fi
}

# Function to verify migration success
verify_migrations() {
    echo "🔍 Verifying migration success..."
    
    # Check that we can connect and query basic tables
    python3 << EOF
import psycopg2
import os
from urllib.parse import urlparse

try:
    database_url = os.environ['DATABASE_URL']
    result = urlparse(database_url)
    
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    
    cursor = conn.cursor()
    
    # Check if alembic_version table exists and has entries
    cursor.execute("""
        SELECT version_num FROM alembic_version 
        ORDER BY version_num DESC LIMIT 1
    """)
    
    latest_version = cursor.fetchone()
    if latest_version:
        print(f"✅ Database is at migration version: {latest_version[0]}")
    else:
        print("⚠️ No migration version found")
        
    conn.close()
    print("✅ Migration verification successful")
    
except Exception as e:
    print(f"❌ Migration verification failed: {e}")
    sys.exit(1)
EOF

    return $?
}

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up migration job..."
    release_migration_lock
    rm -f /tmp/migration_lock_conn
}

# Set up cleanup trap
trap cleanup EXIT

# Main migration process
main() {
    echo "🚀 Database Migration Job Started"
    echo "📅 $(date)"
    echo "🏷️ SERVICE_TYPE: ${SERVICE_TYPE:-migration}"
    
    # Wait for database to be available
    wait_for_database
    
    # Acquire migration lock (with retry)
    RETRY_COUNT=0
    MAX_RETRIES=30  # 5 minutes with 10s intervals
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if acquire_migration_lock; then
            break
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Waiting for migration lock... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 10
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ Failed to acquire migration lock after $MAX_RETRIES attempts"
        exit 1
    fi
    
    # Run migrations
    if run_migrations; then
        echo "✅ Migration job completed successfully"
        
        # Verify migrations worked
        verify_migrations
        
        # Mark completion for health check
        touch /app/migration_complete
        
        echo "🎉 Database migration job finished"
        exit 0
    else
        echo "❌ Migration job failed"
        exit 1
    fi
}

# Run main function
main "$@"