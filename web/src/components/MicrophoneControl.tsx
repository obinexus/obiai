import type { SpeechHandle } from '../speech/useSpeech';
import { useAppStore } from '../store';

interface Props {
  speech: SpeechHandle;
}

export function MicrophoneControl({ speech }: Props) {
  const sessionActive = useAppStore((s) => s.sessionActive);
  const status = useAppStore((s) => s.speech);

  if (!status.supported) {
    return (
      <span className="status-text" role="status">
        Voice input: not supported in this browser
      </span>
    );
  }

  return (
    <>
      {status.listening ? (
        <button type="button" onClick={speech.stop} disabled={!sessionActive}>
          Stop listening
        </button>
      ) : (
        <button type="button" onClick={speech.start} disabled={!sessionActive}>
          Start listening
        </button>
      )}
      <span className="status-text" role="status">
        Voice input: {status.listening ? 'Listening' : 'Off'}
      </span>
    </>
  );
}
