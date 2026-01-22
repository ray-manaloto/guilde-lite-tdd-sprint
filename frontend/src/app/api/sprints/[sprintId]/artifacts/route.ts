import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { ArtifactsResponse } from "@/types/workflow";

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
 * GET /api/sprints/[sprintId]/artifacts
 *
 * Fetches the list of artifacts generated during sprint execution,
 * including specs, code files, and phase outputs.
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { sprintId } = await params;
    const data = await backendFetch<ArtifactsResponse>(`/api/v1/sprints/${sprintId}/artifacts`, {
      method: "GET",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load artifacts";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
