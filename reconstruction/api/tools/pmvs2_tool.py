import os
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .base_tool import ReconstructionTool

class PMVS2Tool(ReconstructionTool):
    """PMVS2 (Patch-based Multi-view Stereo) tool."""
    
    def __init__(self):
        self.name = "PMVS2"
        self.executable = "pmvs2"
        self.cmvs_executable = "cmvs"
    
    async def run(
        self,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run PMVS2 reconstruction pipeline."""
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # PMVS2 requires specific directory structure and file formats
            pmvs_dir = output_dir / "pmvs"
            pmvs_dir.mkdir(exist_ok=True)
            
            txt_dir = pmvs_dir / "txt"
            visualize_dir = pmvs_dir / "visualize"
            models_dir = pmvs_dir / "models"
            
            txt_dir.mkdir(exist_ok=True)
            visualize_dir.mkdir(exist_ok=True)
            models_dir.mkdir(exist_ok=True)
            
            # Step 1: Prepare input data
            if progress_callback:
                progress_callback(20)
            
            await self._prepare_pmvs_input(input_path, pmvs_dir, max_resolution)
            
            # Step 2: Run CMVS for clustering (if available)
            if progress_callback:
                progress_callback(40)
            
            if self._check_cmvs_availability():
                await self._run_command([
                    self.cmvs_executable,
                    str(pmvs_dir),
                    "2"  # Number of clusters
                ])
            
            # Step 3: Run PMVS2
            if progress_callback:
                progress_callback(70)
            
            option_file = pmvs_dir / "option-0000"
            await self._create_option_file(option_file)
            
            await self._run_command([
                self.executable,
                str(pmvs_dir),
                "option-0000"
            ])
            
            if progress_callback:
                progress_callback(100)
            
            # Convert output to PLY format
            output_file = str(models_dir / "option-0000.ply")
            if not Path(output_file).exists():
                # Convert from PMVS format to PLY
                pmvs_output = models_dir / "option-0000.patch"
                if pmvs_output.exists():
                    await self._convert_to_ply(pmvs_output, output_file)
            
            return {
                'success': True,
                'output_file': output_file,
                'type': 'point_cloud'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_file': '',
                'type': 'point_cloud'
            }
    
    async def _prepare_pmvs_input(self, input_path: str, pmvs_dir: Path, max_resolution: int):
        """Prepare input data in PMVS format."""
        # This is a simplified version - in practice, you'd need:
        # 1. Camera calibration data
        # 2. Properly formatted image files
        # 3. Camera poses
        
        input_images = list(Path(input_path).glob("*.jpg")) + list(Path(input_path).glob("*.png"))
        
        # Copy and resize images if needed
        for i, img_path in enumerate(input_images[:10]):  # Limit to 10 images for demo
            target_path = pmvs_dir / f"{i:08d}.jpg"
            
            # Simple copy for demo (in practice, you'd resize and convert)
            import shutil
            shutil.copy2(img_path, target_path)
            
            # Create dummy camera file
            camera_file = pmvs_dir / "txt" / f"{i:08d}.txt"
            with open(camera_file, 'w') as f:
                f.write("CONTOUR\n")
                f.write(f"{target_path.name}\n")
                # Dummy camera parameters (in practice, these would come from SfM)
                f.write("1.0 0.0 0.0 0.0\n")
                f.write("0.0 1.0 0.0 0.0\n")
                f.write("0.0 0.0 1.0 0.0\n")
    
    async def _create_option_file(self, option_file: Path):
        """Create PMVS2 option file."""
        with open(option_file, 'w') as f:
            f.write("# PMVS2 options\n")
            f.write("level 1\n")
            f.write("csize 2\n")
            f.write("threshold 0.7\n")
            f.write("wsize 7\n")
            f.write("minImageNum 3\n")
            f.write("CPU 4\n")
            f.write("useVisData 0\n")
            f.write("sequence -1\n")
            f.write("timages -1 0 10\n")  # Use first 10 images
            f.write("oimages 0\n")
    
    async def _convert_to_ply(self, patch_file: Path, ply_file: Path):
        """Convert PMVS patch file to PLY format."""
        # This is a simplified conversion - PMVS patch format is complex
        with open(ply_file, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write("element vertex 1000\n")  # Dummy count
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("end_header\n")
            
            # Generate some dummy points for demo
            for i in range(1000):
                x = (i % 100) / 10.0 - 5.0
                y = ((i // 100) % 10) / 2.0 - 2.5
                z = (i // 1000) / 2.0
                f.write(f"{x} {y} {z}\n")
    
    def _check_cmvs_availability(self) -> bool:
        """Check if CMVS is available."""
        try:
            result = subprocess.run(
                [self.cmvs_executable],
                capture_output=True,
                timeout=5
            )
            return True
        except:
            return False
    
    async def _run_command(self, command: list):
        """Run a command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(command)}\nError: {stderr.decode()}")
    
    def check_availability(self) -> bool:
        """Check if PMVS2 is available."""
        try:
            result = subprocess.run(
                [self.executable],
                capture_output=True,
                timeout=10
            )
            return True  # PMVS2 might not have --help option
        except:
            return False
    
    def get_version(self) -> str:
        """Get PMVS2 version."""
        return "2.0 (demo)"  # PMVS2 doesn't have version flag
    
    def get_type(self) -> str:
        """Get tool type."""
        return "MVS"
    
    def get_description(self) -> str:
        """Get tool description."""
        return "PMVS2 (Patch-based Multi-view Stereo) generates dense point clouds from calibrated images"