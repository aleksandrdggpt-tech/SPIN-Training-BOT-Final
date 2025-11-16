"""
Active Listening Module for Training Bots.
Detects when user references previous responses (contextual questions).

This module is designed to be portable across different training bots.
"""

from .detector import ActiveListeningDetector
from .config import ActiveListeningConfig

__all__ = [
    'ActiveListeningDetector',
    'ActiveListeningConfig'
]
