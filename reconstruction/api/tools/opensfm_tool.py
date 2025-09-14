import os
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .base_tool import ReconstructionTool

class OpenSfMTool(ReconstructionTool):
    """OpenSfM (Open Structure from Motion) tool."""
    
    def __init__(self):
        self.name = "OpenSfM"
        self.opensfm_path = "/opt/opensfm"
        self.executable = "opensfm"
    
    async def run(
        self,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run OpenSfM reconstruction pipeline."""
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # OpenSfM requires a specific project structure
            project_dir = output_dir / "opensfm_project"
            project_dir.mkdir(exist_ok=True)
            
            images_dir = project_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Step 1: Copy/link images and create config
            if progress_callback:
                progress_callback(10)
            
            await self._prepare_project(input_path, project_dir, max_resolution)
            
            # Step 2: Extract features
            if progress_callback:
                progress_callback(25)
            
            await self._run_opensfm_command(["extract_metadata", str(project_dir)])
            await self._run_opensfm_command(["detect_features", str(project_dir)])
            
            # Step 3: Match features
            if progress_callback:
                progress_callback(45)
            
            await self._run_opensfm_command(["match_features", str(project_dir)])
            
            # Step 4: Create tracks
            if progress_callback:
                progress_callback(60)
            
            await self._run_opensfm_command(["create_tracks", str(project_dir)])
            
            # Step 5: Reconstruct
            if progress_callback:
                progress_callback(80)
            
            await self._run_opensfm_command(["reconstruct", str(project_dir)])
            
            # Step 6: Create dense point cloud
            if progress_callback:
                progress_callback(95)
            
            await self._run_opensfm_command(["undistort", str(project_dir)])
            await self._run_opensfm_command(["compute_depthmaps", str(project_dir)])
            
            if progress_callback:
                progress_callback(100)
            
            # Export results
            output_file = str(output_dir / "point_cloud.ply")
            await self._export_ply(project_dir, output_file)
            
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
    
    async def _prepare_project(self, input_path: str, project_dir: Path, max_resolution: int):
        """Prepare OpenSfM project structure."""
        images_dir = project_dir / "images"
        
        # Copy images to project
        input_images = list(Path(input_path).glob("*.jpg")) + list(Path(input_path).glob("*.png"))
        
        for img_path in input_images:
            target_path = images_dir / img_path.name
            import shutil
            shutil.copy2(img_path, target_path)
        
        # Create config.yaml
        config_file = project_dir / "config.yaml"
        config_content = f"""
# OpenSfM Configuration
feature_type: SIFT
feature_process_size: {max_resolution}
feature_min_frames: 4000
processes: 4

# Matching
matching_gps_distance: 150
matching_gps_neighbors: 8
matching_time_neighbors: 1
matching_order_neighbors: 10
matching_bow_neighbors: 50
matching_robust_matching_threshold: 0.9

# Bundle adjustment
bundle_interval: 100
bundle_new_points_ratio: 1.2
bundle_outlier_filtering_type: AUTO
bundle_outlier_auto_ratio: 0.25

# Reconstruction
reconstruction_algorithm: TRIANGULATION
triangulation_type: ROBUST
resection_threshold: 0.004
resection_min_inliers: 10

# Dense matching
depthmap_method: PATCH_MATCH
depthmap_resolution: 640
depthmap_min_patch_sd: 1
depthmap_min_correlation_score: 0.1
depthmap_same_depth_threshold: 0.01
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
    
    async def _run_opensfm_command(self, command: list):
        """Run an OpenSfM command."""
        # For demo purposes, we'll simulate the commands
        # In practice, you would run: python -m opensfm <command> <project_dir>
        
        cmd = command[0]
        project_dir = Path(command[1]) if len(command) > 1 else None
        
        if cmd == "extract_metadata":
            await self._simulate_extract_metadata(project_dir)
        elif cmd == "detect_features":
            await self._simulate_detect_features(project_dir)
        elif cmd == "match_features":
            await self._simulate_match_features(project_dir)
        elif cmd == "create_tracks":
            await self._simulate_create_tracks(project_dir)
        elif cmd == "reconstruct":
            await self._simulate_reconstruct(project_dir)
        elif cmd == "undistort":
            await self._simulate_undistort(project_dir)
        elif cmd == "compute_depthmaps":
            await self._simulate_compute_depthmaps(project_dir)
    
    async def _simulate_extract_metadata(self, project_dir: Path):
        """Simulate metadata extraction."""
        camera_models_file = project_dir / "camera_models.json"
        with open(camera_models_file, 'w') as f:
            f.write('{"camera1": {"projection_type": "perspective", "width": 1920, "height": 1080}}')
        
        # Short delay to simulate processing
        await asyncio.sleep(0.1)
    
    async def _simulate_detect_features(self, project_dir: Path):
        """Simulate feature detection."""
        features_dir = project_dir / "features"
        features_dir.mkdir(exist_ok=True)
        
        images_dir = project_dir / "images"
        for img_file in images_dir.glob("*"):
            feature_file = features_dir / f"{img_file.stem}.features.npz"
            # Create dummy feature file
            feature_file.touch()
        
        await asyncio.sleep(0.2)
    
    async def _simulate_match_features(self, project_dir: Path):
        """Simulate feature matching."""
        matches_file = project_dir / "matches.pkl"
        matches_file.touch()
        await asyncio.sleep(0.1)
    
    async def _simulate_create_tracks(self, project_dir: Path):
        """Simulate track creation."""
        tracks_file = project_dir / "tracks.csv"
        with open(tracks_file, 'w') as f:
            f.write("track_id,image,feature_id,x,y\n")
            f.write("1,image1.jpg,1,100,200\n")
        await asyncio.sleep(0.1)
    
    async def _simulate_reconstruct(self, project_dir: Path):
        """Simulate reconstruction."""
        reconstruction_file = project_dir / "reconstruction.json"
        reconstruction_data = [{
            "cameras": {},
            "shots": {},
            "points": {}
        }]
        
        import json
        with open(reconstruction_file, 'w') as f:
            json.dump(reconstruction_data, f, indent=2)
        await asyncio.sleep(0.2)
    
    async def _simulate_undistort(self, project_dir: Path):
        """Simulate undistortion."""
        undistorted_dir = project_dir / "undistorted"
        undistorted_dir.mkdir(exist_ok=True)
        await asyncio.sleep(0.1)
    
    async def _simulate_compute_depthmaps(self, project_dir: Path):
        """Simulate depth map computation."""
        depthmaps_dir = project_dir / "undistorted" / "depthmaps"
        depthmaps_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.sleep(0.2)
    
    async def _export_ply(self, project_dir: Path, output_file: str):
        """Export reconstruction to PLY format."""
        with open(output_file, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write("element vertex 3000\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            # Generate dummy point cloud
            import random
            for i in range(3000):
                x = random.uniform(-3, 3)
                y = random.uniform(-3, 3)
                z = random.uniform(-1, 1)
                r = random.randint(50, 255)
                g = random.randint(50, 255)
                b = random.randint(50, 255)
                f.write(f"{x} {y} {z} {r} {g} {b}\n")
    
    def check_availability(self) -> bool:
        """Check if OpenSfM is available."""
        try:
            # Check if OpenSfM directory exists
            opensfm_path = Path(self.opensfm_path)
            return opensfm_path.exists()
        except:
            return False
    
    def get_version(self) -> str:
        """Get OpenSfM version."""
        return "0.5.2 (demo)"
    
    def get_type(self) -> str:
        """Get tool type."""
        return "SfM"
    
    def get_description(self) -> str:
        """Get tool description."""
        return "OpenSfM is a Structure from Motion library written in Python with focus on easy integration and extensibility"