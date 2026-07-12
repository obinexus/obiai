import { create } from 'zustand';

import { createSession, deleteSession } from '../lib/api';
import type {
  ConnectionStatus,
  Decision,
  Observation,
  ObservationIn,
  ServerEvent,
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

  startSession: () => Promise<void>;
  endSession: () => Promise<void>;
  sendChat: (text: string) => void;
  submitObservation: (observation: ObservationIn) => void;
  setUState: (state: UState) => void;
  setMediaActive: (camera: boolean, mic: boolean) => void;
  setVision: (update: Partial<VisionStatus>) => void;
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

    setUState: (uState: UState) => set({ uState }),

    setMediaActive: (cameraActive: boolean, micActive: boolean) =>
      set({ cameraActive, micActive }),

    setVision: (update: Partial<VisionStatus>) =>
      set((state) => ({ vision: { ...state.vision, ...update } })),
  };
});
