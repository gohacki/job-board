import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

// since/until are ISO instants. marked=1 returns every applied/contacted role regardless of the window.
export async function GET(req: NextRequest) {
  const p = req.nextUrl.searchParams;
  const loc = p.get("loc") ?? "bay";
  const modes = loc === "both" ? ["bay", "remote"] : [loc === "remote" ? "remote" : "bay"];
  const marked = p.get("marked") === "1";
  const showHidden = p.get("hidden") === "1";
  const since = new Date(p.get("since") ?? Date.now() - 864e5);
  const until = p.get("until") ? new Date(p.get("until")!) : new Date(Date.now() + 864e5);
  if (isNaN(+since) || isNaN(+until)) return NextResponse.json({ error: "bad date" }, { status: 400 });

  const rows = await sql`
    SELECT l.key, l.company, l.title, l.location, l.mode, l.is_sf, l.apply_url, l.effective_at, l.first_seen, l.posted_at,
           l.closed, l.years_req, l.score, l.score_detail, l.pay, l.snippet, l.hidden, l.ai_verdict, l.ai_reason,
           m.applied_at, m.contacted_at, m.contact_note
    FROM listings l LEFT JOIN marks m ON m.key = l.key
    WHERE l.mode = ANY(${modes})
      AND (${showHidden || marked} OR NOT l.hidden)
      AND ${marked ? sql`(m.applied_at IS NOT NULL OR m.contacted_at IS NOT NULL)` : sql`(l.effective_at >= ${since} AND l.effective_at < ${until})`}
    ORDER BY l.score DESC, l.effective_at DESC
    LIMIT 2500`;

  const [{ applied_urls, applied_companies }] = await sql`
    SELECT coalesce(array_agg(l.apply_url) FILTER (WHERE m.applied_at IS NOT NULL), '{}') AS applied_urls,
           coalesce(array_agg(DISTINCT l.company) FILTER (WHERE m.applied_at IS NOT NULL), '{}') AS applied_companies
    FROM marks m JOIN listings l ON l.key = m.key`;
  const [{ hidden_count }] = marked ? [{ hidden_count: 0 }] : await sql`SELECT count(*)::int AS hidden_count FROM listings l WHERE l.mode = ANY(${modes}) AND l.hidden AND l.effective_at >= ${since} AND l.effective_at < ${until}`;
  const [poll] = await sql`SELECT finished_at, tier, boards_ok, boards_failed FROM poll_runs ORDER BY id DESC LIMIT 1`;

  return NextResponse.json({
    now: new Date().toISOString(),
    lastPoll: poll ?? null,
    appliedUrls: applied_urls,
    appliedCompanies: applied_companies,
    hiddenCount: hidden_count,
    roles: rows.map((r) => ({
      key: r.key, company: r.company, title: r.title, location: r.location, mode: r.mode, isSf: r.is_sf, applyUrl: r.apply_url,
      at: r.effective_at, firstSeen: r.first_seen, postedAt: r.posted_at, closed: r.closed, yearsReq: r.years_req,
      score: r.score, detail: r.score_detail, pay: r.pay, snippet: r.snippet, hidden: r.hidden, aiVerdict: r.ai_verdict, aiReason: r.ai_reason,
      appliedAt: r.applied_at, contactedAt: r.contacted_at, note: r.contact_note,
    })),
  });
}
