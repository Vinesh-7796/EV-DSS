export type WsMessage =
  | { type: "connected"; session_id: string; timestamp: number }
  | { type: "processing"; session_id: string; timestamp: number }
  | { type: "chunk"; content: string; session_id: string; timestamp: number }
  | { type: "complete"; session_id: string; timestamp: number; metadata?: Record<string, unknown> }
  | { type: "error"; detail: string; session_id: string };

type MessageHandler = (msg: WsMessage) => void;
type StatusHandler = (status: ConnectionStatus) => void;

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private messageHandlers: MessageHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private _status: ConnectionStatus = "disconnected";
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private shouldReconnect = true;

  constructor(sessionId?: string) {
    const params = sessionId ? `?session_id=${sessionId}` : "";
    this.url = `${this.getWsBase()}/chat/ws${params}`;
  }

  private getWsBase(): string {
    if (window.location.protocol === "https:") {
      return `wss://${window.location.host}/api`;
    }
    return `ws://${window.location.host}/api`;
  }

  get status(): ConnectionStatus {
    return this._status;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this._status = "connecting";
    this.notifyStatus();
    this.shouldReconnect = true;

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this._status = "error";
      this.notifyStatus();
      return;
    }

    this.ws.onopen = () => {
      this._status = "connected";
      this.reconnectAttempts = 0;
      this.notifyStatus();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this._status = "disconnected";
      this.notifyStatus();
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
      }
    };

    this.ws.onerror = () => {
      this._status = "error";
      this.notifyStatus();
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
    this._status = "disconnected";
    this.notifyStatus();
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  private notifyStatus(): void {
    this.statusHandlers.forEach((h) => h(this._status));
  }
}
