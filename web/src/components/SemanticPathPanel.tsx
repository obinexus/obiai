import { Fragment } from 'react';

import { useAppStore } from '../store';

export function SemanticPathPanel() {
  const decision = useAppStore((s) => s.latestDecision);

  return (
    <section className="card" aria-label="Semantic path">
      <h2>Semantic path</h2>
      {!decision || decision.semantic_path.length === 0 ? (
        <p className="status-text">
          The epistemic DAG traversal (Filter-Flash) appears here.
        </p>
      ) : (
        <>
          <ol className="semantic-path">
            {decision.semantic_path.map((concept) => (
              <li key={concept}>{concept}</li>
            ))}
          </ol>
          <p className="status-text" style={{ marginBottom: 0 }}>
            Concepts:{' '}
            {decision.ontological_concepts.map((concept, index) => (
              <Fragment key={concept}>
                {index > 0 && ', '}
                {concept}
              </Fragment>
            ))}
          </p>
        </>
      )}
    </section>
  );
}
