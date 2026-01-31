#!/usr/bin/env python3
"""
Pan360 Stitching Server
REST API server for processing panorama stitching jobs from Pi clients
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import sys
import uuid
import shutil
import time
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path to import stitching modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stitching import OpenCVAutoStitcher, ManualStitcher, SensorAidedStitcher

app = FastAPI(
    title="Pan360 Stitching Server",
    description="Panorama stitching service for Pan360 clients",
    version="1.0.0"
)

# Enable CORS for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path(__file__).parent / "uploads"
OUTPUT_DIR = Path(__file__).parent / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Job status tracking
jobs = {}

class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    progress: Optional[int] = 0
    message: Optional[str] = ""
    result_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    stats: Optional[dict] = None


class StitchingRequest(BaseModel):
    algorithm: str = "simple_angle"  # simple_angle, opencv_auto, manual
    blend_width: Optional[int] = 100
    confidence_threshold: Optional[float] = 1.0


def process_stitching_job(job_id: str, algorithm: str, blend_width: int, confidence_threshold: float):
    """Background task to process stitching"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Loading images..."
        
        # Load images
        job_dir = UPLOAD_DIR / job_id
        image_files = sorted(job_dir.glob("*.jpg"))
        
        if not image_files:
            raise ValueError("No images found in upload")
        
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = f"Found {len(image_files)} images, initializing stitcher..."
        
        # Initialize stitcher
        if algorithm == "sensor_aided":
            stitcher = SensorAidedStitcher(
                blend_width=blend_width,
                debug_mode=False,
                use_fine_tuning=True
            )
        elif algorithm == "opencv_auto":
            stitcher = OpenCVAutoStitcher(confidence_threshold=confidence_threshold)
        elif algorithm == "manual":
            stitcher = ManualStitcher()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        jobs[job_id]["progress"] = 30
        jobs[job_id]["message"] = f"Stitching with {algorithm}..."
        
        # Stitch
        start_time = time.time()
        panorama, stats = stitcher.stitch([str(f) for f in image_files])
        processing_time = time.time() - start_time
        
        if panorama is None:
            raise ValueError(f"Stitching failed: {stats.get('error', 'Unknown error')}")
        
        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Saving result..."
        
        # Save result
        output_file = OUTPUT_DIR / f"{job_id}_panorama.jpg"
        stitcher.save_result(panorama, str(output_file))
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Stitching completed successfully"
        jobs[job_id]["result_url"] = f"/api/v1/download/{job_id}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["stats"] = {
            **stats,
            "processing_time": processing_time,
            "image_count": len(image_files)
        }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Pan360 Stitching Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "upload": "/api/v1/upload",
            "status": "/api/v1/status/{job_id}",
            "download": "/api/v1/download/{job_id}",
            "jobs": "/api/v1/jobs"
        }
    }


@app.post("/api/v1/upload")
async def upload_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    algorithm: str = "simple_angle",
    blend_width: int = 100,
    confidence_threshold: float = 1.0
):
    """
    Upload images for stitching
    
    - **files**: List of image files (JPG)
    - **algorithm**: Stitching algorithm (simple_angle, opencv_auto, manual)
    - **blend_width**: Blending width for simple_angle (default: 100)
    - **confidence_threshold**: Confidence threshold for opencv_auto (default: 1.0)
    """
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Save uploaded files
    try:
        for file in files:
            file_path = job_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save files: {str(e)}")
    
    # Create job entry
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Job queued for processing",
        "result_url": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "stats": None,
        "algorithm": algorithm,
        "image_count": len(files)
    }
    
    # Start background processing
    background_tasks.add_task(
        process_stitching_job,
        job_id,
        algorithm,
        blend_width,
        confidence_threshold
    )
    
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "message": f"Uploaded {len(files)} images, job queued",
            "status_url": f"/api/v1/status/{job_id}"
        }
    )


@app.get("/api/v1/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a stitching job"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/api/v1/download/{job_id}")
async def download_result(job_id: str):
    """Download stitched panorama result"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed (status: {jobs[job_id]['status']})"
        )
    
    result_file = OUTPUT_DIR / f"{job_id}_panorama.jpg"
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        result_file,
        media_type="image/jpeg",
        filename="panorama.jpg"
    )


@app.get("/api/v1/jobs")
async def list_jobs(limit: int = 50):
    """List recent jobs"""
    
    # Sort by creation time, most recent first
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )
    
    return {"jobs": sorted_jobs[:limit], "total": len(jobs)}


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete files
    job_dir = UPLOAD_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    
    result_file = OUTPUT_DIR / f"{job_id}_panorama.jpg"
    if result_file.exists():
        result_file.unlink()
    
    # Remove from jobs
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}


@app.get("/api/v1/algorithms")
async def list_algorithms():
    """List available stitching algorithms"""
    
    return {
        "algorithms": [
            {
                "id": "simple_angle",
                "name": "Simple Angle Stitcher",
                "description": "Uses known camera angles for geometric stitching",
                "parameters": {
                    "blend_width": {"type": "int", "default": 100, "description": "Feather blending width"}
                },
                "recommended": True
            },
            {
                "id": "opencv_auto",
                "name": "OpenCV Auto Stitcher",
                "description": "OpenCV high-level automatic stitcher",
                "parameters": {
                    "confidence_threshold": {"type": "float", "default": 1.0, "description": "Matching confidence"}
                },
                "recommended": False
            },
            {
                "id": "manual",
                "name": "Manual Pipeline Stitcher",
                "description": "Manual feature-based stitching pipeline",
                "parameters": {},
                "recommended": False
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": sum(1 for j in jobs.values() if j["status"] in ["queued", "processing"]),
        "total_jobs": len(jobs)
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pan360 Stitching Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"Starting Pan360 Stitching Server on {args.host}:{args.port}")
    print(f"Uploads: {UPLOAD_DIR.resolve()}")
    print(f"Results: {OUTPUT_DIR.resolve()}")
    
    uvicorn.run(
        "stitching_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
