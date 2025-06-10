"""
Zero Trust IOC Container
Implements policy-based configuration injection with integrity validation
Compliance: Formal Math Function Reasoning System §5.3
"""

import time
from typing import Dict, Any, Optional

class IOCContainer:
    """
    IOCContainer enforces Zero Trust Preset Principle.
    - No raw configs bypass this container
    - Only validated presets are injected into the system
    - Integrity of preset + config chain is checked per command invocation
    """
    
    def __init__(self, preset_name: str = "default", preset_source: Optional[Dict] = None):
        self.zero_trust_mode = True
        self.integrity_valid = True
        self.creation_time = time.time()
        
        if not preset_source:
            raise ValueError("IOCContainer requires a preset_source dictionary")
        
        if preset_name not in preset_source:
            valid_presets = list(preset_source.keys())
            raise ValueError(f"Invalid preset '{preset_name}'. Valid: {valid_presets}")
        
        # Lock configuration for this run
        self.preset_name = preset_name
        self.config = preset_source[preset_name].copy()  # Defensive copy
        self.context = {}
        
        # Validate configuration integrity
        self._validate_preset_integrity()
    
    def _validate_preset_integrity(self):
        """Validate preset configuration meets Aegis requirements"""
        required_keys = ["feature_name", "aegis_compliance"]
        
        for key in required_keys:
            if key not in self.config:
                self.integrity_valid = False
                raise ValueError(f"Preset '{self.preset_name}' missing required key: {key}")
        
        # Validate Zero Trust requirements
        if self.config.get("zero_trust_validation", False):
            zt_required = ["security_level", "audit_logging"]
            for key in zt_required:
                if key not in self.config:
                    self.integrity_valid = False
                    raise ValueError(f"Zero Trust preset missing required key: {key}")
    
    def validate_integrity(self) -> bool:
        """
        Enforce Zero Trust validation gate
        Must be called before any configuration access
        """
        if not self.integrity_valid:
            raise RuntimeError("[IOCContainer] Integrity violation detected!")
        
        if not self.zero_trust_mode:
            raise RuntimeError("[IOCContainer] Zero Trust mode disabled! Aborting.")
        
        # Check configuration age (expire after 1 hour for security)
        config_age = time.time() - self.creation_time
        if config_age > 3600:  # 1 hour
            raise RuntimeError("[IOCContainer] Configuration expired. Create new container.")
        
        print(f"[IOCContainer] ✓ Integrity validated. Preset: '{self.preset_name}'")
        return True
    
    def get_config_param(self, param_name: str) -> Any:
        """Safely retrieve parameter from active config preset"""
        self.validate_integrity()
        
        if param_name not in self.config:
            raise KeyError(f"Config param '{param_name}' not found in preset '{self.preset_name}'")
        
        return self.config[param_name]
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration (for feature initialization)"""
        self.validate_integrity()
        return self.config.copy()
    
    def set_context(self, key: str, value: Any):
        """Set runtime context (for cross-component communication)"""
        self.validate_integrity()
        self.context[key] = value
    
    def get_context(self, key: str) -> Any:
        """Get runtime context value"""
        self.validate_integrity()
        return self.context.get(key)
