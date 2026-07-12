import { useCallback, useEffect, useRef } from 'react';

import { useAppStore } from '../store';
import { startCapture, startFramePump, stopCapture } from './capture';
import {
  ClassifierTick,
  HandFrame,
  HandRaiseClassifier,
} from './handRaiseClassifier';
import {
  createHands,
  drawHandSkeleton,
  loadMediaPipe,
  MPHands,
  MPResults,
} from './mediapipe';
import { observationFromHandRaise } from './observationEmitter';

export interface VisionHandle {
  enable: () => Promise<void>;
  disable: () => void;
}

export function useVision(
  videoRef: React.RefObject<HTMLVideoElement>,
  canvasRef: React.RefObject<HTMLCanvasElement>,
): VisionHandle {
  const streamRef = useRef<MediaStream | null>(null);
  const handsRef = useRef<MPHands | null>(null);
  const stopPumpRef = useRef<(() => void) | null>(null);
  const classifierRef = useRef(new HandRaiseClassifier());

  const setUState = useAppStore((s) => s.setUState);
  const setMediaActive = useAppStore((s) => s.setMediaActive);
  const setVision = useAppStore((s) => s.setVision);

  const onResults = useCallback(
    (results: MPResults) => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (canvas && video && video.videoWidth > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          drawHandSkeleton(ctx, results);
        }
      }

      const landmarks = results.multiHandLandmarks?.[0];
      const score = results.multiHandedness?.[0]?.score ?? 0;
      const frame: HandFrame | null = landmarks ? { landmarks, score } : null;
      const tick: ClassifierTick = classifierRef.current.update(frame, performance.now());

      setVision({
        trackingActive: tick.trackingActive,
        liveConfidence: Math.round(tick.confidence * 100) / 100,
        handRaised: tick.raisedNow,
      });

      if (tick.event) {
        const store = useAppStore.getState();
        if (store.sessionActive) {
          store.submitObservation(observationFromHandRaise(tick.event));
        }
      }
    },
    [canvasRef, setVision, videoRef],
  );

  const enable = useCallback(async () => {
    const video = videoRef.current;
    if (!video || streamRef.current) return;
    setUState('requesting_permission');
    try {
      const [stream] = await Promise.all([startCapture(video), loadMediaPipe()]);
      streamRef.current = stream;
      const hands = createHands(onResults);
      handsRef.current = hands;
      stopPumpRef.current = startFramePump(video, () => hands.send({ image: video }));
      setMediaActive(true, true);
      setUState(useAppStore.getState().sessionActive ? 'listening' : 'idle');
    } catch (error) {
      setUState('error');
      useAppStore.setState({
        lastError:
          error instanceof Error
            ? `Camera/microphone unavailable: ${error.message}`
            : 'Camera/microphone unavailable.',
      });
    }
  }, [onResults, setMediaActive, setUState, videoRef]);

  const disable = useCallback(() => {
    stopPumpRef.current?.();
    stopPumpRef.current = null;
    void handsRef.current?.close();
    handsRef.current = null;
    if (videoRef.current) {
      stopCapture(videoRef.current, streamRef.current);
    }
    streamRef.current = null;
    setMediaActive(false, false);
    setVision({ trackingActive: false, liveConfidence: 0, handRaised: false });
  }, [setMediaActive, setVision, videoRef]);

  useEffect(() => disable, [disable]); // cleanup on unmount

  return { enable, disable };
}
