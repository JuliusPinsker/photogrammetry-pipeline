from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import json
import shutil
import uuid
import time
from typing import List, Optional
import docker
import redis
from pydantic import BaseModel
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Photogrammetry Pipeline API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATA_PATH = os.getenv("DATA_PATH", "/app/data")
RESULTS_PATH = os.getenv("RESULTS_PATH", "/app/results")
SCENES_PATH = os.getenv("SCENES_PATH", "/app/360_scenes")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Ensure directories exist
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(RESULTS_PATH, exist_ok=True)

# Redis connection
try:
    redis_client = redis.from_url(REDIS_URL)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to connect to Docker: {e}")
    docker_client = None

# Available photogrammetry methods
METHODS = {
    "meshroom": {
        "name": "Meshroom",
        "description": "Traditional SfM with robust feature matching",
        "type": "traditional",
        "gpu_required": False,
        "estimated_time": "2-4 hours",
        "quality": "very_high",
        "mobile_compatible": False
    },
    "colmap": {
        "name": "COLMAP",
        "description": "State-of-the-art Structure-from-Motion",
        "type": "traditional", 
        "gpu_required": False,
        "estimated_time": "1-3 hours",
        "quality": "very_high",
        "mobile_compatible": False
    },
    "openmvg": {
        "name": "OpenMVG/MVS",
        "description": "Modular multi-view geometry library",
        "type": "traditional",
        "gpu_required": False, 
        "estimated_time": "1-2 hours",
        "quality": "high",
        "mobile_compatible": False
    },
    "instant-ngp": {
        "name": "Instant-NGP",
        "description": "Fast neural radiance fields with hash encoding",
        "type": "neural",
        "gpu_required": True,
        "estimated_time": "10-30 minutes",
        "quality": "high",
        "mobile_compatible": False
    },
    "gaussian-splatting": {
        "name": "3D Gaussian Splatting", 
        "description": "Real-time neural rendering with explicit 3D representation",
        "type": "neural",
        "gpu_required": True,
        "estimated_time": "15-45 minutes", 
        "quality": "very_high",
        "mobile_compatible": False
    },
    "mobilenerf": {
        "name": "MobileNeRF",
        "description": "Mobile-optimized neural radiance fields",
        "type": "neural",
        "gpu_required": False,
        "estimated_time": "5-15 minutes",
        "quality": "medium",
        "mobile_compatible": True
    },
    "pifuhd": {
        "name": "PIFuHD",
        "description": "High-resolution human digitization from single images",
        "type": "specialized",
        "gpu_required": True,
        "estimated_time": "30-60 minutes",
        "quality": "high", 
        "mobile_compatible": False
    }
}

# Data models
class JobStatus(BaseModel):
    job_id: str
    method: str
    status: str  # queued, running, completed, failed
    progress: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    result_files: Optional[List[str]] = None

@app.get("/")
async def root():
    return {"message": "Photogrammetry Pipeline API", "version": "1.0.0"}

@app.get("/methods")
async def get_methods():
    """Get available photogrammetry methods with their characteristics"""
    return {"methods": METHODS}

