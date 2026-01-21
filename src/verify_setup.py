#!/usr/bin/env python3
"""
Simple verification script to test Pan360 setup without hardware.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Pan360 Setup Verification")
print("=" * 60)

# Test 1: Configuration
print("\n[1/4] Testing configuration...")
try:
    from config import Config
    # Use absolute path
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    config = Config(str(config_path))
    print(f"  ✓ Config loaded")
    print(f"  ✓ Output directory: {config.camera_output_dir}")
    print(f"  ✓ Motor pins: {config.motor_pins}")
    print(f"  ✓ Camera resolution: {config.camera_resolution}")
    print(f"  ✓ Angle increment: {config.angle_increment}°")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 2: Camera Controller (module import)
print("\n[2/4] Testing camera controller module...")
try:
    from camera_controller import CameraController
    print(f"  ✓ Camera controller module loaded")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Motor Controller (module import)
print("\n[3/4] Testing motor controller module...")
try:
    from stepper_motor import StepperMotor
    print(f"  ✓ Motor controller module loaded")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 4: Output directory
print("\n[4/4] Testing output directory...")
try:
    output_path = Path(config.camera_output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.is_dir():
        print(f"  ✓ Output directory exists: {output_path}")
        print(f"  ✓ Directory is writable: {output_path.stat().st_mode & 0o200 != 0}")
    else:
        print(f"  ✗ Output directory not accessible")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All checks passed!")
print("=" * 60)
print("\nYour Pan360 system is ready!")
print("\nNext steps:")
print("1. Wire the stepper motor to GPIO pins:", config.motor_pins)
print("2. Run: python3 src/test_motor.py (tests motor)")
print("3. Run: python3 src/test_camera.py (tests camera)")
print("4. Run: python3 src/pan360.py (full panoramic scan)")
print("=" * 60)
