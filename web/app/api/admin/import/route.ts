import { NextRequest, NextResponse } from "next/server";
import { allow } from "@/lib/ratelimit";
import { importRows, parseInput } from "@/lib/importer";

export const dynamic = "force-dynamic";
const MAX_ROWS = 500;

// Body: { text: "<JSON array or CSV>" }. The session is enforced by middleware.
export async function POST(req: NextRequest) {
  if (!(await allow("admin:import", 20, 60))) return NextResponse.json({ error: "rate limited, try again in a minute" }, { status: 429 });
  const b = await req.json().catch(() => null);
  const text = typeof b?.text === "string" ? b.text : "";
  if (!text.trim()) return NextResponse.json({ error: "paste some JSON or CSV first" }, { status: 400 });
  if (text.length > 1_500_000) return NextResponse.json({ error: "input too large (limit about 1.5 MB)" }, { status: 413 });
  let rows: Record<string, unknown>[];
  try { rows = parseInput(text); } catch (e) { return NextResponse.json({ error: `could not parse input: ${(e as Error).message}` }, { status: 400 }); }
  if (!rows.length) return NextResponse.json({ error: "no rows found (CSV needs a header row plus at least one data row)" }, { status: 400 });
  if (rows.length > MAX_ROWS) return NextResponse.json({ error: `too many rows (${rows.length}); the limit is ${MAX_ROWS} per import` }, { status: 413 });
  const r = await importRows(rows);
  return NextResponse.json({ rows: rows.length, added: r.added, updated: r.updated, skippedDuplicate: r.duplicates, errors: r.errors, addedKeys: r.addedKeys });
}
