import { useAppStore } from '../store';

export function BeliefPanel() {
  const decision = useAppStore((s) => s.latestDecision);

  return (
    <section className="card" aria-label="Current belief">
      <h2>Current belief</h2>
      {!decision ? (
        <p className="status-text">
          No decision yet. Raise your hand during a session to see U reason.
        </p>
      ) : (
        <>
          <div className="metric-row">
            <span className="label">Proposition</span>
            <span>{decision.proposition}</span>
          </div>
          <div
            className="prob-bar"
            role="img"
            aria-label={`Probability ${(decision.probability * 100).toFixed(1)} percent`}
          >
            <div style={{ width: `${(decision.probability * 100).toFixed(1)}%` }} />
          </div>
          <div className="metric-row">
            <span className="label">Probability</span>
            <span>{decision.probability.toFixed(2)}</span>
          </div>
          <div className="metric-row">
            <span className="label">Uncertainty</span>
            <span>{decision.uncertainty.toFixed(2)}</span>
          </div>
          <div className="metric-row">
            <span className="label">State</span>
            <span className="state-value">{decision.state}</span>
          </div>
        </>
      )}
    </section>
  );
}
