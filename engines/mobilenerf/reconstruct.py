#!/usr/bin/env python3
"""
MobileNeRF reconstruction engine for the photogrammetry pipeline.
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

def prepare_nerf_data(input_dir, output_dir):
    """Prepare data for MobileNeRF training"""
    
    print("Preparing data for MobileNeRF...")
    
    # Create data directory structure
    data_dir = os.path.join(output_dir, "nerf_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Copy images
    images_dir = os.path.join(data_dir, "images")
    if not os.path.exists(images_dir):
        shutil.copytree(input_dir, images_dir)
    
    # Create simplified transforms.json for MobileNeRF
    # This is a basic implementation - in practice you'd use COLMAP or similar
    transforms = create_simple_transforms(images_dir)
    
    with open(os.path.join(data_dir, "transforms.json"), 'w') as f:
        json.dump(transforms, f, indent=2)
    
    return data_dir

def create_simple_transforms(images_dir):
    """Create a simple transforms.json for circular camera path"""
    
    image_files = sorted([f for f in os.listdir(images_dir) 
                         if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    transforms = {
        "camera_angle_x": 0.6911112070083618,
        "frames": []
    }
    
    num_images = len(image_files)
    radius = 4.0
    
    for i, img_file in enumerate(image_files):
        angle = 2 * np.pi * i / num_images
        
        # Simple circular camera path
        x = radius * np.cos(angle)
        z = radius * np.sin(angle)
        y = 0.0
        
        # Look at origin
        transform_matrix = np.eye(4)
        transform_matrix[0, 3] = x
        transform_matrix[1, 3] = y
        transform_matrix[2, 3] = z
        
        frame = {
            "file_path": f"./images/{img_file}",
            "transform_matrix": transform_matrix.tolist()
        }
        transforms["frames"].append(frame)
    
    return transforms

def train_mobilenerf(data_dir, output_dir, params):
    """Train MobileNeRF model"""
    
    print("Training MobileNeRF model...")
    
    # Change to MobileNeRF directory
    mobilenerf_dir = "/opt/google-research/mobilenerf"
    os.chdir(mobilenerf_dir)
    
    # MobileNeRF training command
    cmd = [
        "python3", "-m", "train",
        "--data_dir", data_dir,
        "--model_dir", output_dir,
        "--gin_file", "configs/blender.gin",
        "--gin_param", f"Config.max_steps = {params.get('max_steps', 200000)}",
        "--gin_param", f"Config.batch_size = {params.get('batch_size', 4096)}",
        "--gin_param", f"Config.lr_init = {params.get('lr_init', 5e-4)}",
        "--gin_param", f"Config.lr_final = {params.get('lr_final', 5e-6)}"
    ]
    
    # Additional parameters for mobile optimization
    if params.get('mobile_mode', True):
        cmd.extend([
            "--gin_param", "Config.render_chunk_size = 1024",
            "--gin_param", "Config.factor = 4",  # Downscale images
            "--gin_param", "Config.llffhold = 8"  # Use fewer validation images
        ])
    
    # Run training
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        timeout=params.get('timeout', 7200)  # 2 hours
    )
    
    if result.returncode != 0:
        print(f"MobileNeRF training failed: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
        raise Exception(f"MobileNeRF training failed: {result.stderr}")
    
    print("MobileNeRF training completed")
    return True

def export_mobile_model(model_dir, output_dir, params):
    """Export model for mobile deployment"""
    
    print("Exporting model for mobile deployment...")
    
    mobilenerf_dir = "/opt/google-research/mobilenerf"
    os.chdir(mobilenerf_dir)
    
    # Export command
    cmd = [
        "python3", "-m", "export",
        "--model_dir", model_dir,
        "--output_dir", os.path.join(output_dir, "mobile_export"),
        "--format", params.get('export_format', 'web')
    ]
    
    if params.get('quantize', True):
        cmd.append("--quantize")
    
    if params.get('optimize_size', True):
        cmd.append("--optimize_size")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        print(f"Model export failed: {result.stderr}")
        return False
    
    print("Model export completed")
    return True

def render_test_views(model_dir, output_dir, params):
    """Render test views from trained model"""
    
    print("Rendering test views...")
    
    mobilenerf_dir = "/opt/google-research/mobilenerf"
    os.chdir(mobilenerf_dir)
    
    render_dir = os.path.join(output_dir, "renders")
    os.makedirs(render_dir, exist_ok=True)
    
    cmd = [
        "python3", "-m", "render",
        "--model_dir", model_dir,
        "--output_dir", render_dir,
        "--render_factor", str(params.get('render_factor', 1))
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        print(f"Rendering failed: {result.stderr}")
        return False
    
    print("Rendering completed")
    return True

def create_web_viewer(export_dir, output_dir):
    """Create web viewer files for mobile deployment"""
    
    print("Creating web viewer...")
    
    if not os.path.exists(export_dir):
        return False
    
    web_dir = os.path.join(output_dir, "web_viewer")
    os.makedirs(web_dir, exist_ok=True)
    
    # Copy exported model files
    for file in os.listdir(export_dir):
        src = os.path.join(export_dir, file)
        dst = os.path.join(web_dir, file)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    
    # Create simple HTML viewer
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>MobileNeRF Viewer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; padding: 0; overflow: hidden; }
        canvas { display: block; }
    </style>
</head>
<body>
    <canvas id="nerf-canvas"></canvas>
    <script src="mobilenerf-viewer.js"></script>
    <script>
        // Initialize MobileNeRF viewer
        const canvas = document.getElementById('nerf-canvas');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        // Load and display the model
        loadMobileNeRF(canvas, './model.json');
    </script>
</body>
</html>
"""
    
    with open(os.path.join(web_dir, "index.html"), 'w') as f:
        f.write(html_content)
    
    return True

