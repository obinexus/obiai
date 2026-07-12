from obiai.bias import BiasAuditor
from obiai.ontology import Ontology


def test_protected_path_is_detected() -> None:
    ontology = Ontology()
    ontology.relate("disability", "influences", "score")
    ontology.relate("score", "controls", "decision")
    report = BiasAuditor(["disability"]).audit_paths(ontology, "decision")
    assert not report.passed
    assert report.protected_paths == [["disability", "score", "decision"]]
