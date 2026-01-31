#!/usr/bin/env python3
"""
Two-Image Stress Test for Panorama Stitching
Debug tool to identify overlap, feature matching, and parallax issues
"""

import cv2
import numpy as np
import sys
from pathlib import Path
import argparse


def visualize_features(img1, img2, detector_type='orb', max_features=2000):
    """
    Visualize feature matching between two images
    
    Returns:
        matches_img: Image showing feature matches
        num_good_matches: Number of good matches found
    """
    print(f"\n{'='*70}")
    print(f"FEATURE MATCHING TEST ({detector_type.upper()})")
    print(f"{'='*70}")
    
    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Create detector
    if detector_type.lower() == 'orb':
        detector = cv2.ORB_create(nfeatures=max_features)
    elif detector_type.lower() == 'sift':
        detector = cv2.SIFT_create(nfeatures=max_features)
    elif detector_type.lower() == 'akaze':
        detector = cv2.AKAZE_create()
    else:
        print(f"Unknown detector: {detector_type}, using ORB")
        detector = cv2.ORB_create(nfeatures=max_features)
    
    # Detect and compute
    print(f"Detecting keypoints in image 1...")
    kp1, des1 = detector.detectAndCompute(gray1, None)
    print(f"  Found {len(kp1)} keypoints")
    
    print(f"Detecting keypoints in image 2...")
    kp2, des2 = detector.detectAndCompute(gray2, None)
    print(f"  Found {len(kp2)} keypoints")
    
    if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:
        print("✗ Not enough keypoints found!")
        return None, 0
    
    # Match features
    if detector_type.lower() in ['orb', 'akaze']:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    else:
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    
    print(f"Matching features...")
    matches = matcher.knnMatch(des1, des2, k=2)
    
    # Apply Lowe's ratio test
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
    
    print(f"  Total matches: {len(matches)}")
    print(f"  Good matches (Lowe's ratio test): {len(good_matches)}")
    
    # Analyze match quality
    if len(good_matches) < 4:
        print("✗ CRITICAL: Not enough good matches (<4)")
        print("  Possible causes:")
        print("  - Images don't overlap")
        print("  - Repetitive patterns (plain walls, grids)")
        print("  - Extreme lighting difference")
    elif len(good_matches) < 10:
        print("⚠ WARNING: Very few matches (<10)")
        print("  Stitching may be unreliable")
    elif len(good_matches) < 30:
        print("⚠ Marginal: Limited matches (<30)")
        print("  May work but not robust")
    else:
        print(f"✓ Good: {len(good_matches)} matches found")
    
    # Draw matches
    matches_img = cv2.drawMatches(
        img1, kp1, img2, kp2, good_matches[:100],  # Limit to 100 for clarity
        None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    )
    
    # Check for crossing matches (parallax indicator)
    if len(good_matches) >= 4:
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        # Check if matches preserve order (no crossing)
        y_diffs = pts2[:, 1] - pts1[:, 1]
        crossing_count = sum(abs(y_diffs) > 50)  # Vertical displacement > 50px
        
        if crossing_count > len(good_matches) * 0.2:
            print(f"⚠ WARNING: {crossing_count} matches have large vertical displacement")
            print("  This suggests parallax error (nodal point not aligned)")
    
    return matches_img, len(good_matches)


def test_cylindrical_warp(img1, img2, focal_length=None):
    """
    Test cylindrical warping on two images
    """
    print(f"\n{'='*70}")
    print("CYLINDRICAL WARP TEST")
    print(f"{'='*70}")
    
    if focal_length is None:
        # Estimate focal length from image width and FOV
        # Pi Camera V2: 54° HFOV
        hfov_deg = 54
        hfov_rad = np.radians(hfov_deg)
        focal_length = img1.shape[1] / (2 * np.tan(hfov_rad / 2))
        print(f"Estimated focal length: {focal_length:.1f}px (from 54° HFOV)")
    else:
        print(f"Using focal length: {focal_length:.1f}px")
    
    def cylindrical_warp(img, f):
        """Apply cylindrical projection"""
        h, w = img.shape[:2]
        K = np.array([[f, 0, w/2],
                      [0, f, h/2],
                      [0, 0, 1]])
        
        # Create coordinate arrays
        y_i, x_i = np.indices((h, w))
        X = np.stack([x_i, y_i, np.ones_like(x_i)], axis=-1).reshape(h*w, 3)
        
        # Inverse camera matrix
        Kinv = np.linalg.inv(K)
        X = Kinv.dot(X.T).T
        
        # Calculate cylindrical coordinates
        A = np.stack([np.sin(X[:, 0]), X[:, 1], np.cos(X[:, 0])], axis=-1).T
        B = K.dot(A).T
        
        # Normalize
        B = B[:, :-1] / B[:, [-1]]
        B = B.reshape(h, w, 2)
        
        # Remap
        warped = cv2.remap(img, B[:,:,0].astype(np.float32), 
                          B[:,:,1].astype(np.float32),
                          cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT)
        return warped
    
    print("Applying cylindrical warp to both images...")
    warped1 = cylindrical_warp(img1, focal_length)
    warped2 = cylindrical_warp(img2, focal_length)
    
    print("✓ Cylindrical warp applied")
    print("  Note: Warped images will have black borders")
    print("  This is normal - it's the 'unwrapping' of the lens distortion")
    
    return warped1, warped2


