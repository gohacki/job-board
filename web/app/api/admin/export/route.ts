import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { allow } from "@/lib/ratelimit";

export const dynamic = "force-dynamic";

// Query: q (matches company, title or url), source (all|manual|scanned), hidden (1 to include filtered-out), limit (default 25000)
export async function GET(req: NextRequest) {
  if (!(await allow("admin:export", 10, 60))) return NextResponse.json({ error: "rate limited, try again in a minute" }, { status: 429 });
  const p = req.nextUrl.searchParams;
  const q = (p.get("q") ?? "").trim().toLowerCase();
  const source = p.get("source") ?? "all";
  const hidden = p.get("hidden") === "1";
  const limit = Math.min(Math.max(parseInt(p.get("limit") ?? "25000", 10) || 25000, 1), 25000);
  const rows = await sql`
    SELECT l.company, l.title, l.apply_url AS url, l.key, l.closed,
           CASE WHEN m.applied_at IS NOT NULL AND m.contacted_at IS NOT NULL THEN 'applied+contacted'
                WHEN m.applied_at IS NOT NULL THEN 'applied' WHEN m.contacted_at IS NOT NULL THEN 'contacted' ELSE 'none' END AS status
    FROM listings l LEFT JOIN marks m ON m.key = l.key
    WHERE (${q} = '' OR lower(l.company) LIKE ${"%" + q + "%"} OR lower(l.title) LIKE ${"%" + q + "%"} OR lower(l.apply_url) LIKE ${"%" + q + "%"})
      AND (${source} = 'all' OR (${source} = 'manual' AND l.ats = 'manual') OR (${source} = 'scanned' AND l.ats <> 'manual'))
      AND (${hidden} OR NOT l.hidden)
    ORDER BY l.company, l.title LIMIT ${limit}`;
  return NextResponse.json(rows.map((r) => ({ company: r.company, title: r.title, url: r.url, key: r.key, status: r.closed ? `${r.status} (closed)` : r.status })));
}
