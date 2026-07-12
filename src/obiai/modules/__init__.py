from obiai.modules.base import AgentModule
from obiai.modules.loader import ModuleRegistry

__all__ = ["AgentModule", "ModuleRegistry"]

# Import-path/class registry for dynamically loadable modules (paper
# Hypothesis III). New capability modules (voice, vision, robotics, ...)
# register here and are enabled through ``modules.enabled`` in config.
KNOWN_MODULES: dict[str, tuple[str, str]] = {
    "echo": ("obiai.modules.echo", "EchoModule"),
}
