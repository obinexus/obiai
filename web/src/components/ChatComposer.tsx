import { FormEvent, useState } from 'react';

import { useAppStore } from '../store';

export function ChatComposer() {
  const [text, setText] = useState('');
  const sendChat = useAppStore((s) => s.sendChat);
  const sessionActive = useAppStore((s) => s.sessionActive);
  const pendingAssistantResponse = useAppStore((s) => s.pendingAssistantResponse);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (text.trim().length === 0) return;
    sendChat(text.trim());
    setText('');
  }

  return (
    <form className="composer" onSubmit={submit}>
      <input
        type="text"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={
          pendingAssistantResponse
            ? 'U is replying…'
            : sessionActive
              ? 'Ask U…'
              : 'Start a session to chat with U'
        }
        aria-label="Ask U"
        disabled={!sessionActive || pendingAssistantResponse}
      />
      <button
        type="submit"
        disabled={!sessionActive || pendingAssistantResponse || text.trim().length === 0}
      >
        {pendingAssistantResponse ? 'Waiting' : 'Send'}
      </button>
    </form>
  );
}
