#!/bin/bash

# DotMac Backend - Start All Services
echo "Starting DotMac Backend Services..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Start all services using supervisor
echo "Starting all services with supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf