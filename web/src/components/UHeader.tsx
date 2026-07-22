import { useEffect, useState } from 'react';

import { fetchUModelProfile, fetchUaiModelStatus } from '../lib/api';
import { U_STATE_LABELS } from '../lib/types';
import type { UAIModelStatus, UModelProfile } from '../lib/types';
import { useAppStore } from '../store';
import { AccessibilityControls } from './AccessibilityControls';
import { ConnectionStatus } from './ConnectionStatus';

function trainedModelLabel(status: UAIModelStatus): string {
  if (!status.current_run_id) return 'none yet';
  if (!status.loaded) return `registered (${status.current_run_id})`;
  const device = status.loaded_device ? ` on ${status.loaded_device}` : '';
  return `loaded${device} (${status.current_run_id})`;
}

export function UHeader() {
  const uState = useAppStore((s) => s.uState);
  const transcriptLength = useAppStore((s) => s.transcript.length);
  const [model, setModel] = useState<UModelProfile | null>(null);
  const [uaiStatus, setUaiStatus] = useState<UAIModelStatus | null>(null);

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

  useEffect(() => {
    // Re-checked as messages arrive: the trained model loads lazily on
    // first use, so "loaded" can flip true partway through a session.
    let active = true;
    fetchUaiModelStatus()
      .then((status) => {
        if (active) setUaiStatus(status);
      })
      .catch(() => {
        if (active) setUaiStatus(null);
      });
    return () => {
      active = false;
    };
  }, [transcriptLength]);

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
          {uaiStatus && (
            <div
              className={`state-chip trained-model-chip${uaiStatus.loaded ? ' is-loaded' : ''}`}
              title={uaiStatus.artifact_root ?? undefined}
            >
              Trained model: {trainedModelLabel(uaiStatus)}
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