def organize_results(model_dir, output_dir):
    """Organize MobileNeRF output files"""
    
    print("Organizing reconstruction results...")
    
    results = {
        "model": None,
        "mobile_export": None,
        "web_viewer": None,
        "renders": None
    }
    
    # Model directory
    if os.path.exists(model_dir):
        results["model"] = model_dir
    
    # Mobile export
    mobile_export = os.path.join(output_dir, "mobile_export")
    if os.path.exists(mobile_export):
        results["mobile_export"] = mobile_export
    
    # Web viewer
    web_viewer = os.path.join(output_dir, "web_viewer")
    if os.path.exists(web_viewer):
        results["web_viewer"] = web_viewer
    
    # Renders
    render_dir = os.path.join(output_dir, "renders")
    if os.path.exists(render_dir):
        results["renders"] = render_dir
    
    # Create summary report
    summary = {
        "method": "MobileNeRF",
        "status": "completed",
        "files": results,
        "timestamp": time.time(),
        "mobile_optimized": True
    }
    
    with open(os.path.join(output_dir, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='MobileNeRF reconstruction engine')
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
        
        print(f"Starting MobileNeRF reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Prepare data
        data_dir = prepare_nerf_data(args.input, args.output)
        
        # Train model
        model_dir = os.path.join(args.output, "model")
        os.makedirs(model_dir, exist_ok=True)
        train_mobilenerf(data_dir, model_dir, params)
        
        # Export for mobile
        if params.get('export_mobile', True):
            export_mobile_model(model_dir, args.output, params)
            
            # Create web viewer
            export_dir = os.path.join(args.output, "mobile_export")
            create_web_viewer(export_dir, args.output)
        
        # Render test views (optional)
        if params.get('render_views', True):
            render_test_views(model_dir, args.output, params)
        
        # Organize results
        results = organize_results(model_dir, args.output)
        
        print("MobileNeRF reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "MobileNeRF",
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
