import { useAppStore } from '../store';

export function CaptionsToggle() {
  const captionsEnabled = useAppStore((s) => s.speech.captionsEnabled);
  const toggleCaptions = useAppStore((s) => s.toggleCaptions);

  return (
    <button
      type="button"
      aria-pressed={captionsEnabled}
      onClick={toggleCaptions}
      title="Live captions can stay on independently of audio"
    >
      Captions: {captionsEnabled ? 'On' : 'Off'}
    </button>
  );
}
