"""
Epistemological_dag Command Implementation
Feature: epistemological_dag
"""

from ..ioc_config import IOCContainer
from ...core.epistemological_dag.epistemological_dag_config import PRESETS
from ...core.epistemological_dag.epistemological_dag import Epistemological_dag

def add_arguments(parser):
    """Add command-specific arguments"""
    parser.add_argument('--cycles', type=int, default=100,
                       help='Number of processing cycles')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')

def run_command(args):
    """Execute epistemological_dag command with IOC container"""
    try:
        # Initialize IOC container with feature presets
        ioc = IOCContainer(preset_name=args.preset, preset_source=PRESETS)
        ioc.validate_integrity()
        
        # Override config with CLI arguments
        config = ioc.get_full_config()
        if args.debug:
            config['debug_mode'] = True
        
        # Initialize feature
        feature_instance = Epistemological_dag(config)
        
        print(f"Executing epistemological_dag with preset: {args.preset}")
        print(f"Feature: {config['feature_name']}")
        
        # Execute feature processing
        for cycle in range(args.cycles):
            result = feature_instance.process({"cycle": cycle})
            
            if args.verbose or args.debug:
                print(f"Cycle {cycle}: {result['status']}")
            elif cycle % 10 == 0:
                print(f"Progress: {cycle}/{args.cycles}")
        
        print("✓ Command completed successfully")
        return 0
        
    except Exception as e:
        print(f"Command failed: {e}")
        return 1
