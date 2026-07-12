from __future__ import annotations

from .agent import OBIAgent
from .bayes import BayesianNetwork, BinaryNode
from .bias import BiasAuditor
from .ontology import Ontology


def build_demo_agent() -> OBIAgent:
    network = BayesianNetwork()
    network.add(BinaryNode("rain", cpt={(): 0.20}))
    network.add(BinaryNode("sprinkler", parents=("rain",), cpt={(False,): 0.40, (True,): 0.01}))
    network.add(BinaryNode(
        "wet_grass",
        parents=("rain", "sprinkler"),
        cpt={(False, False): 0.01, (False, True): 0.90, (True, False): 0.80, (True, True): 0.99},
    ))

    ontology = Ontology()
    ontology.relate("rain", "causes", "wet_grass")
    ontology.relate("sprinkler", "causes", "wet_grass")

    auditor = BiasAuditor(["age_group", "disability", "ethnicity", "gender"])
    return OBIAgent(network, ontology, auditor)
