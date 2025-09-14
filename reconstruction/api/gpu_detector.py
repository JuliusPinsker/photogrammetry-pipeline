import os
import subprocess
import sys

class GPUDetector:
    """Detect and manage GPU availability."""
    
    def __init__(self):
        self._gpu_available = None
        self._gpu_info = None
        self._detect_gpu()
    
    def _detect_gpu(self):
        """Detect GPU availability and information."""
        try:
            # Try to run nvidia-smi
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse GPU information
                lines = result.stdout.strip().split('\n')
                gpu_info = []
                
                for line in lines:
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        gpu_info.append({
                            'name': parts[0].strip(),
                            'memory_mb': int(parts[1].strip()),
                            'driver_version': parts[2].strip()
                        })
                
                self._gpu_available = True
                self._gpu_info = gpu_info
                
                # Set environment variable for other tools
                os.environ['GPU_ENABLED'] = 'true'
                
            else:
                self._gpu_available = False
                self._gpu_info = []
                os.environ['GPU_ENABLED'] = 'false'
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            self._gpu_available = False
            self._gpu_info = []
            os.environ['GPU_ENABLED'] = 'false'
    
    def is_available(self) -> bool:
        """Check if GPU is available."""
        return self._gpu_available
    
    def get_info(self) -> list:
        """Get GPU information."""
        return self._gpu_info or []
    
    def get_status(self) -> dict:
        """Get complete GPU status."""
        if self._gpu_available and self._gpu_info:
            primary_gpu = self._gpu_info[0]
            return {
                'available': True,
                'count': len(self._gpu_info),
                'name': primary_gpu['name'],
                'memory_mb': primary_gpu['memory_mb'],
                'driver_version': primary_gpu['driver_version'],
                'gpus': self._gpu_info
            }
        else:
            return {
                'available': False,
                'count': 0,
                'name': 'CPU Mode',
                'memory_mb': 0,
                'driver_version': None,
                'gpus': []
            }
    
    def get_cuda_flags(self) -> list:
        """Get CUDA compilation flags for tools that support GPU acceleration."""
        if self._gpu_available:
            return [
                '-DWITH_CUDA=ON',
                '-DCUDA_ENABLED=ON',
                '-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc'
            ]
        else:
            return [
                '-DWITH_CUDA=OFF',
                '-DCUDA_ENABLED=OFF'
            ]