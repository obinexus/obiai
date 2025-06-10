"""
OBIAI CLI Main Entry Point
Implements Sinphasé-aligned command dispatch with Zero Trust IOC
"""

import argparse
import sys
from .ioc_config import IOCContainer

def main():
    """OBIAI CLI entrypoint with Sinphasé component isolation"""
    parser = argparse.ArgumentParser(
        description="OBIAI - Ontological Bayesian Intelligence Architecture",
        epilog="Developed by OBINexus Computing - Aegis Framework Division"
    )
    
    # Global arguments
    parser.add_argument('--preset', choices=['default', 'zero_trust', 'development'],
                       default='default', help='Configuration preset')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Register feature commands
    from .commands import register_commands
    register_commands(subparsers)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command with IOC container
    try:
        return execute_command(args)
    except Exception as e:
        print(f"Error: {e}")
        return 1

def execute_command(args):
    """Execute command with Zero Trust IOC validation"""
    from .commands import get_command_handler
    
    handler = get_command_handler(args.command)
    if not handler:
        print(f"Unknown command: {args.command}")
        return 1
    
    # Execute with proper IOC container
    return handler(args)

if __name__ == "__main__":
    sys.exit(main())
