import { U_STATE_LABELS } from '../lib/types';
import { useAppStore } from '../store';
import { AccessibilityControls } from './AccessibilityControls';
import { ConnectionStatus } from './ConnectionStatus';

export function UHeader() {
  const uState = useAppStore((s) => s.uState);
  return (
    <header className="u-header">
      <span className="u-mark" aria-hidden="true">
        U
      </span>
      <div>
        <div className="u-title">U — Ontological Bayesian Video Intelligence</div>
        <div className="state-chip" role="status" aria-live="polite">
          State: {U_STATE_LABELS[uState]}
        </div>
      </div>
      <div className="spacer" />
      <AccessibilityControls />
      <ConnectionStatus />
    </header>
  );
}
