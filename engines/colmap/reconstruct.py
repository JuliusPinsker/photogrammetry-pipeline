#!/usr/bin/env python3
"""
COLMAP reconstruction engine for the photogrammetry pipeline.
"""

import os
import sys
import json
import argparse
import subprocess
import time
import shutil
from pathlib import Path

def extract_features(database_path, image_path, params):
    """Extract features from images using COLMAP"""
    
    print("Extracting features...")
    
    cmd = [
        "colmap", "feature_extractor",
        "--database_path", database_path,
        "--image_path", image_path,
        "--ImageReader.single_camera", "1" if params.get('single_camera', True) else "0",
        "--SiftExtraction.use_gpu", "1" if params.get('use_gpu', True) else "0"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Feature extraction failed: {result.stderr}")
        raise Exception(f"Feature extraction failed: {result.stderr}")
    
    print("Feature extraction completed")
    return True

def match_features(database_path, params):
    """Match features between images using COLMAP"""
    
    print("Matching features...")
    
    # Use exhaustive matcher for smaller datasets, vocabulary tree for larger
    num_images = get_num_images_in_database(database_path)
    
    if num_images <= params.get('exhaustive_threshold', 50):
        cmd = [
            "colmap", "exhaustive_matcher",
            "--database_path", database_path,
            "--SiftMatching.use_gpu", "1" if params.get('use_gpu', True) else "0"
        ]
    else:
        # For larger datasets, use vocabulary tree matcher
        cmd = [
            "colmap", "vocab_tree_matcher",
            "--database_path", database_path,
            "--VocabTreeMatching.vocab_tree_path", "/usr/local/share/colmap/vocab_tree_flickr100K_words32K.bin",
            "--SiftMatching.use_gpu", "1" if params.get('use_gpu', True) else "0"
        ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Feature matching failed: {result.stderr}")
        raise Exception(f"Feature matching failed: {result.stderr}")
    
    print("Feature matching completed")
    return True

def structure_from_motion(database_path, image_path, output_path, params):
    """Perform Structure-from-Motion reconstruction"""
    
    print("Running Structure-from-Motion...")
    
    cmd = [
        "colmap", "mapper",
        "--database_path", database_path,
        "--image_path", image_path,
        "--output_path", output_path,
        "--Mapper.ba_refine_focal_length", "1" if params.get('refine_focal_length', True) else "0",
        "--Mapper.ba_refine_principal_point", "1" if params.get('refine_principal_point', False) else "0"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get('timeout', 3600))
    
    if result.returncode != 0:
        print(f"Structure-from-Motion failed: {result.stderr}")
        raise Exception(f"Structure-from-Motion failed: {result.stderr}")
    
    print("Structure-from-Motion completed")
    return True

def dense_reconstruction(input_path, output_path, params):
    """Perform dense reconstruction using COLMAP"""
    
    print("Starting dense reconstruction...")
    
    # Image undistortion
    print("Undistorting images...")
    undistorted_path = os.path.join(output_path, "undistorted")
    os.makedirs(undistorted_path, exist_ok=True)
    
    cmd = [
        "colmap", "image_undistorter",
        "--image_path", os.path.join(input_path, "images"),
        "--input_path", input_path,
        "--output_path", undistorted_path,
        "--output_type", "COLMAP"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Image undistortion failed: {result.stderr}")
        raise Exception(f"Image undistortion failed: {result.stderr}")
    
    # Patch match stereo
    print("Computing stereo depth maps...")
    stereo_path = os.path.join(output_path, "stereo")
    os.makedirs(stereo_path, exist_ok=True)
    
    cmd = [
        "colmap", "patch_match_stereo",
        "--workspace_path", undistorted_path,
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "1" if params.get('geom_consistency', True) else "0"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get('stereo_timeout', 1800))
    if result.returncode != 0:
        print(f"Stereo computation failed: {result.stderr}")
        raise Exception(f"Stereo computation failed: {result.stderr}")
    
    # Stereo fusion
    print("Fusing stereo depth maps...")
    cmd = [
        "colmap", "stereo_fusion",
        "--workspace_path", undistorted_path,
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", os.path.join(output_path, "fused.ply")
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Stereo fusion failed: {result.stderr}")
        raise Exception(f"Stereo fusion failed: {result.stderr}")
    
    print("Dense reconstruction completed")
    return True

def poisson_meshing(input_ply, output_path, params):
    """Generate mesh using Poisson reconstruction"""
    
    print("Generating Poisson mesh...")
    
    mesh_output = os.path.join(output_path, "poisson_mesh.ply")
    
    cmd = [
        "colmap", "poisson_mesher",
        "--input_path", input_ply,
        "--output_path", mesh_output,
        "--PoissonMeshing.depth", str(params.get('poisson_depth', 13)),
        "--PoissonMeshing.color", "1" if params.get('use_color', True) else "0"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Poisson meshing failed: {result.stderr}")
        # Don't fail completely, as dense point cloud might still be useful
        print("Continuing without mesh generation")
        return False
    
    print("Poisson meshing completed")
    return True

def get_num_images_in_database(database_path):
    """Get number of images in COLMAP database"""
    try:
        cmd = ["colmap", "database_query", "--database_path", database_path, "--query", "SELECT COUNT(*) FROM images;"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass
    return 0

def organize_results(workspace_path, output_path):
    """Organize COLMAP output files"""
    
    print("Organizing reconstruction results...")
    
    results = {
        "sparse_model": None,
        "dense_point_cloud": None,
        "mesh": None,
        "cameras": None
    }
    
    # Find sparse reconstruction
    sparse_dir = os.path.join(workspace_path, "sparse")
    if os.path.exists(sparse_dir):
        # COLMAP creates numbered subdirectories for each model
        model_dirs = [d for d in os.listdir(sparse_dir) if d.isdigit()]
        if model_dirs:
            # Use the first (usually best) model
            model_dir = os.path.join(sparse_dir, model_dirs[0])
            
            # Copy sparse model files
            sparse_output = os.path.join(output_path, "sparse")
            os.makedirs(sparse_output, exist_ok=True)
            
            for file in ["cameras.txt", "images.txt", "points3D.txt"]:
                src = os.path.join(model_dir, file)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(sparse_output, file))
            
            results["sparse_model"] = sparse_output
            results["cameras"] = os.path.join(sparse_output, "cameras.txt")
    
    # Find dense point cloud
    fused_ply = os.path.join(workspace_path, "fused.ply")
    if os.path.exists(fused_ply):
        results["dense_point_cloud"] = fused_ply
        shutil.copy2(fused_ply, os.path.join(output_path, "dense_point_cloud.ply"))
    
    # Find mesh
    mesh_file = os.path.join(workspace_path, "poisson_mesh.ply")
    if os.path.exists(mesh_file):
        results["mesh"] = mesh_file
        shutil.copy2(mesh_file, os.path.join(output_path, "final_mesh.ply"))
    
    # Create summary report
    summary = {
        "method": "COLMAP",
        "status": "completed",
        "files": results,
        "timestamp": time.time()
    }
    
    with open(os.path.join(output_path, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='COLMAP reconstruction engine')
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
        
        print(f"Starting COLMAP reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Set up workspace
        workspace_path = os.path.join(args.output, "colmap_workspace")
        os.makedirs(workspace_path, exist_ok=True)
        
        # Create symlink to images for COLMAP
        images_link = os.path.join(workspace_path, "images")
        if not os.path.exists(images_link):
            os.symlink(args.input, images_link)
        
        database_path = os.path.join(workspace_path, "database.db")
        sparse_path = os.path.join(workspace_path, "sparse")
        os.makedirs(sparse_path, exist_ok=True)
        
        # Run COLMAP pipeline
        extract_features(database_path, images_link, params)
        match_features(database_path, params)
        structure_from_motion(database_path, images_link, sparse_path, params)
        
        # Dense reconstruction (optional)
        if params.get('dense_reconstruction', True):
            dense_reconstruction(sparse_path, workspace_path, params)
            
            # Mesh generation (optional)
            if params.get('generate_mesh', True):
                fused_ply = os.path.join(workspace_path, "fused.ply")
                if os.path.exists(fused_ply):
                    poisson_meshing(fused_ply, workspace_path, params)
        
        # Organize results
        results = organize_results(workspace_path, args.output)
        
        print("COLMAP reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "COLMAP",
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
