import { useAppStore } from '../store';

export function SessionControls() {
  const sessionActive = useAppStore((s) => s.sessionActive);
  const startSession = useAppStore((s) => s.startSession);
  const endSession = useAppStore((s) => s.endSession);

  return sessionActive ? (
    <button type="button" onClick={() => void endSession()}>
      End session
    </button>
  ) : (
    <button type="button" className="primary" onClick={() => void startSession()}>
      Start session
    </button>
  );
}
