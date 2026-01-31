#!/usr/bin/env python3
"""
Pan360 Upload Client
Uploads captured images to stitching server and retrieves results
"""

import requests
import time
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


class UploadClient:
    """Client for uploading images to Pan360 stitching server"""
    
    def __init__(self, server_url: str, timeout: int = 300):
        """
        Initialize upload client
        
        Args:
            server_url: Base URL of stitching server (e.g., http://192.168.1.100:8000)
            timeout: Maximum time to wait for stitching (seconds)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def check_server_health(self) -> bool:
        """Check if server is reachable and healthy"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "healthy"
        except Exception as e:
            print(f"Server health check failed: {e}")
            return False
    
    def list_algorithms(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of available stitching algorithms"""
        try:
            response = self.session.get(f"{self.server_url}/api/v1/algorithms", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("algorithms", [])
        except Exception as e:
            print(f"Failed to list algorithms: {e}")
            return None
    
    def upload_images(
        self,
        image_paths: List[Path],
        algorithm: str = "simple_angle",
        blend_width: int = 100,
        confidence_threshold: float = 1.0
    ) -> Optional[str]:
        """
        Upload images for stitching
        
        Args:
            image_paths: List of image file paths
            algorithm: Stitching algorithm to use
            blend_width: Blending width for simple_angle
            confidence_threshold: Confidence threshold for opencv_auto
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # Prepare files for upload
            files = []
            for img_path in image_paths:
                if not img_path.exists():
                    print(f"Warning: Image not found: {img_path}")
                    continue
                files.append(
                    ('files', (img_path.name, open(img_path, 'rb'), 'image/jpeg'))
                )
            
            if not files:
                print("Error: No valid images to upload")
                return None
            
            print(f"Uploading {len(files)} images to {self.server_url}...")
            
            # Upload with parameters
            data = {
                'algorithm': algorithm,
                'blend_width': blend_width,
                'confidence_threshold': confidence_threshold
            }
            
            response = self.session.post(
                f"{self.server_url}/api/v1/upload",
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            
            # Close file handles
            for _, file_tuple in files:
                file_tuple[1].close()
            
            result = response.json()
            job_id = result.get("job_id")
            
            print(f"✓ Upload successful! Job ID: {job_id}")
            print(f"  Status: {result.get('message')}")
            
            return job_id
            
        except requests.exceptions.RequestException as e:
            print(f"Upload failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during upload: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a stitching job"""
        try:
            response = self.session.get(
                f"{self.server_url}/api/v1/status/{job_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get job status: {e}")
            return None
    
    def wait_for_completion(self, job_id: str, poll_interval: int = 2) -> Optional[Dict[str, Any]]:
        """
        Wait for job to complete, showing progress
        
        Args:
            job_id: Job ID to monitor
            poll_interval: Seconds between status checks
            
        Returns:
            Final job status if successful, None if failed or timeout
        """
        start_time = time.time()
        last_progress = -1
        
        print(f"Waiting for job {job_id} to complete...")
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > self.timeout:
                print(f"\n✗ Timeout after {self.timeout}s")
                return None
            
            status = self.get_job_status(job_id)
            if not status:
                time.sleep(poll_interval)
                continue
            
            job_status = status.get("status")
            progress = status.get("progress", 0)
            message = status.get("message", "")
            
            # Show progress update
            if progress != last_progress:
                print(f"  [{progress:3d}%] {message}")
                last_progress = progress
            
            # Check terminal states
            if job_status == "completed":
                print(f"✓ Stitching completed in {elapsed:.1f}s")
                if status.get("stats"):
                    stats = status["stats"]
                    if "width" in stats and "height" in stats:
                        print(f"  Output: {stats['width']}x{stats['height']}px")
                    if "processing_time" in stats:
                        print(f"  Server processing: {stats['processing_time']:.1f}s")
                return status
            
            elif job_status == "failed":
                print(f"✗ Stitching failed: {message}")
                return None
            
            # Still processing
            time.sleep(poll_interval)
    
    def download_result(self, job_id: str, output_path: Path) -> bool:
        """
        Download stitched panorama result
        
        Args:
            job_id: Job ID
            output_path: Path to save result
            
        Returns:
            True if successful
        """
        try:
            print(f"Downloading result to {output_path}...")
            
            response = self.session.get(
                f"{self.server_url}/api/v1/download/{job_id}",
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"✓ Downloaded: {output_path.name} ({size_mb:.2f} MB)")
                return True
            else:
                print("✗ Download failed: file not created")
                return False
                
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def upload_and_stitch(
        self,
        image_paths: List[Path],
        output_path: Path,
        algorithm: str = "simple_angle",
        blend_width: int = 100,
        confidence_threshold: float = 1.0
    ) -> bool:
        """
        Complete workflow: upload, wait, download
        
        Args:
            image_paths: List of image files to stitch
            output_path: Where to save result
            algorithm: Stitching algorithm
            blend_width: Blending width for simple_angle
            confidence_threshold: Confidence threshold for opencv_auto
            
        Returns:
            True if entire process successful
        """
        # Check server
        if not self.check_server_health():
            print("✗ Server is not available")
            return False
        
        # Upload
        job_id = self.upload_images(
            image_paths,
            algorithm=algorithm,
            blend_width=blend_width,
            confidence_threshold=confidence_threshold
        )
        
        if not job_id:
            return False
        
        # Wait for completion
        result = self.wait_for_completion(job_id)
        
        if not result:
            return False
        
        # Download
        return self.download_result(job_id, output_path)


def main():
    """Command-line interface for upload client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload images to Pan360 stitching server")
    parser.add_argument(
        "images",
        nargs="*",
        type=Path,
        help="Image files to upload (if not specified, auto-discovers latest from images/)"
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("images"),
        help="Directory to search for images (default: images/)"
    )
    parser.add_argument(
        "--server",
        default="http://192.168.5.138:8000",
        help="Server URL (default: http://192.168.5.138:8000)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: auto-generated with algorithm name)"
    )
    parser.add_argument(
        "--algorithm",
        choices=["simple_angle", "opencv_auto", "manual"],
        default="simple_angle",
        help="Stitching algorithm"
    )
    parser.add_argument(
        "--blend-width",
        type=int,
        default=100,
        help="Blending width for simple_angle (default: 100)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum wait time in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    # Auto-discover images if not specified
    if not args.images:
        print(f"No images specified, searching in {args.images_dir}...")
        
        # Look for angle_*.jpg pattern
        image_paths = sorted(args.images_dir.glob("angle_*.jpg"))
        
        if not image_paths:
            # Fallback to any .jpg files
            image_paths = sorted(args.images_dir.glob("*.jpg"))
        
        if not image_paths:
            print(f"✗ No images found in {args.images_dir}")
            print(f"  Please specify image files or check the directory path")
            sys.exit(1)
        
        print(f"✓ Found {len(image_paths)} images")
        args.images = image_paths
    
    # Create client
    client = UploadClient(args.server, timeout=args.timeout)
    
    # Auto-generate output filename if not specified
    if args.output is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = output_dir / f"panorama_{args.algorithm}_{timestamp}.jpg"
    
    # Process
    success = client.upload_and_stitch(
        args.images,
        args.output,
        algorithm=args.algorithm,
        blend_width=args.blend_width
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
