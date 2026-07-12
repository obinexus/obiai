import { useAppStore } from '../store';

export function EvidencePanel() {
  const decision = useAppStore((s) => s.latestDecision);
  const lastObservation = useAppStore((s) => s.lastObservation);

  return (
    <section className="card" aria-label="Evidence">
      <h2>Evidence</h2>
      {!decision ? (
        <p className="status-text">Evidence used by the latest decision appears here.</p>
      ) : (
        <ul className="flag-list">
          {decision.evidence.map((item) => (
            <li key={item.evidence_id}>
              {item.proposition} = {String(item.value)} (confidence {item.confidence.toFixed(2)},
              via {item.provenance.module} v{item.provenance.version})
            </li>
          ))}
        </ul>
      )}
      {lastObservation && (
        <>
          <h2 style={{ marginTop: '0.8rem' }}>Last observation</h2>
          <div className="mono">{JSON.stringify(lastObservation, null, 2)}</div>
        </>
      )}
    </section>
  );
}
