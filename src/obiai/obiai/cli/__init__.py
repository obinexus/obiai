"""
OBIAI CLI Module
Command-line interface with Zero Trust IOC container
"""

from .main import main
from .ioc_config import IOCContainer

__all__ = ['main', 'IOCContainer']