def test_opencv_stitcher(img1, img2, mode='panorama'):
    """
    Test OpenCV's built-in Stitcher on two images
    """
    print(f"\n{'='*70}")
    print(f"OPENCV AUTO STITCHER TEST (mode: {mode})")
    print(f"{'='*70}")
    
    if mode == 'scan':
        stitcher = cv2.Stitcher.create(cv2.Stitcher_SCANS)
    else:
        stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
    
    print("Attempting to stitch...")
    status, panorama = stitcher.stitch([img1, img2])
    
    status_names = {
        cv2.Stitcher_OK: "OK",
        cv2.Stitcher_ERR_NEED_MORE_IMGS: "NEED_MORE_IMGS",
        cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: "HOMOGRAPHY_EST_FAIL",
        cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "CAMERA_PARAMS_ADJUST_FAIL"
    }
    
    status_name = status_names.get(status, f"UNKNOWN({status})")
    
    if status == cv2.Stitcher_OK:
        print(f"✓ SUCCESS: Stitching completed!")
        print(f"  Output size: {panorama.shape[1]}x{panorama.shape[0]}px")
        return panorama
    else:
        print(f"✗ FAILED: {status_name}")
        
        if status == cv2.Stitcher_ERR_NEED_MORE_IMGS:
            print("  Cause: Not enough overlap or features")
            print("  Solution: Take images with more overlap")
        elif status == cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL:
            print("  Cause: Cannot find valid geometric transformation")
            print("  Solutions:")
            print("  - Check for parallax (nodal point alignment)")
            print("  - Ensure sufficient overlap (30-50%)")
            print("  - Try cylindrical warping first")
        elif status == cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL:
            print("  Cause: Camera parameter estimation failed")
            print("  Solutions:")
            print("  - Use SCANS mode instead of PANORAMA")
            print("  - Apply cylindrical warp manually first")
        
        return None


def create_side_by_side(img1, img2, overlap_pct=40):
    """
    Create a side-by-side comparison with transparency overlay
    """
    print(f"\n{'='*70}")
    print("MANUAL OVERLAP TEST")
    print(f"{'='*70}")
    
    h = max(img1.shape[0], img2.shape[0])
    w1, w2 = img1.shape[1], img2.shape[1]
    
    # Calculate overlap region
    overlap_px = int(w1 * overlap_pct / 100)
    
    print(f"Expected overlap: {overlap_pct}% = {overlap_px}px")
    print(f"Image 1: {w1}x{img1.shape[0]}px")
    print(f"Image 2: {w2}x{img2.shape[0]}px")
    
    # Create canvas
    total_width = w1 + w2 - overlap_px
    canvas = np.zeros((h, total_width, 3), dtype=np.uint8)
    
    # Place images
    canvas[:img1.shape[0], :w1] = img1
    
    # Blend in overlap region
    overlap_start = w1 - overlap_px
    for i in range(overlap_px):
        alpha = i / overlap_px
        x = overlap_start + i
        if x < w1 and i < w2:
            canvas[:img2.shape[0], x] = cv2.addWeighted(
                img1[:, w1-overlap_px+i],
                1-alpha,
                img2[:, i],
                alpha,
                0
            )
    
    # Place rest of image 2
    if overlap_px < w2:
        canvas[:img2.shape[0], w1:w1+(w2-overlap_px)] = img2[:, overlap_px:]
    
    print("✓ Created blended overlay")
    print("  Look for:")
    print("  - Smooth transitions in overlap region")
    print("  - No ghosting or doubling of objects")
    print("  - Straight lines remain straight (not curved)")
    
    return canvas


