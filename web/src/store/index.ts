import { create } from 'zustand';

import { createSession, deleteSession } from '../lib/api';
import type {
  ConnectionStatus,
  Decision,
  Observation,
  ObservationIn,
  ServerEvent,
  TranscriptSegment,
  UState,
} from '../lib/types';
import { UWebSocket } from '../lib/wsClient';

export interface TranscriptEntry {
  role: 'user' | 'u';
  text: string;
  timestamp: string;
}

export interface VisionStatus {
  trackingActive: boolean;
  liveConfidence: number;
  handRaised: boolean;
}

export interface SpeechStatus {
  /** Whether the browser's speech recognizer is actively listening. */
  listening: boolean;
  /** The current interim (not-yet-final) caption, or '' when idle. */
  liveCaption: string;
  /** Live captions are shown independently of whether recognition is on. */
  captionsEnabled: boolean;
  supported: boolean;
}

interface AppState {
  sessionId: string | null;
  sessionActive: boolean;
  connection: ConnectionStatus;
  uState: UState;
  transcript: TranscriptEntry[];
  decisions: Decision[];
  latestDecision: Decision | null;
  lastObservation: Observation | null;
  lastError: string | null;
  cameraActive: boolean;
  micActive: boolean;
  vision: VisionStatus;
  speech: SpeechStatus;

  startSession: () => Promise<void>;
  endSession: () => Promise<void>;
  sendChat: (text: string) => void;
  submitObservation: (observation: ObservationIn) => void;
  submitTranscriptPartial: (segment: TranscriptSegment) => void;
  submitTranscriptFinal: (segment: TranscriptSegment) => void;
  setUState: (state: UState) => void;
  setMediaActive: (camera: boolean, mic: boolean) => void;
  setVision: (update: Partial<VisionStatus>) => void;
  setSpeech: (update: Partial<SpeechStatus>) => void;
  toggleCaptions: () => void;
}

let socket: UWebSocket | null = null;

function nowIso(): string {
  return new Date().toISOString();
}

export const useAppStore = create<AppState>((set, get) => {
  function handleServerEvent(event: ServerEvent): void {
    switch (event.type) {
      case 'session.ready':
        set({ uState: 'listening' });
        break;
      case 'agent.message':
        set((state) => ({
          transcript: [
            ...state.transcript,
            { role: 'u', text: event.text, timestamp: nowIso() },
          ],
          uState:
            state.uState === 'waiting_clarification' ? 'waiting_clarification' : 'listening',
        }));
        break;
      case 'observation.created':
        set({ lastObservation: event.observation, uState: 'observing' });
        break;
      case 'reasoning.started':
        set({ uState: 'reasoning' });
        break;
      case 'decision.created':
        set((state) => ({
          decisions: [...state.decisions, event.decision],
          latestDecision: event.decision,
          uState: event.decision.state === 'MAYBE' ? 'waiting_clarification' : 'listening',
        }));
        break;
      case 'audit.created':
        break; // audits already arrive inside decision.created
      case 'transcript.partial':
        set((state) => ({ speech: { ...state.speech, liveCaption: event.segment.text } }));
        break;
      case 'transcript.final':
        set((state) => ({
          transcript: [
            ...state.transcript,
            { role: 'user', text: event.segment.text, timestamp: nowIso() },
          ],
          speech: { ...state.speech, liveCaption: '' },
        }));
        break;
      case 'error':
        set({ lastError: event.message });
        break;
    }
  }

  function handleStatus(status: ConnectionStatus): void {
    set({ connection: status });
    if (status === 'disconnected' && get().sessionActive) {
      set({ uState: 'disconnected' });
    }
  }

  function handleSessionLost(): void {
    socket = null;
    set({
      sessionActive: false,
      sessionId: null,
      uState: 'error',
      lastError: 'Session no longer exists on the server. Start a new session.',
    });
  }

  return {
    sessionId: null,
    sessionActive: false,
    connection: 'disconnected',
    uState: 'idle',
    transcript: [],
    decisions: [],
    latestDecision: null,
    lastObservation: null,
    lastError: null,
    cameraActive: false,
    micActive: false,
    vision: { trackingActive: false, liveConfidence: 0, handRaised: false },
    speech: { listening: false, liveCaption: '', captionsEnabled: true, supported: false },

    startSession: async () => {
      if (get().sessionActive) return;
      set({ uState: 'connecting', lastError: null, transcript: [], decisions: [], latestDecision: null });
      try {
        const sessionId = await createSession();
        socket = new UWebSocket(sessionId, handleServerEvent, handleStatus, handleSessionLost);
        socket.connect();
        socket.send({ type: 'session.start' });
        set({ sessionId, sessionActive: true });
      } catch (error) {
        set({
          uState: 'error',
          lastError: error instanceof Error ? error.message : String(error),
        });
      }
    },

    endSession: async () => {
      const { sessionId } = get();
      socket?.send({ type: 'session.end' });
      socket?.close();
      socket = null;
      if (sessionId) {
        try {
          await deleteSession(sessionId);
        } catch {
          // Session data is in-memory server-side; deletion failure is non-fatal.
        }
      }
      set({
        sessionId: null,
        sessionActive: false,
        uState: 'idle',
        lastObservation: null,
      });
    },

    sendChat: (text: string) => {
      if (!get().sessionActive || text.trim().length === 0) return;
      socket?.send({ type: 'chat.message', text });
      set((state) => ({
        transcript: [...state.transcript, { role: 'user', text, timestamp: nowIso() }],
      }));
    },

    submitObservation: (observation: ObservationIn) => {
      if (!get().sessionActive) return;
      socket?.send({ type: 'observation.submit', observation });
    },

    submitTranscriptPartial: (segment: TranscriptSegment) => {
      if (!get().sessionActive) return;
      socket?.send({ type: 'transcript.partial', segment });
      set((state) => ({ speech: { ...state.speech, liveCaption: segment.text } }));
    },

    submitTranscriptFinal: (segment: TranscriptSegment) => {
      if (!get().sessionActive) return;
      socket?.send({ type: 'transcript.final', segment });
      // The server echoes transcript.final, which appends the transcript
      // entry; clear the live caption immediately for a responsive feel.
      set((state) => ({ speech: { ...state.speech, liveCaption: '' } }));
    },

    setUState: (uState: UState) => set({ uState }),

    setMediaActive: (cameraActive: boolean, micActive: boolean) =>
      set({ cameraActive, micActive }),

    setVision: (update: Partial<VisionStatus>) =>
      set((state) => ({ vision: { ...state.vision, ...update } })),

    setSpeech: (update: Partial<SpeechStatus>) =>
      set((state) => ({ speech: { ...state.speech, ...update } })),

    toggleCaptions: () =>
      set((state) => ({
        speech: { ...state.speech, captionsEnabled: !state.speech.captionsEnabled },
      })),
  };
});
