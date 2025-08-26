#!/bin/bash
# Deployment script for ISP Framework on remote server

set -e

echo "🚀 Starting ISP Framework Deployment..."

# Create deployment directory
mkdir -p /opt/dotmac-tenant
cd /opt/dotmac-tenant

# Stop existing services
echo "⏹️ Stopping existing services..."
docker-compose -f docker-compose.remote.yml down || true

# Pull latest images
echo "📦 Pulling Docker images..."
docker-compose -f docker-compose.remote.yml pull

# Build ISP Framework
echo "🏗️ Building ISP Framework..."
docker-compose -f docker-compose.remote.yml build

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.remote.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.remote.yml ps

# Test ISP Framework
echo "🧪 Testing ISP Framework..."
curl -f http://localhost:8000/health || exit 1

echo "✅ Deployment completed successfully!"
echo "📍 ISP Framework: http://149.102.135.97:8000"
echo "🏥 Health Check: http://149.102.135.97:8000/health"
echo "📚 API Docs: http://149.102.135.97:8000/docs"
