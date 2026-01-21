"""
Camera Controller for Raspberry Pi Camera Module
Handles image acquisition with optimized settings for panoramic stitching.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from picamera2 import Picamera2
from libcamera import controls


class CameraController:
    """
    Controller for Raspberry Pi Camera Module with panorama-optimized settings.
    """
    
    def __init__(
        self,
        resolution: Tuple[int, int] = (4056, 3040),
        output_dir: str = "images",
        stabilization_delay: float = 0.5
    ):
        """
        Initialize the camera controller.
        
        Args:
            resolution: Image resolution (width, height). Default is max for Pi Camera V2
            output_dir: Directory to save captured images
            stabilization_delay: Delay after camera setup for stabilization (seconds)
        """
        self.resolution = resolution
        # Convert to absolute path
        self.output_dir = Path(output_dir).resolve()
        self.stabilization_delay = stabilization_delay
        self.camera = None
        
        # Create output directory if it doesn't exist
        print(f"Output directory: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.output_dir.exists():
            raise RuntimeError(f"Failed to create output directory: {self.output_dir}")
    
    def initialize(self) -> None:
        """Initialize the camera with optimized settings for panoramas."""
        if self.camera is not None:
            return
        
        print("Initializing camera...")
        self.camera = Picamera2()
        
        # Configure camera for still capture
        config = self.camera.create_still_configuration(
            main={"size": self.resolution, "format": "RGB888"},
            buffer_count=2
        )
        self.camera.configure(config)
        
        self.camera.start()
        
        # Enable auto-exposure initially to meter the scene
        print("Starting camera with auto-exposure to meter scene...")
        try:
            self.camera.set_controls({
                "AeEnable": True,  # Enable auto exposure initially
                "AwbEnable": True,  # Enable auto white balance initially
            })
        except Exception as e:
            print(f"Warning: Auto controls not available: {e}")
        
        # Let camera meter the scene
        print(f"Metering scene for {self.stabilization_delay + 1.0}s...")
        time.sleep(self.stabilization_delay + 1.0)
        
        # Now lock exposure and white balance for consistent panorama
        print("Locking exposure and white balance for consistent captures...")
        try:
            # Get current exposure values
            metadata = self.camera.capture_metadata()
            current_exposure = metadata.get("ExposureTime", 20000)
            current_gain = metadata.get("AnalogueGain", 1.0)
            
            print(f"Locked settings - Exposure: {current_exposure}µs, Gain: {current_gain:.2f}")
            
            # Lock with current values
            self.camera.set_controls({
                "AeEnable": False,  # Disable auto exposure
                "AwbEnable": False,  # Disable auto white balance
                "ExposureTime": current_exposure,
                "AnalogueGain": current_gain,
            })
        except Exception as e:
            print(f"Warning: Could not lock exposure: {e}")
            print("Using auto-exposure mode for all captures")
        
        print("Camera initialized successfully")
    
    def capture(
        self,
        angle: float,
        session_id: Optional[str] = None,
        settle_time: float = 0.5
    ) -> str:
        """
        Capture an image at the specified angle.
        
        Args:
            angle: Current angle position
            session_id: Optional session identifier for organizing images
            settle_time: Time to wait before capture for vibration to settle
        
        Returns:
            Path to the saved image file
        """
        if self.camera is None:
            self.initialize()
        
        # Wait for motor vibrations to settle
        if settle_time > 0:
            time.sleep(settle_time)
        
        # Generate filename with only angle (overwrites previous captures at same angle)
        filename = f"angle_{int(angle):03d}.jpg"
        filepath = self.output_dir / filename
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Capture image
        print(f"Capturing image at angle {angle:.2f}°...")
        print(f"Saving to: {filepath.absolute()}")
        
        try:
            self.camera.capture_file(str(filepath.absolute()))
            
            # Verify file was created
            if filepath.exists():
                file_size = filepath.stat().st_size
                print(f"✓ Saved: {filepath} ({file_size} bytes)")
            else:
                print(f"✗ Warning: File not found after capture: {filepath}")
                
        except Exception as e:
            print(f"✗ Error capturing image: {e}")
            raise
        
        return str(filepath)
    
    def capture_sequence(
        self,
        angles: list,
        session_id: Optional[str] = None,
        settle_time: float = 0.5
    ) -> list:
        """
        Capture a sequence of images at specified angles.
        
        Args:
            angles: List of angles to capture
            session_id: Session identifier
            settle_time: Time to wait before each capture
        
        Returns:
            List of captured image file paths
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        captured_images = []
        
        for i, angle in enumerate(angles):
            print(f"\nCapturing image {i+1}/{len(angles)}")
            filepath = self.capture(angle, session_id, settle_time)
            captured_images.append(filepath)
        
        return captured_images
    
    def set_exposure(self, exposure_time: int = None, gain: float = None) -> None:
        """
        Set manual exposure settings.
        
        Args:
            exposure_time: Exposure time in microseconds (None = keep current)
            gain: Analogue gain value (None = keep current)
        """
        if self.camera is None:
            self.initialize()
        
        try:
            controls = {"AeEnable": False}
            if exposure_time is not None:
                controls["ExposureTime"] = exposure_time
            if gain is not None:
                controls["AnalogueGain"] = gain
            
            self.camera.set_controls(controls)
            print(f"Manual exposure set - Time: {exposure_time}µs, Gain: {gain}")
            
            # Allow settings to take effect
            time.sleep(0.2)
        except Exception as e:
            print(f"Warning: Could not set exposure settings: {e}")
    
    def set_white_balance(self, red_gain: float = 1.5, blue_gain: float = 1.5) -> None:
        """
        Set manual white balance.
        
        Args:
            red_gain: Red color gain
            blue_gain: Blue color gain
        """
        if self.camera is None:
            self.initialize()
        
        try:
            self.camera.set_controls({
                "ColourGains": (red_gain, blue_gain),
            })
            
            time.sleep(0.2)
        except Exception as e:
            print(f"Warning: Could not set white balance: {e}")
    
    def close(self) -> None:
        """Close the camera and release resources."""
        if self.camera is not None:
            print("Closing camera...")
            self.camera.stop()
            self.camera.close()
            self.camera = None
            print("Camera closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
