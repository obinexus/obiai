/** Minimal REST helpers (everything realtime rides the WebSocket). */

import type { UModelProfile } from './types';

export async function createSession(): Promise<string> {
  const response = await fetch('/sessions', { method: 'POST' });
  if (!response.ok) {
    throw new Error(`Failed to create session: HTTP ${response.status}`);
  }
  const payload = (await response.json()) as { session_id: string };
  return payload.session_id;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 404) {
    throw new Error(`Failed to delete session: HTTP ${response.status}`);
  }
}

export async function fetchUModelProfile(): Promise<UModelProfile> {
  const response = await fetch('/model/uagentic');
  if (!response.ok) {
    throw new Error(`Failed to load U model profile: HTTP ${response.status}`);
  }
  return (await response.json()) as UModelProfile;
}
