#!/usr/bin/env python3
"""
Pan360 Stitching Comparison Tool
Runs multiple stitching algorithms by calling stitch_panorama.
Reads algorithm list from config.yaml
"""

import sys
import subprocess
import yaml
from pathlib import Path
from datetime import datetime


def load_config():
    """Load comparison algorithms from config.yaml"""
    config_path = Path("config") / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config.get('stitching', {}).get('compare_algorithms', ['opencv'])


def run_stitcher(algorithm, image_dir, output_path):
    """Run stitch_panorama with specified algorithm"""
    print(f"\n{'='*70}")
    print(f"Running: {algorithm}")
    print(f"{'='*70}")
    
    cmd = [
        sys.executable,
        "src/stitch_panorama.py",
        str(output_path),
        "--auto",
        "--image-dir", str(image_dir),
        "--algorithm", algorithm
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {algorithm} failed")
        return False


def main():
    """Main entry point for stitching comparison."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pan360 Stitching Comparison Tool")
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="Custom images directory (default: images/)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Pan360 - Panorama Stitching Comparison")
    print("=" * 70)
    
    # Load algorithms from config
    algorithms_to_test = load_config()
    
    print(f"\nAlgorithms from config.yaml: {', '.join(algorithms_to_test)}")
    
    # Get input images
    images_dir = args.images_dir if args.images_dir else Path("images")
    
    if not images_dir.exists():
        print(f"\n✗ Image directory not found: {images_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Algorithm names for display
    algorithm_names = {
        "opencv": "OpenCV Auto Stitcher",
        "sensor_aided": "Sensor-Aided Sequential Stitcher",
        "manual": "Manual Feature-Based Stitcher"
    }
    
    print(f"\nWill test {len(algorithms_to_test)} algorithm(s):")
    for i, alg in enumerate(algorithms_to_test, 1):
        print(f"  {i}. {algorithm_names.get(alg, alg)}")
    
    # Run each algorithm
    results = {}
    
    for alg in algorithms_to_test:
        output_path = output_dir / f"panorama_{alg}_{timestamp}.jpg"
        success = run_stitcher(alg, images_dir, output_path)
        results[alg] = {"success": success, "output": output_path if success else None}
    
    # Print summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    
    for alg, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"{status} {algorithm_names.get(alg, alg)}")
        if result["success"]:
            print(f"    Output: {result['output']}")
    
    print(f"\n{'='*70}")


if __name__ == "__main__":
    main()
