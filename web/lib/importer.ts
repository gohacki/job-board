import { createHash } from "node:crypto";
import { sql } from "@/lib/db";

// ---- same key logic as poller/poll.py: sha256(company.lower() + '|' + req + '|' + canon(url)); imports have no req id ----
const DROP = new Set(["utm_source", "utm_medium", "utm_campaign", "gh_src", "source", "ref"]);
export function canon(u: string) {
  try {
    const p = new URL(u);
    for (const k of [...p.searchParams.keys()]) if (DROP.has(k)) p.searchParams.delete(k);
    const path = p.pathname.replace(/\/+$/, "").replace(/\/application$/, "").replace(/\/apply$/, "");
    return `${p.protocol}//${p.host}${path}${p.searchParams.toString() ? "?" + p.searchParams.toString() : ""}`;
  } catch { return ""; }
}
export const makeKey = (company: string, url: string) => createHash("sha256").update(`${company.toLowerCase()}||${canon(url)}`).digest("hex");

const BAY = /san francisco|\bsf\b|south san francisco|bay area|oakland|berkeley|emeryville|alameda|san leandro|hayward|fremont|milpitas|san jose|santa clara|sunnyvale|mountain view|los altos|palo alto|menlo park|redwood city|san carlos|foster city|san mateo|burlingame|millbrae|san bruno|brisbane, ca|daly city|pacifica|half moon bay|cupertino|campbell, ca|los gatos|saratoga|pleasanton|dublin, ca|livermore|walnut creek|san ramon|san rafael|mill valley|sausalito|novato|petaluma|stanford/i;
const SF = /san francisco|\bsf\b/i;

// ---- parsing ----
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []; let row: string[] = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cell); cell = ""; if (row.some((x) => x.trim())) rows.push(row); row = []; }
    else cell += c;
  }
  row.push(cell); if (row.some((x) => x.trim())) rows.push(row);
  if (rows.length < 2) return [];
  const head = rows[0].map((h) => h.trim());
  return rows.slice(1).map((r) => Object.fromEntries(head.map((h, i) => [h, (r[i] ?? "").trim()])));
}
export function parseInput(text: string): Record<string, unknown>[] {
  const t = text.trim();
  if (t.startsWith("[") || t.startsWith("{")) {
    const j = JSON.parse(t);
    return Array.isArray(j) ? j : Array.isArray(j?.postings) ? j.postings : [j];
  }
  return parseCsv(t);
}

const pick = (o: Record<string, unknown>, ...names: string[]) => {
  const low = Object.fromEntries(Object.entries(o).map(([k, v]) => [k.toLowerCase().replace(/[\s_-]+/g, ""), v]));
  for (const n of names) { const v = low[n.replace(/[\s_-]+/g, "")]; if (v !== undefined && v !== null && String(v).trim()) return String(v).trim(); }
  return "";
};

export type Row = { company: string; title: string; location: string; url: string; source: string; posted: Date | null; mode: "bay" | "remote"; level: string; notes: string };

/** Returns a normalized row, or an error string. */
export function normalize(o: Record<string, unknown>): Row | string {
  const company = pick(o, "company", "employer"), url = pick(o, "url", "link", "applyurl");
  if (!company) return "missing company";
  if (!url) return "missing url";
  if (!/^https?:\/\//i.test(url) || !canon(url)) return "url is not a valid http(s) link";
  const title = pick(o, "title", "role", "jobtitle") || "Untitled role";
  const location = pick(o, "location");
  const wm = pick(o, "workmode", "remotehybridonsite", "remote", "mode", "type").toLowerCase();
  const posted = pick(o, "posted", "posteddate", "postedat", "date");
  let postedAt: Date | null = null;
  if (posted) { const d = new Date(posted); if (isNaN(+d)) return `posted date not understood: ${posted}`; postedAt = d; }
  let mode: "bay" | "remote";
  if (/^(true|yes)$/.test(wm) || /remote/.test(wm)) mode = "remote";
  else if (/hybrid|on-?site|office|in-?person/.test(wm) || BAY.test(location)) {
    if (!BAY.test(location)) return location ? `location "${location}" is not in the Bay Area (the board tracks Bay Area on-site/hybrid or remote)` : "location required for hybrid/onsite roles";
    mode = "bay";
  } else if (!wm) {
    if (BAY.test(location)) mode = "bay"; else return "work mode missing and location is not in the Bay Area";
  } else return `work mode not understood: ${wm}`;
  return { company, title, location, url, source: pick(o, "source") || "manual", posted: postedAt, mode, level: pick(o, "level", "seniority"), notes: pick(o, "notes", "note") };
}

export type Result = { added: number; updated: number; duplicates: number; errors: { row: number; error: string }[]; addedKeys: string[] };

export async function importRows(raw: Record<string, unknown>[]): Promise<Result> {
  const res: Result = { added: 0, updated: 0, duplicates: 0, errors: [], addedKeys: [] };
  const seen = new Set<string>();
  for (let i = 0; i < raw.length; i++) {
    const n = normalize(raw[i] ?? {});
    if (typeof n === "string") { res.errors.push({ row: i + 1, error: n }); continue; }
    const key = makeKey(n.company, n.url), cu = canon(n.url);
    if (seen.has(key)) { res.duplicates++; continue; }
    seen.add(key);
    // an existing row counts as the same posting if it has the same key or the same apply link
    const [ex] = await sql`SELECT key, ats, title, location, mode, source, level, notes, posted_at FROM listings WHERE key = ${key} OR apply_url = ${n.url} OR apply_url = ${cu} LIMIT 1`;
    if (ex) {
      if (ex.ats !== "manual") { res.duplicates++; continue; }   // never overwrite scanned data
      const same = ex.title === n.title && (ex.location ?? "") === n.location && ex.mode === n.mode && (ex.source ?? "") === n.source && (ex.level ?? "") === n.level && (ex.notes ?? "") === n.notes && (ex.posted_at ? +new Date(ex.posted_at) : null) === (n.posted ? +n.posted : null);
      if (same) { res.duplicates++; continue; }   // identical re-import
      await sql`UPDATE listings SET title=${n.title}, location=${n.location}, mode=${n.mode}, is_sf=${SF.test(n.location)}, source=${n.source}, level=${n.level || null}, notes=${n.notes || null},
                description=${n.notes || null}, posted_at=${n.posted}, effective_at=coalesce(${n.posted}, effective_at), last_seen=now(), closed=false WHERE key=${ex.key}`;
      res.updated++; continue;
    }
    await sql`INSERT INTO listings(key, company, ats, title, location, mode, is_sf, apply_url, posted_at, first_seen, last_seen, baseline, effective_at, closed, score, score_detail, source, level, notes, description, source_endpoint, hidden)
              VALUES (${key}, ${n.company}, 'manual', ${n.title}, ${n.location}, ${n.mode}, ${SF.test(n.location)}, ${n.url}, ${n.posted}, now(), now(), false, ${n.posted ?? new Date()}, false, 50,
                      ${sql.json({ manual: true, loc: SF.test(n.location) ? 20 : n.mode === "bay" ? 12 : 0 })}, ${n.source}, ${n.level || null}, ${n.notes || null}, ${n.notes || null}, 'manual:import', false)`;
    res.added++; res.addedKeys.push(key);
  }
  return res;
}
