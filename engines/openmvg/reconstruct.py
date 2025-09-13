#!/usr/bin/env python3
"""
OpenMVG/OpenMVS reconstruction engine for the photogrammetry pipeline.
"""

import os
import sys
import json
import argparse
import subprocess
import time
import shutil
from pathlib import Path

def intrinsic_analysis(input_dir, output_dir, params):
    """Analyze image intrinsics using OpenMVG"""
    
    print("Analyzing image intrinsics...")
    
    cmd = [
        "openMVG_main_SfMInit_ImageListing",
        "-i", input_dir,
        "-o", output_dir,
        "-d", "/usr/local/share/openMVG/sensor_width_camera_database.txt"
    ]
    
    if params.get('focal_pixels'):
        cmd.extend(["-f", str(params['focal_pixels'])])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Intrinsic analysis failed: {result.stderr}")
        raise Exception(f"Intrinsic analysis failed: {result.stderr}")
    
    print("Intrinsic analysis completed")
    return True

def compute_features(output_dir, params):
    """Compute image features using OpenMVG"""
    
    print("Computing features...")
    
    cmd = [
        "openMVG_main_ComputeFeatures",
        "-i", os.path.join(output_dir, "sfm_data.json"),
        "-o", output_dir
    ]
    
    # Feature type
    feature_type = params.get('feature_type', 'SIFT')
    if feature_type.upper() == 'AKAZE':
        cmd.extend(["-m", "AKAZE_FLOAT"])
    else:
        cmd.extend(["-m", "SIFT"])
    
    # Use GPU if available
    if params.get('use_gpu', False):
        cmd.append("-G")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Feature computation failed: {result.stderr}")
        raise Exception(f"Feature computation failed: {result.stderr}")
    
    print("Feature computation completed")
    return True

