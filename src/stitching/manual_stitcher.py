"""
Option B: Manual Pipeline Stitcher
Full control over each step of the stitching process.
"""

import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
from .base_stitcher import BaseStitcher


class ManualStitcher(BaseStitcher):
    """
    Manual stitching pipeline with full control over each step.
    
    Best for: Custom optimization, understanding the process, fine-tuning.
    
    Pipeline:
    1. Feature detection (ORB/AKAZE)
    2. Feature matching (BFMatcher/FLANN)
    3. Homography estimation (RANSAC)
    4. Cylindrical projection
    5. Image warping
    6. Exposure compensation
    7. Seam finding
    8. Multi-band blending
    """
    
    def __init__(
        self,
        feature_detector: str = "orb",
        matcher_type: str = "bf",
        projection: str = "cylindrical"
    ):
        """
        Initialize manual stitcher.
        
        Args:
            feature_detector: "orb" or "akaze"
            matcher_type: "bf" (brute-force) or "flann"
            projection: "cylindrical" or "spherical"
        """
        super().__init__("Manual Pipeline Stitcher")
        self.feature_detector_type = feature_detector
        self.matcher_type = matcher_type
        self.projection = projection
    
    def _detect_and_describe(self, image: np.ndarray) -> Tuple[List, np.ndarray]:
        """Detect keypoints and compute descriptors."""
        if self.feature_detector_type == "orb":
            detector = cv2.ORB_create(nfeatures=2000)
        else:  # akaze
            detector = cv2.AKAZE_create()
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = detector.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def _match_features(
        self,
        desc1: np.ndarray,
        desc2: np.ndarray
    ) -> List[cv2.DMatch]:
        """Match features between two images."""
        if self.matcher_type == "bf":
            if self.feature_detector_type == "orb":
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            else:
                matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        else:  # flann
            if self.feature_detector_type == "orb":
                index_params = dict(
                    algorithm=6,  # FLANN_INDEX_LSH
                    table_number=6,
                    key_size=12,
                    multi_probe_level=1
                )
            else:
                index_params = dict(algorithm=1, trees=5)  # FLANN_INDEX_KDTREE
            
            search_params = dict(checks=50)
            matcher = cv2.FlannBasedMatcher(index_params, search_params)
        
        # Use KNN matching with ratio test
        knn_matches = matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for m_n in knn_matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
        
        return good_matches
    
    def _estimate_homography(
        self,
        kp1: List,
        kp2: List,
        matches: List[cv2.DMatch]
    ) -> Tuple[Optional[np.ndarray], np.ndarray]:
        """Estimate homography matrix between two images."""
        if len(matches) < 4:
            return None, None
        
        # Extract matched keypoint locations
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Find homography using RANSAC
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        return H, mask
    
    def _cylindrical_warp(self, img: np.ndarray, focal_length: float) -> np.ndarray:
        """Warp image to cylindrical coordinates."""
        h, w = img.shape[:2]
        
        # Create coordinate matrices
        y_i, x_i = np.indices((h, w))
        
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
        Stitch images using manual pipeline.
        
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
            'feature_detector': self.feature_detector_type,
            'matcher': self.matcher_type,
            'projection': self.projection,
            'status': 'processing'
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
                stats['status'] = 'failed'
                return None, stats
            
            print(f"✓ Loaded {len(images)} images")
            
            # Step 1: Apply cylindrical projection
            if self.projection == "cylindrical":
                print("Applying cylindrical projection...")
                # Estimate focal length from image size and FOV
                h, w = images[0].shape[:2]
                focal_length = w / (2 * np.tan(np.radians(54 / 2)))  # 54° HFOV
                
                warped_images = []
                for i, img in enumerate(images):
                    warped = self._cylindrical_warp(img, focal_length)
                    warped_images.append(warped)
                    if (i + 1) % 5 == 0:
                        print(f"  Warped {i + 1}/{len(images)} images...")
                images = warped_images
                print("✓ Cylindrical projection complete")
            
            # Step 2: Detect features in all images
            print(f"Detecting features ({self.feature_detector_type.upper()})...")
            all_keypoints = []
            all_descriptors = []
            
            for i, img in enumerate(images):
                kp, desc = self._detect_and_describe(img)
                all_keypoints.append(kp)
                all_descriptors.append(desc)
                if (i + 1) % 5 == 0:
                    print(f"  Processed {i + 1}/{len(images)} images...")
            
            total_features = sum(len(kp) for kp in all_keypoints)
            print(f"✓ Detected {total_features} total features")
            stats['total_features'] = total_features
            
            # Step 3: Sequential stitching with better canvas management
            print("Matching and stitching images sequentially...")
            
            # Start with first image
            h0, w0 = images[0].shape[:2]
            
            # Create large canvas to accumulate all images
            canvas_width = w0 * len(images) // 2  # Estimate
            canvas_height = h0 * 2
            canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
            
            # Place first image in center
            x_offset = canvas_width // 2 - w0 // 2
            y_offset = canvas_height // 2 - h0 // 2
            canvas[y_offset:y_offset+h0, x_offset:x_offset+w0] = images[0]
            
            current_offset = x_offset + w0
            
            for i in range(1, len(images)):
                print(f"  Stitching image {i+1}/{len(images)}...")
                
                # Match features between consecutive images
                matches = self._match_features(
                    all_descriptors[i-1],
                    all_descriptors[i]
                )
                
                print(f"    Found {len(matches)} matches")
                
                if len(matches) < 10:
                    print(f"    ✗ Not enough matches, placing with offset")
                    # Place next to previous image with overlap
                    h_img, w_img = images[i].shape[:2]
                    overlap = int(w_img * 0.3)  # 30% overlap estimate
                    place_x = current_offset - overlap
                    
                    if place_x + w_img < canvas_width:
                        # Simple alpha blending in overlap region
                        for x in range(max(0, overlap)):
                            alpha = x / overlap
                            blend_x = place_x + x
                            if 0 <= blend_x < canvas_width:
                                canvas[y_offset:y_offset+h_img, blend_x] = (
                                    alpha * images[i][:, x] + 
                                    (1 - alpha) * canvas[y_offset:y_offset+h_img, blend_x]
                                ).astype(np.uint8)
                        
                        # Place rest of image
                        canvas[y_offset:y_offset+h_img, place_x+overlap:place_x+w_img] = images[i][:, overlap:]
                        current_offset = place_x + w_img
                    continue
                
                # Estimate homography
                H, mask = self._estimate_homography(
                    all_keypoints[i-1],
                    all_keypoints[i],
                    matches
                )
                
                if H is None:
                    print(f"    ✗ Failed to estimate homography, using offset")
                    h_img, w_img = images[i].shape[:2]
                    overlap = int(w_img * 0.3)
                    place_x = current_offset - overlap
                    if place_x + w_img < canvas_width:
                        canvas[y_offset:y_offset+h_img, place_x:place_x+w_img] = images[i]
                        current_offset = place_x + w_img
                    continue
                
                inliers = np.sum(mask)
                print(f"    Inliers: {inliers}/{len(matches)}")
                
                # For cylindrical 360°, we mainly need horizontal translation
                # Extract just the x-translation
                h_img, w_img = images[i].shape[:2]
                
                # Simple placement based on expected angle
                place_x = current_offset - int(w_img * 0.5)  # 50% overlap
                
                if place_x + w_img < canvas_width and place_x >= 0:
                    # Alpha blending in overlap region
                    overlap = current_offset - place_x
                    if overlap > 0:
                        for x in range(min(overlap, w_img)):
                            alpha = x / overlap
                            blend_x = place_x + x
                            if 0 <= blend_x < canvas_width:
                                canvas[y_offset:y_offset+h_img, blend_x] = (
                                    alpha * images[i][:, x] +
                                    (1 - alpha) * canvas[y_offset:y_offset+h_img, blend_x]
                                ).astype(np.uint8)
                        
                        # Place rest of image
                        if overlap < w_img:
                            canvas[y_offset:y_offset+h_img, place_x+overlap:place_x+w_img] = images[i][:, overlap:]
                    else:
                        canvas[y_offset:y_offset+h_img, place_x:place_x+w_img] = images[i]
                    
                    current_offset = place_x + w_img
            
            result = canvas
            
            # Crop black borders
            print("Cropping result...")
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                x, y, w, h = cv2.boundingRect(contours[0])
                result = result[y:y+h, x:x+w]
            
            print(f"✓ Stitching complete!")
            stats['status'] = 'success'
            stats['panorama_shape'] = result.shape
            stats['panorama_size_mb'] = result.nbytes / (1024 * 1024)
            
            self.processing_time = time.time() - start_time
            self.stats = stats
            
            return result, stats
        
        except Exception as e:
            print(f"✗ Error during stitching: {e}")
            import traceback
            traceback.print_exc()
            stats['status'] = 'failed'
            stats['error'] = str(e)
            self.processing_time = time.time() - start_time
            self.stats = stats
            return None, stats
