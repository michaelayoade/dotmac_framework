#!/bin/bash
# Generate SSL certificates for PostgreSQL

set -e

CERT_DIR="/home/dotmac_framework/certs/dev"
mkdir -p "$CERT_DIR"

# Generate CA key and certificate
openssl genrsa -out "$CERT_DIR/postgres-ca.key" 4096
openssl req -new -x509 -days 3650 -key "$CERT_DIR/postgres-ca.key" \
    -out "$CERT_DIR/postgres-ca.crt" \
    -subj "/C=US/ST=CA/L=Silicon Valley/O=DotMac/CN=PostgreSQL CA"

# Generate server key and certificate
openssl genrsa -out "$CERT_DIR/postgres-server.key" 4096
openssl req -new -key "$CERT_DIR/postgres-server.key" \
    -out "$CERT_DIR/postgres-server.csr" \
    -subj "/C=US/ST=CA/L=Silicon Valley/O=DotMac/CN=postgres.dotmac.local"

# Sign server certificate with CA
openssl x509 -req -days 365 -in "$CERT_DIR/postgres-server.csr" \
    -CA "$CERT_DIR/postgres-ca.crt" -CAkey "$CERT_DIR/postgres-ca.key" \
    -CAcreateserial -out "$CERT_DIR/postgres-server.crt"

# Set proper permissions
chmod 600 "$CERT_DIR/postgres-server.key"
chmod 644 "$CERT_DIR/postgres-server.crt"
chmod 644 "$CERT_DIR/postgres-ca.crt"

echo "PostgreSQL SSL certificates generated successfully in $CERT_DIR"
echo "Restart PostgreSQL to apply: sudo systemctl restart postgresql"
