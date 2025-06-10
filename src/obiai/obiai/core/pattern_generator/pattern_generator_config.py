"""
pattern_generator Configuration Module
Feature-scoped IoC configuration following Sinphasé isolation principles
Compliance: Formal Math Function Reasoning System §5.3
"""

def get_config():
    """Default configuration for pattern_generator"""
    return {
        "feature_name": "pattern_generator",
        "enable_logging": True,
        "debug_mode": False,
        "performance_monitoring": True,
        "aegis_compliance": True,
        "zero_trust_validation": True
    }

def get_zero_trust_config():
    """Zero Trust preset for clinical deployment"""
    config = get_config()
    config.update({
        "security_level": "maximum",
        "audit_logging": "comprehensive",
        "failure_mode": "safe_shutdown",
        "integrity_checks": "continuous",
        "pattern_validation": "strict"
    })
    return config

def get_development_config():
    """Development preset with enhanced debugging"""
    config = get_config()
    config.update({
        "debug_mode": True,
        "verbose_logging": True,
        "performance_profiling": True,
        "test_mode": True
    })
    return config

# Configuration presets for CLI integration
PRESETS = {
    "default": get_config(),
    "zero_trust": get_zero_trust_config(),
    "development": get_development_config()
}
