#!/bin/bash

# Exit on error
set -e

# Configuration
VPS_USER="root"
VPS_HOST="" # To be filled by user
REMOTE_DIR="/opt/video-analyzer"

if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh <VPS_IP>"
    exit 1
fi

VPS_HOST=$1

echo "Deploying to $VPS_USER@$VPS_HOST..."

# Create remote directory
ssh $VPS_USER@$VPS_HOST "mkdir -p $REMOTE_DIR"

# Transfer files
echo "Transferring files..."
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' --exclude 'output' \
    ./ $VPS_USER@$VPS_HOST:$REMOTE_DIR/

# Deploy
echo "Starting services..."
ssh $VPS_USER@$VPS_HOST "cd $REMOTE_DIR && docker compose build && docker compose up -d"

echo "Deployment complete!"
