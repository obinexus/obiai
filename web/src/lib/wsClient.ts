import type { ClientEvent, ConnectionStatus, ServerEvent } from './types';

const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 15000;
/** Server closes with this code when the session id is unknown (e.g. after a
 * backend restart wiped the in-memory store). Reconnecting is pointless. */
export const SESSION_NOT_FOUND_CODE = 4404;

export class UWebSocket {
  private ws: WebSocket | null = null;
  private backoffMs = INITIAL_BACKOFF_MS;
  private outbound: string[] = [];
  private closedByUser = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly sessionId: string,
    private readonly onEvent: (event: ServerEvent) => void,
    private readonly onStatus: (status: ConnectionStatus) => void,
    private readonly onSessionLost: () => void,
  ) {}

  connect(): void {
    this.closedByUser = false;
    this.onStatus('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}/ws/sessions/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.backoffMs = INITIAL_BACKOFF_MS;
      this.onStatus('connected');
      for (const message of this.outbound.splice(0)) {
        this.ws?.send(message);
      }
    };

    this.ws.onmessage = (message: MessageEvent<string>) => {
      try {
        this.onEvent(JSON.parse(message.data) as ServerEvent);
      } catch {
        // Malformed frame; ignore rather than crash the UI.
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.ws = null;
      this.onStatus('disconnected');
      if (event.code === SESSION_NOT_FOUND_CODE) {
        this.onSessionLost();
        return;
      }
      if (!this.closedByUser) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose always follows; reconnect is handled there.
    };
  }

  send(event: ClientEvent): void {
    const message = JSON.stringify(event);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      this.outbound.push(message);
    }
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close(1000, 'client closed');
    this.ws = null;
    this.onStatus('disconnected');
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.backoffMs);
    this.backoffMs = Math.min(this.backoffMs * 2, MAX_BACKOFF_MS);
  }
}
