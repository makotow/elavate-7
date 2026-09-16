import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const BACKEND_URL = process.env.ADK_BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${BACKEND_URL}/api/mcp-status`, {
      cache: "no-store",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      {
        status: "disconnected",
        error: error?.message || "Backend offline",
      },
      { status: 500 }
    );
  }
}
