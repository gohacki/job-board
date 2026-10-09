import { NextRequest, NextResponse } from "next/server";
import { applyMark } from "@/lib/marks";

// Body: { key, applied?: boolean, contacted?: boolean, note?: string }
export async function POST(req: NextRequest) {
  const b = await req.json().catch(() => null);
  if (!b || typeof b.key !== "string") return NextResponse.json({ error: "bad request" }, { status: 400 });
  const r = await applyMark(b.key, b);
  return r ? NextResponse.json(r) : NextResponse.json({ error: "not found" }, { status: 404 });
}
