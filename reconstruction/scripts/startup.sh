#!/bin/bash

echo "Starting 3D Reconstruction Service..."

# GPU Detection
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected: enabling CUDA"
    export GPU_ENABLED=true
    nvidia-smi
else
    echo "No GPU: using CPU mode"
    export GPU_ENABLED=false
fi

# Verify tool installations
echo "Verifying reconstruction tools..."

tools=("colmap" "DensifyPointCloud" "pmvs2" "cmvs")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo "✓ $tool: Available"
    else
        echo "✗ $tool: Not found"
    fi
done

# Check Python packages
python3 -c "
import sys
packages = ['fastapi', 'uvicorn', 'numpy', 'cv2', 'PIL']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✓ {pkg}: Available')
    except ImportError:
        print(f'✗ {pkg}: Not found')
        sys.exit(1)
"

# Create output directories
mkdir -p /results/{colmap,openmvs,pmvs2,alicevision,opensfm}

# Start the FastAPI server
echo "Starting reconstruction API server..."
exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1