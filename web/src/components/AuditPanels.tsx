import { useAppStore } from '../store';

export function BiasAuditPanel() {
  const decision = useAppStore((s) => s.latestDecision);
  const audit = decision?.bias_audit;

  return (
    <section className="card" aria-label="Bias audit">
      <h2>Bias audit</h2>
      {!audit ? (
        <p className="status-text">Protected-attribute audit results appear here.</p>
      ) : (
        <>
          <p style={{ margin: 0 }} className={audit.passed ? 'audit-pass' : 'audit-fail'}>
            {audit.passed ? 'Passed' : 'Failed'}
          </p>
          <p className="status-text" style={{ marginBottom: 0 }}>
            Protected paths:{' '}
            {audit.protected_paths.length === 0
              ? 'None'
              : audit.protected_paths.map((path) => path.join(' → ')).join('; ')}
          </p>
          {audit.notes.length > 0 && (
            <ul className="flag-list">
              {audit.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

export function SafetyAuditPanel() {
  const decision = useAppStore((s) => s.latestDecision);
  const audit = decision?.safety_audit;

  return (
    <section className="card" aria-label="Safety audit">
      <h2>Safety audit</h2>
      {!audit ? (
        <p className="status-text">Observable-events policy results appear here.</p>
      ) : (
        <>
          <p style={{ margin: 0 }} className={audit.passed ? 'audit-pass' : 'audit-fail'}>
            {audit.passed ? 'Passed' : 'Failed'}
          </p>
          {audit.policy_flags.length > 0 && (
            <ul className="flag-list">
              {audit.policy_flags.map((flag) => (
                <li key={flag}>{flag}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
