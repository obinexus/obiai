# OBIAI Agent

A runnable foundation for the **OBI Ontological Bayesian Intelligence** agentic modular model.

The architecture separates:

1. **Ontology** — explicit concepts and relations.
2. **Bayesian inference** — uncertainty-aware belief updates.
3. **Bias auditing** — protected attributes are measured and controlled rather than hidden.
4. **Agent planning** — goals are decomposed into auditable actions.
5. **Dynamic modules** — voice, vision, accessibility, robotics, browser, or other capabilities can be loaded without changing the core.

## Install

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
```

Optional production capabilities:

```bash
pip install -e ".[bayesian,api]"
```

## Run

```bash
obiai demo
obiai reason --evidence rain=true --evidence sprinkler=false
pytest
```

## Design rule

A protected attribute may be retained for auditing, but it must not silently become a causal decision path. Decisions return a probability, uncertainty, explanation, provenance, and bias report.
