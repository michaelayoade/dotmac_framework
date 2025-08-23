#!/bin/bash
# Initialize multiple test databases for isolated testing

set -e

# Create databases for each service
databases="dotmac_identity_test dotmac_billing_test dotmac_services_test dotmac_networking_test dotmac_analytics_test dotmac_platform_test"

echo "Creating test databases..."

for db in $databases; do
    echo "Creating database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        CREATE DATABASE $db;
        GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
done

# Create test data schema
echo "Creating test schemas..."
for db in $databases; do
    echo "Setting up schema for: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        CREATE SCHEMA IF NOT EXISTS test_data;
        CREATE SCHEMA IF NOT EXISTS fixtures;
        
        -- Create a test tenants table for multi-tenancy testing
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert test tenant data
        INSERT INTO tenants (name, slug) VALUES 
        ('Test ISP 1', 'test-isp-1'),
        ('Test ISP 2', 'test-isp-2'),
        ('Demo ISP', 'demo-isp')
        ON CONFLICT (slug) DO NOTHING;
        
        -- Create test users table
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id),
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            is_admin BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert test user data  
        INSERT INTO test_users (tenant_id, email, username, hashed_password) VALUES
        (1, 'admin@test-isp-1.com', 'admin1', 'hashed_password_123'),
        (1, 'user@test-isp-1.com', 'user1', 'hashed_password_123'),
        (2, 'admin@test-isp-2.com', 'admin2', 'hashed_password_123'),
        (3, 'demo@demo-isp.com', 'demo', 'hashed_password_123')
        ON CONFLICT (email) DO NOTHING;
        
EOSQL
done

echo "Test databases initialized successfully!"