def compute_matches(output_dir, params):
    """Compute feature matches using OpenMVG"""
    
    print("Computing matches...")
    
    # Choose matching strategy
    matching_strategy = params.get('matching_strategy', 'exhaustive')
    
    if matching_strategy == 'sequential':
        cmd = [
            "openMVG_main_ComputeMatches",
            "-i", os.path.join(output_dir, "sfm_data.json"),
            "-o", output_dir,
            "-n", "HNNSW"  # Hierarchical Navigable Small World
        ]
    else:
        # Exhaustive matching
        cmd = [
            "openMVG_main_ComputeMatches",
            "-i", os.path.join(output_dir, "sfm_data.json"),
            "-o", output_dir
        ]
    
    # Geometric filter
    geometric_filter = params.get('geometric_filter', 'fundamental')
    if geometric_filter.upper() == 'ESSENTIAL':
        cmd.extend(["-g", "e"])
    else:
        cmd.extend(["-g", "f"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Match computation failed: {result.stderr}")
        raise Exception(f"Match computation failed: {result.stderr}")
    
    print("Match computation completed")
    return True

def incremental_sfm(output_dir, params):
    """Perform incremental Structure-from-Motion"""
    
    print("Running incremental Structure-from-Motion...")
    
    cmd = [
        "openMVG_main_IncrementalSfM",
        "-i", os.path.join(output_dir, "sfm_data.json"),
        "-m", output_dir,
        "-o", output_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get('timeout', 3600))
    
    if result.returncode != 0:
        print(f"Incremental SfM failed: {result.stderr}")
        raise Exception(f"Incremental SfM failed: {result.stderr}")
    
    print("Incremental SfM completed")
    return True

def colorize_structure(output_dir):
    """Colorize the sparse 3D structure"""
    
    print("Colorizing 3D structure...")
    
    cmd = [
        "openMVG_main_ComputeSfM_DataColor",
        "-i", os.path.join(output_dir, "sfm_data.bin"),
        "-o", os.path.join(output_dir, "colorized.ply")
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Structure colorization failed: {result.stderr}")
        # Don't fail completely
        return False
    
    print("Structure colorization completed")
    return True

def convert_to_mvs(output_dir):
    """Convert OpenMVG scene to OpenMVS format"""
    
    print("Converting to OpenMVS format...")
    
    cmd = [
        "openMVG_main_openMVG2openMVS",
        "-i", os.path.join(output_dir, "sfm_data.bin"),
        "-o", os.path.join(output_dir, "scene.mvs"),
        "-d", output_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"OpenMVS conversion failed: {result.stderr}")
        raise Exception(f"OpenMVS conversion failed: {result.stderr}")
    
    print("OpenMVS conversion completed")
    return True

def dense_reconstruction_mvs(output_dir, params):
    """Perform dense reconstruction using OpenMVS"""
    
    print("Starting OpenMVS dense reconstruction...")
    
    scene_file = os.path.join(output_dir, "scene.mvs")
    
    # DensifyPointCloud
    print("Densifying point cloud...")
    cmd = [
        "DensifyPointCloud",
        scene_file,
        "--resolution-level", str(params.get('resolution_level', 1)),
        "--number-views", str(params.get('number_views', 4))
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get('dense_timeout', 1800))
    
    if result.returncode != 0:
        print(f"Point cloud densification failed: {result.stderr}")
        raise Exception(f"Point cloud densification failed: {result.stderr}")
    
    # ReconstructMesh
    print("Reconstructing mesh...")
    dense_scene = os.path.join(output_dir, "scene_dense.mvs")
    cmd = [
        "ReconstructMesh",
        dense_scene,
        "--thickness-factor", str(params.get('thickness_factor', 1.0)),
        "--quality-factor", str(params.get('quality_factor', 1.0))
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get('mesh_timeout', 1800))
    
    if result.returncode != 0:
        print(f"Mesh reconstruction failed: {result.stderr}")
        # Continue without mesh
        return False
    
    # RefineMesh
    print("Refining mesh...")
    mesh_scene = os.path.join(output_dir, "scene_dense_mesh.mvs")
    if os.path.exists(mesh_scene):
        cmd = [
            "RefineMesh",
            mesh_scene,
            "--resolution-level", str(params.get('refine_resolution', 1))
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Mesh refinement failed: {result.stderr}")
            # Continue without refinement
        
        # TextureMesh
        print("Texturing mesh...")
        refined_mesh = os.path.join(output_dir, "scene_dense_mesh_refine.mvs")
        if os.path.exists(refined_mesh):
            cmd = [
                "TextureMesh",
                refined_mesh,
                "--resolution-level", str(params.get('texture_resolution', 0))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Mesh texturing failed: {result.stderr}")
    
    print("OpenMVS dense reconstruction completed")
    return True

def organize_results(output_dir):
    """Organize OpenMVG/OpenMVS output files"""
    
    print("Organizing reconstruction results...")
    
    results = {
        "sparse_model": None,
        "dense_point_cloud": None,
        "mesh": None,
        "textured_mesh": None,
        "cameras": None
    }
    
    # Sparse reconstruction
    sfm_data_bin = os.path.join(output_dir, "sfm_data.bin")
    if os.path.exists(sfm_data_bin):
        results["sparse_model"] = sfm_data_bin
    
    # Colorized point cloud
    colorized_ply = os.path.join(output_dir, "colorized.ply")
    if os.path.exists(colorized_ply):
        results["sparse_point_cloud"] = colorized_ply
        shutil.copy2(colorized_ply, os.path.join(output_dir, "sparse_point_cloud.ply"))
    
    # Dense point cloud
    dense_ply = os.path.join(output_dir, "scene_dense.ply")
    if os.path.exists(dense_ply):
        results["dense_point_cloud"] = dense_ply
        shutil.copy2(dense_ply, os.path.join(output_dir, "dense_point_cloud.ply"))
    
    # Mesh files
    mesh_ply = os.path.join(output_dir, "scene_dense_mesh.ply")
    if os.path.exists(mesh_ply):
        results["mesh"] = mesh_ply
        shutil.copy2(mesh_ply, os.path.join(output_dir, "final_mesh.ply"))
    
    # Textured mesh
    textured_mesh = os.path.join(output_dir, "scene_dense_mesh_refine_texture.ply")
    if os.path.exists(textured_mesh):
        results["textured_mesh"] = textured_mesh
        shutil.copy2(textured_mesh, os.path.join(output_dir, "textured_mesh.ply"))
    
    # Create summary report
    summary = {
        "method": "OpenMVG/OpenMVS",
        "status": "completed",
        "files": results,
        "timestamp": time.time()
    }
    
    with open(os.path.join(output_dir, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='OpenMVG/OpenMVS reconstruction engine')
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
        
        print(f"Starting OpenMVG/OpenMVS reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Run OpenMVG pipeline
        intrinsic_analysis(args.input, args.output, params)
        compute_features(args.output, params)
        compute_matches(args.output, params)
        incremental_sfm(args.output, params)
        colorize_structure(args.output)
        
        # Dense reconstruction with OpenMVS (optional)
        if params.get('dense_reconstruction', True):
            convert_to_mvs(args.output)
            dense_reconstruction_mvs(args.output, params)
        
        # Organize results
        results = organize_results(args.output)
        
        print("OpenMVG/OpenMVS reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "OpenMVG/OpenMVS",
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
