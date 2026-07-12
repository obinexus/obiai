/** Camera/microphone capture and the frame pump feeding MediaPipe. */

export async function startCapture(video: HTMLVideoElement): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error(
      'getUserMedia is not available — open the app via http://localhost or https://',
    );
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 } },
    audio: true,
  });
  video.srcObject = stream;
  await video.play();
  return stream;
}

export function stopCapture(video: HTMLVideoElement, stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
  video.srcObject = null;
}

/**
 * Drives `sendFrame` from requestAnimationFrame at a bounded rate. Only
 * landmarks derived from these frames ever leave the browser — the frames
 * themselves stay local.
 */
export function startFramePump(
  video: HTMLVideoElement,
  sendFrame: () => Promise<void>,
  fps = 20,
): () => void {
  let running = true;
  let busy = false;
  let lastSent = 0;
  const interval = 1000 / fps;

  const tick = (timestamp: number) => {
    if (!running) return;
    if (!busy && timestamp - lastSent >= interval && video.readyState >= 2) {
      lastSent = timestamp;
      busy = true;
      void sendFrame().finally(() => {
        busy = false;
      });
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  return () => {
    running = false;
  };
}
