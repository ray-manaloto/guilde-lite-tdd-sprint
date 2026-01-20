import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SpecPlanningCreate, SpecPlanningResponse } from "@/types";

const getAuthHeader = (request: NextRequest) => {
  const accessToken = request.cookies.get("access_token")?.value;
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SpecPlanningCreate;
    const data = await backendFetch<SpecPlanningResponse>("/api/v1/specs/planning", {
      method: "POST",
      headers: getAuthHeader(request),
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail =
        (error.data as { detail?: string })?.detail || "Failed to start planning interview";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
