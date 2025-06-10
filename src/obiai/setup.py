"""
OBIAI Setup Configuration
Ontological Bayesian Intelligence Architecture Infrastructure
"""

from setuptools import setup, find_packages

setup(
    name="obiai",
    version="2.3.1",
    description="OBIAI: Ontological Bayesian Intelligence Architecture with Consciousness Modeling",
    author="Nnamdi Michael Okpala",
    author_email="nnamdi@obinexuscomputing.org",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "click>=8.0.0",
        "pydantic>=1.8.0",
    ],
    entry_points={
        'console_scripts': [
            'obiai=obiai.cli.main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