def main():
    parser = argparse.ArgumentParser(
        description="Two-Image Stress Test for Panorama Stitching"
    )
    parser.add_argument(
        "image1",
        type=Path,
        help="First image (left)"
    )
    parser.add_argument(
        "image2",
        type=Path,
        help="Second image (right)"
    )
    parser.add_argument(
        "--detector",
        choices=['orb', 'sift', 'akaze'],
        default='orb',
        help="Feature detector to use (default: orb)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("debug_output"),
        help="Output directory for debug images (default: debug_output)"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=40,
        help="Expected overlap percentage (default: 40)"
    )
    
    args = parser.parse_args()
    
    # Load images
    print(f"\n{'='*70}")
    print("TWO-IMAGE STRESS TEST")
    print(f"{'='*70}")
    print(f"Image 1: {args.image1}")
    print(f"Image 2: {args.image2}")
    
    img1 = cv2.imread(str(args.image1))
    img2 = cv2.imread(str(args.image2))
    
    if img1 is None or img2 is None:
        print("✗ Error: Could not load images")
        sys.exit(1)
    
    print(f"✓ Images loaded")
    print(f"  Image 1: {img1.shape[1]}x{img1.shape[0]}px")
    print(f"  Image 2: {img2.shape[1]}x{img2.shape[0]}px")
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test 1: Feature matching
    matches_img, num_matches = visualize_features(img1, img2, args.detector)
    if matches_img is not None:
        out_path = args.output_dir / f"01_features_{args.detector}.jpg"
        cv2.imwrite(str(out_path), matches_img)
        print(f"  Saved: {out_path}")
    
    # Test 2: Cylindrical warp
    warped1, warped2 = test_cylindrical_warp(img1, img2)
    cv2.imwrite(str(args.output_dir / "02_warped_img1.jpg"), warped1)
    cv2.imwrite(str(args.output_dir / "02_warped_img2.jpg"), warped2)
    print(f"  Saved: {args.output_dir}/02_warped_img*.jpg")
    
    # Test 3: Feature matching on warped images
    print("\nRe-testing feature matching on WARPED images...")
    matches_warped, num_matches_warped = visualize_features(warped1, warped2, args.detector)
    if matches_warped is not None:
        out_path = args.output_dir / f"03_features_warped_{args.detector}.jpg"
        cv2.imwrite(str(out_path), matches_warped)
        print(f"  Saved: {out_path}")
        
        improvement = num_matches_warped - num_matches
        if improvement > 0:
            print(f"✓ Cylindrical warp IMPROVED matching (+{improvement} matches)")
        elif improvement < 0:
            print(f"⚠ Cylindrical warp REDUCED matching ({improvement} matches)")
        else:
            print("= Cylindrical warp had no effect on matching")
    
    # Test 4: OpenCV Stitcher (original)
    result_pano = test_opencv_stitcher(img1, img2, mode='panorama')
    if result_pano is not None:
        cv2.imwrite(str(args.output_dir / "04_opencv_panorama.jpg"), result_pano)
        print(f"  Saved: {args.output_dir}/04_opencv_panorama.jpg")
    
    # Test 5: OpenCV Stitcher (scan mode)
    result_scan = test_opencv_stitcher(img1, img2, mode='scan')
    if result_scan is not None:
        cv2.imwrite(str(args.output_dir / "05_opencv_scan.jpg"), result_scan)
        print(f"  Saved: {args.output_dir}/05_opencv_scan.jpg")
    
    # Test 6: OpenCV Stitcher on warped images
    print(f"\n{'='*70}")
    print("OPENCV STITCHER ON WARPED IMAGES")
    print(f"{'='*70}")
    result_warped = test_opencv_stitcher(warped1, warped2, mode='scan')
    if result_warped is not None:
        cv2.imwrite(str(args.output_dir / "06_opencv_warped.jpg"), result_warped)
        print(f"  Saved: {args.output_dir}/06_opencv_warped.jpg")
    
    # Test 7: Manual overlap
    blend = create_side_by_side(img1, img2, args.overlap)
    cv2.imwrite(str(args.output_dir / "07_manual_blend.jpg"), blend)
    print(f"  Saved: {args.output_dir}/07_manual_blend.jpg")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Feature matches (original): {num_matches}")
    if matches_warped is not None:
        print(f"Feature matches (warped):   {num_matches_warped}")
    print(f"OpenCV panorama mode:       {'SUCCESS' if result_pano is not None else 'FAILED'}")
    print(f"OpenCV scan mode:           {'SUCCESS' if result_scan is not None else 'FAILED'}")
    print(f"OpenCV on warped:           {'SUCCESS' if result_warped is not None else 'FAILED'}")
    print(f"\nAll debug images saved to: {args.output_dir}/")
    print(f"{'='*70}")
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    if num_matches < 10:
        print("⚠ CRITICAL: Very few feature matches")
        print("  1. Check overlap - images may not overlap enough")
        print("  2. Avoid plain walls or repetitive patterns")
        print("  3. Try different angle_increment (more overlap)")
    elif matches_warped is not None and num_matches_warped > num_matches * 1.5:
        print("✓ Cylindrical warp significantly helped!")
        print("  Use cylindrical projection in your stitching pipeline")
    
    if result_pano is None and result_scan is None and result_warped is None:
        print("⚠ All OpenCV stitching failed")
        print("  This suggests a fundamental issue:")
        print("  1. Check nodal point alignment (parallax test)")
        print("  2. Verify overlap (should be 30-50%)")
        print("  3. Check image focus and sharpness")
    
    print("\nNext steps:")
    print("1. Review images in debug_output/ folder")
    print("2. Look at 01_features_*.jpg - are match lines crossing?")
    print("3. Look at 07_manual_blend.jpg - does overlap region look smooth?")
    print("4. If ghosting visible, adjust camera position for nodal point")


if __name__ == "__main__":
    main()
