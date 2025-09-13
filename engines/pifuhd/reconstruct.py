#!/usr/bin/env python3
"""
PIFuHD reconstruction engine for the photogrammetry pipeline.
Specialized for human digitization from single or few images.
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
import cv2

def preprocess_images(input_dir, output_dir, params):
    """Preprocess images for PIFuHD (human detection, segmentation, etc.)"""
    
    print("Preprocessing images for PIFuHD...")
    
    processed_dir = os.path.join(output_dir, "processed_images")
    os.makedirs(processed_dir, exist_ok=True)
    
    # Find image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(input_dir).glob(f"*{ext}"))
        image_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
    
    if not image_files:
        raise Exception(f"No images found in {input_dir}")
    
    processed_files = []
    
    for img_file in image_files:
        print(f"Processing {img_file.name}...")
        
        # Load image
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        
        # Resize to appropriate size for PIFuHD (typically 512x512)
        target_size = params.get('image_size', 512)
        
        # Maintain aspect ratio
        h, w = img.shape[:2]
        if h > w:
            new_h = target_size
            new_w = int(w * target_size / h)
        else:
            new_w = target_size
            new_h = int(h * target_size / w)
        
        img_resized = cv2.resize(img, (new_w, new_h))
        
        # Pad to square
        pad_x = (target_size - new_w) // 2
        pad_y = (target_size - new_h) // 2
        
        img_padded = cv2.copyMakeBorder(
            img_resized, 
            pad_y, target_size - new_h - pad_y,
            pad_x, target_size - new_w - pad_x,
            cv2.BORDER_CONSTANT, 
            value=[128, 128, 128]  # Gray padding
        )
        
        # Save processed image
        output_file = os.path.join(processed_dir, img_file.name)
        cv2.imwrite(output_file, img_padded)
        processed_files.append(output_file)
    
    print(f"Processed {len(processed_files)} images")
    return processed_files, processed_dir

def segment_humans(processed_dir, output_dir, params):
    """Segment human figures using built-in or external segmentation"""
    
    print("Segmenting human figures...")
    
    # This would typically use a human segmentation model
    # For demonstration, we'll create a simple mask
    
    mask_dir = os.path.join(output_dir, "masks")
    os.makedirs(mask_dir, exist_ok=True)
    
    image_files = list(Path(processed_dir).glob("*.jpg")) + list(Path(processed_dir).glob("*.png"))
    
    for img_file in image_files:
        # Create a simple center mask (in practice, use proper segmentation)
        img = cv2.imread(str(img_file))
        h, w = img.shape[:2]
        
        # Simple elliptical mask for human shape
        mask = np.zeros((h, w), dtype=np.uint8)
        center_x, center_y = w // 2, h // 2
        cv2.ellipse(mask, (center_x, center_y), (w//3, h//2), 0, 0, 360, 255, -1)
        
        mask_file = os.path.join(mask_dir, f"{img_file.stem}_mask.png")
        cv2.imwrite(mask_file, mask)
    
    return mask_dir

def run_pifuhd_reconstruction(processed_dir, mask_dir, output_dir, params):
    """Run PIFuHD reconstruction"""
    
    print("Running PIFuHD reconstruction...")
    
    # Change to PIFuHD directory
    pifuhd_dir = "/opt/pifuhd"
    os.chdir(pifuhd_dir)
    
    # Find processed images
    image_files = sorted(list(Path(processed_dir).glob("*.jpg")) + list(Path(processed_dir).glob("*.png")))
    
    if not image_files:
        raise Exception("No processed images found for reconstruction")
    
    results = []
    
    for img_file in image_files:
        print(f"Reconstructing {img_file.name}...")
        
        # Prepare output for this image
        img_output_dir = os.path.join(output_dir, f"result_{img_file.stem}")
        os.makedirs(img_output_dir, exist_ok=True)
        
        # PIFuHD command
        cmd = [
            "python3", "-m", "apps.simple_test",
            "-c", "checkpoints/pifuhd.pt",
            "-i", str(img_file),
            "-o", img_output_dir,
            "--resolution", str(params.get('resolution', 512))
        ]
        
        # Add mask if available
        mask_file = os.path.join(mask_dir, f"{img_file.stem}_mask.png")
        if os.path.exists(mask_file):
            cmd.extend(["-m", mask_file])
        
        # Add additional parameters
        if params.get('use_rect', True):
            cmd.append("--use_rect")
        
        if params.get('hd_mode', True):
            cmd.append("--hd")
        
        # Run reconstruction
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=params.get('timeout_per_image', 600)
        )
        
        if result.returncode != 0:
            print(f"PIFuHD failed for {img_file.name}: {result.stderr}")
            continue
        
        results.append(img_output_dir)
        print(f"Completed reconstruction for {img_file.name}")
    
    if not results:
        raise Exception("All PIFuHD reconstructions failed")
    
    print(f"Successfully reconstructed {len(results)} images")
    return results

def post_process_meshes(result_dirs, output_dir, params):
    """Post-process generated meshes"""
    
    print("Post-processing meshes...")
    
    final_meshes = []
    
    for result_dir in result_dirs:
        # Find generated PLY files
        ply_files = list(Path(result_dir).glob("*.ply"))
        
        for ply_file in ply_files:
            # Copy to main output directory with descriptive name
            result_name = f"human_mesh_{Path(result_dir).name}.ply"
            final_path = os.path.join(output_dir, result_name)
            shutil.copy2(str(ply_file), final_path)
            final_meshes.append(final_path)
    
    # Optionally combine multiple meshes if there are several
    if len(final_meshes) > 1 and params.get('combine_meshes', False):
        try:
            import trimesh
            combined_mesh = trimesh.Trimesh()
            
            for mesh_file in final_meshes:
                mesh = trimesh.load(mesh_file)
                combined_mesh += mesh
            
            combined_path = os.path.join(output_dir, "combined_human_mesh.ply")
            combined_mesh.export(combined_path)
            final_meshes.append(combined_path)
            
        except ImportError:
            print("Trimesh not available for mesh combination")
        except Exception as e:
            print(f"Failed to combine meshes: {e}")
    
    return final_meshes

def create_visualization(output_dir, mesh_files, params):
    """Create visualization of the reconstruction results"""
    
    print("Creating visualization...")
    
    viz_dir = os.path.join(output_dir, "visualization")
    os.makedirs(viz_dir, exist_ok=True)
    
    # Create simple HTML viewer for meshes
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>PIFuHD Results</title>
    <script src="https://threejs.org/build/three.min.js"></script>
    <script src="https://threejs.org/examples/js/loaders/PLYLoader.js"></script>
    <script src="https://threejs.org/examples/js/controls/OrbitControls.js"></script>
    <style>
        body { margin: 0; overflow: hidden; }
        canvas { display: block; }
    </style>
</head>
<body>
    <div id="container"></div>
    <script>
        // Basic Three.js setup for viewing PLY files
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer();
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.getElementById('container').appendChild(renderer.domElement);
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040);
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(1, 1, 1);
        scene.add(directionalLight);
        
        // Controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        
        camera.position.z = 5;
        
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
"""
    
    with open(os.path.join(viz_dir, "viewer.html"), 'w') as f:
        f.write(html_content)
    
    return viz_dir

