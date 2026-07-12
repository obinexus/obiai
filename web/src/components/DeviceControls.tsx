import { useAppStore } from '../store';

interface Props {
  onEnable: () => Promise<void>;
  onDisable: () => void;
}

export function DeviceControls({ onEnable, onDisable }: Props) {
  const cameraActive = useAppStore((s) => s.cameraActive);
  const micActive = useAppStore((s) => s.micActive);

  return (
    <>
      {cameraActive ? (
        <button type="button" onClick={onDisable}>
          Turn camera off
        </button>
      ) : (
        <button type="button" onClick={() => void onEnable()}>
          Enable camera and microphone
        </button>
      )}
      <span className="status-text" role="status">
        Camera: {cameraActive ? 'Active' : 'Off'} · Microphone: {micActive ? 'Active' : 'Off'}
      </span>
    </>
  );
}
