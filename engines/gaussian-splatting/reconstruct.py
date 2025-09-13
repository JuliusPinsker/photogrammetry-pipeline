#!/usr/bin/env python3
"""
3D Gaussian Splatting reconstruction engine for the photogrammetry pipeline.
"""

import os
import sys
import json
import argparse
import subprocess
import time
import shutil
import numpy as np
from pathlib import Path

def prepare_colmap_data(input_dir, output_dir):
    """Prepare COLMAP data for Gaussian Splatting"""
    
    print("Preparing COLMAP data for Gaussian Splatting...")
    
    # Create COLMAP workspace
    colmap_workspace = os.path.join(output_dir, "input")
    os.makedirs(colmap_workspace, exist_ok=True)
    
    # Create images directory and copy images
    images_path = os.path.join(colmap_workspace, "images")
    if not os.path.exists(images_path):
        shutil.copytree(input_dir, images_path)
    
    database_path = os.path.join(colmap_workspace, "database.db")
    sparse_path = os.path.join(colmap_workspace, "sparse")
    os.makedirs(sparse_path, exist_ok=True)
    
    # Feature extraction
    print("Extracting features with COLMAP...")
    cmd = [
        "colmap", "feature_extractor",
        "--database_path", database_path,
        "--image_path", images_path,
        "--ImageReader.single_camera", "1",
        "--ImageReader.camera_model", "PINHOLE"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"COLMAP feature extraction failed: {result.stderr}")
    
    # Feature matching
    print("Matching features with COLMAP...")
    cmd = [
        "colmap", "exhaustive_matcher",
        "--database_path", database_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"COLMAP feature matching failed: {result.stderr}")
    
    # Structure from motion
    print("Running COLMAP SfM...")
    cmd = [
        "colmap", "mapper",
        "--database_path", database_path,
        "--image_path", images_path,
        "--output_path", sparse_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise Exception(f"COLMAP SfM failed: {result.stderr}")
    
    # Convert to text format for Gaussian Splatting
    model_dirs = [d for d in os.listdir(sparse_path) if d.isdigit()]
    if model_dirs:
        model_path = os.path.join(sparse_path, model_dirs[0])
        cmd = [
            "colmap", "model_converter",
            "--input_path", model_path,
            "--output_path", model_path,
            "--output_type", "TXT"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: COLMAP model conversion failed: {result.stderr}")
    
    return colmap_workspace

def train_gaussian_splatting(data_dir, output_dir, params):
    """Train 3D Gaussian Splatting model"""
    
    print("Training 3D Gaussian Splatting model...")
    
    # Change to Gaussian Splatting directory
    os.chdir("/opt/gaussian-splatting")
    
    cmd = [
        "python3", "train.py",
        "-s", data_dir,
        "-m", output_dir,
        "--iterations", str(params.get('iterations', 30000)),
        "--test_iterations", str(params.get('test_iterations', 7000)),
        "--save_iterations", str(params.get('save_iterations', 30000)),
        "--checkpoint_iterations", str(params.get('checkpoint_iterations', 30000))
    ]
    
    # Additional parameters
    if params.get('resolution', 1) != 1:
        cmd.extend(["--resolution", str(params['resolution'])])
    
    if params.get('data_device') == "cpu":
        cmd.append("--data_device")
        cmd.append("cpu")
    
    if params.get('white_background'):
        cmd.append("--white_background")
    
    if params.get('sh_degree'):
        cmd.extend(["--sh_degree", str(params['sh_degree'])])
    
    # Run training
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        timeout=params.get('timeout', 3600)
    )
    
    if result.returncode != 0:
        print(f"Gaussian Splatting training failed: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
        raise Exception(f"Gaussian Splatting training failed: {result.stderr}")
    
    print("Gaussian Splatting training completed")
    return True

def render_views(model_dir, output_dir, params):
    """Render novel views from trained model"""
    
    print("Rendering novel views...")
    
    os.chdir("/opt/gaussian-splatting")
    
    render_output = os.path.join(output_dir, "renders")
    os.makedirs(render_output, exist_ok=True)
    
    cmd = [
        "python3", "render.py",
        "-m", model_dir,
        "--iteration", str(params.get('render_iteration', 30000)),
        "--skip_train"
    ]
    
    if params.get('render_path'):
        cmd.extend(["--render_path", params['render_path']])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        print(f"Rendering failed: {result.stderr}")
        return False
    
    print("Rendering completed")
    return True

def extract_mesh(model_dir, output_dir, params):
    """Extract mesh from Gaussian Splatting model"""
    
    print("Extracting mesh from Gaussian model...")
    
    os.chdir("/opt/gaussian-splatting")
    
    # This requires additional tools like TSDF fusion or similar
    # For now, we'll export the point cloud as PLY
    point_cloud_path = os.path.join(model_dir, "point_cloud")
    
    if os.path.exists(point_cloud_path):
        iteration_dirs = [d for d in os.listdir(point_cloud_path) if d.startswith("iteration_")]
        if iteration_dirs:
            latest_iteration = sorted(iteration_dirs, key=lambda x: int(x.split("_")[1]))[-1]
            ply_file = os.path.join(point_cloud_path, latest_iteration, "point_cloud.ply")
            
            if os.path.exists(ply_file):
                output_ply = os.path.join(output_dir, "gaussian_point_cloud.ply")
                shutil.copy2(ply_file, output_ply)
                return True
    
    return False

def create_video(render_dir, output_dir, params):
    """Create video from rendered frames"""
    
    print("Creating video from rendered frames...")
    
    if not os.path.exists(render_dir):
        return False
    
    # Find rendered images
    image_files = sorted(list(Path(render_dir).glob("*.png")))
    if not image_files:
        return False
    
    # Create video using ffmpeg
    video_output = os.path.join(output_dir, "render_video.mp4")
    
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(params.get('video_fps', 30)),
        "-pattern_type", "glob",
        "-i", os.path.join(render_dir, "*.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        video_output
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("Video creation completed")
            return True
    except:
        pass
    
    print("Video creation failed or ffmpeg not available")
    return False

def organize_results(model_dir, output_dir):
    """Organize Gaussian Splatting output files"""
    
    print("Organizing reconstruction results...")
    
    results = {
        "model": None,
        "point_cloud": None,
        "renders": None,
        "video": None,
        "cameras": None
    }
    
    # Model directory
    if os.path.exists(model_dir):
        results["model"] = model_dir
    
    # Point cloud
    gaussian_ply = os.path.join(output_dir, "gaussian_point_cloud.ply")
    if os.path.exists(gaussian_ply):
        results["point_cloud"] = gaussian_ply
        shutil.copy2(gaussian_ply, os.path.join(output_dir, "final_point_cloud.ply"))
    
    # Renders
    render_dir = os.path.join(model_dir, "test")
    if os.path.exists(render_dir):
        results["renders"] = render_dir
    
    # Video
    video_file = os.path.join(output_dir, "render_video.mp4")
    if os.path.exists(video_file):
        results["video"] = video_file
    
    # Cameras (from COLMAP input)
    cameras_file = os.path.join(model_dir, "cameras.json")
    if os.path.exists(cameras_file):
        results["cameras"] = cameras_file
    
    # Create summary report
    summary = {
        "method": "3D Gaussian Splatting",
        "status": "completed",
        "files": results,
        "timestamp": time.time()
    }
    
    with open(os.path.join(output_dir, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='3D Gaussian Splatting reconstruction engine')
    parser.add_argument('--input', required=True, help='Input directory with images')
    parser.add_argument('--output', required=True, help='Output directory for results')
    parser.add_argument('--params', default='{}', help='JSON parameters for reconstruction')
    
    args = parser.parse_args()
    
    try:
        # Parse parameters
        params = json.loads(args.params) if args.params else {}
        
        # Validate input directory
        if not os.path.exists(args.input):
            raise Exception(f"Input directory does not exist: {args.input}")
        
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        print(f"Starting 3D Gaussian Splatting reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Prepare data
        if not params.get('skip_colmap', False):
            data_dir = prepare_colmap_data(args.input, args.output)
        else:
            data_dir = args.input
        
        # Train model
        model_dir = os.path.join(args.output, "model")
        os.makedirs(model_dir, exist_ok=True)
        train_gaussian_splatting(data_dir, model_dir, params)
        
        # Extract point cloud
        extract_mesh(model_dir, args.output, params)
        
        # Render views (optional)
        if params.get('render_views', True):
            render_views(model_dir, args.output, params)
            
            # Create video from renders
            render_dir = os.path.join(model_dir, "test", "renders")
            if os.path.exists(render_dir):
                create_video(render_dir, args.output, params)
        
        # Organize results
        results = organize_results(model_dir, args.output)
        
        print("3D Gaussian Splatting reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "3D Gaussian Splatting",
            "status": "failed",
            "error": str(e),
            "timestamp": time.time()
        }
        
        os.makedirs(args.output, exist_ok=True)
        with open(os.path.join(args.output, "reconstruction_summary.json"), 'w') as f:
            json.dump(error_summary, f, indent=2)
        
        sys.exit(1)

if __name__ == "__main__":
    main()
