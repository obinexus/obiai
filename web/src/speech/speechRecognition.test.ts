import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { isSpeechRecognitionSupported, SpeechRecognizer } from './speechRecognition';

/** A minimal fake matching the SpeechRecognition surface this module uses. */
class FakeSpeechRecognition implements Partial<SpeechRecognition> {
  static instances: FakeSpeechRecognition[] = [];

  continuous = false;
  interimResults = false;
  lang = '';
  maxAlternatives = 1;
  onresult: ((event: SpeechRecognitionEvent) => void) | null = null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null = null;
  onend: (() => void) | null = null;
  onstart: (() => void) | null = null;
  started = 0;
  stopped = 0;

  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }

  start(): void {
    this.started += 1;
    this.onstart?.();
  }

  stop(): void {
    this.stopped += 1;
    this.onend?.();
  }

  emitResult(results: { transcript: string; confidence: number; isFinal: boolean }[]): void {
    const list = results.map((r) => {
      const alt = { transcript: r.transcript, confidence: r.confidence };
      const arr = [alt] as unknown as SpeechRecognitionResult;
      Object.defineProperty(arr, 'isFinal', { value: r.isFinal });
      return arr;
    });
    const event = {
      resultIndex: 0,
      results: list as unknown as SpeechRecognitionResultList,
    } as SpeechRecognitionEvent;
    this.onresult?.(event);
  }

  emitError(error: string, message = ''): void {
    this.onerror?.({ error, message } as SpeechRecognitionErrorEvent);
  }
}

function lastInstance(): FakeSpeechRecognition {
  const instance = FakeSpeechRecognition.instances.at(-1);
  if (!instance) throw new Error('no SpeechRecognition instance created');
  return instance;
}

describe('speechRecognition', () => {
  beforeEach(() => {
    FakeSpeechRecognition.instances = [];
    vi.stubGlobal('window', { SpeechRecognition: FakeSpeechRecognition });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reports support based on the global constructor', () => {
    expect(isSpeechRecognitionSupported()).toBe(true);
    vi.stubGlobal('window', {});
    expect(isSpeechRecognitionSupported()).toBe(false);
  });

  it('reports unsupported via onError when no constructor exists', () => {
    vi.stubGlobal('window', {});
    const onError = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial: vi.fn(),
      onFinal: vi.fn(),
      onError,
      onListeningChange: vi.fn(),
    });
    recognizer.start();
    expect(onError).toHaveBeenCalledWith('unsupported', expect.any(String));
  });

  it('routes interim results to onPartial and final results to onFinal', () => {
    const onPartial = vi.fn();
    const onFinal = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial,
      onFinal,
      onError: vi.fn(),
      onListeningChange: vi.fn(),
    });
    recognizer.start();

    lastInstance().emitResult([{ transcript: 'can you inspect', confidence: 0, isFinal: false }]);
    expect(onPartial).toHaveBeenCalledTimes(1);
    expect(onPartial.mock.calls[0][0].text).toBe('can you inspect');
    expect(onPartial.mock.calls[0][0].final).toBe(false);
    expect(onFinal).not.toHaveBeenCalled();

    lastInstance().emitResult([
      { transcript: 'can you inspect this error', confidence: 0.93, isFinal: true },
    ]);
    expect(onFinal).toHaveBeenCalledTimes(1);
    expect(onFinal.mock.calls[0][0].text).toBe('can you inspect this error');
    expect(onFinal.mock.calls[0][0].confidence).toBeCloseTo(0.93);
    expect(onFinal.mock.calls[0][0].final).toBe(true);
  });

  it('ignores empty transcripts', () => {
    const onPartial = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial,
      onFinal: vi.fn(),
      onError: vi.fn(),
      onListeningChange: vi.fn(),
    });
    recognizer.start();
    lastInstance().emitResult([{ transcript: '   ', confidence: 0.5, isFinal: false }]);
    expect(onPartial).not.toHaveBeenCalled();
  });

  it('auto-restarts on end while still wanted, but not after stop()', () => {
    const onListeningChange = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial: vi.fn(),
      onFinal: vi.fn(),
      onError: vi.fn(),
      onListeningChange,
    });
    recognizer.start();
    expect(FakeSpeechRecognition.instances).toHaveLength(1);

    // Chrome ends the session on its own (e.g. after a pause); should restart.
    lastInstance().onend?.();
    expect(FakeSpeechRecognition.instances).toHaveLength(2);
    expect(onListeningChange).toHaveBeenCalledWith(true);

    recognizer.stop();
    expect(FakeSpeechRecognition.instances).toHaveLength(2); // no relaunch after explicit stop
    expect(onListeningChange).toHaveBeenLastCalledWith(false);
  });

  it('treats no-speech and aborted errors as benign', () => {
    const onError = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial: vi.fn(),
      onFinal: vi.fn(),
      onError,
      onListeningChange: vi.fn(),
    });
    recognizer.start();
    lastInstance().emitError('no-speech');
    lastInstance().emitError('aborted');
    expect(onError).not.toHaveBeenCalled();
  });

  it('surfaces permission errors as not-allowed and stops retrying', () => {
    const onError = vi.fn();
    const recognizer = new SpeechRecognizer({
      onPartial: vi.fn(),
      onFinal: vi.fn(),
      onError,
      onListeningChange: vi.fn(),
    });
    recognizer.start();
    lastInstance().emitError('not-allowed', 'permission denied');
    expect(onError).toHaveBeenCalledWith('not-allowed', 'permission denied');

    lastInstance().onend?.();
    expect(FakeSpeechRecognition.instances).toHaveLength(1); // did not relaunch
  });
});