@app.get("/datasets")
async def get_datasets():
    """Get available test datasets from 360_scenes"""
    datasets = []
    if os.path.exists(SCENES_PATH):
        for scene_name in os.listdir(SCENES_PATH):
            scene_path = os.path.join(SCENES_PATH, scene_name)
            if os.path.isdir(scene_path):
                images_path = os.path.join(scene_path, "images")
                if os.path.exists(images_path):
                    image_count = len([f for f in os.listdir(images_path) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                    datasets.append({
                        "name": scene_name,
                        "path": scene_path,
                        "image_count": image_count,
                        "has_poses": os.path.exists(os.path.join(scene_path, "poses_bounds.npy"))
                    })
    return {"datasets": datasets}

@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload images for reconstruction"""
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(DATA_PATH, job_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if file.content_type and file.content_type.startswith('image/'):
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            uploaded_files.append(file.filename)
    
    return {
        "job_id": job_id,
        "uploaded_files": uploaded_files,
        "file_count": len(uploaded_files)
    }

@app.post("/reconstruct")
async def start_reconstruction(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    method: str = Form(...),
    dataset_name: Optional[str] = Form(None),
    parameters: Optional[str] = Form("{}")
):
    """Start reconstruction process"""
    
    if method not in METHODS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
    
    # Determine input directory
    if dataset_name:
        input_dir = os.path.join(SCENES_PATH, dataset_name, "images")
        if not os.path.exists(input_dir):
            raise HTTPException(status_code=400, detail=f"Dataset not found: {dataset_name}")
    else:
        input_dir = os.path.join(DATA_PATH, job_id)
        if not os.path.exists(input_dir):
            raise HTTPException(status_code=400, detail=f"Job data not found: {job_id}")
    
    # Create unique reconstruction job ID
    reconstruction_id = f"{job_id}_{method}_{int(time.time())}"
    
    # Parse parameters
    try:
        params = json.loads(parameters)
    except:
        params = {}
    
    # Store job info in Redis
    if redis_client:
        job_info = {
            "job_id": reconstruction_id,
            "method": method,
            "status": "queued",
            "progress": 0.0,
            "start_time": time.time(),
            "input_dir": input_dir,
            "parameters": params
        }
        redis_client.set(f"job:{reconstruction_id}", json.dumps(job_info), ex=3600*24)  # 24h expiry
    
    # Start reconstruction in background
    background_tasks.add_task(run_reconstruction, reconstruction_id, method, input_dir, params)
    
    return {
        "reconstruction_id": reconstruction_id,
        "method": method,
        "status": "queued",
        "estimated_time": METHODS[method]["estimated_time"]
    }

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get reconstruction job status"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    job_data = redis_client.get(f"job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = json.loads(job_data)
    return JobStatus(**job_info)

@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get reconstruction results"""
    result_dir = os.path.join(RESULTS_PATH, job_id)
    if not os.path.exists(result_dir):
        raise HTTPException(status_code=404, detail="Results not found")
    
    # List result files
    result_files = []
    for root, dirs, files in os.walk(result_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), result_dir)
            result_files.append(rel_path)
    
    return {
        "job_id": job_id,
        "result_files": result_files,
        "result_dir": result_dir
    }

@app.get("/download/{job_id}/{file_path:path}")
async def download_result(job_id: str, file_path: str):
    """Download a specific result file"""
    full_path = os.path.join(RESULTS_PATH, job_id, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=full_path,
        filename=os.path.basename(file_path),
        media_type='application/octet-stream'
    )

async def run_reconstruction(job_id: str, method: str, input_dir: str, parameters: dict):
    """Run reconstruction using specified method"""
    try:
        # Update status to running
        if redis_client:
            job_info = json.loads(redis_client.get(f"job:{job_id}") or "{}")
            job_info.update({"status": "running", "progress": 0.1})
            redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=3600*24)
        
        # Create output directory
        output_dir = os.path.join(RESULTS_PATH, job_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Run the appropriate Docker container
        if docker_client:
            container_name = f"photogrammetry-pipeline-{method}-1"
            
            # Check if container exists and is running
            try:
                container = docker_client.containers.get(container_name)
                if container.status != 'running':
                    container.start()
            except docker.errors.NotFound:
                # Start the service if container doesn't exist
                logger.warning(f"Container {container_name} not found. Please ensure it's running.")
                raise Exception(f"Engine container {method} not available")
            
            # Execute reconstruction command in container
            exec_result = container.exec_run(
                f"python /workspace/reconstruct.py --input {input_dir} --output {output_dir} --params '{json.dumps(parameters)}'",
                workdir="/workspace"
            )
            
            # Update progress
            if redis_client:
                job_info = json.loads(redis_client.get(f"job:{job_id}") or "{}")
                job_info.update({"status": "processing", "progress": 0.5})
                redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=3600*24)
            
            if exec_result.exit_code == 0:
                # Success
                result_files = []
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), output_dir)
                        result_files.append(rel_path)
                
                if redis_client:
                    job_info = json.loads(redis_client.get(f"job:{job_id}") or "{}")
                    job_info.update({
                        "status": "completed",
                        "progress": 1.0,
                        "end_time": time.time(),
                        "result_files": result_files
                    })
                    redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=3600*24)
            else:
                # Failure
                error_msg = exec_result.output.decode('utf-8') if exec_result.output else "Unknown error"
                if redis_client:
                    job_info = json.loads(redis_client.get(f"job:{job_id}") or "{}")
                    job_info.update({
                        "status": "failed",
                        "end_time": time.time(),
                        "error_message": error_msg
                    })
                    redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=3600*24)
        else:
            raise Exception("Docker client not available")
            
    except Exception as e:
        logger.error(f"Reconstruction failed for job {job_id}: {e}")
        if redis_client:
            job_info = json.loads(redis_client.get(f"job:{job_id}") or "{}")
            job_info.update({
                "status": "failed",
                "end_time": time.time(),
                "error_message": str(e)
            })
            redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=3600*24)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