def organize_results(output_dir, mesh_files, result_dirs):
    """Organize PIFuHD output files"""
    
    print("Organizing reconstruction results...")
    
    results = {
        "meshes": mesh_files,
        "individual_results": result_dirs,
        "visualization": None
    }
    
    # Visualization
    viz_dir = os.path.join(output_dir, "visualization")
    if os.path.exists(viz_dir):
        results["visualization"] = viz_dir
    
    # Create summary report
    summary = {
        "method": "PIFuHD",
        "status": "completed",
        "files": results,
        "timestamp": time.time(),
        "specialization": "human_digitization",
        "mesh_count": len(mesh_files)
    }
    
    with open(os.path.join(output_dir, "reconstruction_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='PIFuHD reconstruction engine')
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
        
        print(f"Starting PIFuHD reconstruction")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Parameters: {params}")
        
        # Preprocess images
        processed_files, processed_dir = preprocess_images(args.input, args.output, params)
        
        # Segment humans
        mask_dir = segment_humans(processed_dir, args.output, params)
        
        # Run PIFuHD reconstruction
        result_dirs = run_pifuhd_reconstruction(processed_dir, mask_dir, args.output, params)
        
        # Post-process meshes
        mesh_files = post_process_meshes(result_dirs, args.output, params)
        
        # Create visualization
        create_visualization(args.output, mesh_files, params)
        
        # Organize results
        results = organize_results(args.output, mesh_files, result_dirs)
        
        print("PIFuHD reconstruction completed successfully")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Create error summary
        error_summary = {
            "method": "PIFuHD",
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
