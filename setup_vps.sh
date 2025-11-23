#!/bin/bash

# Exit on error
set -e

echo "Updating system..."
sudo apt-get update
sudo apt-get upgrade -y

echo "Installing prerequisites..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "Adding Docker's official GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "Setting up the repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing Docker Engine..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "Verifying Docker installation..."
sudo docker run hello-world

echo "Docker installed successfully!"
