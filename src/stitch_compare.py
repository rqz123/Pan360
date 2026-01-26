#!/usr/bin/env python3
"""
Pan360 Stitching Comparison Tool
Runs multiple stitching algorithms and compares results.
"""

import sys
import glob
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from stitching import OpenCVAutoStitcher, ManualStitcher, SimpleAngleStitcher


def main():
    """Main entry point for stitching comparison."""
    print("=" * 70)
    print("Pan360 - Panorama Stitching Comparison")
    print("=" * 70)
    
    # Get input images
    images_dir = Path(__file__).parent.parent / "images"
    image_pattern = str(images_dir / "angle_*.jpg")
    image_paths = sorted(glob.glob(image_pattern))
    
    if not image_paths:
        print(f"\n✗ No images found matching: {image_pattern}")
        print(f"  Please run pan360.py first to capture images")
        sys.exit(1)
    
    print(f"\nFound {len(image_paths)} images to stitch")
    print(f"Image directory: {images_dir}")
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Define stitchers to compare
    stitchers = [
        SimpleAngleStitcher(hfov=54.0, blend_width=100),  # New: angle-based
        OpenCVAutoStitcher(mode="panorama"),
        ManualStitcher(feature_detector="orb", matcher_type="bf", projection="cylindrical"),
        # Add more stitchers here in the future:
        # ManualStitcher(feature_detector="akaze", matcher_type="flann", projection="spherical"),
        # OpticalFlowStitcher(),  # Future
        # DeepLearningStitcher(),  # Future
    ]
    
    print(f"\nWill test {len(stitchers)} stitching algorithms:")
    for i, stitcher in enumerate(stitchers, 1):
        print(f"  {i}. {stitcher.name}")
    
    # Run each stitcher
    results = []
    
    for i, stitcher in enumerate(stitchers, 1):
        print(f"\n{'='*70}")
        print(f"Algorithm {i}/{len(stitchers)}: {stitcher.name}")
        print('='*70)
        
        # Stitch
        panorama, stats = stitcher.stitch(image_paths)
        
        # Save result
        if panorama is not None:
            # Generate output filename
            safe_name = stitcher.name.lower().replace(' ', '_').replace('-', '_')
            output_path = output_dir / f"panorama_{safe_name}_{timestamp}.jpg"
            
            success = stitcher.save_result(panorama, str(output_path))
            
            if success:
                results.append({
                    'name': stitcher.name,
                    'output_path': output_path,
                    'processing_time': stitcher.processing_time,
                    'stats': stats,
                    'success': True
                })
        else:
            results.append({
                'name': stitcher.name,
                'output_path': None,
                'processing_time': stitcher.processing_time,
                'stats': stats,
                'success': False
            })
        
        # Print stats
        print(stitcher.get_stats_summary())
    
    # Final comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        print(f"\n✓ Successful: {len(successful)}/{len(results)}")
        print("\nResults (sorted by processing time):")
        successful.sort(key=lambda x: x['processing_time'])
        
        for i, result in enumerate(successful, 1):
            print(f"\n{i}. {result['name']}")
            print(f"   Time: {result['processing_time']:.2f}s")
            print(f"   Output: {result['output_path']}")
            if 'panorama_shape' in result['stats']:
                h, w = result['stats']['panorama_shape'][:2]
                print(f"   Size: {w} x {h} pixels")
    
    if failed:
        print(f"\n✗ Failed: {len(failed)}/{len(results)}")
        for result in failed:
            print(f"   - {result['name']}")
            if 'error' in result['stats']:
                print(f"     Error: {result['stats']['error']}")
    
    print("\n" + "=" * 70)
    print("Comparison complete!")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    # Tips for next steps
    if successful:
        print("\nNext steps:")
        print("1. View the panoramas to compare quality")
        print("2. Choose the best algorithm for your needs")
        print("3. Fine-tune parameters in the chosen algorithm")
        print("\nFuture enhancements:")
        print("- Add optical flow stitching")
        print("- Implement deep learning methods (UDIS, GANs)")
        print("- Add quality metrics for automatic comparison")


if __name__ == "__main__":
    main()
