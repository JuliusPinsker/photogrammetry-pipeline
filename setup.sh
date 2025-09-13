#!/bin/bash

# Photogrammetry Pipeline Setup Script
# This script sets up the complete photogrammetry pipeline environment

set -e

echo "🚀 Setting up Photogrammetry Pipeline..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose V2 is not installed. Please install Docker with Compose V2."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for NVIDIA Docker (optional but recommended)
if command -v nvidia-docker &> /dev/null || docker info | grep -q nvidia; then
    echo "✅ NVIDIA Docker support detected"
    GPU_SUPPORT=true
else
    echo "⚠️  NVIDIA Docker not detected. GPU-accelerated methods will not be available."
    echo "   To enable GPU support, install nvidia-docker2:"
    echo "   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    GPU_SUPPORT=false
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data results benchmarks

# Set proper permissions
chmod 755 data results benchmarks

# Build core services
echo "🔨 Building core services..."
docker compose build web core

echo "🎯 Building reconstruction engines..."

# Build traditional methods
echo "   Building Meshroom..."
docker compose build meshroom

echo "   Building COLMAP..."
docker compose build colmap

echo "   Building OpenMVG/MVS..."
docker compose build openmvg

if [ "$GPU_SUPPORT" = true ]; then
    # Build neural methods (require GPU)
    echo "   Building Instant-NGP..."
    docker compose build instant-ngp

    echo "   Building 3D Gaussian Splatting..."
    docker compose build gaussian-splatting

    echo "   Building PIFuHD..."
    docker compose build pifuhd
else
    echo "   Skipping GPU-dependent engines (Instant-NGP, Gaussian Splatting, PIFuHD)"
fi

# Build mobile-optimized method
echo "   Building MobileNeRF..."
docker compose build mobilenerf

# Start core services
echo "🚀 Starting core services..."
docker compose up -d web core redis

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo "✅ Core services are running!"
    echo ""
    echo "🌐 Web interface: http://localhost:8080"
    echo "🔌 API endpoint: http://localhost:5000"
    echo ""
    echo "📊 Service status:"
    docker compose ps
    echo ""
    echo "🎉 Setup complete! You can now:"
    echo "   1. Open http://localhost:8080 in your browser"
    echo "   2. Upload images or select a test dataset"
    echo "   3. Choose a reconstruction method"
    echo "   4. Start the reconstruction process"
    echo ""
    
    if [ "$GPU_SUPPORT" = false ]; then
        echo "⚠️  Note: Only CPU-based methods are available without GPU support"
        echo "   Available methods: Meshroom, COLMAP, OpenMVG/MVS, MobileNeRF"
    fi
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker compose logs"
    exit 1
fi

echo "📖 For more information, see README.md"
