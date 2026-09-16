import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const BACKEND_URL = process.env.ADK_BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const employeeId = req.nextUrl.searchParams.get("employee_id") || "";
    const query = employeeId ? `?employee_id=${encodeURIComponent(employeeId)}` : "";
    const response = await fetch(`${BACKEND_URL}/api/state${query}`, {
      cache: "no-store",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { error: `Backend state fetch failed: ${error?.message}` },
      { status: 500 }
    );
  }
}

export async function POST() {
  const BACKEND_URL = process.env.ADK_BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${BACKEND_URL}/api/reset`, {
      method: "POST",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { error: `Reset failed: ${error?.message}` },
      { status: 500 }
    );
  }
}
