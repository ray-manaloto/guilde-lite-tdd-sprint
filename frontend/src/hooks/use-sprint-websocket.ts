"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/constants";
import type { Sprint, SprintStatus } from "@/types";

/**
 * WebSocket event types from the backend PhaseRunner.
 */
export type SprintEventType =
  | "sprint_update" // Legacy event for backwards compatibility
  | "workflow.status"
  | "phase.started"
  | "phase.completed"
  | "phase.failed"
  | "candidate.started"
  | "candidate.generated"
  | "judge.started"
  | "judge.decided";

/**
 * Legacy sprint_update event (backwards compatibility).
 */
export interface SprintUpdateEvent {
  type: "sprint_update";
  sprint_id: string;
  status: string;
  phase?: string | null;
  details?: string | null;
}

/**
 * Workflow status event from new event system.
 */
export interface WorkflowStatusEvent {
  type: "workflow.status";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  status: string;
  phase?: string | null;
  details?: string | null;
}

/**
 * Phase started event.
 */
export interface PhaseStartedEvent {
  type: "phase.started";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  phase: string;
  attempt?: number | null;
  details?: string | null;
}

/**
 * Phase completed event.
 */
export interface PhaseCompletedEvent {
  type: "phase.completed";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  phase: string;
  duration_ms?: number | null;
  output?: Record<string, unknown> | null;
  details?: string | null;
}

/**
 * Phase failed event.
 */
export interface PhaseFailedEvent {
  type: "phase.failed";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  phase: string;
  details?: string | null;
  attempt?: number | null;
}

/**
 * Candidate started event.
 */
export interface CandidateStartedEvent {
  type: "candidate.started";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  provider: string;
  model_name?: string | null;
  phase: string;
}

/**
 * Candidate generated event.
 */
export interface CandidateGeneratedEvent {
  type: "candidate.generated";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  candidate: {
    candidate_id?: string | null;
    provider: string;
    model_name?: string | null;
    agent_name?: string | null;
    output?: string | null;
    duration_ms?: number | null;
    trace_id?: string | null;
    success?: boolean;
  };
}

/**
 * Judge started event.
 */
export interface JudgeStartedEvent {
  type: "judge.started";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  candidate_count: number;
  phase: string;
}

/**
 * Judge decided event.
 */
export interface JudgeDecidedEvent {
  type: "judge.decided";
  sprint_id: string;
  timestamp: string;
  sequence: number;
  decision: {
    winner_candidate_id?: string | null;
    winner_model: string;
    score?: number | null;
    rationale?: string | null;
    model_name?: string | null;
    trace_id?: string | null;
  };
}

/**
 * Union of all sprint events.
 */
export type SprintEvent =
  | SprintUpdateEvent
  | WorkflowStatusEvent
  | PhaseStartedEvent
  | PhaseCompletedEvent
  | PhaseFailedEvent
  | CandidateStartedEvent
  | CandidateGeneratedEvent
  | JudgeStartedEvent
  | JudgeDecidedEvent;

/**
 * Current sprint phase info from WebSocket events.
 */
export interface SprintPhaseInfo {
  phase: string;
  status: "starting" | "running" | "completed" | "failed";
  attempt?: number;
  details?: string;
  duration_ms?: number;
}

/**
 * Sprint WebSocket connection state.
 */
export interface UseSprintWebSocketReturn {
  /** Whether the WebSocket is connected */
  isConnected: boolean;
  /** Current phase info from last event */
  currentPhase: SprintPhaseInfo | null;
  /** Current sprint status from last event */
  currentStatus: SprintStatus | null;
  /** Last received event for debugging */
  lastEvent: SprintEvent | null;
  /** All events received (limited to last 100) */
  events: SprintEvent[];
  /** Connect to the sprint WebSocket room */
  connect: () => void;
  /** Disconnect from the WebSocket */
  disconnect: () => void;
}

interface UseSprintWebSocketOptions {
  /** Sprint ID to subscribe to */
  sprintId: string | null;
  /** Callback when sprint status changes */
  onStatusChange?: (status: SprintStatus) => void;
  /** Callback when phase changes */
  onPhaseChange?: (phase: SprintPhaseInfo) => void;
  /** Callback for any event */
  onEvent?: (event: SprintEvent) => void;
  /** Auto-connect when sprintId is provided (default: true) */
  autoConnect?: boolean;
  /** Max events to keep in history (default: 100) */
  maxEvents?: number;
}

/**
 * Hook for subscribing to real-time sprint updates via WebSocket.
 *
 * Connects to the backend WebSocket endpoint and receives events
 * from the PhaseRunner during sprint execution.
 *
 * @example
 * ```tsx
 * const { isConnected, currentPhase, currentStatus, events } = useSprintWebSocket({
 *   sprintId: "123-456",
 *   onStatusChange: (status) => {
 *     // Update sprint in local state
 *     setSprint(prev => prev ? { ...prev, status } : null);
 *   },
 *   onPhaseChange: (phase) => {
 *     console.log(`Phase ${phase.phase}: ${phase.status}`);
 *   },
 * });
 * ```
 */
