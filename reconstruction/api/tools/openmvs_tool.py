import os
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .base_tool import ReconstructionTool

class OpenMVSTool(ReconstructionTool):
    """OpenMVS Multi-View Stereo tool."""
    
    def __init__(self):
        self.name = "OpenMVS"
        self.executables = {
            "InterfaceCOLMAP": "InterfaceCOLMAP",
            "DensifyPointCloud": "DensifyPointCloud", 
            "ReconstructMesh": "ReconstructMesh",
            "RefineMesh": "RefineMesh"
        }
    
    async def run(
        self,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run OpenMVS reconstruction pipeline."""
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Note: OpenMVS typically requires COLMAP output as input
            # For this demo, we'll create a simplified pipeline
            
            # Step 1: Convert COLMAP to OpenMVS format (if COLMAP data exists)
            if progress_callback:
                progress_callback(20)
            
            scene_file = output_dir / "scene.mvs"
            
            # Look for COLMAP sparse reconstruction
            colmap_sparse = Path(input_path).parent / "sparse" / "0"
            if colmap_sparse.exists():
                await self._run_command([
                    self.executables["InterfaceCOLMAP"],
                    "-i", str(colmap_sparse),
                    "-o", str(scene_file),
                    "--image-folder", input_path
                ])
            else:
                # Create dummy scene file for demo
                await self._create_dummy_scene(scene_file, input_path)
            
            # Step 2: Dense point cloud generation
            if progress_callback:
                progress_callback(50)
            
            dense_scene = output_dir / "scene_dense.mvs"
            await self._run_command([
                self.executables["DensifyPointCloud"],
                "-i", str(scene_file),
                "-o", str(dense_scene),
                "--resolution-level", "1",
                "--max-resolution", str(max_resolution)
            ])
            
            # Step 3: Mesh reconstruction
            if progress_callback:
                progress_callback(75)
            
            mesh_scene = output_dir / "scene_mesh.mvs"
            await self._run_command([
                self.executables["ReconstructMesh"],
                "-i", str(dense_scene),
                "-o", str(mesh_scene)
            ])
            
            # Step 4: Mesh refinement
            if progress_callback:
                progress_callback(90)
            
            refined_mesh = output_dir / "scene_mesh_refined.mvs"
            await self._run_command([
                self.executables["RefineMesh"],
                "-i", str(mesh_scene),
                "-o", str(refined_mesh)
            ])
            
            if progress_callback:
                progress_callback(100)
            
            # Output should be a PLY file
            output_file = str(output_dir / "scene_mesh_refined.ply")
            
            return {
                'success': True,
                'output_file': output_file,
                'type': 'mesh'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_file': '',
                'type': 'mesh'
            }
    
    async def _create_dummy_scene(self, scene_file: Path, input_path: str):
        """Create a dummy scene file for demo purposes."""
        # This is a simplified version - in practice, you'd need proper camera calibration
        images = list(Path(input_path).glob("*.jpg")) + list(Path(input_path).glob("*.png"))
        
        with open(scene_file, 'w') as f:
            f.write("# OpenMVS scene file\n")
            f.write(f"# Generated for demo with {len(images)} images\n")
    
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
        """Check if OpenMVS tools are available."""
        try:
            for name, executable in self.executables.items():
                result = subprocess.run(
                    [executable, "--help"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return False
            return True
        except:
            return False
    
    def get_version(self) -> str:
        """Get OpenMVS version."""
        try:
            result = subprocess.run(
                [self.executables["DensifyPointCloud"], "--version"],
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
        return "MVS"
    
    def get_description(self) -> str:
        """Get tool description."""
        return "OpenMVS is a library for computer-vision scientists and especially for Multi-View Stereo reconstruction"