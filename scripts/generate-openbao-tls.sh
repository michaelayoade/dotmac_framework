#!/bin/bash

# OpenBao TLS Certificate Generation Script
# Generates production-ready TLS certificates for OpenBao deployment

set -e

echo "🔐 OpenBao TLS Certificate Generation"
echo "====================================="

# Configuration
CERT_DIR="${1:-/tmp/openbao-tls}"
DOMAIN="${OPENBAO_DOMAIN:-openbao.dotmac.com}"
COUNTRY="${TLS_COUNTRY:-US}"
STATE="${TLS_STATE:-California}"
CITY="${TLS_CITY:-San Francisco}"
ORG="${TLS_ORG:-DotMac Framework}"
ORG_UNIT="${TLS_ORG_UNIT:-Platform Engineering}"
EMAIL="${TLS_EMAIL:-security@dotmac.com}"
KEY_SIZE=4096
DAYS=365

echo "📁 Certificate directory: $CERT_DIR"
echo "🌐 Domain: $DOMAIN"
echo "🔑 Key size: $KEY_SIZE bits"
echo "📅 Validity: $DAYS days"
echo ""

# Create certificate directory
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# Generate CA private key
echo "🔑 Generating CA private key..."
openssl genrsa -out ca-key.pem $KEY_SIZE

# Generate CA certificate
echo "📜 Generating CA certificate..."
cat > ca.conf <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORG
OU = $ORG_UNIT Certificate Authority
CN = DotMac OpenBao CA
emailAddress = $EMAIL

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
EOF

openssl req -new -x509 -key ca-key.pem -out ca.crt -days $DAYS -config ca.conf

# Generate server private key
echo "🔑 Generating server private key..."
openssl genrsa -out server-key.pem $KEY_SIZE

# Generate server certificate signing request
echo "📝 Generating server certificate signing request..."
cat > server.conf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORG
OU = $ORG_UNIT
CN = $DOMAIN
emailAddress = $EMAIL

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation,digitalSignature,keyEncipherment
subjectAltName = @alt_names
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = openbao
DNS.3 = localhost
DNS.4 = openbao.default.svc.cluster.local
DNS.5 = openbao.dotmac.svc.cluster.local
DNS.6 = *.dotmac.com
IP.1 = 127.0.0.1
IP.2 = 10.0.0.0/8
IP.3 = 172.16.0.0/12
IP.4 = 192.168.0.0/16
EOF

openssl req -new -key server-key.pem -out server.csr -config server.conf

# Generate server certificate signed by CA
echo "📜 Generating server certificate..."
cat > server-ext.conf <<EOF
basicConstraints = CA:FALSE
keyUsage = nonRepudiation,digitalSignature,keyEncipherment
subjectAltName = @alt_names
extendedKeyUsage = serverAuth
authorityKeyIdentifier = keyid,issuer

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = openbao
DNS.3 = localhost
DNS.4 = openbao.default.svc.cluster.local
DNS.5 = openbao.dotmac.svc.cluster.local
DNS.6 = *.dotmac.com
IP.1 = 127.0.0.1
IP.2 = 10.0.0.0/8
IP.3 = 172.16.0.0/12
IP.4 = 192.168.0.0/16
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca-key.pem -out server.crt -days $DAYS -extensions v3_req -extfile server-ext.conf -CAcreateserial

# Generate client certificate for mutual TLS (optional)
echo "🔑 Generating client certificate for mutual TLS..."
openssl genrsa -out client-key.pem $KEY_SIZE

cat > client.conf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORG
OU = $ORG_UNIT Client
CN = DotMac OpenBao Client
emailAddress = $EMAIL

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation,digitalSignature,keyEncipherment
extendedKeyUsage = clientAuth
EOF

openssl req -new -key client-key.pem -out client.csr -config client.conf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca-key.pem -out client.crt -days $DAYS -extensions v3_req -extfile client.conf -CAcreateserial

# Set proper permissions
chmod 600 *-key.pem
chmod 644 *.crt

# Create symbolic links for OpenBao expected names
ln -sf server.crt tls.crt
ln -sf server-key.pem tls.key

echo ""
echo "✅ TLS certificates generated successfully!"
echo "📁 Certificate directory: $CERT_DIR"
echo ""
echo "📋 Generated files:"
echo "   ca.crt                - Certificate Authority certificate"
echo "   ca-key.pem           - Certificate Authority private key"
echo "   server.crt / tls.crt - Server certificate"
echo "   server-key.pem / tls.key - Server private key"
echo "   client.crt           - Client certificate (for mutual TLS)"
echo "   client-key.pem       - Client private key"
echo ""

# Verify certificates
echo "🔍 Certificate verification:"
echo "CA Certificate:"
openssl x509 -in ca.crt -text -noout | grep -A 2 "Subject:"
echo ""
echo "Server Certificate:"
openssl x509 -in server.crt -text -noout | grep -A 2 "Subject:"
echo ""
echo "Certificate chain verification:"
openssl verify -CAfile ca.crt server.crt

echo ""
echo "🚀 Next steps:"
echo "1. Copy certificates to OpenBao container/pod:"
echo "   docker cp $CERT_DIR/ca.crt openbao:/openbao/tls/"
echo "   docker cp $CERT_DIR/server.crt openbao:/openbao/tls/"
echo "   docker cp $CERT_DIR/server-key.pem openbao:/openbao/tls/"
echo ""
echo "2. Update OpenBao configuration to use TLS certificates"
echo "3. Restart OpenBao service"
echo "4. Update client configurations to use HTTPS endpoints"
echo ""
echo "⚠️  Security reminder:"
echo "   - Store the CA private key (ca-key.pem) securely"
echo "   - Distribute the CA certificate (ca.crt) to clients"
echo "   - Monitor certificate expiration dates"
echo "   - Implement certificate rotation procedures"