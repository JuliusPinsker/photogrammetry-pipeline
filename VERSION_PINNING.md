# Repository Version Pinning

This document tracks the specific commits used for each external repository to ensure reproducible builds.

## Traditional Photogrammetry Methods

### OpenMVG (Traditional SfM)
- **Repository**: https://github.com/openMVG/openMVG
- **Pinned Version**: c92ed1be (Latest commit - March 2025)
- **Verification**: `curl -s https://api.github.com/repos/openMVG/openMVG/commits/c92ed1be`
- **Base OS**: Ubuntu 22.04 (for Eigen3 compatibility)
- **Rationale**: Latest commit with Ubuntu 22.04 resolving Eigen3 SparseCholesky compatibility issues

### OpenMVS
- **Repository**: https://github.com/cdcseacave/openMVS.git
- **Commit**: `ce03889e2055a3d6cbcae9dd5a93b5eeea94b909`
- **Date**: September 2025 (current master)
- **Notes**: Compatible with OpenMVG v2.1

### COLMAP
- **Repository**: https://github.com/colmap/colmap.git
- **Version**: `3.8` (stable release tag)
- **Notes**: Using stable release tag instead of commit for better compatibility

## Neural Rendering Methods

### Instant-NGP
- **Repository**: https://github.com/NVlabs/instant-ngp.git
- **Commit**: `be57ba8b80e2ba4925af6c0014fd153cd62fde2c`
- **Date**: September 2025 (current master)
- **Notes**: Latest stable commit with CUDA 11.8 compatibility

### 3D Gaussian Splatting
- **Repository**: https://github.com/graphdeco-inria/gaussian-splatting
- **Commit**: `54c035f7834b564019656c3e3fcc3646292f727d`
- **Date**: September 2025 (current main)
- **Notes**: Latest stable commit with working submodules

### MobileNeRF
- **Repository**: https://github.com/google-research/google-research.git
- **Commit**: `e8977b905d1d0db300d4eb7bc54a0620d96e587d`
- **Date**: September 2025 (current master)
- **Notes**: Using sparse checkout for mobilenerf subdirectory

### PIFuHD
- **Repository**: https://github.com/facebookresearch/pifuhd.git
- **Commit**: `e47c4d918aaedd5f5608192b130bda150b1fb0ab`
- **Date**: September 2025 (current main)
- **Notes**: Latest stable commit with working dependencies

## Update Strategy

When updating these versions:

1. Test the build in isolation first
2. Run the full test suite with the new version
3. Update both the commit hash and the date in this document
4. Update any version-specific code or configurations

## Verification Commands

To verify these commits are still accessible:

```bash
# OpenMVG (using v1.6 release tag)
git ls-remote --tags https://github.com/openMVG/openMVG.git | grep v1.6

# OpenMVS  
git ls-remote https://github.com/cdcseacave/openMVS.git | grep ce03889e2055a3d6cbcae9dd5a93b5eeea94b909

# COLMAP
git ls-remote --tags https://github.com/colmap/colmap.git | grep 3.8

# Instant-NGP
git ls-remote https://github.com/NVlabs/instant-ngp.git | grep be57ba8b80e2ba4925af6c0014fd153cd62fde2c

# Gaussian Splatting
git ls-remote https://github.com/graphdeco-inria/gaussian-splatting | grep 54c035f7834b564019656c3e3fcc3646292f727d

# MobileNeRF (Google Research)
git ls-remote https://github.com/google-research/google-research.git | grep e8977b905d1d0db300d4eb7bc54a0620d96e587d

# PIFuHD
git ls-remote https://github.com/facebookresearch/pifuhd.git | grep e47c4d918aaedd5f5608192b130bda150b1fb0ab
```
