"""
OBIAI - Ontological Bayesian Intelligence Architecture Infrastructure
Developed by OBINexus Computing - Aegis Framework Division
"""

__version__ = "2.3.1"
__author__ = "Nnamdi Michael Okpala"
__organization__ = "OBINexus Computing"

# Core module imports
from .core import *
from .cli import main as cli_main

__all__ = ['cli_main', '__version__']
