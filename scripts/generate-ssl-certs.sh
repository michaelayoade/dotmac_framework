#!/bin/bash
# DotMac Platform - SSL Certificate Generation Script
# Generates self-signed certificates for development/testing

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="$PROJECT_ROOT/ssl/certs"

echo -e "${BLUE}🔐 DotMac Platform - SSL Certificate Generator${NC}"
echo "================================================="
echo ""

# Create SSL directory
mkdir -p "$SSL_DIR"

# Certificate configuration
COUNTRY="US"
STATE="CA"
CITY="San Francisco"
ORGANIZATION="DotMac Technologies"
ORGANIZATIONAL_UNIT="Engineering"
EMAIL="engineering@dotmac.app"

# Domains to generate certificates for
DOMAINS=(
    "dotmac.local"
    "admin.dotmac.local"
    "portal.dotmac.local"
    "monitoring.dotmac.local"
    "*.dotmac.local"
    "localhost"
)

# Generate root CA private key
echo -e "${BLUE}🔑 Generating root CA private key...${NC}"
openssl genrsa -out "$SSL_DIR/ca.key" 4096

# Generate root CA certificate
echo -e "${BLUE}📜 Generating root CA certificate...${NC}"
openssl req -new -x509 -days 3650 -key "$SSL_DIR/ca.key" -out "$SSL_DIR/ca.crt" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT Root CA/CN=DotMac Root CA/emailAddress=$EMAIL"

# Function to generate certificate for a domain
generate_certificate() {
    local domain="$1"
    local safe_domain="${domain//\*/_wildcard}"
    
    echo -e "${BLUE}🌐 Generating certificate for: $domain${NC}"
    
    # Generate private key
    openssl genrsa -out "$SSL_DIR/${safe_domain}.key" 2048
    
    # Create certificate signing request config
    cat > "$SSL_DIR/${safe_domain}.conf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=$ORGANIZATIONAL_UNIT
CN=$domain
emailAddress=$EMAIL

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
EOF
    
    # Add subject alternative names
    if [[ "$domain" == *"*"* ]]; then
        # Wildcard certificate
        echo "DNS.1 = $domain" >> "$SSL_DIR/${safe_domain}.conf"
        echo "DNS.2 = ${domain#\*.}" >> "$SSL_DIR/${safe_domain}.conf"
        echo "DNS.3 = localhost" >> "$SSL_DIR/${safe_domain}.conf"
        echo "IP.1 = 127.0.0.1" >> "$SSL_DIR/${safe_domain}.conf"
        echo "IP.2 = ::1" >> "$SSL_DIR/${safe_domain}.conf"
    else
        # Regular certificate
        echo "DNS.1 = $domain" >> "$SSL_DIR/${safe_domain}.conf"
        echo "DNS.2 = localhost" >> "$SSL_DIR/${safe_domain}.conf"
        echo "IP.1 = 127.0.0.1" >> "$SSL_DIR/${safe_domain}.conf"
        echo "IP.2 = ::1" >> "$SSL_DIR/${safe_domain}.conf"
    fi
    
    # Generate certificate signing request
    openssl req -new -key "$SSL_DIR/${safe_domain}.key" -out "$SSL_DIR/${safe_domain}.csr" -config "$SSL_DIR/${safe_domain}.conf"
    
    # Generate certificate signed by CA
    openssl x509 -req -in "$SSL_DIR/${safe_domain}.csr" -CA "$SSL_DIR/ca.crt" -CAkey "$SSL_DIR/ca.key" -CAcreateserial -out "$SSL_DIR/${safe_domain}.crt" -days 365 -extensions v3_req -extfile "$SSL_DIR/${safe_domain}.conf"
    
    # Clean up
    rm "$SSL_DIR/${safe_domain}.csr" "$SSL_DIR/${safe_domain}.conf"
    
    echo -e "${GREEN}✅ Certificate generated: ${safe_domain}.crt${NC}"
}

# Generate certificates for all domains
for domain in "${DOMAINS[@]}"; do
    generate_certificate "$domain"
done

# Create default certificate (catch-all)
echo -e "${BLUE}🔒 Generating default certificate...${NC}"
openssl genrsa -out "$SSL_DIR/default.key" 2048
openssl req -new -x509 -days 365 -key "$SSL_DIR/default.key" -out "$SSL_DIR/default.crt" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=default/emailAddress=$EMAIL"

# Set proper permissions
chmod 600 "$SSL_DIR"/*.key
chmod 644 "$SSL_DIR"/*.crt

# Create certificate chain files
echo -e "${BLUE}🔗 Creating certificate chains...${NC}"
for cert in "$SSL_DIR"/*.crt; do
    if [[ "$(basename "$cert")" != "ca.crt" && "$(basename "$cert")" != "default.crt" ]]; then
        cat "$cert" "$SSL_DIR/ca.crt" > "${cert%.crt}-chain.crt"
    fi
done

# Generate DH parameters for better security
echo -e "${BLUE}🔐 Generating DH parameters (this may take a while)...${NC}"
openssl dhparam -out "$SSL_DIR/dhparam.pem" 2048

# Create nginx password file for monitoring access
echo -e "${BLUE}👤 Creating basic auth file for monitoring...${NC}"
mkdir -p "$PROJECT_ROOT/nginx"
echo "admin:\$apr1\$h4Ysdxdh\$kNjQiQN0.FMZY4OzKRKdh1" > "$PROJECT_ROOT/nginx/.htpasswd"
echo -e "${YELLOW}💡 Default monitoring credentials: admin/dotmac123${NC}"

echo ""
echo -e "${GREEN}🎉 SSL certificates generated successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Generated certificates:${NC}"
ls -la "$SSL_DIR"/*.crt | while read -r line; do
    echo "  • $(basename "${line##*/}")"
done
echo ""
echo -e "${BLUE}📁 Certificate files location:${NC}"
echo "  $SSL_DIR"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NOTES:${NC}"
echo "• These are self-signed certificates for development/testing"
echo "• Browsers will show security warnings"
echo "• For production, use Let's Encrypt or a commercial CA"
echo "• The CA certificate is in: $SSL_DIR/ca.crt"
echo "• Add the CA to your browser's trusted certificates to avoid warnings"
echo ""
echo -e "${BLUE}🔧 To trust the CA certificate:${NC}"
echo "1. Open $SSL_DIR/ca.crt in your browser"
echo "2. Add it to your browser's certificate authorities"
echo "3. Or use: certutil -d sql:\$HOME/.pki/nssdb -A -t 'C,,' -n 'DotMac Root CA' -i $SSL_DIR/ca.crt"
echo ""
echo -e "${BLUE}🌐 Test the certificates:${NC}"
echo "• https://admin.dotmac.local (add to /etc/hosts: 127.0.0.1 admin.dotmac.local)"
echo "• https://portal.dotmac.local"
echo "• https://monitoring.dotmac.local"
echo ""