import { useAppStore } from '../store';

export function HandTrackingToggle() {
  const enabled = useAppStore((s) => s.handTrackingEnabled);
  const toggleHandTracking = useAppStore((s) => s.toggleHandTracking);

  return (
    <label className="toggle-control">
      <input type="checkbox" checked={enabled} onChange={toggleHandTracking} />
      <span>Hand tracking</span>
    </label>
  );
}
