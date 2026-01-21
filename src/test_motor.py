#!/usr/bin/env python3
"""
Quick test script to verify motor functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from stepper_motor import StepperMotor

def main():
    print("=== Pan360 Motor Test ===\n")
    
    # Initialize motor with default pins
    pins = [17, 18, 27, 22]
    print(f"Initializing motor on GPIO pins: {pins}")
    
    motor = StepperMotor(pins)
    
    try:
        print("\nTest 1: Rotate 90° clockwise")
        motor.rotate_angle(90, clockwise=True)
        print(f"Current position: {motor.current_angle:.2f}°")
        
        input("\nPress Enter for next test...")
        
        print("\nTest 2: Rotate 90° counter-clockwise")
        motor.rotate_angle(90, clockwise=False)
        print(f"Current position: {motor.current_angle:.2f}°")
        
        input("\nPress Enter for next test...")
        
        print("\nTest 3: Complete 360° rotation")
        motor.rotate_angle(360, clockwise=True)
        print(f"Current position: {motor.current_angle:.2f}°")
        
        input("\nPress Enter to return home...")
        
        print("\nReturning to home position (0°)")
        motor.reset_position()
        print(f"Current position: {motor.current_angle:.2f}°")
        
        print("\n=== Motor test complete! ===")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    finally:
        motor.cleanup()
        print("Motor cleanup complete")

if __name__ == "__main__":
    main()
