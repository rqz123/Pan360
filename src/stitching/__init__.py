"""
Stitching module for Pan360.
Provides multiple stitching algorithms for panorama creation.
"""

from .base_stitcher import BaseStitcher
from .opencv_auto_stitcher import OpenCVAutoStitcher
from .manual_stitcher import ManualStitcher
from .simple_angle_stitcher import SimpleAngleStitcher

__all__ = [
    'BaseStitcher',
    'OpenCVAutoStitcher',
    'ManualStitcher',
    'SimpleAngleStitcher',
]
