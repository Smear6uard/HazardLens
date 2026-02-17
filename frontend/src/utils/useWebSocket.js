import { useState, useEffect, useRef, useCallback } from 'react';

export default function useWebSocket(url, enabled = false) {
  const [frame, setFrame] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = useCallback(() => {
    if (!url || !enabled) return;

    setError(null);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.frame) {
          setFrame(data.frame);
        }
        if (data.events && data.events.length > 0) {
          setAlerts(prev => [...data.events, ...prev].slice(0, 200));
        }
      } catch { /* skip malformed */ }
    };

    ws.onerror = () => {
      setError('WebSocket error');
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      if (enabled) {
        reconnectRef.current = setTimeout(connect, 3000);
      }
    };
  }, [url, enabled]);

  const disconnect = useCallback(() => {
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendFrame = useCallback((base64Frame) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ frame: base64Frame }));
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }
    return disconnect;
  }, [enabled, connect, disconnect]);

  return { frame, alerts, isConnected, error, sendFrame, disconnect };
}
