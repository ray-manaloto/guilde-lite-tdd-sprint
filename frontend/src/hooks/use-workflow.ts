"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Workflow, TimelineResponse, ArtifactsResponse } from "@/types/workflow";

/**
 * Query keys for workflow-related queries.
 */
export const workflowKeys = {
  all: ["workflows"] as const,
  workflow: (sprintId: string) => [...workflowKeys.all, sprintId] as const,
  timeline: (sprintId: string) => [...workflowKeys.all, sprintId, "timeline"] as const,
  artifacts: (sprintId: string) => [...workflowKeys.all, sprintId, "artifacts"] as const,
};

/**
 * Fetch the full workflow for a sprint.
 * @param sprintId - Sprint UUID
 * @returns TanStack Query result with Workflow data
 */
export function useWorkflow(sprintId: string) {
  return useQuery({
    queryKey: workflowKeys.workflow(sprintId),
    queryFn: () => apiClient.get<Workflow>(`/sprints/${sprintId}/workflow`),
    enabled: Boolean(sprintId),
  });
}

/**
 * Fetch timeline events for a sprint.
 * @param sprintId - Sprint UUID
 * @returns TanStack Query result with TimelineResponse data
 */
export function useTimeline(sprintId: string) {
  return useQuery({
    queryKey: workflowKeys.timeline(sprintId),
    queryFn: () => apiClient.get<TimelineResponse>(`/sprints/${sprintId}/timeline`),
    enabled: Boolean(sprintId),
  });
}

/**
 * Fetch artifacts list for a sprint.
 * @param sprintId - Sprint UUID
 * @returns TanStack Query result with ArtifactsResponse data
 */
export function useArtifacts(sprintId: string) {
  return useQuery({
    queryKey: workflowKeys.artifacts(sprintId),
    queryFn: () => apiClient.get<ArtifactsResponse>(`/sprints/${sprintId}/artifacts`),
    enabled: Boolean(sprintId),
  });
}
