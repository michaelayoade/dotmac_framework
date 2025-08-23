#!/bin/bash

# DotMac ISP Framework - Production Celery Setup Script
# This script sets up Celery for production deployment with systemd

set -e

echo "🚀 Setting up Celery for production..."

# Create necessary directories
echo "Creating directories..."
sudo mkdir -p /var/log/celery
sudo mkdir -p /var/run/celery

# Create celery user if it doesn't exist
if ! id "dotmac" &>/dev/null; then
    echo "Creating dotmac user..."
    sudo useradd --system --shell /bin/bash --home /home/dotmac_framework --no-create-home dotmac
fi

# Set permissions
echo "Setting permissions..."
sudo chown dotmac:dotmac /var/log/celery
sudo chown dotmac:dotmac /var/run/celery
sudo chmod 755 /var/log/celery
sudo chmod 755 /var/run/celery

# Copy systemd service files
echo "Installing systemd service files..."
sudo cp scripts/celery-worker.service /etc/systemd/system/
sudo cp scripts/celery-beat.service /etc/systemd/system/

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable services
echo "Enabling Celery services..."
sudo systemctl enable celery-worker.service
sudo systemctl enable celery-beat.service

echo "✅ Celery production setup completed!"
echo ""
echo "To start Celery services:"
echo "  sudo systemctl start celery-worker"
echo "  sudo systemctl start celery-beat"
echo ""
echo "To check service status:"
echo "  sudo systemctl status celery-worker"
echo "  sudo systemctl status celery-beat"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u celery-worker -f"
echo "  sudo journalctl -u celery-beat -f"
echo ""
echo "Log files location:"
echo "  Worker: /var/log/celery/worker.log"
echo "  Beat: /var/log/celery/beat.log"