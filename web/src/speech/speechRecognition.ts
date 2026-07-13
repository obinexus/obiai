import type { TranscriptSegment } from '../lib/types';

/**
 * Wraps the browser's Web Speech API (SpeechRecognition /
 * webkitSpeechRecognition) for continuous, real-time voice-to-text.
 *
 * Recognition runs entirely in the browser — only recognized text is ever
 * handed to callers (see observationEmitter-style callbacks below); no audio
 * leaves this module. Chrome's implementation streams audio to a Google
 * speech service to produce that text, but the raw audio itself never
 * touches the U backend.
 *
 * Chrome's recognizer stops after a pause or a few minutes even in
 * "continuous" mode; this wrapper auto-restarts unless the caller explicitly
 * stopped it, so a video-call-style always-listening experience holds up.
 */

export type SpeechErrorReason = 'not-allowed' | 'audio-capture' | 'unsupported' | 'other';

export interface SpeechRecognizerCallbacks {
  onPartial: (segment: TranscriptSegment) => void;
  onFinal: (segment: TranscriptSegment) => void;
  onError: (reason: SpeechErrorReason, message: string) => void;
  onListeningChange: (listening: boolean) => void;
}

const FATAL_ERRORS = new Set(['not-allowed', 'audio-capture', 'service-not-allowed']);

function getConstructor(): SpeechRecognitionConstructor | null {
  const w = window as unknown as Window;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getConstructor() !== null;
}

export class SpeechRecognizer {
  private recognition: SpeechRecognition | null = null;
  private wantsListening = false;
  private startedAtMs = 0;

  constructor(
    private readonly callbacks: SpeechRecognizerCallbacks,
    private readonly lang = 'en-US',
  ) {}

  start(): void {
    const Ctor = getConstructor();
    if (!Ctor) {
      this.callbacks.onError('unsupported', 'Speech recognition is not supported in this browser.');
      return;
    }
    if (this.recognition) return; // already running

    this.wantsListening = true;
    this.launch(Ctor);
  }

  stop(): void {
    this.wantsListening = false;
    this.recognition?.stop();
  }

  private launch(Ctor: SpeechRecognitionConstructor): void {
    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = this.lang;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      this.startedAtMs = performance.now();
      this.callbacks.onListeningChange(true);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const alternative = result[0];
        if (!alternative || alternative.transcript.trim().length === 0) continue;
        const segment: TranscriptSegment = {
          text: alternative.transcript.trim(),
          start_ms: Math.max(0, Math.round(performance.now() - this.startedAtMs) - 500),
          end_ms: Math.max(0, Math.round(performance.now() - this.startedAtMs)),
          confidence: Number.isFinite(alternative.confidence) && alternative.confidence > 0
            ? alternative.confidence
            : 0.85, // Chrome often reports 0 confidence on interim results.
          final: result.isFinal,
        };
        if (result.isFinal) {
          this.callbacks.onFinal(segment);
        } else {
          this.callbacks.onPartial(segment);
        }
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'no-speech' || event.error === 'aborted') {
        return; // benign; onend will restart if still wanted
      }
      const reason: SpeechErrorReason = FATAL_ERRORS.has(event.error) ? 'not-allowed' : 'other';
      if (reason === 'not-allowed') {
        this.wantsListening = false;
      }
      this.callbacks.onError(reason, event.message || event.error);
    };

    recognition.onend = () => {
      this.recognition = null;
      this.callbacks.onListeningChange(false);
      if (this.wantsListening) {
        this.launch(Ctor); // Chrome stops after silence/timeout; resume.
      }
    };

    this.recognition = recognition;
    try {
      recognition.start();
    } catch {
      // start() throws if called while already starting; the next onend
      // (if any) or a fresh user click will recover.
    }
  }
}
