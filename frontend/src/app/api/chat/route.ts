import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const BACKEND_URL = process.env.ADK_BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const body = await req.json();
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      {
        status: "error",
        response: `ADK FastAPI Backend connection error (${BACKEND_URL}): ${error?.message || "Server unavailable"}`,
        audit_log: [],
      },
      { status: 500 }
    );
  }
}
