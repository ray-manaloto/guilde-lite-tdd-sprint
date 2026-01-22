import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { TimelineResponse } from "@/types/workflow";

const getAuthHeader = (request: NextRequest): Record<string, string> => {
  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
};

interface RouteParams {
  params: Promise<{ sprintId: string }>;
}

/**
 * GET /api/sprints/[sprintId]/timeline
 *
 * Fetches timeline events for a sprint showing the chronological
 * sequence of phases, candidate generation, and judge decisions.
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { sprintId } = await params;
    const data = await backendFetch<TimelineResponse>(`/api/v1/sprints/${sprintId}/timeline`, {
      method: "GET",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load timeline";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
