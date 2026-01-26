"""
Option A: OpenCV High-Level Automatic Stitcher
Uses OpenCV's built-in Stitcher class with automatic feature detection,
matching, and blending.
"""

import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
from .base_stitcher import BaseStitcher


class OpenCVAutoStitcher(BaseStitcher):
    """
    Automatic stitching using OpenCV's high-level Stitcher API.
    
    Best for: Quick results, reliable stitching with minimal tuning.
    """
    
    def __init__(self, mode: str = "panorama"):
        """
        Initialize OpenCV automatic stitcher.
        
        Args:
            mode: Stitching mode - "panorama" (default) or "scans"
                  panorama mode is optimized for 360° panoramas
        """
        super().__init__("OpenCV Auto Stitcher")
        self.mode = mode
    
    def stitch(self, image_paths: List[str]) -> Tuple[Optional[np.ndarray], dict]:
        """
        Stitch images using OpenCV's automatic stitcher.
        
        Args:
            image_paths: List of paths to input images
        
        Returns:
            Tuple of (panorama, stats)
        """
        print(f"\n{'='*60}")
        print(f"{self.name} - Starting")
        print('='*60)
        
        start_time = time.time()
        stats = {
            'num_images': len(image_paths),
            'mode': self.mode,
            'status': 'unknown'
        }
        
        try:
            # Load images
            print(f"Loading {len(image_paths)} images...")
            images = []
            for i, path in enumerate(image_paths):
                img = cv2.imread(path)
                if img is None:
                    print(f"✗ Failed to load: {path}")
                    continue
                images.append(img)
                if (i + 1) % 5 == 0:
                    print(f"  Loaded {i + 1}/{len(image_paths)} images...")
            
            if len(images) < 2:
                print("✗ Need at least 2 valid images")
                return None, stats
            
            stats['images_loaded'] = len(images)
            print(f"✓ Loaded {len(images)} images")
            
            # Create stitcher
            print(f"Creating stitcher (mode: {self.mode})...")
            if self.mode == "panorama":
                stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
            else:
                stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
            
            # Configure stitcher for better results
            # Use ORB for feature detection (patent-free)
            # stitcher.setFeaturesFinder(cv2.ORB_create(nfeatures=500))
            
            print("Stitching images...")
            print("  - Detecting features...")
            print("  - Matching features...")
            print("  - Estimating camera parameters...")
            print("  - Warping images...")
            print("  - Blending...")
            
            # Perform stitching
            status, panorama = stitcher.stitch(images)
            
            # Check status
            status_messages = {
                cv2.Stitcher_OK: "Success",
                cv2.Stitcher_ERR_NEED_MORE_IMGS: "Need more images",
                cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: "Homography estimation failed",
                cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "Camera parameters adjustment failed"
            }
            
            status_msg = status_messages.get(status, f"Unknown error ({status})")
            stats['status'] = status_msg
            
            if status == cv2.Stitcher_OK:
                print(f"✓ Stitching successful!")
                stats['panorama_shape'] = panorama.shape
                stats['panorama_size_mb'] = panorama.nbytes / (1024 * 1024)
                
                self.processing_time = time.time() - start_time
                self.stats = stats
                
                return panorama, stats
            else:
                print(f"✗ Stitching failed: {status_msg}")
                self.processing_time = time.time() - start_time
                self.stats = stats
                return None, stats
        
        except Exception as e:
            print(f"✗ Error during stitching: {e}")
            import traceback
            traceback.print_exc()
            stats['error'] = str(e)
            self.processing_time = time.time() - start_time
            self.stats = stats
            return None, stats
