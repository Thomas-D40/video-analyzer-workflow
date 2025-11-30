#!/bin/sh

set -e

SSL_DIR="/etc/nginx/ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

# Generate self-signed certificate if it doesn't exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating self-signed SSL certificate..."

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=FR/ST=France/L=Paris/O=VideoAnalyzer/CN=46.202.128.11" \
        -addext "subjectAltName=IP:46.202.128.11,DNS:localhost"

    echo "Self-signed certificate generated at $CERT_FILE"
else
    echo "SSL certificate already exists"
fi

# Execute the main command
exec "$@"
