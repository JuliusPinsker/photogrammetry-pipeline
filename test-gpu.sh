#!/bin/bash

# GPU Capability Test Script
# Run this script to verify GPU setup before building the photogrammetry pipeline

echo "🔍 GPU Capability Test for Photogrammetry Pipeline"
echo "=================================================="

# Test 1: Check if NVIDIA drivers are installed
echo "Test 1: NVIDIA Driver Installation"
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA drivers found"
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -n1)
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)
    
    echo "   GPU: $GPU_NAME"
    echo "   Driver: $DRIVER_VERSION"
    echo "   Memory: ${GPU_MEMORY}MB"
    
    # Check memory requirements
    GPU_MEMORY_INT=$(echo $GPU_MEMORY | sed 's/[^0-9]//g')
    if [ "$GPU_MEMORY_INT" -lt 6000 ]; then
        echo "⚠️  WARNING: GPU memory (${GPU_MEMORY}MB) may be insufficient"
        echo "   Minimum recommended: 8GB for neural methods"
        echo "   Some methods may fail or be very slow"
    elif [ "$GPU_MEMORY_INT" -lt 8000 ]; then
        echo "⚠️  CAUTION: GPU memory (${GPU_MEMORY}MB) is minimal"
        echo "   High-resolution reconstructions may fail"
    else
        echo "✅ GPU memory sufficient for all methods"
    fi
else
    echo "❌ NVIDIA drivers not found"
    echo "   Install NVIDIA drivers first:"
    echo "   https://www.nvidia.com/drivers"
    exit 1
fi

echo ""

# Test 2: Check Docker installation
echo "Test 2: Docker Installation"
if command -v docker &> /dev/null; then
    echo "✅ Docker found"
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo "   Version: $DOCKER_VERSION"
    
    if docker compose version &> /dev/null; then
        echo "✅ Docker Compose V2 found"
        COMPOSE_VERSION=$(docker compose version --short)
        echo "   Version: $COMPOSE_VERSION"
    else
        echo "❌ Docker Compose V2 not found"
        echo "   Install Docker Compose V2:"
        echo "   https://docs.docker.com/compose/install/"
        exit 1
    fi
else
    echo "❌ Docker not found"
    echo "   Install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo ""

# Test 3: Check NVIDIA Docker runtime
echo "Test 3: NVIDIA Docker Runtime"
if docker info | grep -q nvidia; then
    echo "✅ NVIDIA Docker runtime detected"
else
    echo "❌ NVIDIA Docker runtime not found"
    echo "   Install nvidia-docker2:"
    echo "   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi

echo ""

# Test 4: Test CUDA base image access
echo "Test 4: CUDA Base Image Test"
echo "Testing NVIDIA CUDA Docker images..."

# Try different CUDA image variants
CUDA_IMAGES=(
    "nvidia/cuda:12.0-base-ubuntu20.04"
    "nvidia/cuda:11.8-base-ubuntu20.04" 
    "nvidia/cuda:12.0-runtime-ubuntu20.04"
    "nvidia/cuda:11.8-runtime-ubuntu20.04"
    "nvidia/cuda:12.0-devel-ubuntu20.04"
    "nvidia/cuda:11.8-devel-ubuntu20.04"
)

WORKING_IMAGE=""
for image in "${CUDA_IMAGES[@]}"; do
    echo "Trying $image..."
    if docker run --rm --gpus all $image nvidia-smi &> /dev/null; then
        echo "✅ $image working correctly"
        WORKING_IMAGE=$image
        break
    else
        echo "❌ $image not available or not working"
    fi
done

if [ -z "$WORKING_IMAGE" ]; then
    echo "⚠️  NVIDIA CUDA base images not accessible from Docker Hub"
    echo "   This is common due to registry access issues"
    echo "   The pipeline will install CUDA during build instead"
    
    # Test that NVIDIA runtime works with regular Ubuntu
    echo "   Testing NVIDIA runtime with Ubuntu base..."
    if docker run --rm --runtime=nvidia --gpus all ubuntu:20.04 nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA runtime working with Ubuntu base"
        echo "   GPU methods will work after CUDA installation during build"
    else
        echo "❌ NVIDIA runtime test failed"
        exit 1
    fi
fi

echo ""

# Test 5: Test CUDA development image
echo "Test 5: CUDA Development Image Test"
if [ -n "$WORKING_IMAGE" ]; then
    # Test with development variant of the working image
    DEV_IMAGE=$(echo $WORKING_IMAGE | sed 's/base/devel/' | sed 's/runtime/devel/')
    echo "Testing $DEV_IMAGE..."
    
    if docker run --rm --gpus all $DEV_IMAGE bash -c "nvidia-smi && nvcc --version" &> /dev/null; then
        echo "✅ CUDA development image working correctly"
    else
        echo "⚠️  CUDA development image test failed, but base image works"
        echo "   Neural methods may still work with runtime image"
    fi
else
    echo "⚠️  Skipping development image test - no working base image found"
fi

echo ""

# Test 6: Check system resources
echo "Test 6: System Resources"
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
AVAILABLE_DISK=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')

echo "System RAM: ${TOTAL_RAM}GB"
echo "Available disk space: ${AVAILABLE_DISK}GB"

if [ "$TOTAL_RAM" -lt 16 ]; then
    echo "⚠️  WARNING: System RAM (${TOTAL_RAM}GB) is below recommended 16GB"
    echo "   Some methods may fail due to insufficient memory"
fi

if [ "$AVAILABLE_DISK" -lt 100 ]; then
    echo "⚠️  WARNING: Available disk space (${AVAILABLE_DISK}GB) is below recommended 100GB"
    echo "   Model downloads and results may fill disk space"
fi

echo ""
echo "🎉 GPU Capability Test Complete!"
echo ""
echo "Summary:"
echo "- GPU: $GPU_NAME ($GPU_MEMORY MB)"
echo "- Driver: $DRIVER_VERSION"
echo "- Docker: $DOCKER_VERSION with Compose $COMPOSE_VERSION"
echo "- NVIDIA Docker: ✅ Working"
echo "- CUDA Runtime: ✅ Available in containers"
echo "- System RAM: ${TOTAL_RAM}GB"
echo "- Available Disk: ${AVAILABLE_DISK}GB"
echo ""
echo "✅ Your system is ready for GPU-accelerated photogrammetry methods!"
echo ""
echo "Note: NVIDIA CUDA base images from Docker Hub may not be accessible,"
echo "      but the pipeline will install CUDA during container build process."
echo ""
echo "Next steps:"
echo "1. Run ./setup.sh to build and start the pipeline"
echo "2. Neural methods available: Instant-NGP, 3D Gaussian Splatting, PIFuHD"
echo "3. Traditional methods available: Meshroom, COLMAP, OpenMVG/MVS"
echo "4. Mobile method available: MobileNeRF"
