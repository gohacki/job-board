import { NextRequest, NextResponse } from "next/server";
import { allow } from "@/lib/ratelimit";
import { applyMark } from "@/lib/marks";

export const dynamic = "force-dynamic";
const MAP: Record<string, { applied: boolean; contacted: boolean }> = {
  none: { applied: false, contacted: false }, applied: { applied: true, contacted: false },
  contacted: { applied: false, contacted: true }, "applied+contacted": { applied: true, contacted: true },
};

// Body: { key, status: none|applied|contacted|applied+contacted, note?: string }. Same logic as /api/mark.
export async function POST(req: NextRequest) {
  if (!(await allow("admin:status", 60, 60))) return NextResponse.json({ error: "rate limited, try again in a minute" }, { status: 429 });
  const b = await req.json().catch(() => null);
  if (!b || typeof b.key !== "string" || !MAP[b.status]) return NextResponse.json({ error: "need key and a status of none, applied, contacted or applied+contacted" }, { status: 400 });
  const r = await applyMark(b.key.trim(), { ...MAP[b.status], note: typeof b.note === "string" ? b.note : undefined });
  return r ? NextResponse.json({ key: b.key, status: b.status, ...r }) : NextResponse.json({ error: "no listing with that key" }, { status: 404 });
}
