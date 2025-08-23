#!/bin/bash
# wait-for-services.sh - Wait for required services to be available

set -e

# Default service endpoints
POSTGRES_HOST=${POSTGRES_HOST:-test-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-test-redis}
REDIS_PORT=${REDIS_PORT:-6379}

echo "⏳ Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
until nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  echo "⏳ PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is up!"

echo "⏳ Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
until nc -z $REDIS_HOST $REDIS_PORT; do
  echo "⏳ Redis is unavailable - sleeping"
  sleep 2
done
echo "✅ Redis is up!"

echo "🎯 All services are ready! Running: $@"
exec "$@"