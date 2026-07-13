import { useCallback, useEffect, useRef } from 'react';

import { useAppStore } from '../store';
import { isSpeechRecognitionSupported, SpeechRecognizer } from './speechRecognition';

export interface SpeechHandle {
  start: () => void;
  stop: () => void;
}

/** Wires the browser speech recognizer to the store: recognized text goes
 * out as transcript.partial / transcript.final WS events; nothing else. */
export function useSpeech(): SpeechHandle {
  const recognizerRef = useRef<SpeechRecognizer | null>(null);
  const setSpeech = useAppStore((s) => s.setSpeech);
  const submitTranscriptPartial = useAppStore((s) => s.submitTranscriptPartial);
  const submitTranscriptFinal = useAppStore((s) => s.submitTranscriptFinal);
  const sessionActive = useAppStore((s) => s.sessionActive);

  useEffect(() => {
    setSpeech({ supported: isSpeechRecognitionSupported() });
  }, [setSpeech]);

  const ensureRecognizer = useCallback((): SpeechRecognizer => {
    recognizerRef.current ??= new SpeechRecognizer({
      onPartial: submitTranscriptPartial,
      onFinal: submitTranscriptFinal,
      onListeningChange: (listening) => setSpeech({ listening }),
      onError: (reason, message) => {
        setSpeech({ listening: false, ...(reason === 'unsupported' ? { supported: false } : {}) });
        useAppStore.setState({ lastError: `Speech recognition: ${message}` });
      },
    });
    return recognizerRef.current;
  }, [setSpeech, submitTranscriptFinal, submitTranscriptPartial]);

  const start = useCallback(() => {
    ensureRecognizer().start();
  }, [ensureRecognizer]);

  const stop = useCallback(() => {
    recognizerRef.current?.stop();
  }, []);

  // A session end should stop the microphone even if the user forgets to.
  useEffect(() => {
    if (!sessionActive) stop();
  }, [sessionActive, stop]);

  useEffect(() => stop, [stop]); // cleanup on unmount

  return { start, stop };
}
