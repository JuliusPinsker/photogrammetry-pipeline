#!/usr/bin/env python3
"""
Meshroom reconstruction engine for the photogrammetry pipeline.
"""

import os
import sys
import json
import argparse
import subprocess
import time
import shutil
from pathlib import Path

def setup_meshroom_project(input_dir, output_dir, params):
    """Set up Meshroom project with input images"""
    
    # Create Meshroom project structure
    project_dir = os.path.join(output_dir, "meshroom_project")
    os.makedirs(project_dir, exist_ok=True)
    
    # Find all image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(input_dir).glob(f"*{ext}"))
        image_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
    
    if not image_files:
        raise Exception(f"No images found in {input_dir}")
    
    print(f"Found {len(image_files)} images for reconstruction")
    
    # Create Meshroom graph file
    graph_template = {
        "header": {
            "pipelineVersion": "2.2",
            "releaseVersion": "2023.3.0",
            "fileVersion": "1.1",
            "template": False,
            "nodesVersions": {
                "CameraInit": "9.0",
                "FeatureExtraction": "1.1",
                "ImageMatching": "2.0",
                "FeatureMatching": "2.0",
                "StructureFromMotion": "3.0",
                "PrepareDenseScene": "3.0",
                "DepthMap": "4.0",
                "DepthMapFilter": "3.0",
                "Meshing": "7.0",
                "MeshFiltering": "3.0",
                "Texturing": "6.0"
            }
        },
        "graph": {}
    }
    
    # Add image inputs to viewpoints
    viewpoints = []
    for i, img_path in enumerate(image_files):
        viewpoint = {
            "viewId": i,
            "poseId": i,
            "path": str(img_path),
            "intrinsicId": 0,
            "rigId": -1,
            "subPoseId": -1,
            "metadata": ""
        }
        viewpoints.append(viewpoint)
    
    # Create simplified node structure for command line execution
    nodes = {
        "CameraInit_1": {
            "nodeType": "CameraInit",
            "attributes": {
                "viewpoints": viewpoints,
                "intrinsics": [],
                "sensorDatabase": "${ALICEVISION_SENSOR_DB}",
                "defaultFieldOfView": 45.0,
                "groupCameraFallback": "folder",
                "verboseLevel": "info"
            }
        }
    }
    
    graph_template["graph"] = nodes
    
    # Save graph file
    graph_file = os.path.join(project_dir, "pipeline.mg")
    with open(graph_file, 'w') as f:
        json.dump(graph_template, f, indent=2)
    
    return graph_file, len(image_files)

def run_meshroom_pipeline(graph_file, output_dir, params):
    """Run the Meshroom reconstruction pipeline"""
    
    print("Starting Meshroom reconstruction...")
    
    # Meshroom command line execution
    cmd = [
        "/opt/meshroom/meshroom_photogrammetry",
        "--input", os.path.dirname(graph_file),
        "--output", output_dir,
        "--save", graph_file
    ]
    
    # Add custom parameters
    if params.get('verbose', False):
        cmd.extend(["--verboseLevel", "info"])
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        # Run Meshroom
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=params.get('timeout', 7200)  # 2 hour default timeout
        )
        
        if result.returncode != 0:
            print(f"Meshroom failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"Meshroom reconstruction failed: {result.stderr}")
        
        print("Meshroom reconstruction completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print("Meshroom reconstruction timed out")
        raise Exception("Reconstruction timed out")
    except Exception as e:
        print(f"Error running Meshroom: {e}")
        raise

def organize_results(output_dir):
    """Organize Meshroom output files"""
    
    print("Organizing reconstruction results...")
    
    # Look for Meshroom output files
    meshroom_cache = os.path.join(output_dir, "MeshroomCache")
    
    results = {
        "mesh": None,
        "texture": None,
        "cameras": None,
        "point_cloud": None
    }
    
    if os.path.exists(meshroom_cache):
        # Find the final mesh
        texturing_dirs = [d for d in os.listdir(meshroom_cache) if d.startswith("Texturing")]
        if texturing_dirs:
            texturing_dir = os.path.join(meshroom_cache, texturing_dirs[-1])
            mesh_file = os.path.join(texturing_dir, "texturedMesh.obj")
            if os.path.exists(mesh_file):
                results["mesh"] = mesh_file
                # Copy to main output directory
                shutil.copy2(mesh_file, os.path.join(output_dir, "final_mesh.obj"))
                
                # Copy associated files
                mtl_file = os.path.join(texturing_dir, "texturedMesh.mtl")
                if os.path.exists(mtl_file):
                    shutil.copy2(mtl_file, os.path.join(output_dir, "final_mesh.mtl"))
                
                # Copy textures
                texture_dir = os.path.join(output_dir, "textures")
                os.makedirs(texture_dir, exist_ok=True)
                for file in os.listdir(texturing_dir):
                    if file.endswith(('.jpg', '.png', '.tiff')):
                        shutil.copy2(
                            os.path.join(texturing_dir, file),
                            os.path.join(texture_dir, file)
                        )
        
        # Find camera poses
        sfm_dirs = [d for d in os.listdir(meshroom_cache) if d.startswith("StructureFromMotion")]
        if sfm_dirs:
            sfm_dir = os.path.join(meshroom_cache, sfm_dirs[-1])
            cameras_file = os.path.join(sfm_dir, "cameras.sfm")
            if os.path.exists(cameras_file):
                results["cameras"] = cameras_file
                shutil.copy2(cameras_file, os.path.join(output_dir, "cameras.sfm"))
    
    # Create summary report
    summary = {
        "method": "Meshroom",
        "status": "completed",
        "files": results,
        "timestamp": time.time()
    }
    
    with open(os.path.join(output_dir, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Meshroom reconstruction engine')
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
        
        print(f"Starting Meshroom reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Set up Meshroom project
        graph_file, num_images = setup_meshroom_project(args.input, args.output, params)
        print(f"Created Meshroom project with {num_images} images")
        
        # Run reconstruction
        run_meshroom_pipeline(graph_file, args.output, params)
        
        # Organize results
        results = organize_results(args.output)
        
        print("Meshroom reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "Meshroom",
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
