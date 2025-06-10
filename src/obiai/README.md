# OBIAI - Ontological Bayesian Intelligence Architecture Infrastructure

**Version 2.3.1** - Aegis Framework Compliant

Developed by **Nnamdi Michael Okpala** - OBINexus Computing

## Architecture Overview

OBIAI implements a Sinphasé-aligned component architecture with Zero Trust IOC container management. The system provides:

- **Component Isolation**: Each feature maintains independent configuration and lifecycle
- **Zero Trust Security**: All configuration access validated through IOC container
- **Aegis Compliance**: Mathematical verification and formal proof integration
- **CLI Interface**: Feature-specific commands with preset management

## Quick Start

```bash
# Install the package
pip install -e .

# Run with default configuration
obiai simulate_barrier --cycles 50

# Use Zero Trust preset for production
obiai simulate_barrier --preset zero_trust --cycles 100

# Development mode with debug output
obiai query_pattern --preset development --debug --verbose
```

## Architecture Components

### Core Features
- `protective_barrier`: Consciousness state isolation and integrity validation
- `pattern_generator`: Authentication pattern generation and validation
- `state_monitor`: Consciousness state transition monitoring
- `epistemological_dag`: DAG-based semantic inference (AEGIS-PROOF-1.2)

### CLI System
- Zero Trust IOC container for secure configuration management
- Feature-specific command handlers with preset support
- Comprehensive argument validation and error handling

## Configuration Presets

### Default
Standard configuration for general use

### Zero Trust
Enhanced security configuration for clinical deployment:
- Maximum security validation
- Comprehensive audit logging
- Safe shutdown on integrity violations

### Development
Debug-enabled configuration for development work:
- Verbose logging
- Performance profiling
- Test mode activation

## Testing

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run mathematical verification tests
python -m pytest tests/mathematical/
```

## Development

The project follows Sinphasé development patterns:
- Component isolation with clear boundaries
- Feature-scoped configuration management
- Zero Trust policy enforcement
- Aegis mathematical compliance

For detailed development guidelines, see `docs/development/`

## License

MIT License - see LICENSE file for details.

---

**OBINexus Computing - Computing from the Heart**
