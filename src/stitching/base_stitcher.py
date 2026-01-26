"""
Base class for panorama stitching algorithms.
Defines the interface that all stitchers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import numpy as np
from pathlib import Path


class BaseStitcher(ABC):
    """Abstract base class for panorama stitching algorithms."""
    
    def __init__(self, name: str):
        """
        Initialize the stitcher.
        
        Args:
            name: Name of the stitching algorithm
        """
        self.name = name
        self.processing_time = 0.0
        self.stats = {}
    
    @abstractmethod
    def stitch(self, image_paths: List[str]) -> Tuple[Optional[np.ndarray], dict]:
        """
        Stitch a list of images into a panorama.
        
        Args:
            image_paths: List of paths to input images (sorted by angle)
        
        Returns:
            Tuple of (panorama_image, statistics_dict)
            - panorama_image: Stitched panorama as numpy array, or None if failed
            - statistics_dict: Dictionary with stitching statistics
        """
        pass
    
    def save_result(self, panorama: np.ndarray, output_path: str) -> bool:
        """
        Save the panorama to disk.
        
        Args:
            panorama: Panorama image as numpy array
            output_path: Path to save the image
        
        Returns:
            True if successful, False otherwise
        """
        import cv2
        
        try:
            # Create output directory if needed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            success = cv2.imwrite(output_path, panorama)
            
            if success:
                file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
                print(f"✓ Saved panorama: {output_path} ({file_size:.2f} MB)")
            else:
                print(f"✗ Failed to save: {output_path}")
            
            return success
        except Exception as e:
            print(f"✗ Error saving panorama: {e}")
            return False
    
    def get_stats_summary(self) -> str:
        """
        Get a formatted summary of stitching statistics.
        
        Returns:
            String with formatted statistics
        """
        lines = [f"\n{'='*60}"]
        lines.append(f"{self.name} - Statistics")
        lines.append('='*60)
        
        if self.stats:
            for key, value in self.stats.items():
                lines.append(f"  {key}: {value}")
        
        lines.append(f"  Processing Time: {self.processing_time:.2f}s")
        lines.append('='*60)
        
        return '\n'.join(lines)
