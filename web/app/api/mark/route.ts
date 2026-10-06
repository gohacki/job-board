import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";

// Body: { key, applied?: boolean, contacted?: boolean, note?: string }
export async function POST(req: NextRequest) {
  const b = await req.json().catch(() => null);
  if (!b || typeof b.key !== "string") return NextResponse.json({ error: "bad request" }, { status: 400 });
  const [exists] = await sql`SELECT 1 FROM listings WHERE key = ${b.key}`;
  if (!exists) return NextResponse.json({ error: "not found" }, { status: 404 });
  await sql`INSERT INTO marks(key) VALUES (${b.key}) ON CONFLICT (key) DO NOTHING`;
  if (typeof b.applied === "boolean")
    await sql`UPDATE marks SET applied_at = ${b.applied ? sql`coalesce(applied_at, now())` : null} WHERE key = ${b.key}`;
  if (typeof b.contacted === "boolean")
    await sql`UPDATE marks SET contacted_at = ${b.contacted ? sql`coalesce(contacted_at, now())` : null},
              contact_note = ${b.contacted ? (typeof b.note === "string" ? b.note.slice(0, 500) : null) : null} WHERE key = ${b.key}`;
  else if (typeof b.note === "string")
    await sql`UPDATE marks SET contact_note = ${b.note.slice(0, 500)} WHERE key = ${b.key}`;
  const [m] = await sql`SELECT applied_at, contacted_at, contact_note FROM marks WHERE key = ${b.key}`;
  return NextResponse.json({ appliedAt: m.applied_at, contactedAt: m.contacted_at, note: m.contact_note });
}
