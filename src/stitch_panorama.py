#!/usr/bin/env python3
"""
Unified panorama stitcher - combines sequential and windowed approaches.
Starts with two-image stitching, then incrementally adds images using windowed method.
"""

import cv2
import numpy as np
import sys
import yaml
from pathlib import Path
import argparse


def load_config():
    """Load stitching configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config.get('stitching', {
        'algorithm': 'opencv',
        'window_ratio': 0.7,
        'stop_on_failure': True
    })


def stitch_two_images(img1_path, img2_path, algorithm='opencv'):
    """Stitch two images using specified algorithm"""
    print(f"\n{'='*70}")
    print(f"INITIAL PAIR: {Path(img1_path).name} + {Path(img2_path).name}")
    print(f"Algorithm: {algorithm}")
    print(f"{'='*70}")
    
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    
    if img1 is None or img2 is None:
        print("❌ Failed to load images")
        return None
    
    print(f"Image 1: {img1.shape[1]}x{img1.shape[0]}px")
    print(f"Image 2: {img2.shape[1]}x{img2.shape[0]}px")
    
    if algorithm == 'opencv':
        print("Stitching with OpenCV...")
        stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
        status, panorama = stitcher.stitch([img1, img2])
        
        if status != cv2.Stitcher_OK:
            print(f"❌ Stitching failed with status: {status}")
            return None
    else:
        print(f"❌ Algorithm '{algorithm}' not supported for initial pair")
        return None
    
    print(f"✓ Success! Result: {panorama.shape[1]}x{panorama.shape[0]}px")
    return panorama


def add_image_windowed(panorama, new_image_path, window_ratio=0.7):
    """Add a new image to panorama using windowed approach"""
    print(f"\n{'='*70}")
    print(f"ADDING: {Path(new_image_path).name}")
    print(f"{'='*70}")
    
    new_img = cv2.imread(str(new_image_path))
    
    if new_img is None:
        print("❌ Failed to load new image")
        return None
    
    pano_h, pano_w = panorama.shape[:2]
    new_h, new_w = new_img.shape[:2]
    
    print(f"Current panorama: {pano_w}x{pano_h}px")
    print(f"New image: {new_w}x{new_h}px")
    
    # Extract window from right side
    window_width = int(new_w * window_ratio)
    window_start = pano_w - window_width
    window = panorama[:, window_start:].copy()
    
    print(f"Window: {window.shape[1]}px ({window_ratio*100:.0f}% of image width)")
    
    # Stitch window + new image
    print("Stitching window + new image...")
    stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
    status, stitched = stitcher.stitch([window, new_img])
    
    if status != cv2.Stitcher_OK:
        print(f"❌ Stitching failed with status: {status}")
        return None
    
    stitched_h, stitched_w = stitched.shape[:2]
    print(f"Stitched: {stitched_w}x{stitched_h}px")
    
    # Calculate new portion
    new_portion_width = stitched_w - window.shape[1]
    
    if new_portion_width <= 0:
        print(f"❌ No new content added")
        return None
    
    print(f"New content: {new_portion_width}px")
    
    # Extract new portion
    new_portion = stitched[:, window.shape[1]:].copy()
    
    # Extend panorama
    final_w = pano_w + new_portion_width
    final_h = max(pano_h, new_portion.shape[0])
    
    final = np.zeros((final_h, final_w, 3), dtype=np.uint8)
    final[:pano_h, :pano_w] = panorama
    final[:new_portion.shape[0], pano_w:final_w] = new_portion
    
    print(f"✓ Success! Result: {final_w}x{final_h}px")
    return final


def discover_images(image_dir="images"):
    """Discover and sort angle images from directory"""
    image_path = Path(image_dir)
    
    if not image_path.exists():
        print(f"❌ Image directory not found: {image_dir}")
        return []
    
    # Find all angle_*.jpg files
    image_files = sorted(image_path.glob("angle_*.jpg"))
    
    if not image_files:
        print(f"❌ No angle_*.jpg files found in {image_dir}")
        return []
    
    print(f"Found {len(image_files)} images in {image_dir}")
    return [str(f) for f in image_files]


def stitch_panorama(image_paths, output_path, config, save_steps=False):
    """
    Stitch multiple images into a panorama.
    Uses sequential approach for first two images, then windowed approach for rest.
    
    Args:
        image_paths: List of image paths to stitch
        output_path: Final output path
        config: Configuration dictionary
        save_steps: If True, save intermediate results after each step
    """
    if len(image_paths) < 2:
        print("❌ Need at least 2 images to stitch")
        return False
    
    print(f"\n{'#'*70}")
    print(f"# PANORAMA STITCHING")
    print(f"# Images: {len(image_paths)}")
    print(f"# Algorithm: {config['algorithm']}")
    print(f"# Window ratio: {config['window_ratio']}")
    print(f"# Output: {output_path}")
    if save_steps:
        print(f"# Saving intermediate steps: YES")
    print(f"{'#'*70}")
    
    # Prepare output directory for steps
    if save_steps:
        output_dir = Path(output_path).parent
        step_dir = output_dir / "steps"
        step_dir.mkdir(exist_ok=True)
        print(f"Step outputs will be saved to: {step_dir}")
    
    # Start with first two images
    panorama = stitch_two_images(image_paths[0], image_paths[1], config['algorithm'])
    
    if panorama is None:
        print(f"\n❌ Failed at initial pair")
        return False
    
    # Save step 1
    if save_steps:
        step1_path = step_dir / f"step_01_{Path(image_paths[1]).stem}.jpg"
        cv2.imwrite(str(step1_path), panorama)
        print(f"Saved step 1: {step1_path}")
    
    # Add remaining images one by one
    for i, img_path in enumerate(image_paths[2:], start=3):
        panorama = add_image_windowed(panorama, img_path, config['window_ratio'])
        
        if panorama is None:
            print(f"\n❌ Failed at image {i}/{len(image_paths)}: {Path(img_path).name}")
            if config['stop_on_failure']:
                print("Stopping due to failure")
                return False
            else:
                print("Skipping and continuing...")
                continue
        
        # Save intermediate step
        if save_steps:
            step_path = step_dir / f"step_{i:02d}_{Path(img_path).stem}.jpg"
            cv2.imwrite(str(step_path), panorama)
            print(f"Saved step {i}: {step_path}")
    
    # Save final result
    print(f"\n{'='*70}")
    print(f"SAVING RESULT")
    print(f"{'='*70}")
    print(f"Final size: {panorama.shape[1]}x{panorama.shape[0]}px")
    print(f"Output: {output_path}")
    
    cv2.imwrite(str(output_path), panorama)
    
    print(f"\n✓ COMPLETE! Panorama saved to {output_path}")
    if save_steps:
        print(f"✓ Intermediate steps saved to {step_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Unified panorama stitcher with sequential and windowed approaches'
    )
    parser.add_argument('output', help='Output panorama path')
    parser.add_argument('images', nargs='*', help='Input images in order (optional if using --auto)')
    parser.add_argument('--auto', action='store_true', help='Auto-discover images from images/ folder')
    parser.add_argument('--image-dir', default='images', help='Image directory for auto-discovery (default: images)')
    parser.add_argument('--window-ratio', type=float, help='Window ratio (0.5-1.0), overrides config')
    parser.add_argument('--algorithm', choices=['opencv', 'sensor_aided', 'manual'], 
                        help='Stitching algorithm (overrides config)')
    parser.add_argument('--save-steps', action='store_true', 
                        help='Save intermediate results after each step')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Override with command line if provided
    if args.window_ratio:
        config['window_ratio'] = args.window_ratio
    if args.algorithm:
        config['algorithm'] = args.algorithm
    
    # Get image list
    if args.auto or not args.images:
        print("Auto-discovering images...")
        image_paths = discover_images(args.image_dir)
    else:
        image_paths = args.images
    
    if not image_paths:
        print("❌ No images to stitch")
        sys.exit(1)
    
    # Stitch
    success = stitch_panorama(image_paths, args.output, config, save_steps=args.save_steps)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
