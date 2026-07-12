import { useRef } from 'react';

import { useAppStore } from '../store';
import { useVision } from '../vision/useVision';
import { DeviceControls } from './DeviceControls';
import { LocalVideoTile } from './LocalVideoTile';
import { PermissionDialog } from './PermissionDialog';
import { SessionControls } from './SessionControls';

export function VideoRoom() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { enable, disable } = useVision(videoRef, canvasRef);
  const cameraActive = useAppStore((s) => s.cameraActive);

  return (
    <section className="card" aria-label="Video room">
      <h2>Local video</h2>
      <div className="video-tile">
        <LocalVideoTile videoRef={videoRef} canvasRef={canvasRef} />
        {!cameraActive && <PermissionDialog onEnable={enable} />}
      </div>
      <div className="controls-row">
        <DeviceControls onDisable={disable} onEnable={enable} />
        <SessionControls />
      </div>
    </section>
  );
}
