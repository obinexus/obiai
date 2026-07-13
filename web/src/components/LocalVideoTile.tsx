import { useAppStore } from '../store';

interface Props {
  videoRef: React.RefObject<HTMLVideoElement>;
  canvasRef: React.RefObject<HTMLCanvasElement>;
}

export function LocalVideoTile({ videoRef, canvasRef }: Props) {
  const vision = useAppStore((s) => s.vision);
  const cameraActive = useAppStore((s) => s.cameraActive);
  const speech = useAppStore((s) => s.speech);

  return (
    <>
      {/* Frames stay local: only structured events are sent to the backend. */}
      <video ref={videoRef} muted playsInline aria-label="Local camera preview" />
      <canvas ref={canvasRef} aria-hidden="true" />
      {cameraActive && (
        <div className="video-badges" role="status" aria-live="polite">
          <span className="badge">
            Hand tracking: <strong>{vision.trackingActive ? 'active' : 'searching…'}</strong>
          </span>
          <span className="badge">
            Classifier confidence: <strong>{vision.liveConfidence.toFixed(2)}</strong>
          </span>
          <span className="badge">
            Hand raised: <strong>{vision.handRaised ? 'YES' : 'no'}</strong>
          </span>
          <span className="badge">Processing locally — frames are not uploaded</span>
        </div>
      )}
      {speech.captionsEnabled && (
        <div className="caption-bar" aria-live="polite" aria-label="Live captions">
          {speech.liveCaption || (speech.listening ? '…' : '')}
        </div>
      )}
    </>
  );
}
