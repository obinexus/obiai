import { useCallback } from 'react';

const SIZES = ['0.9rem', '1rem', '1.15rem', '1.35rem'];

export function AccessibilityControls() {
  const adjust = useCallback((direction: 1 | -1) => {
    const root = document.documentElement;
    const current = getComputedStyle(root).getPropertyValue('--transcript-size').trim();
    const index = Math.max(0, SIZES.indexOf(current));
    const next = SIZES[Math.min(SIZES.length - 1, Math.max(0, index + direction))];
    root.style.setProperty('--transcript-size', next);
  }, []);

  return (
    <div className="a11y-controls" role="group" aria-label="Transcript text size">
      <span aria-hidden="true">Text</span>
      <button type="button" aria-label="Decrease transcript text size" onClick={() => adjust(-1)}>
        A−
      </button>
      <button type="button" aria-label="Increase transcript text size" onClick={() => adjust(1)}>
        A+
      </button>
    </div>
  );
}
