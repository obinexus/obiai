import { useAppStore } from '../store';

export function AgentActionPanel() {
  const decision = useAppStore((s) => s.latestDecision);
  const action = decision?.action;

  return (
    <section className="card" aria-label="Agent action">
      <h2>Agent action</h2>
      {!action ? (
        <p className="status-text">The action U selects (and why) appears here.</p>
      ) : (
        <>
          <div className="metric-row">
            <span className="label">Action</span>
            <span className="state-value">{action.name}</span>
          </div>
          <p className="status-text" style={{ marginBottom: 0 }}>
            {action.rationale}
          </p>
          {decision && decision.explanation.length > 0 && (
            <details style={{ marginTop: '0.6rem' }}>
              <summary>Full explanation trace</summary>
              <ul className="flag-list">
                {decision.explanation.map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
