"""
CLI Commands Module
Feature-specific command handlers with IOC integration
"""

from .simulate_barrier import add_arguments as add_barrier_args, run_command as run_barrier
from .query_pattern import add_arguments as add_pattern_args, run_command as run_pattern
from .monitor_state import add_arguments as add_monitor_args, run_command as run_monitor

def register_commands(subparsers):
    """Register all available commands"""
    
    # Barrier simulation command
    barrier_parser = subparsers.add_parser("simulate_barrier",
                                          help="Simulate protective barrier dynamics")
    add_barrier_args(barrier_parser)
    
    # Pattern generation command
    pattern_parser = subparsers.add_parser("query_pattern",
                                          help="Generate and validate authentication patterns")
    add_pattern_args(pattern_parser)
    
    # State monitoring command
    monitor_parser = subparsers.add_parser("monitor_state",
                                          help="Monitor consciousness state transitions")
    add_monitor_args(monitor_parser)

def get_command_handler(command_name):
    """Get command handler function"""
    handlers = {
        "simulate_barrier": run_barrier,
        "query_pattern": run_pattern,
        "monitor_state": run_monitor
    }
    return handlers.get(command_name)
