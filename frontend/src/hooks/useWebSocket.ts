import { useEffect, useRef, useCallback, useState } from "react";
import { WebSocketClient, type ConnectionStatus, type WsMessage } from "../services/websocket";

export function useWebSocket(sessionId?: string) {
  const clientRef = useRef<WebSocketClient | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);

  useEffect(() => {
    const client = new WebSocketClient(sessionId);
    clientRef.current = client;

    const unsubStatus = client.onStatusChange(setStatus);
    const unsubMsg = client.onMessage(setLastMessage);

    client.connect();

    return () => {
      unsubStatus();
      unsubMsg();
      client.disconnect();
    };
  }, [sessionId]);

  const send = useCallback((data: Record<string, unknown>) => {
    clientRef.current?.send(data);
  }, []);

  const reconnect = useCallback(() => {
    clientRef.current?.disconnect();
    const client = new WebSocketClient(sessionId);
    clientRef.current = client;
  }, [sessionId]);

  return { status, lastMessage, send, reconnect };
}
