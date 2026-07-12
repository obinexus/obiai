interface Props {
  onEnable: () => Promise<void>;
}

export function PermissionDialog({ onEnable }: Props) {
  return (
    <div className="permission-card" role="dialog" aria-label="Enable camera and microphone">
      <div className="greeting">Hi, I am U.</div>
      <p style={{ margin: 0, maxWidth: '44ch' }}>
        I can join this call and reason about observable events while showing my
        evidence and uncertainty.
      </p>
      <button type="button" className="primary" onClick={() => void onEnable()}>
        Enable camera and microphone
      </button>
      <p className="privacy">
        Privacy: video and audio are not stored by default. Hand tracking runs in
        your browser; only structured events (never frames) are sent to the
        backend.
      </p>
    </div>
  );
}
