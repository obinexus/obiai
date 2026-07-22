import { useEffect, useRef } from 'react';

import { useAppStore } from '../store';
import { ChatComposer } from './ChatComposer';

const RESPONSE_SOURCE_LABELS: Record<string, string> = {
  governance_pipeline: 'Governance',
  trained_uai: 'Trained model',
  seeded_uagentic: 'Seeded',
  transcript_confidence_guard: 'Low confidence',
  static_greeting: 'Greeting',
};

export function TranscriptPanel() {
  const transcript = useAppStore((s) => s.transcript);
  const pendingAssistantResponse = useAppStore((s) => s.pendingAssistantResponse);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [pendingAssistantResponse, transcript.length]);

  return (
    <section className="card" aria-label="Live transcript">
      <h2>Live transcript</h2>
      <div className="transcript" ref={listRef} aria-live="polite" aria-relevant="additions">
        {transcript.length === 0 && (
          <p className="status-text">Start a session and U will introduce itself here.</p>
        )}
        {transcript.map((entry, index) => {
          const sourceLabel =
            entry.role === 'u' && entry.responseSource
              ? (RESPONSE_SOURCE_LABELS[entry.responseSource] ?? entry.responseSource)
              : null;
          return (
            <div key={index} className={`entry ${entry.role}`}>
              <span className="who">
                {entry.role === 'u' ? 'U' : 'You'}
                {sourceLabel && (
                  <span
                    className={`source-tag source-${entry.responseSource}`}
                    title={entry.modelRunId ? `Model run: ${entry.modelRunId}` : undefined}
                  >
                    {sourceLabel}
                  </span>
                )}
              </span>
              {entry.text}
            </div>
          );
        })}
        {pendingAssistantResponse && (
          <div className="entry u pending">
            <span className="who">U</span>
            Thinking…
          </div>
        )}
      </div>
      <ChatComposer />
    </section>
  );
}
