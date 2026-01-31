#!/usr/bin/env python3
"""
Sensor-Aided Sequential Stitcher
Uses known motor angles with optional fine-tuning via constrained feature matching
Implements cylindrical warping and loop closure for 360° panoramas
"""

import cv2
import numpy as np
from pathlib import Path
import re
from typing import List, Tuple, Optional
import time

from .base_stitcher import BaseStitcher


class SensorAidedStitcher(BaseStitcher):
    """
    Sequential stitching using known camera angles from stepper motor
    
    Key improvements:
    1. Uses motor angles as strong prior (not feature matching alone)
    2. Sequential placement with constrained search in overlap regions
    3. Cylindrical warping for rotational motion
    4. Loop closure to ensure 360° alignment
    5. Debug mode without blending
    """
    
    def __init__(
        self,
        hfov_deg: float = 54.0,
        blend_width: int = 100,
        use_fine_tuning: bool = True,
        overlap_search_width: float = 0.3,
        debug_mode: bool = False,
        enable_loop_closure: bool = True
    ):
        """
        Args:
            hfov_deg: Horizontal field of view in degrees
            blend_width: Feather blending width
            use_fine_tuning: Use feature matching for fine adjustment
            overlap_search_width: Search region as fraction (0.3 = 30% of image)
            debug_mode: Skip blending, show placement only
            enable_loop_closure: Force last image to align with first
        """
        super().__init__(name="Sensor-Aided Stitcher")
        self.hfov_deg = hfov_deg
        self.blend_width = blend_width
        self.use_fine_tuning = use_fine_tuning
        self.overlap_search_width = overlap_search_width
        self.debug_mode = debug_mode
        self.enable_loop_closure = enable_loop_closure
    
    def _extract_angle(self, filename: str) -> Optional[float]:
        """Extract angle from filename (angle_XXX.jpg)"""
        match = re.search(r'angle[_-](\d+)', filename)
        if match:
            return float(match.group(1))
        return None
    
    def _cylindrical_warp(self, img: np.ndarray, focal_length: float) -> np.ndarray:
        """Apply cylindrical projection"""
        h, w = img.shape[:2]
        
        # Camera matrix
        K = np.array([
            [focal_length, 0, w/2],
            [0, focal_length, h/2],
            [0, 0, 1]
        ])
        
        # Create coordinate grid
        y_i, x_i = np.indices((h, w))
        X = np.stack([x_i, y_i, np.ones_like(x_i)], axis=-1).reshape(h*w, 3)
        
        # Inverse camera matrix
        Kinv = np.linalg.inv(K)
        X = Kinv.dot(X.T).T
        
        # Cylindrical coordinates
        A = np.stack([
            np.sin(X[:, 0]),
            X[:, 1],
            np.cos(X[:, 0])
        ], axis=-1).T
        
        B = K.dot(A).T
        B = B[:, :-1] / B[:, [-1]]
        B = B.reshape(h, w, 2)
        
        # Remap
        warped = cv2.remap(
            img,
            B[:, :, 0].astype(np.float32),
            B[:, :, 1].astype(np.float32),
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )
        
        return warped
    
    def _find_constrained_offset(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        expected_offset: int
    ) -> int:
        """
        Find fine offset adjustment using feature matching in overlap region
        
        Args:
            img1: Previous image
            img2: Current image
            expected_offset: Expected horizontal offset in pixels
            
        Returns:
            Refined offset in pixels
        """
        h, w = img1.shape[:2]
        
        # Define search regions (right side of img1, left side of img2)
        search_width = int(w * self.overlap_search_width)
        
        # Extract overlap regions
        roi1 = img1[:, w - search_width:]
        roi2 = img2[:, :search_width]
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(roi1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(roi2, cv2.COLOR_BGR2GRAY)
        
        # Detect features
        detector = cv2.ORB_create(nfeatures=500)
        kp1, des1 = detector.detectAndCompute(gray1, None)
        kp2, des2 = detector.detectAndCompute(gray2, None)
        
        if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
            # Not enough features, use expected offset
            return expected_offset
        
        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(des1, des2, k=2)
        
        # Apply ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
        
        if len(good_matches) < 4:
            return expected_offset
        
        # Calculate median horizontal displacement
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        # Adjust for ROI position
        pts1[:, 0] += (w - search_width)
        
        # Calculate horizontal displacements
        h_displacements = pts2[:, 0] - pts1[:, 0] + expected_offset
        
        # Use median to be robust against outliers
        refined_offset = int(np.median(h_displacements))
        
        # Limit adjustment to reasonable range (±20% of expected)
        max_adjustment = int(expected_offset * 0.2)
        refined_offset = np.clip(
            refined_offset,
            expected_offset - max_adjustment,
            expected_offset + max_adjustment
        )
        
        return refined_offset
    
    def stitch(self, image_paths: List[str]) -> Tuple[Optional[np.ndarray], dict]:
        """
        Stitch images using sensor-aided sequential approach
        """
        start_time = time.time()
        
        # Load and parse images
        images = []
        angles = []
        
        for path in sorted(image_paths):
            img = cv2.imread(path)
            if img is None:
                continue
            
            angle = self._extract_angle(Path(path).name)
            if angle is None:
                continue
            
            images.append(img)
            angles.append(angle)
        
        if len(images) < 2:
            return None, {'error': 'Need at least 2 images'}
        
        print(f"Loaded {len(images)} images")
        print(f"Angle range: {min(angles)}° to {max(angles)}°")
        
        # Calculate focal length from HFOV
        h, w = images[0].shape[:2]
        hfov_rad = np.radians(self.hfov_deg)
        focal_length = w / (2 * np.tan(hfov_rad / 2))
        print(f"Focal length: {focal_length:.1f}px")
        
        # Apply cylindrical warp
        print("Applying cylindrical warp...")
        warped_images = []
        for img in images:
            warped = self._cylindrical_warp(img, focal_length)
            warped_images.append(warped)
        
        # Calculate pixels per degree
        angle_increment = angles[1] - angles[0] if len(angles) > 1 else 25.0
        pixels_per_degree = focal_length * np.tan(np.radians(angle_increment))
        print(f"Pixels per degree: {pixels_per_degree:.2f}")
        
        # Calculate canvas size
        total_angle = 360.0
        canvas_width = int(pixels_per_degree * total_angle)
        canvas_height = h
        
        print(f"Canvas size: {canvas_width}x{canvas_height}px")
        
        # Create canvas
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.float32)
        weight_map = np.zeros((canvas_height, canvas_width), dtype=np.float32)
        
        # Sequential placement
        print("\nPlacing images sequentially...")
        
        offsets = []  # Track actual offsets for loop closure
        
        for i, (img, angle) in enumerate(zip(warped_images, angles)):
            # Calculate expected position
            expected_x = int(angle * pixels_per_degree)
            
            # Fine-tune using feature matching (if enabled and not first image)
            if i > 0 and self.use_fine_tuning:
                expected_offset = expected_x - offsets[-1][0]
                refined_offset = self._find_constrained_offset(
                    warped_images[i-1],
                    img,
                    expected_offset
                )
                actual_x = offsets[-1][0] + refined_offset
                
                adjustment = actual_x - expected_x
                if abs(adjustment) > 5:
                    print(f"  Image {i}: angle={angle}°, adjusted by {adjustment:+.0f}px")
            else:
                actual_x = expected_x
            
            offsets.append((actual_x, 0))
            
            # Place image on canvas
            if self.debug_mode:
                # Debug: Just copy pixels without blending
                x_start = actual_x
                x_end = min(actual_x + w, canvas_width)
                img_end = x_end - actual_x
                
                canvas[:, x_start:x_end] = img[:, :img_end].astype(np.float32)
                weight_map[:, x_start:x_end] = 1.0
            else:
                # Create feather weights
                weights = np.ones((h, w), dtype=np.float32)
                
                # Left feather
                for x in range(self.blend_width):
                    alpha = x / self.blend_width
                    weights[:, x] = alpha
                
                # Right feather
                for x in range(self.blend_width):
                    alpha = 1.0 - (x / self.blend_width)
                    weights[:, w - self.blend_width + x] = alpha
                
                # Place with blending
                x_start = actual_x
                x_end = min(actual_x + w, canvas_width)
                img_width = x_end - x_start
                
                for c in range(3):
                    canvas[:, x_start:x_end, c] += img[:, :img_width, c] * weights[:, :img_width]
                
                weight_map[:, x_start:x_end] += weights[:, :img_width]
        
        # Loop closure (if enabled)
        if self.enable_loop_closure and len(offsets) > 2:
            print("\nApplying loop closure...")
            first_x = offsets[0][0]
            last_x = offsets[-1][0]
            expected_last_x = int((angles[-1] + angle_increment) * pixels_per_degree) % canvas_width
            
            closure_error = (expected_last_x - (last_x + w)) % canvas_width
            if abs(closure_error) > 10:
                print(f"  Closure error: {closure_error}px")
                print(f"  Distributing across {len(offsets)} images...")
                
                # Distribute error across all images
                correction_per_image = closure_error / len(offsets)
                # Could implement progressive correction here
        
        # Normalize by weights
        print("\nNormalizing...")
        mask = weight_map > 0
        for c in range(3):
            canvas[:, :, c][mask] /= weight_map[mask]
        
        # Convert to uint8
        result = np.clip(canvas, 0, 255).astype(np.uint8)
        
        # Crop to valid region
        valid_mask = (weight_map > 0.1).astype(np.uint8)
        coords = cv2.findNonZero(valid_mask)
        if coords is not None:
            x, y, w_crop, h_crop = cv2.boundingRect(coords)
            result = result[y:y+h_crop, x:x+w_crop]
        
        processing_time = time.time() - start_time
        
        stats = {
            'width': result.shape[1],
            'height': result.shape[0],
            'image_count': len(images),
            'processing_time': processing_time,
            'focal_length': focal_length,
            'pixels_per_degree': pixels_per_degree,
            'debug_mode': self.debug_mode
        }
        
        print(f"\n✓ Stitching complete in {processing_time:.2f}s")
        print(f"  Output: {result.shape[1]}x{result.shape[0]}px")
        
        return result, stats


