import { useEffect, useState } from 'react';

import { fetchUModelProfile } from '../lib/api';
import { U_STATE_LABELS } from '../lib/types';
import type { UModelProfile } from '../lib/types';
import { useAppStore } from '../store';
import { AccessibilityControls } from './AccessibilityControls';
import { ConnectionStatus } from './ConnectionStatus';

export function UHeader() {
  const uState = useAppStore((s) => s.uState);
  const [model, setModel] = useState<UModelProfile | null>(null);

  useEffect(() => {
    let active = true;
    fetchUModelProfile()
      .then((profile) => {
        if (active) setModel(profile);
      })
      .catch(() => {
        if (active) setModel(null);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <header className="u-header">
      <span className="u-mark" aria-hidden="true">
        U
      </span>
      <div>
        <div className="u-title">U — Ontological Bayesian Video Intelligence</div>
        <div className="header-status">
          <div className="state-chip" role="status" aria-live="polite">
            State: {U_STATE_LABELS[uState]}
          </div>
          {model && (
            <div className="state-chip model-chip" title={model.data_manifest_ref}>
              Model: {model.artifact_name}
            </div>
          )}
        </div>
      </div>
      <div className="spacer" />
      <AccessibilityControls />
      <ConnectionStatus />
    </header>
  );
}
