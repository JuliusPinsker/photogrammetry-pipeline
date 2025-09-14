#!/bin/bash

# Script to verify that all pinned repository commits are still accessible
# This ensures our version pinning is valid and repositories haven't been force-pushed

set -e

echo "🔍 Verifying pinned repository commits..."
echo "========================================="

# Function to check if a commit exists in a repository
check_commit() {
    local repo_url="$1"
    local commit="$2"
    local name="$3"
    
    echo -n "Checking $name... "
    
    if git ls-remote "$repo_url" | grep -q "$commit"; then
        echo "✅ Valid"
        return 0
    else
        echo "❌ INVALID - Commit not found!"
        return 1
    fi
}

# Function to check if a tag exists in a repository
check_tag() {
    local repo_url="$1"
    local tag="$2"
    local name="$3"
    
    echo -n "Checking $name... "
    
    if git ls-remote --tags "$repo_url" | grep -q "refs/tags/$tag"; then
        echo "✅ Valid"
        return 0
    else
        echo "❌ INVALID - Tag not found!"
        return 1
    fi
}

failed_checks=0

echo
echo "Traditional Photogrammetry Methods:"
echo "-----------------------------------"

# OpenMVG (using v1.6 tag)
echo "🔍 Verifying OpenMVG latest commit..."
check_commit "https://github.com/openMVG/openMVG.git" "c92ed1be" "OpenMVG c92ed1be"

# OpenMVS
check_commit "https://github.com/cdcseacave/openMVS.git" "ce03889e2055a3d6cbcae9dd5a93b5eeea94b909" "OpenMVS" || ((failed_checks++))

# COLMAP (using tag)
check_tag "https://github.com/colmap/colmap.git" "3.8" "COLMAP" || ((failed_checks++))

echo
echo "Neural Rendering Methods:"
echo "------------------------"

# Instant-NGP
check_commit "https://github.com/NVlabs/instant-ngp.git" "be57ba8b80e2ba4925af6c0014fd153cd62fde2c" "Instant-NGP" || ((failed_checks++))

# 3D Gaussian Splatting
check_commit "https://github.com/graphdeco-inria/gaussian-splatting" "54c035f7834b564019656c3e3fcc3646292f727d" "3D Gaussian Splatting" || ((failed_checks++))

# MobileNeRF (Google Research)
check_commit "https://github.com/google-research/google-research.git" "e8977b905d1d0db300d4eb7bc54a0620d96e587d" "MobileNeRF" || ((failed_checks++))

# PIFuHD
check_commit "https://github.com/facebookresearch/pifuhd.git" "e47c4d918aaedd5f5608192b130bda150b1fb0ab" "PIFuHD" || ((failed_checks++))

echo
echo "========================================="

if [ $failed_checks -eq 0 ]; then
    echo "✅ All pinned versions are valid and accessible!"
    echo "   Builds should be reproducible."
    exit 0
else
    echo "❌ $failed_checks version(s) failed verification!"
    echo "   Check VERSION_PINNING.md and update invalid commits."
    echo "   Some builds may fail with current pinning."
    exit 1
fi
