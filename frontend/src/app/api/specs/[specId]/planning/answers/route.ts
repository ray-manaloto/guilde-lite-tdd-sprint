import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SpecPlanningAnswers, SpecPlanningResponse } from "@/types";

const getAuthHeader = (request: NextRequest): Record<string, string> => {
  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
};

interface RouteParams {
  params: Promise<{ specId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const body = (await request.json()) as SpecPlanningAnswers;
    const { specId } = await params;
    const data = await backendFetch<SpecPlanningResponse>(
      `/api/v1/specs/${specId}/planning/answers`,
      {
        method: "POST",
        headers: getAuthHeader(request),
        body: JSON.stringify(body),
      }
    );
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail =
        (error.data as { detail?: string })?.detail || "Failed to save planning answers";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
