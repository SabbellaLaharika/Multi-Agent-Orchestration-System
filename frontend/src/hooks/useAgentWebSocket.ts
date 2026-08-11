import { useState, useEffect, useRef, useCallback } from 'react';
import { AgentEvent } from '../types';

interface UseAgentWebSocketReturn {
  events: AgentEvent[];
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  resetEvents: () => void;
}

export function useAgentWebSocket(taskId: string | null): UseAgentWebSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  const resetEvents = useCallback(() => {
    setEvents([]);
    setError(null);
  }, []);

  useEffect(() => {
    if (!taskId) {
      setIsConnected(false);
      setIsConnecting(false);
      return;
    }

    setIsConnecting(true);
    setError(null);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    const wsUrl = `${protocol}//${host}:8000/api/ws/${taskId}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      setIsConnected(true);
      setIsConnecting(false);
      
      // Start ping heartbeat interval every 15 seconds
      pingIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 15000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;

        setEvents((prev) => [...prev, data as AgentEvent]);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (evt) => {
      console.error('WebSocket connection error:', evt);
      setError('WebSocket connection encountered an error.');
      setIsConnecting(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setIsConnected(false);
      setIsConnecting(false);
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [taskId]);

  return { events, isConnected, isConnecting, error, resetEvents };
}