export function useSprintWebSocket({
  sprintId,
  onStatusChange,
  onPhaseChange,
  onEvent,
  autoConnect = true,
  maxEvents = 100,
}: UseSprintWebSocketOptions): UseSprintWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<SprintPhaseInfo | null>(null);
  const [currentStatus, setCurrentStatus] = useState<SprintStatus | null>(null);
  const [lastEvent, setLastEvent] = useState<SprintEvent | null>(null);
  const [events, setEvents] = useState<SprintEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectInterval = 3000;

  // Use refs for callbacks to avoid recreating connect function
  const onStatusChangeRef = useRef(onStatusChange);
  const onPhaseChangeRef = useRef(onPhaseChange);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
    onPhaseChangeRef.current = onPhaseChange;
    onEventRef.current = onEvent;
  }, [onStatusChange, onPhaseChange, onEvent]);

  const handleMessage = useCallback(
    (messageEvent: MessageEvent) => {
      try {
        const event = JSON.parse(messageEvent.data) as SprintEvent;
        setLastEvent(event);
        setEvents((prev) => {
          const newEvents = [...prev, event];
          // Keep only the last maxEvents
          return newEvents.slice(-maxEvents);
        });

        // Call generic event handler
        onEventRef.current?.(event);

        // Process event based on type
        if (event.type === "sprint_update") {
          // Legacy event
          const legacyEvent = event as SprintUpdateEvent;
          const newStatus = legacyEvent.status as SprintStatus;
          setCurrentStatus(newStatus);
          onStatusChangeRef.current?.(newStatus);

          if (legacyEvent.phase) {
            const phaseInfo: SprintPhaseInfo = {
              phase: legacyEvent.phase,
              status: "running",
              details: legacyEvent.details || undefined,
            };
            setCurrentPhase(phaseInfo);
            onPhaseChangeRef.current?.(phaseInfo);
          }
        } else if (event.type === "workflow.status") {
          const statusEvent = event as WorkflowStatusEvent;
          const newStatus = statusEvent.status as SprintStatus;
          setCurrentStatus(newStatus);
          onStatusChangeRef.current?.(newStatus);

          if (statusEvent.phase) {
            const phaseInfo: SprintPhaseInfo = {
              phase: statusEvent.phase,
              status: "running",
              details: statusEvent.details || undefined,
            };
            setCurrentPhase(phaseInfo);
            onPhaseChangeRef.current?.(phaseInfo);
          }
        } else if (event.type === "phase.started") {
          const phaseEvent = event as PhaseStartedEvent;
          const phaseInfo: SprintPhaseInfo = {
            phase: phaseEvent.phase,
            status: "starting",
            attempt: phaseEvent.attempt || undefined,
            details: phaseEvent.details || undefined,
          };
          setCurrentPhase(phaseInfo);
          onPhaseChangeRef.current?.(phaseInfo);
        } else if (event.type === "phase.completed") {
          const phaseEvent = event as PhaseCompletedEvent;
          const phaseInfo: SprintPhaseInfo = {
            phase: phaseEvent.phase,
            status: "completed",
            details: phaseEvent.details || undefined,
            duration_ms: phaseEvent.duration_ms || undefined,
          };
          setCurrentPhase(phaseInfo);
          onPhaseChangeRef.current?.(phaseInfo);
        } else if (event.type === "phase.failed") {
          const phaseEvent = event as PhaseFailedEvent;
          const phaseInfo: SprintPhaseInfo = {
            phase: phaseEvent.phase,
            status: "failed",
            attempt: phaseEvent.attempt || undefined,
            details: phaseEvent.details || undefined,
          };
          setCurrentPhase(phaseInfo);
          onPhaseChangeRef.current?.(phaseInfo);
        }
      } catch (error) {
        console.warn("Failed to parse WebSocket message:", error);
      }
    },
    [maxEvents]
  );

  const connect = useCallback(() => {
    if (!sprintId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Use the public sprint WebSocket endpoint (no auth required)
    const wsUrl = `${WS_URL}/api/v1/ws/sprint/${sprintId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      console.log(`[SprintWS] Connected to room: ${sprintId}`);
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      setIsConnected(false);
      console.log(`[SprintWS] Disconnected from room: ${sprintId}`);

      // Attempt reconnection
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          console.log(
            `[SprintWS] Reconnecting (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
          );
          connect();
        }, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      console.error("[SprintWS] WebSocket error:", error);
    };
  }, [sprintId, handleMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  // Auto-connect when sprintId changes
  useEffect(() => {
    if (autoConnect && sprintId) {
      // Reset state for new sprint
      setCurrentPhase(null);
      setCurrentStatus(null);
      setLastEvent(null);
      setEvents([]);
      reconnectAttemptsRef.current = 0;
      connect();
    }

    return () => {
      disconnect();
    };
  }, [sprintId, autoConnect, connect, disconnect]);

  return {
    isConnected,
    currentPhase,
    currentStatus,
    lastEvent,
    events,
    connect,
    disconnect,
  };
}
