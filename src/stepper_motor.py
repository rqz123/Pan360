"""
Stepper Motor Controller for 28BYJ-48 with ULN2003 Driver
Provides precise rotational control for the panoramic camera system.
"""

import RPi.GPIO as GPIO
import time
from typing import List


class StepperMotor:
    """
    Controller for 28BYJ-48 stepper motor with ULN2003 driver.
    
    The 28BYJ-48 is a 5V unipolar stepper motor with gear reduction.
    - Step angle: 5.625° / 64 = 0.087890625° per step (with gearing)
    - Steps per revolution: 4096 (with 64:1 gear ratio)
    - Operating sequence: 8-step sequence for smooth operation
    """
    
    # 8-step sequence (half-step mode) for smooth rotation
    STEP_SEQUENCE = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1]
    ]
    
    STEPS_PER_REVOLUTION = 4096  # Full 360° rotation
    
    def __init__(self, pins: List[int], step_delay: float = 0.001):
        """
        Initialize the stepper motor controller.
        
        Args:
            pins: List of 4 GPIO pin numbers [IN1, IN2, IN3, IN4]
            step_delay: Delay between steps in seconds (default: 1ms)
        """
        self.pins = pins
        self.step_delay = step_delay
        self.current_step = 0
        self.current_angle = 0.0
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
    
    def _set_step(self, step_pattern: List[int]) -> None:
        """Set the GPIO pins according to the step pattern."""
        for pin, state in zip(self.pins, step_pattern):
            GPIO.output(pin, state)
    
    def step(self, steps: int, clockwise: bool = True) -> None:
        """
        Move the motor by a specified number of steps.
        
        Args:
            steps: Number of steps to move
            clockwise: Direction of rotation (True = clockwise, False = counter-clockwise)
        """
        direction = 1 if clockwise else -1
        
        for _ in range(abs(steps)):
            self.current_step = (self.current_step + direction) % len(self.STEP_SEQUENCE)
            self._set_step(self.STEP_SEQUENCE[self.current_step])
            time.sleep(self.step_delay)
        
        # Calculate current angle
        total_steps_moved = steps * direction
        angle_per_step = 360.0 / self.STEPS_PER_REVOLUTION
        self.current_angle = (self.current_angle + (total_steps_moved * angle_per_step)) % 360.0
    
    def rotate_angle(self, angle: float, clockwise: bool = True) -> None:
        """
        Rotate the motor by a specified angle in degrees.
        
        Args:
            angle: Angle to rotate in degrees
            clockwise: Direction of rotation
        """
        steps = int((angle / 360.0) * self.STEPS_PER_REVOLUTION)
        self.step(steps, clockwise)
    
    def rotate_to_angle(self, target_angle: float) -> None:
        """
        Rotate to an absolute angle position (0-360°).
        
        Args:
            target_angle: Target angle in degrees (0-360)
        """
        target_angle = target_angle % 360.0
        angle_diff = target_angle - self.current_angle
        
        # Choose shortest path
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        if angle_diff != 0:
            clockwise = angle_diff > 0
            self.rotate_angle(abs(angle_diff), clockwise)
    
    def reset_position(self) -> None:
        """Reset the motor to home position (0°)."""
        self.rotate_to_angle(0)
        # Ensure angle is exactly 0
        self.current_angle = 0.0
    
    def stop(self) -> None:
        """Stop the motor and disable all coils to prevent heating."""
        for pin in self.pins:
            GPIO.output(pin, GPIO.LOW)
    
    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        self.stop()
        GPIO.cleanup(self.pins)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
