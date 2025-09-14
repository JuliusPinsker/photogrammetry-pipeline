from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import uuid
import time
import psutil
import shutil
import json
from pathlib import Path

from .reconstruction_manager import ReconstructionManager
from .gpu_detector import GPUDetector

app = FastAPI(
    title="3D Reconstruction API",
    description="Compare 5 non-neural 3D reconstruction tools",
    version="1.0.0"
)

# Global instances
reconstruction_manager = ReconstructionManager()
gpu_detector = GPUDetector()

# Models
class ReconstructionRequest(BaseModel):
    tools: List[str]
    maxResolution: int = 2048
    dataset: Optional[str] = None
    resolution: str = "images"

class ToolStatus(BaseModel):
    status: str
    progress: int
    output: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

class JobStatus(BaseModel):
    jobId: str
    status: str
    tools: Dict[str, ToolStatus]

# Job storage
active_jobs: Dict[str, JobStatus] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/gpu-status")
async def get_gpu_status():
    """Get GPU availability and information."""
    return gpu_detector.get_status()

@app.get("/dataset/{dataset_name}/{resolution}")
async def get_dataset_images(dataset_name: str, resolution: str):
    """Get list of images in a dataset folder."""
    dataset_path = Path(f"/datasets/{dataset_name}/{resolution}")
    
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    images = []
    
    for file_path in dataset_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            images.append({
                "name": file_path.name,
                "path": str(file_path.relative_to(Path("/datasets"))),
                "size": file_path.stat().st_size
            })
    
    return {"dataset": dataset_name, "resolution": resolution, "images": images}

@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload images for reconstruction."""
    upload_id = str(uuid.uuid4())
    upload_dir = Path(f"/tmp/uploads/{upload_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        if not file.content_type.startswith('image/'):
            continue
            
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        uploaded_files.append({
            "name": file.filename,
            "path": str(file_path),
            "size": len(content)
        })
    
    return {"upload_id": upload_id, "files": uploaded_files}

@app.delete("/revert")
async def revert_upload(upload_id: str):
    """Remove uploaded files."""
    upload_dir = Path(f"/tmp/uploads/{upload_id}")
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    return {"status": "success"}

@app.post("/reconstruct")
async def start_reconstruction(
    request: ReconstructionRequest,
    background_tasks: BackgroundTasks
):
    """Start reconstruction process with selected tools."""
    job_id = str(uuid.uuid4())
    
    # Validate tools
    supported_tools = ["COLMAP", "OpenMVS", "PMVS2", "AliceVision", "OpenSfM"]
    invalid_tools = [tool for tool in request.tools if tool not in supported_tools]
    if invalid_tools:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported tools: {invalid_tools}"
        )
    
    # Initialize job status
    job_status = JobStatus(
        jobId=job_id,
        status="starting",
        tools={
            tool: ToolStatus(status="waiting", progress=0)
            for tool in request.tools
        }
    )
    active_jobs[job_id] = job_status
    
    # Start reconstruction in background
    background_tasks.add_task(
        run_reconstruction,
        job_id,
        request
    )
    
    return {"jobId": job_id, "status": "started"}

@app.get("/status/{job_id}")
async def get_reconstruction_status(job_id: str):
    """Get reconstruction progress and status."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return active_jobs[job_id]

@app.get("/results/{job_id}")
async def get_reconstruction_results(job_id: str):
    """Get final reconstruction results."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = active_jobs[job_id]
    if job_status.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    return job_status

async def run_reconstruction(job_id: str, request: ReconstructionRequest):
    """Background task to run reconstruction process."""
    job_status = active_jobs[job_id]
    job_status.status = "running"
    
    try:
        # Prepare input data
        if request.dataset:
            # Use pre-loaded dataset
            input_path = f"/datasets/{request.dataset}/{request.resolution}"
        else:
            # Use uploaded images (would need upload_id from request)
            input_path = "/tmp/uploads/latest"  # Simplified for demo
        
        # Run each tool
        results = {}
        for tool in request.tools:
            tool_status = job_status.tools[tool]
            tool_status.status = "running"
            tool_status.progress = 0
            
            try:
                # Run reconstruction tool
                result = await reconstruction_manager.run_tool(
                    tool=tool,
                    input_path=input_path,
                    output_path=f"/results/{job_id}/{tool.lower()}",
                    max_resolution=request.maxResolution,
                    progress_callback=lambda p: setattr(tool_status, 'progress', p)
                )
                
                tool_status.status = "completed"
                tool_status.progress = 100
                tool_status.output = result["output_file"]
                tool_status.metrics = result["metrics"]
                
                results[tool] = result
                
            except Exception as e:
                tool_status.status = "failed"
                tool_status.progress = 0
                print(f"Tool {tool} failed: {str(e)}")
        
        # Check if all tools completed successfully
        all_completed = all(
            status.status == "completed" 
            for status in job_status.tools.values()
        )
        
        job_status.status = "completed" if all_completed else "partial"
        
    except Exception as e:
        job_status.status = "failed"
        print(f"Reconstruction job {job_id} failed: {str(e)}")

@app.get("/tools")
async def get_available_tools():
    """Get list of available reconstruction tools and their status."""
    return reconstruction_manager.get_tool_status()

@app.get("/system-info")
async def get_system_info():
    """Get system information for debugging."""
    gpu_info = gpu_detector.get_status()
    
    return {
        "gpu": gpu_info,
        "cpu": {
            "cores": psutil.cpu_count(),
            "usage": psutil.cpu_percent(interval=1)
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
            "free": psutil.disk_usage("/").free,
            "percent": psutil.disk_usage("/").percent
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)