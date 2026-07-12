import { FormEvent, useState } from 'react';

import { useAppStore } from '../store';

export function ChatComposer() {
  const [text, setText] = useState('');
  const sendChat = useAppStore((s) => s.sendChat);
  const sessionActive = useAppStore((s) => s.sessionActive);

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
        placeholder={sessionActive ? 'Ask U…' : 'Start a session to chat with U'}
        aria-label="Ask U"
        disabled={!sessionActive}
      />
      <button type="submit" disabled={!sessionActive || text.trim().length === 0}>
        Send
      </button>
    </form>
  );
}
