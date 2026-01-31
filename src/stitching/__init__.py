"""
Stitching module for Pan360.
Provides multiple stitching algorithms for panorama creation.
"""

from .base_stitcher import BaseStitcher
from .opencv_auto_stitcher import OpenCVAutoStitcher
from .manual_stitcher import ManualStitcher
from .sensor_aided_stitcher import SensorAidedStitcher

__all__ = [
    'BaseStitcher',
    'OpenCVAutoStitcher',
    'ManualStitcher',
    'SensorAidedStitcher',
]
