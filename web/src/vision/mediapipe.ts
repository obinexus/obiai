/**
 * MediaPipe Hands loader.
 *
 * Adapted from the working prototype (poc/www/index.html): the MediaPipe
 * solution scripts attach globals (`Hands`, `HAND_CONNECTIONS`,
 * `drawConnectors`, `drawLandmarks`), so we load them as scripts — served
 * locally from /mediapipe/* (copied out of node_modules at build time) —
 * instead of fighting the UMD bundle through the module graph.
 * Set VITE_MEDIAPIPE_BASE to a CDN base URL to restore the prototype's
 * remote-loading behavior.
 */

export interface MPLandmark {
  x: number;
  y: number;
  z: number;
}

export interface MPResults {
  multiHandLandmarks?: MPLandmark[][];
  multiHandedness?: { score: number; label: string; index: number }[];
}

export interface MPHands {
  setOptions(options: Record<string, unknown>): void;
  onResults(callback: (results: MPResults) => void): void;
  send(input: { image: HTMLVideoElement }): Promise<void>;
  close(): Promise<void>;
}

const HANDS_BASE: string =
  (import.meta.env.VITE_MEDIAPIPE_BASE as string | undefined) ?? '/mediapipe/hands/';
const DRAWING_BASE = '/mediapipe/drawing_utils/';

let loading: Promise<void> | null = null;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.crossOrigin = 'anonymous';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
}

export async function loadMediaPipe(): Promise<void> {
  loading ??= (async () => {
    await loadScript(`${HANDS_BASE}hands.js`);
    await loadScript(`${DRAWING_BASE}drawing_utils.js`);
  })();
  return loading;
}

type MediaPipeWindow = Window & {
  Hands: new (config: { locateFile: (file: string) => string }) => MPHands;
  HAND_CONNECTIONS: unknown;
  drawConnectors: (
    ctx: CanvasRenderingContext2D,
    landmarks: MPLandmark[],
    connections: unknown,
    style: Record<string, unknown>,
  ) => void;
  drawLandmarks: (
    ctx: CanvasRenderingContext2D,
    landmarks: MPLandmark[],
    style: Record<string, unknown>,
  ) => void;
};

function mp(): MediaPipeWindow {
  return window as unknown as MediaPipeWindow;
}

/** Options match the prototype (poc/www/index.html) except maxNumHands: 1. */
export function createHands(onResults: (results: MPResults) => void): MPHands {
  const hands = new (mp().Hands)({ locateFile: (file) => `${HANDS_BASE}${file}` });
  hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 1,
    minDetectionConfidence: 0.65,
    minTrackingConfidence: 0.65,
  });
  hands.onResults(onResults);
  return hands;
}

/** Skeleton overlay, same style as the prototype's ready screen. */
export function drawHandSkeleton(
  ctx: CanvasRenderingContext2D,
  results: MPResults,
): void {
  const w = mp();
  for (const landmarks of results.multiHandLandmarks ?? []) {
    w.drawConnectors(ctx, landmarks, w.HAND_CONNECTIONS, {
      color: 'rgba(45, 212, 191, 0.65)',
      lineWidth: 2,
    });
    w.drawLandmarks(ctx, landmarks, { color: '#2dd4bf', lineWidth: 1, radius: 3 });
  }
}
