#!/usr/bin/env python3
"""
Pan360 - 360° Panoramic Camera System
Main application for automated panoramic image capture.
"""

import sys
import time
import signal
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from stepper_motor import StepperMotor
from camera_controller import CameraController
from config import Config


class Pan360Scanner:
    """Main controller for the Pan360 panoramic scanning system."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the Pan360 scanner.
        
        Args:
            config_path: Path to configuration file
        """
        print("=" * 60)
        print("Pan360 - 360° Panoramic Camera System")
        print("=" * 60)
        
        # Load configuration
        print("\nLoading configuration...")
        self.config = Config(config_path)
        print(f"Configuration loaded from: {config_path}")
        
        # Initialize components
        self.motor = None
        self.camera = None
        self.session_id = None
        
        # Setup signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals for clean shutdown."""
        print("\n\nInterrupt received. Shutting down safely...")
        self.cleanup()
        sys.exit(0)
    
    def initialize(self) -> None:
        """Initialize motor and camera."""
        print("\n" + "-" * 60)
        print("Initializing hardware...")
        print("-" * 60)
        
        # Initialize stepper motor
        print("\n[Motor] Initializing stepper motor...")
        self.motor = StepperMotor(
            pins=self.config.motor_pins,
            step_delay=self.config.motor_step_delay
        )
        print(f"[Motor] GPIO Pins: {self.config.motor_pins}")
        print(f"[Motor] Step delay: {self.config.motor_step_delay}s")
        print("[Motor] Motor initialized successfully")
        
        # Initialize camera
        print("\n[Camera] Initializing Pi Camera...")
        self.camera = CameraController(
            resolution=self.config.camera_resolution,
            output_dir=self.config.camera_output_dir,
            stabilization_delay=self.config.camera_stabilization_delay
        )
        self.camera.initialize()
        
        # Set camera parameters if specified in config
        exposure_time = self.config.exposure_time
        exposure_gain = self.config.exposure_gain
        
        if exposure_time is not None and exposure_gain is not None:
            print(f"[Camera] Overriding with manual exposure: {exposure_time}µs, Gain: {exposure_gain}")
            self.camera.set_exposure(exposure_time, exposure_gain)
        else:
            print(f"[Camera] Using auto-metered exposure (locked after metering)")
        
        print(f"[Camera] Resolution: {self.config.camera_resolution}")
        
        print("\n" + "=" * 60)
        print("Hardware initialization complete!")
        print("=" * 60)
    
    def calculate_scan_angles(self) -> list:
        """
        Calculate the angles for image capture.
        
        Returns:
            List of angles (in degrees) to capture
        """
        angles = []
        current_angle = 0.0
        total_angle = self.config.total_angle
        increment = self.config.angle_increment
        
        while current_angle < total_angle:
            angles.append(current_angle)
            current_angle += increment
        
        return angles
    
    def scan(self) -> list:
        """
        Execute a complete 360° panoramic scan.
        
        Returns:
            List of captured image file paths
        """
        # Generate session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate scan parameters
        angles = self.calculate_scan_angles()
        num_images = len(angles)
        
        print("\n" + "=" * 60)
        print("Starting Panoramic Scan")
        print("=" * 60)
        print(f"Session ID: {self.session_id}")
        print(f"Total rotation: {self.config.total_angle}°")
        print(f"Angle increment: {self.config.angle_increment}°")
        print(f"Number of images: {num_images}")
        print(f"Settle time: {self.config.settle_time}s")
        print(f"Direction: {'Clockwise' if self.config.clockwise else 'Counter-clockwise'}")
        print("=" * 60)
        
        captured_images = []
        start_time = time.time()
        
        # Scan loop
        for i, angle in enumerate(angles):
            print(f"\n{'=' * 60}")
            print(f"Image {i + 1}/{num_images}")
            print(f"{'=' * 60}")
            
            # Rotate to angle
            print(f"[Motor] Rotating to {angle:.2f}°...")
            if i == 0:
                # First position - rotate from 0
                if angle > 0:
                    self.motor.rotate_angle(angle, self.config.clockwise)
            else:
                # Subsequent positions - rotate by increment
                self.motor.rotate_angle(
                    self.config.angle_increment,
                    self.config.clockwise
                )
            
            print(f"[Motor] Position: {self.motor.current_angle:.2f}°")
            
            # Wait for vibrations to settle
            print(f"[Camera] Settling for {self.config.settle_time}s...")
            time.sleep(self.config.settle_time)
            
            # Capture image
            filepath = self.camera.capture(
                angle=angle,
                session_id=self.session_id,
                settle_time=0  # Already settled above
            )
            captured_images.append(filepath)
            
            # Progress update
            elapsed = time.time() - start_time
            avg_time_per_image = elapsed / (i + 1)
            remaining_images = num_images - (i + 1)
            estimated_remaining = avg_time_per_image * remaining_images
            
            print(f"[Progress] {i + 1}/{num_images} complete")
            print(f"[Progress] Elapsed: {elapsed:.1f}s, Est. remaining: {estimated_remaining:.1f}s")
        
        # Return to home position if configured
        if self.config.return_home:
            print("\n" + "=" * 60)
            print(f"[Motor] Current position: {self.motor.current_angle:.2f}°")
            print(f"[Motor] Rotating back {self.config.total_angle}° to unwind cable...")
            # Rotate back the full amount in opposite direction to unwind
            self.motor.rotate_angle(self.config.total_angle, clockwise=not self.config.clockwise)
            self.motor.current_angle = 0.0  # Reset to exactly 0
            print(f"[Motor] Home position reached: {self.motor.current_angle:.2f}°")
        
        # Summary
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("Scan Complete!")
        print("=" * 60)
        print(f"Total images captured: {len(captured_images)}")
        print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"Average time per image: {total_time/len(captured_images):.1f}s")
        print(f"Images saved to: {self.config.camera_output_dir}/")
        print("=" * 60)
        
        return captured_images
    
    def cleanup(self) -> None:
        """Clean up resources."""
        print("\nCleaning up resources...")
        
        if self.motor is not None:
            self.motor.cleanup()
            print("Motor cleanup complete")
        
        if self.camera is not None:
            self.camera.close()
            print("Camera cleanup complete")
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


def main():
    """Main entry point."""
    try:
        # Create and run scanner
        with Pan360Scanner() as scanner:
            # Run the scan
            images = scanner.scan()
            
            print("\n" + "=" * 60)
            print("Next Steps:")
            print("=" * 60)
            print("1. Review captured images in the 'images/' directory")
            print("2. Use panorama stitching software to create the final panorama:")
            print("   - Hugin (free, open-source)")
            print("   - PTGui (commercial)")
            print("   - Microsoft ICE (free, Windows)")
            print("   - Or use Python: OpenCV with cv2.Stitcher")
            print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
