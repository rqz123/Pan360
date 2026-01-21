#!/usr/bin/env python3
"""
Quick test script to verify camera functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from camera_controller import CameraController

def main():
    print("=== Pan360 Camera Test ===\n")
    
    # Use absolute path for output directory
    output_dir = Path(__file__).parent.parent / "images" / "test"
    print(f"Images will be saved to: {output_dir.absolute()}\n")
    
    print("Initializing camera...")
    camera = CameraController(
        resolution=(1640, 1232),  # Lower resolution for quick test
        output_dir=str(output_dir)
    )
    
    try:
        camera.initialize()
        
        print("\nTest 1: Capture single image")
        image_path = camera.capture(angle=0, session_id="camera_test")
        print(f"Image saved: {image_path}")
        
        input("\nPress Enter for next test...")
        
        print("\nTest 2: Capture 3 images")
        for i, angle in enumerate([0, 90, 180]):
            print(f"\nCapturing image {i+1}/3 at {angle}°")
            camera.capture(angle=angle, session_id="camera_test", settle_time=0.5)
        
        print("\n=== Camera test complete! ===")
        print("Check the images/test/ directory for captured images")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        camera.close()
        print("Camera cleanup complete")

if __name__ == "__main__":
    main()
