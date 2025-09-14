# OpenMVG Eigen3 Compatibility Fix

## Problem Description

OpenMVG versions (including v1.6, v2.1, and latest commits) have compilation issues with Ubuntu 20.04's Eigen3 library due to SparseCholesky module compatibility problems:

```
error: #error The SparseCholesky module has nothing to offer in MPL2 only mode
error: 'AMDOrdering' does not name a type; did you mean 'COLAMDOrdering'?
```

## Root Cause

The issue stems from:
1. Ubuntu 20.04 ships with an older Eigen3 version that has MPL2-only licensing restrictions
2. OpenMVG's `rotation_averaging_l1.cpp` uses SparseCholesky features not available in MPL2 mode
3. Template argument compatibility issues between OpenMVG and system Eigen3

## Solutions Attempted

### ❌ Approach 1: Downgrade to OpenMVG v1.6 (2019)
- **Result**: Successful build but version too old (user requirement: 2023+)
- **Issue**: Not meeting user requirement for modern versions

### ❌ Approach 2: Upgrade to OpenMVG v2.1 (Dec 2023)
- **Result**: Same Eigen3 SparseCholesky compilation errors
- **Issue**: Ubuntu 20.04's Eigen3 still incompatible

### ❌ Approach 3: Latest OpenMVG commit (March 2025)
- **Result**: Same Eigen3 SparseCholesky compilation errors
- **Issue**: Fundamental Ubuntu 20.04 Eigen3 incompatibility

### ✅ Approach 4: Ubuntu 22.04 + Latest OpenMVG (CURRENT)
- **Strategy**: Use newer base OS with compatible Eigen3 version
- **Expected Result**: Resolve Eigen3 compatibility while using modern OpenMVG
- **Status**: Currently building...

## Technical Details

### Ubuntu 20.04 vs 22.04 Eigen3 Versions
- **Ubuntu 20.04**: Eigen3 3.3.7 with MPL2 restrictions
- **Ubuntu 22.04**: Eigen3 3.4.0+ with better SparseCholesky support

### OpenMVG Dependencies Updated for Ubuntu 22.04
- `libeigen3-dev` - Modern Eigen3 with SparseCholesky support
- `libvtk9-dev` - Updated from VTK7 to VTK9
- `libopencv-dev` - Ubuntu 22.04 compatible OpenCV

## Verification

```bash
# Check Eigen3 version in container
dpkg -l | grep eigen3

# Verify SparseCholesky availability
echo '#include <Eigen/SparseCholesky>' | g++ -x c++ -c - -I/usr/include/eigen3
```

## Fallback Options

If Ubuntu 22.04 approach fails:
1. **Custom Eigen3 build**: Compile Eigen3 from source with full license
2. **Disable SparseCholesky**: Patch OpenMVG to use alternative solvers
3. **Alternative SfM**: Switch to COLMAP which has better dependency management

## Current Status

- ✅ Ubuntu 22.04 Dockerfile created
- 🔄 Building with modern Eigen3 and latest OpenMVG commit
- ⏳ Awaiting build completion to verify fix
