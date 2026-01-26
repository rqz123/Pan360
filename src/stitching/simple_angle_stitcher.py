"""
Simple 360° Stitcher
Uses known camera angles for placement (no homography needed).
Perfect for motorized panoramas where angles are precise.
"""

import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
from pathlib import Path
import re
from stitching.base_stitcher import BaseStitcher


class SimpleAngleStitcher(BaseStitcher):
    """
    Simple stitching using known angles from filenames.
    
    Best for: Motorized 360° panoramas with precise angles.
    No feature matching needed - uses geometry only.
    """
    
    def __init__(self, hfov: float = 54.0, blend_width: int = 50):
        """
        Initialize simple angle-based stitcher.
        
        Args:
            hfov: Horizontal field of view in degrees
            blend_width: Width of blending region in pixels
        """
        super().__init__("Simple Angle Stitcher")
        self.hfov = hfov
        self.blend_width = blend_width
    
    def _extract_angle(self, path: str) -> float:
        """Extract angle from filename like 'angle_045.jpg'."""
        match = re.search(r'angle_(\d+)', Path(path).name)
        if match:
            return float(match.group(1))
        return 0.0
    
    def _cylindrical_warp(self, img: np.ndarray, focal_length: float) -> np.ndarray:
        """Warp image to cylindrical coordinates."""
        h, w = img.shape[:2]
        
        # Create coordinate matrices
        y_i, x_i = np.indices((h, w), dtype=np.float32)
        
        # Convert to cylindrical coordinates
        x_c = (x_i - w / 2) / focal_length
        y_c = (y_i - h / 2) / focal_length
        
        # Convert to image coordinates
        x_warped = focal_length * np.arctan(x_c) + w / 2
        y_warped = focal_length * y_c / np.sqrt(x_c**2 + 1) + h / 2
        
        # Remap image
        warped = cv2.remap(
            img,
            x_warped.astype(np.float32),
            y_warped.astype(np.float32),
            cv2.INTER_LINEAR
        )
        
        return warped
    
    def stitch(self, image_paths: List[str]) -> Tuple[Optional[np.ndarray], dict]:
        """
        Stitch images using known angles.
        
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
            'hfov': self.hfov,
            'blend_width': self.blend_width,
            'status': 'processing'
        }
        
        try:
            # Load images with angles
            print(f"Loading {len(image_paths)} images...")
            images_data = []
            
            for i, path in enumerate(image_paths):
                img = cv2.imread(path)
                if img is None:
                    print(f"✗ Failed to load: {path}")
                    continue
                
                angle = self._extract_angle(path)
                images_data.append({'image': img, 'angle': angle, 'path': path})
                
                if (i + 1) % 5 == 0:
                    print(f"  Loaded {i + 1}/{len(image_paths)} images...")
            
            if len(images_data) < 2:
                print("✗ Need at least 2 valid images")
                stats['status'] = 'failed'
                return None, stats
            
            # Sort by angle
            images_data.sort(key=lambda x: x['angle'])
            print(f"✓ Loaded {len(images_data)} images")
            print(f"  Angle range: {images_data[0]['angle']}° to {images_data[-1]['angle']}°")
            
            # Get image dimensions
            h, w = images_data[0]['image'].shape[:2]
            
            # Calculate focal length from image width and HFOV
            focal_length = w / (2 * np.tan(np.radians(self.hfov / 2)))
            print(f"  Calculated focal length: {focal_length:.1f} pixels")
            
            # Apply cylindrical warping
            print("Applying cylindrical projection...")
            for i, data in enumerate(images_data):
                data['warped'] = self._cylindrical_warp(data['image'], focal_length)
                if (i + 1) % 5 == 0:
                    print(f"  Warped {i + 1}/{len(images_data)} images...")
            print("✓ Cylindrical projection complete")
            
            # Calculate canvas size
            # Pixels per degree
            pixels_per_degree = w / self.hfov
            total_angle = 360.0  # Full panorama
            canvas_width = int(pixels_per_degree * total_angle)
            canvas_height = h
            
            print(f"Creating panorama canvas: {canvas_width} x {canvas_height}")
            canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.float32)
            weight_map = np.zeros((canvas_height, canvas_width), dtype=np.float32)
            
            # Place each image on canvas
            print("Placing images on canvas with blending...")
            for i, data in enumerate(images_data):
                angle = data['angle']
                warped = data['warped'].astype(np.float32)
                
                # Calculate x position on canvas
                x_pos = int(angle * pixels_per_degree)
                
                # Handle wrap-around
                x_pos = x_pos % canvas_width
                
                print(f"  Image {i+1}: angle={angle}°, x_pos={x_pos}")
                
                # Create feather mask for blending
                mask = np.ones((h, w), dtype=np.float32)
                
                # Feather left edge
                for x in range(min(self.blend_width, w)):
                    mask[:, x] = x / self.blend_width
                
                # Feather right edge  
                for x in range(max(0, w - self.blend_width), w):
                    mask[:, x] = (w - x) / self.blend_width
                
                # Place image with wrapping
                for x in range(w):
                    canvas_x = (x_pos + x) % canvas_width
                    canvas[:, canvas_x:canvas_x+1] += warped[:, x:x+1] * mask[:, x:x+1, np.newaxis]
                    weight_map[:, canvas_x] += mask[:, x]
            
            print("✓ All images placed")
            
            # Normalize by weight map
            print("Normalizing and finalizing panorama...")
            weight_map[weight_map == 0] = 1  # Avoid division by zero
            canvas = canvas / weight_map[:, :, np.newaxis]
            panorama = canvas.astype(np.uint8)
            
            print(f"✓ Stitching complete!")
            stats['status'] = 'success'
            stats['panorama_shape'] = panorama.shape
            stats['panorama_size_mb'] = panorama.nbytes / (1024 * 1024)
            stats['canvas_width'] = canvas_width
            stats['pixels_per_degree'] = pixels_per_degree
            
            self.processing_time = time.time() - start_time
            self.stats = stats
            
            return panorama, stats
        
        except Exception as e:
            print(f"✗ Error during stitching: {e}")
            import traceback
            traceback.print_exc()
            stats['status'] = 'failed'
            stats['error'] = str(e)
            self.processing_time = time.time() - start_time
            self.stats = stats
            return None, stats
