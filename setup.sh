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
echo "🔍 Checking GPU support..."
GPU_SUPPORT=false
GPU_DRIVER_VERSION=""
GPU_MEMORY=""

# Check if nvidia-smi is available (NVIDIA driver installed)
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA drivers detected"
    GPU_DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -n1)
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)
    echo "   Driver version: $GPU_DRIVER_VERSION"
    echo "   GPU memory: ${GPU_MEMORY}MB"
    
    # Check if Docker can access NVIDIA runtime
    if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA Docker runtime working"
        GPU_SUPPORT=true
    else
        echo "❌ NVIDIA Docker runtime not working"
        echo "   Docker can't access GPU. Please install nvidia-docker2:"
        echo "   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        GPU_SUPPORT=false
    fi
else
    echo "⚠️  NVIDIA drivers not detected"
    echo "   GPU-accelerated methods will not be available."
    echo "   To enable GPU support:"
    echo "   1. Install NVIDIA drivers"
    echo "   2. Install nvidia-docker2"
    echo "   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    GPU_SUPPORT=false
fi

# Verify GPU memory requirements for neural methods
if [ "$GPU_SUPPORT" = true ]; then
    GPU_MEMORY_INT=$(echo $GPU_MEMORY | sed 's/[^0-9]//g')
    if [ "$GPU_MEMORY_INT" -lt 6000 ]; then
        echo "⚠️  GPU memory (${GPU_MEMORY}MB) may be insufficient for neural methods"
        echo "   Recommended: 8GB+ for optimal performance"
        echo "   Some methods may fail or run very slowly"
    elif [ "$GPU_MEMORY_INT" -lt 8000 ]; then
        echo "⚠️  GPU memory (${GPU_MEMORY}MB) is minimal for neural methods"
        echo "   Some high-resolution reconstructions may fail"
    else
        echo "✅ GPU memory (${GPU_MEMORY}MB) sufficient for all neural methods"
    fi
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data results benchmarks

# Set proper permissions
chmod 755 data results benchmarks

# Build core services
echo "🔨 Building core services..."
docker compose build web core

# Test GPU base image if GPU support is available
if [ "$GPU_SUPPORT" = true ]; then
    echo "🧪 Testing NVIDIA CUDA base image..."
    if docker run --rm --gpus all nvidia/cuda:11.8-cudnn8-devel-ubuntu20.04 nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA CUDA 11.8 base image working"
    else
        echo "❌ NVIDIA CUDA 11.8 base image failed"
        echo "   This may cause GPU method builds to fail"
        echo "   Check CUDA compatibility with your driver"
        GPU_SUPPORT=false
    fi
fi

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
    if docker compose build instant-ngp; then
        echo "✅ Instant-NGP built successfully"
        # Test GPU access in container
        if docker run --rm --gpus all photogrammetry-pipeline-instant-ngp nvidia-smi &> /dev/null; then
            echo "✅ Instant-NGP GPU access working"
        else
            echo "⚠️  Instant-NGP GPU access failed"
        fi
    else
        echo "❌ Instant-NGP build failed"
    fi

    echo "   Building 3D Gaussian Splatting..."
    if docker compose build gaussian-splatting; then
        echo "✅ 3D Gaussian Splatting built successfully"
        # Test GPU access in container
        if docker run --rm --gpus all photogrammetry-pipeline-gaussian-splatting nvidia-smi &> /dev/null; then
            echo "✅ 3D Gaussian Splatting GPU access working"
        else
            echo "⚠️  3D Gaussian Splatting GPU access failed"
        fi
    else
        echo "❌ 3D Gaussian Splatting build failed"
    fi

    echo "   Building PIFuHD..."
    if docker compose build pifuhd; then
        echo "✅ PIFuHD built successfully"
        # Test GPU access in container
        if docker run --rm --gpus all photogrammetry-pipeline-pifuhd nvidia-smi &> /dev/null; then
            echo "✅ PIFuHD GPU access working"
        else
            echo "⚠️  PIFuHD GPU access failed"
        fi
    else
        echo "❌ PIFuHD build failed"
    fi
else
    echo "   Skipping GPU-dependent engines (Instant-NGP, Gaussian Splatting, PIFuHD)"
    echo "   Reason: No GPU support detected"
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
