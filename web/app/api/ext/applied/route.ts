import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";
import { sql } from "@/lib/db";

// Called by the Application Helper extension when an application confirmation page appears.
// Auth: Bearer EXTENSION_TOKEN (the session cookie is not available to the extension).
function authorized(req: NextRequest) {
  const want = process.env.EXTENSION_TOKEN;
  const got = (req.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!want || !got) return false;
  const a = Buffer.from(got), b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}

// Greenhouse: ?for=slug&token=ID or /jobs/ID. Ashby and Lever: the UUID in the path.
function jobId(url: string) {
  const u = new URL(url);
  return (
    u.searchParams.get("token") ??
    u.searchParams.get("gh_jid") ??
    u.pathname.match(/\/jobs\/(\d+)/)?.[1] ??
    u.pathname.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)?.[0] ??
    null
  );
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const body = await req.json().catch(() => null);
  let id: string | null = null;
  try { id = body?.url ? jobId(String(body.url)) : null; } catch {}
  if (!id || !/^[0-9a-zA-Z-]{5,40}$/.test(id)) return NextResponse.json({ error: "no job id in url" }, { status: 400 });

  const rows = await sql`SELECT key, company, title FROM listings WHERE apply_url LIKE ${"%" + id + "%"} LIMIT 5`;
  if (rows.length !== 1) return NextResponse.json({ matched: rows.length, error: rows.length ? "ambiguous" : "not on the board" }, { status: rows.length ? 409 : 404 });
  const [r] = rows;
  await sql`INSERT INTO marks(key, applied_at) VALUES (${r.key}, now()) ON CONFLICT (key) DO UPDATE SET applied_at = coalesce(marks.applied_at, now())`;
  return NextResponse.json({ matched: 1, company: r.company, title: r.title });
}
