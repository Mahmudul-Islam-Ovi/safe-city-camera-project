"use client";

import { useEffect, useState, useRef } from "react";
import { AlertItem, EventItem } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:8000/ws/events";

export function useSafeCityWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<EventItem | null>(null);
  const [latestAlert, setLatestAlert] = useState<AlertItem | null>(null);
  const [alertUpdates, setAlertUpdates] = useState<{ id: string; status: string } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;

    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
        };

        ws.onclose = () => {
          setIsConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          setIsConnected(false);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "event" && data.event) {
              setLatestEvent(data.event);
            }
            if (data.alert) {
              setLatestAlert(data.alert);
            }
            if (data.type === "alert_update") {
              setAlertUpdates({ id: data.alert_id, status: data.status });
            }
          } catch (e) {
            console.error("Failed to parse websocket message", e);
          }
        };
      } catch (e) {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    }

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { isConnected, latestEvent, latestAlert, alertUpdates };
}
