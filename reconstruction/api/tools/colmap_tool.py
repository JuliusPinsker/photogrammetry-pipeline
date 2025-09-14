import os
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .base_tool import ReconstructionTool

class ColmapTool(ReconstructionTool):
    """COLMAP Structure-from-Motion tool."""
    
    def __init__(self):
        self.name = "COLMAP"
        self.executable = "colmap"
    
    async def run(
        self,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run COLMAP reconstruction pipeline."""
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        database_path = output_dir / "database.db"
        sparse_dir = output_dir / "sparse"
        dense_dir = output_dir / "dense"
        sparse_dir.mkdir(exist_ok=True)
        dense_dir.mkdir(exist_ok=True)
        
        try:
            # Step 1: Feature extraction
            if progress_callback:
                progress_callback(10)
            
            await self._run_command([
                self.executable, "feature_extractor",
                "--database_path", str(database_path),
                "--image_path", input_path,
                "--ImageReader.single_camera", "1",
                "--SiftExtraction.max_image_size", str(max_resolution)
            ])
            
            # Step 2: Feature matching
            if progress_callback:
                progress_callback(30)
            
            await self._run_command([
                self.executable, "exhaustive_matcher",
                "--database_path", str(database_path)
            ])
            
            # Step 3: Sparse reconstruction
            if progress_callback:
                progress_callback(50)
            
            await self._run_command([
                self.executable, "mapper",
                "--database_path", str(database_path),
                "--image_path", input_path,
                "--output_path", str(sparse_dir)
            ])
            
            # Step 4: Dense reconstruction
            if progress_callback:
                progress_callback(70)
            
            # Find the reconstruction folder (usually 0)
            reconstruction_dirs = [d for d in sparse_dir.iterdir() if d.is_dir()]
            if not reconstruction_dirs:
                raise RuntimeError("No sparse reconstruction found")
            
            recon_dir = reconstruction_dirs[0]
            
            await self._run_command([
                self.executable, "image_undistorter",
                "--image_path", input_path,
                "--input_path", str(recon_dir),
                "--output_path", str(dense_dir),
                "--output_type", "COLMAP"
            ])
            
            # Step 5: Dense point cloud
            if progress_callback:
                progress_callback(90)
            
            await self._run_command([
                self.executable, "patch_match_stereo",
                "--workspace_path", str(dense_dir)
            ])
            
            await self._run_command([
                self.executable, "stereo_fusion",
                "--workspace_path", str(dense_dir),
                "--output_path", str(dense_dir / "fused.ply")
            ])
            
            if progress_callback:
                progress_callback(100)
            
            output_file = str(dense_dir / "fused.ply")
            
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
        """Check if COLMAP is available."""
        try:
            result = subprocess.run(
                [self.executable, "--help"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def get_version(self) -> str:
        """Get COLMAP version."""
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "unknown"
        except:
            return "unknown"
    
    def get_type(self) -> str:
        """Get tool type."""
        return "SfM + MVS"
    
    def get_description(self) -> str:
        """Get tool description."""
        return "COLMAP is a general-purpose Structure-from-Motion (SfM) and Multi-View Stereo (MVS) pipeline"