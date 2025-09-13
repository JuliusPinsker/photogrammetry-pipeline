#!/bin/bash

# NVIDIA Docker Setup Script for Ubuntu/Debian
# This script installs the NVIDIA Container Toolkit for Docker GPU support

set -e

echo "🚀 Installing NVIDIA Docker Runtime"
echo "===================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges"
    echo "Run with: sudo ./install-nvidia-docker.sh"
    exit 1
fi

# Check if NVIDIA drivers are installed
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA drivers not found"
    echo "Please install NVIDIA drivers first:"
    echo "sudo apt update && sudo apt install nvidia-driver-470"
    echo "Then reboot and run this script again"
    exit 1
fi

echo "✅ NVIDIA drivers found"
nvidia-smi

# Detect distribution
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
   && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "📦 Installing NVIDIA Container Toolkit..."
apt-get update
apt-get install -y nvidia-container-toolkit

echo "🔧 Configuring Docker..."
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo "🧪 Testing NVIDIA Docker..."
if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi; then
    echo "✅ NVIDIA Docker is working!"
else
    echo "❌ NVIDIA Docker test failed"
    exit 1
fi

echo ""
echo "🎉 NVIDIA Docker setup complete!"
echo ""
echo "Your system now supports GPU-accelerated Docker containers."
echo "You can now run: ./setup.sh to build the photogrammetry pipeline"