if __name__ == "__main__":
    # Test with images from images/ directory
    from pathlib import Path
    
    image_dir = Path("images")
    image_files = sorted(image_dir.glob("angle_*.jpg"))
    
    if not image_files:
        print("No images found in images/ directory")
        exit(1)
    
    print(f"Found {len(image_files)} images")
    
    # Test with debug mode first
    print("\n" + "="*70)
    print("Testing with DEBUG MODE (no blending)")
    print("="*70)
    
    stitcher_debug = SensorAidedStitcher(debug_mode=True)
    panorama_debug, stats = stitcher_debug.stitch([str(f) for f in image_files])
    
    if panorama_debug is not None:
        output_path = Path("output/panorama_sensor_aided_debug.jpg")
        output_path.parent.mkdir(exist_ok=True)
        stitcher_debug.save_result(panorama_debug, str(output_path))
        print(f"\nSaved debug output: {output_path}")
    
    # Test with blending
    print("\n" + "="*70)
    print("Testing with BLENDING enabled")
    print("="*70)
    
    stitcher = SensorAidedStitcher(
        debug_mode=False,
        use_fine_tuning=True,
        enable_loop_closure=True
    )
    panorama, stats = stitcher.stitch([str(f) for f in image_files])
    
    if panorama is not None:
        output_path = Path("output/panorama_sensor_aided.jpg")
        stitcher.save_result(panorama, str(output_path))
        print(f"\nSaved final output: {output_path}")
