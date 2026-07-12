import { useEffect, useRef } from 'react';

import { useAppStore } from '../store';
import { ChatComposer } from './ChatComposer';

export function TranscriptPanel() {
  const transcript = useAppStore((s) => s.transcript);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [transcript.length]);

  return (
    <section className="card" aria-label="Live transcript">
      <h2>Live transcript</h2>
      <div className="transcript" ref={listRef} aria-live="polite" aria-relevant="additions">
        {transcript.length === 0 && (
          <p className="status-text">Start a session and U will introduce itself here.</p>
        )}
        {transcript.map((entry, index) => (
          <div key={index} className={`entry ${entry.role}`}>
            <span className="who">{entry.role === 'u' ? 'U' : 'You'}</span>
            {entry.text}
          </div>
        ))}
      </div>
      <ChatComposer />
    </section>
  );
}
