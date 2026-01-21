"""
Configuration loader for Pan360 system.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for Pan360 system."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse the YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Path to config value (e.g., 'motor.gpio_pins')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @property
    def motor_pins(self):
        """Get motor GPIO pins."""
        return self.get('motor.gpio_pins', [17, 18, 27, 22])
    
    @property
    def motor_step_delay(self):
        """Get motor step delay."""
        return self.get('motor.step_delay', 0.001)
    
    @property
    def camera_resolution(self):
        """Get camera resolution as tuple."""
        res = self.get('camera.resolution', [3280, 2464])
        return tuple(res)
    
    @property
    def camera_output_dir(self):
        """Get camera output directory as absolute path."""
        output_dir = self.get('camera.output_dir', 'images')
        # Convert to absolute path relative to project root
        path = Path(output_dir)
        if not path.is_absolute():
            # Assuming config file is in config/ subdirectory
            project_root = self.config_path.parent.parent
            path = project_root / output_dir
        return str(path.resolve())
    
    @property
    def camera_stabilization_delay(self):
        """Get camera stabilization delay."""
        return self.get('camera.stabilization_delay', 2.0)
    
    @property
    def exposure_time(self):
        """Get exposure time (returns None if not set for auto-metering)."""
        return self.get('camera.exposure.time', None)
    
    @property
    def exposure_gain(self):
        """Get exposure gain (returns None if not set for auto-metering)."""
        return self.get('camera.exposure.gain', None)
    
    @property
    def angle_increment(self):
        """Get angle increment for scanning."""
        return self.get('scan.angle_increment', 15.0)
    
    @property
    def total_angle(self):
        """Get total rotation angle."""
        return self.get('scan.total_angle', 360.0)
    
    @property
    def settle_time(self):
        """Get settle time before capture."""
        return self.get('scan.settle_time', 0.8)
    
    @property
    def clockwise(self):
        """Get rotation direction."""
        return self.get('scan.clockwise', True)
    
    @property
    def return_home(self):
        """Get whether to return home after scan."""
        return self.get('scan.return_home', True)
    
    @property
    def verbose(self):
        """Get verbose logging setting."""
        return self.get('advanced.verbose', True)
    
    def __repr__(self):
        return f"Config(config_path='{self.config_path}')"
