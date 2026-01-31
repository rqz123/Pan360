#!/usr/bin/env python3
"""
Interactive motor test with keyboard control.
Use arrow keys to manually control motor rotation for nodal point calibration.
"""

import sys
from pathlib import Path
import termios
import tty

sys.path.insert(0, str(Path(__file__).parent))

from stepper_motor import StepperMotor


def get_key():
    """Get a single keypress from stdin"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        # Handle arrow keys (escape sequences)
        if ch == '\x1b':
            ch = sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def main():
    print("=" * 60)
    print("Pan360 Motor Test - Keyboard Control")
    print("=" * 60)
    
    # Initialize motor with default pins
    pins = [17, 18, 27, 22]
    print(f"\nInitializing motor on GPIO pins: {pins}")
    
    motor = StepperMotor(pins)
    
    # Settings
    step_size = 5.0  # degrees per keypress
    
    print("\n" + "=" * 60)
    print("KEYBOARD CONTROLS")
    print("=" * 60)
    print("  ← LEFT  : Rotate counter-clockwise")
    print("  → RIGHT : Rotate clockwise")
    print("  ↑ UP    : Increase step size")
    print("  ↓ DOWN  : Decrease step size")
    print("  h       : Go to home position (0°)")
    print("  r       : Reset position counter to 0°")
    print("  1-9     : Quick angles (10°, 20°, 30°, ... 90°)")
    print("  0       : Go to 0°")
    print("  q       : Quit")
    print("=" * 60)
    print(f"\nCurrent position: {motor.current_angle:.2f}°")
    print(f"Step size: {step_size:.1f}°")
    print("\nReady! Press arrow keys to control motor...\n")
    
    try:
        while True:
            key = get_key()
            
            # Arrow keys
            if key == '[D':  # Left arrow
                print(f"← Rotating {step_size:.1f}° counter-clockwise...")
                motor.rotate_angle(step_size, clockwise=False)
                print(f"  Position: {motor.current_angle:.2f}°")
                
            elif key == '[C':  # Right arrow
                print(f"→ Rotating {step_size:.1f}° clockwise...")
                motor.rotate_angle(step_size, clockwise=True)
                print(f"  Position: {motor.current_angle:.2f}°")
                
            elif key == '[A':  # Up arrow
                step_size = min(step_size + 1.0, 90.0)
                print(f"↑ Step size increased: {step_size:.1f}°")
                
            elif key == '[B':  # Down arrow
                step_size = max(step_size - 1.0, 1.0)
                print(f"↓ Step size decreased: {step_size:.1f}°")
            
            # Letter keys
            elif key.lower() == 'h':
                print("⌂ Going to home (0°)...")
                target = 0.0
                if motor.current_angle != target:
                    diff = target - motor.current_angle
                    motor.rotate_angle(abs(diff), clockwise=(diff > 0))
                print(f"  Position: {motor.current_angle:.2f}°")
                
            elif key.lower() == 'r':
                print("⟲ Resetting position counter to 0°")
                motor.reset_position()
                print(f"  Position: {motor.current_angle:.2f}°")
                
            elif key.lower() == 'q':
                print("\n✓ Quitting...")
                break
            
            # Number keys for quick angles
            elif key in '0123456789':
                target_angle = int(key) * 10
                print(f"Rotating to {target_angle}°...")
                
                # Calculate shortest path
                diff = target_angle - motor.current_angle
                
                # Normalize to -180 to 180
                while diff > 180:
                    diff -= 360
                while diff < -180:
                    diff += 360
                
                if diff != 0:
                    motor.rotate_angle(abs(diff), clockwise=(diff > 0))
                print(f"  Position: {motor.current_angle:.2f}°")
            
            elif key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            
            elif key == '\r' or key == '\n':  # Enter
                print(f"Current position: {motor.current_angle:.2f}°, Step: {step_size:.1f}°")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    
    finally:
        print("\n" + "=" * 60)
        print(f"Final position: {motor.current_angle:.2f}°")
        print("Cleaning up motor...")
        motor.cleanup()
        print("✓ Motor cleanup complete")
        print("=" * 60)


if __name__ == "__main__":
    main()
