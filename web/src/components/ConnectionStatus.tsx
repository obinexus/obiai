import { useAppStore } from '../store';

const LABELS = {
  disconnected: 'Disconnected',
  connecting: 'Connecting…',
  connected: 'Connected',
} as const;

export function ConnectionStatus() {
  const connection = useAppStore((s) => s.connection);
  return (
    <span className="state-chip" role="status" aria-live="polite">
      Connection: {LABELS[connection]}
    </span>
  );
}
