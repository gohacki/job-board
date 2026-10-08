"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Detail = { title?: number; skills?: number; exp?: number; fit?: number; ai?: boolean; verdict?: string; loc: number; years: number | null; seniority?: number | null; matched?: string[]; negative?: string[]; languages?: string[]; gap?: string; gaps?: string[] };
type Role = {
  key: string; company: string; title: string; location: string; mode: "bay" | "remote"; isSf: boolean; applyUrl: string;
  at: string | null; firstSeen: string; postedAt: string | null; closed: boolean; yearsReq: number | null; score: number;
  detail: Detail | null; aiVerdict: string | null; aiReason: string | null; hidden: boolean; pay: string | null; snippet: string | null; appliedAt: string | null; contactedAt: string | null; note: string | null;
};
type Resp = { now: string; lastPoll: { finished_at: string; tier: string; boards_ok: number; boards_failed: number } | null; appliedUrls: string[]; appliedCompanies: string[]; hiddenCount: number; roles: Role[] };

const TZ = "America/Los_Angeles";

// ---- Pacific-time helpers -------------------------------------------------
function wall(t: number) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" })
      .formatToParts(new Date(t)).map((x) => [x.type, x.value]),
  );
  return { y: +p.year, m: +p.month, d: +p.day, ms: Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) };
}
/** Instant at which the Pacific wall clock reads y-m-d h:00 (month/day may overflow). */
function ptInstant(y: number, m: number, d: number, h = 0) {
  const guess = Date.UTC(y, m - 1, d, h);
  let t = guess;
  for (let i = 0; i < 3; i++) t = guess - (wall(t).ms - t);
  return t;
}
function dayOffset(base: { y: number; m: number; d: number }, n: number) {
  const x = new Date(Date.UTC(base.y, base.m - 1, base.d + n));
  return { y: x.getUTCFullYear(), m: x.getUTCMonth() + 1, d: x.getUTCDate() };
}

type Win = { id: string; label: string; since: number; until: number | null };
function makeWindows(nowMs: number): Win[] {
  const w = wall(nowMs);
  const day = (n: number) => dayOffset(w, n);
  const start = (n: number) => { const x = day(n); return ptInstant(x.y, x.m, x.d); };
  const y = day(-1);
  const out: Win[] = [
    { id: "recent", label: "Since 5pm yesterday", since: ptInstant(y.y, y.m, y.d, 17), until: null },
    { id: "today", label: "Today", since: start(0), until: null },
  ];
  for (let n = 1; n <= 5; n++)
    out.push({ id: `d${n}`, label: new Date(start(-n) + 12 * 36e5).toLocaleDateString("en-US", { timeZone: TZ, weekday: "short", month: "short", day: "numeric" }), since: start(-n), until: start(-n + 1) });
  out.push({ id: "week", label: "Last 7 days", since: start(-6), until: null }, { id: "all", label: "Last 30 days", since: start(-29), until: null });
  return out;
}

const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-US", { timeZone: TZ, month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "");
function ago(iso: string | null, now: number) {
  if (!iso) return "";
  const m = Math.max(0, Math.round((now - +new Date(iso)) / 60000));
  if (m < 60) return `${m}m ago`;
  if (m < 60 * 24) return `${Math.round(m / 60)}h ago`;
  return `${Math.round(m / 1440)}d ago`;
}

// ---- component ---------------------------------------------------------------
export default function Board() {
  const [winId, setWinId] = useState("recent");
  const [loc, setLoc] = useState<"bay" | "remote" | "both">("bay");
  const [status, setStatus] = useState<"all" | "todo" | "applied" | "contacted">("all");
  const [sort, setSort] = useState<"score" | "new">("score");
  const [minScore, setMinScore] = useState(0);
  const [q, setQ] = useState("");
  const [showClosed, setShowClosed] = useState(false);
  const [hideSenior, setHideSenior] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [dedupe, setDedupe] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [data, setData] = useState<Resp | null>(null);
  const [err, setErr] = useState("");
  const [tick, setTick] = useState(() => Date.now());
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState<string | null>(null);
  const [noteFor, setNoteFor] = useState<string | null>(null);
  const [descs, setDescs] = useState<Record<string, string>>({});
  const [ext, setExt] = useState<string | null>(null);
  const [fills, setFills] = useState<Record<string, { state: string; message: string }>>({});
  const loadRef = useRef<() => void>(() => {});
  const known = useRef<{ q: string; keys: Set<string> } | null>(null);

  useEffect(() => {
    try {
      const s = JSON.parse(localStorage.getItem("jb-prefs") || "{}");
      if (s.loc) setLoc(s.loc);
      if (s.sort) setSort(s.sort);
      if (typeof s.minScore === "number") setMinScore(s.minScore);
      if (typeof s.hideSenior === "boolean") setHideSenior(s.hideSenior);
      if (typeof s.dedupe === "boolean") setDedupe(s.dedupe);
    } catch {}
  }, []);
  useEffect(() => {
    try { localStorage.setItem("jb-prefs", JSON.stringify({ loc, sort, minScore, hideSenior, dedupe })); } catch {}
  }, [loc, sort, minScore, hideSenior, dedupe]);

  // Application Helper extension bridge (extension 1.6.0+). Absent extension => plain links only.
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.source !== window || e.origin !== location.origin || e.data?.source !== "application-helper") return;
      const m = e.data;
      if (m.type === "ready") setExt(m.version);
      if (m.type === "applied") loadRef.current();
      if (m.type === "result") setFills((f) => ({ ...f, [m.id]: { state: m.state, message: m.message } }));
      if (m.type === "accepted" && m.error) setErr(`Application Helper: ${m.error}`);
    };
    window.addEventListener("message", onMsg);
    window.postMessage({ source: "job-board", type: "ping" }, location.origin);
    return () => window.removeEventListener("message", onMsg);
  }, []);
  const prefill = (rs: Role[]) => {
    const jobs = rs.map((r) => ({ id: r.key, company: r.company, title: r.title, url: r.applyUrl }));
    setFills((f) => ({ ...f, ...Object.fromEntries(jobs.map((j) => [j.id, { state: "Opening…", message: "" }])) }));
    window.postMessage({ source: "job-board", type: "fill", jobs }, location.origin);
  };

  const wins = useMemo(() => makeWindows(tick), [tick]);
  const win = wins.find((w) => w.id === winId) ?? wins[0];
  const marked = status === "applied" || status === "contacted";
  const query = useMemo(() => {
    const p = new URLSearchParams({ loc });
    if (showHidden) p.set("hidden", "1");
    if (marked) p.set("marked", "1");
    else { p.set("since", new Date(win.since).toISOString()); if (win.until) p.set("until", new Date(win.until).toISOString()); }
    return p.toString();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loc, marked, showHidden, win.since, win.until]);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/roles?${query}`, { cache: "no-store" });
      if (r.status === 401) { location.href = "/login"; return; }
      if (!r.ok) throw new Error(String(r.status));
      const d: Resp = await r.json();
      const keys = new Set(d.roles.map((x) => x.key));
      if (known.current && known.current.q === query) {
        const added = d.roles.filter((x) => !known.current!.keys.has(x.key)).map((x) => x.key);
        if (added.length) setFresh((f) => new Set([...f, ...added]));
        known.current.keys = new Set([...known.current.keys, ...keys]);
      } else {
        known.current = { q: query, keys };
        setFresh(new Set());
      }
      setData(d); setErr(""); setTick(Date.now());
    } catch (e) { setErr(`Could not load roles (${(e as Error).message})`); }
  }, [query]);

  loadRef.current = load;
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const id = setInterval(load, 60_000);
    const vis = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", vis);
    return () => { clearInterval(id); document.removeEventListener("visibilitychange", vis); };
  }, [load]);

  const roles = useMemo(() => {
    if (!data) return [];
    const needle = q.trim().toLowerCase();
    return data.roles
      .filter((r) => (showClosed || !r.closed || marked))
      .filter((r) => r.score >= minScore)
      .filter((r) => !hideSenior || ((r.yearsReq ?? 0) < 4 && (r.detail?.seniority ?? 0) < 5 && r.aiVerdict !== "stretch" && !r.detail?.languages?.length))
      .filter((r) => !needle || `${r.title} ${r.company} ${r.location}`.toLowerCase().includes(needle))
      .filter((r) => status === "all" ? true : status === "todo" ? !r.appliedAt : status === "applied" ? !!r.appliedAt : !!r.contactedAt)
      .sort((a, b) => sort === "score" ? b.score - a.score || +new Date(b.at ?? 0) - +new Date(a.at ?? 0) : +new Date(b.at ?? 0) - +new Date(a.at ?? 0));
  }, [data, q, minScore, status, sort, showClosed, hideSenior, marked]);

  // One card per company: its best-scoring role (newest breaks ties). The rest are tucked under it.
  type Card = Role & { others: Role[] };
  const cards: Card[] = useMemo(() => {
    if (!dedupe) return roles.map((r) => ({ ...r, others: [] }));
    const best = (a: Role, b: Role) => b.score - a.score || +new Date(b.at ?? 0) - +new Date(a.at ?? 0);
    const by = new Map<string, Role[]>();
    for (const r of roles) by.set(r.company, [...(by.get(r.company) ?? []), r]);
    const out = [...by.values()].map((g) => { const [top, ...others] = [...g].sort(best); return { ...top, others }; });
    return out.sort((a, b) => sort === "score" ? b.score - a.score || +new Date(b.at ?? 0) - +new Date(a.at ?? 0) : +new Date(b.at ?? 0) - +new Date(a.at ?? 0));
  }, [roles, dedupe, sort]);

  async function mark(r: Role, body: { applied?: boolean; contacted?: boolean; note?: string }) {
    const prev = { appliedAt: r.appliedAt, contactedAt: r.contactedAt, note: r.note };
    const patch = (v: Partial<Role>) => setData((d) => d && { ...d, roles: d.roles.map((x) => (x.key === r.key ? { ...x, ...v } : x)) });
    const nowIso = new Date().toISOString();
    patch({
      ...(body.applied !== undefined && { appliedAt: body.applied ? nowIso : null }),
      ...(body.contacted !== undefined && { contactedAt: body.contacted ? nowIso : null, note: body.contacted ? body.note ?? r.note : null }),
    });
    try {
      const res = await fetch("/api/mark", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ key: r.key, ...body }) });
      if (!res.ok) throw new Error();
      const m = await res.json();
      patch({ appliedAt: m.appliedAt, contactedAt: m.contactedAt, note: m.note });
      if (body.applied !== undefined) load();
    } catch { patch(prev); setErr("Could not save that change"); }
  }

  async function toggleDesc(r: Role) {
    setOpen(open === r.key ? null : r.key);
    if (descs[r.key] === undefined) {
      const res = await fetch(`/api/role/${r.key}`);
      const d = res.ok ? await res.json() : { description: "Could not load the description." };
      setDescs((x) => ({ ...x, [r.key]: d.description }));
    }
  }

  function exportHelper() {
    if (!data) return;
    const today = new Date(tick).toLocaleDateString("en-CA", { timeZone: TZ });
    const jobs = roles.filter((r) => !r.appliedAt && !r.closed).slice(0, 40).map((r) => ({
      decision: "KEEP", company: r.company, title: r.title, url: r.applyUrl, firstSeenDate: today, postedDate: r.at?.slice(0, 10) ?? "",
      postingSourceUrl: r.applyUrl, location: r.location, workMode: r.mode === "remote" ? "Remote" : "Not stated", pay: r.pay ?? "Unknown",
      fitReview: `Score ${r.score}/100${r.yearsReq ? `; asks ${r.yearsReq}+ yrs` : "; no years listed"}${r.isSf ? "; SF" : ""}`,
    }));
    const body = { schemaVersion: 1, batchDate: today, generatedAt: new Date().toISOString(), submittedCheckedAt: new Date().toISOString(), submittedUrls: data.appliedUrls.filter(Boolean), submittedCompanies: data.appliedCompanies, jobs };
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(body, null, 2)], { type: "application/json" }));
    a.download = `daily-refresh-${today}.json`;
    a.click();
  }

  const applied = data?.roles.filter((r) => r.appliedAt).length ?? 0;
  const contacted = data?.roles.filter((r) => r.contactedAt).length ?? 0;

  return (
    <div className="wrap">
      <header className="top">
        <div>
          <h1>Job board</h1>
          <div className="sub">
            {data ? `${dedupe ? `${cards.length} companies · ` : ""}${roles.length} roles · ${applied} applied · ${contacted} contacted` : "Loading…"}
            {data?.lastPoll && ` · last poll ${ago(data.lastPoll.finished_at, tick)}${data.lastPoll.boards_failed ? ` (${data.lastPoll.boards_failed} boards failed)` : ""}`}
          </div>
        </div>
        <div className="row">
          {ext && (
            <button className="btn small" title="Opens the 5 best not-yet-applied roles in a new window and prefills each one"
              onClick={() => prefill(roles.filter((r) => !r.appliedAt && !r.closed && /ashbyhq\.com|greenhouse\.io|lever\.co/.test(r.applyUrl)).slice(0, 5))}>Prefill top 5</button>
          )}
          <button className="btn small" onClick={exportHelper} title="Download a daily-refresh JSON for the Application Helper extension (top 40 not-yet-applied roles in this view)">Export for Application Helper</button>
          <button className="btn small" onClick={async () => { await fetch("/api/logout", { method: "POST" }); location.href = "/login"; }}>Sign out</button>
        </div>
      </header>

      <div className="filters">
        <div className="row">
          <span className="lbl">Day</span>
          {wins.map((w) => (
            <button key={w.id} className={`chipbtn ${winId === w.id && !marked ? "on" : ""}`} onClick={() => { setWinId(w.id); if (marked) setStatus("all"); }}>{w.label}</button>
          ))}
        </div>
        <div className="row">
          <span className="lbl">Where</span>
          {([["bay", "Bay Area hybrid/onsite"], ["remote", "Remote (US)"], ["both", "Both"]] as const).map(([v, l]) => (
            <button key={v} className={`chipbtn ${loc === v ? "on" : ""}`} onClick={() => setLoc(v)}>{l}</button>
          ))}
          <span className="lbl" style={{ marginLeft: 10 }}>Status</span>
          {([["all", "All"], ["todo", "Not applied"], ["applied", "Applied"], ["contacted", "Contacted"]] as const).map(([v, l]) => (
            <button key={v} className={`chipbtn ${status === v ? "on" : ""}`} onClick={() => setStatus(v)}>{l}</button>
          ))}
        </div>
        <div className="row">
          <input type="search" placeholder="Search title, company, location" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
          <label className="sub">Min score {minScore}
            <input type="range" min={0} max={90} step={5} value={minScore} onChange={(e) => setMinScore(+e.target.value)} style={{ marginLeft: 8, verticalAlign: "middle" }} />
          </label>
          <select value={sort} onChange={(e) => setSort(e.target.value as "score" | "new")} aria-label="Sort">
            <option value="score">Sort: best score</option>
            <option value="new">Sort: newest</option>
          </select>
          <label className="sub"><input type="checkbox" checked={dedupe} onChange={(e) => setDedupe(e.target.checked)} /> one role per company</label>
          <label className="sub"><input type="checkbox" checked={hideSenior} onChange={(e) => setHideSenior(e.target.checked)} /> hide 4+ yrs / senior / language req</label>
          <label className="sub" title="Roles Claude judged not to be software jobs for you"><input type="checkbox" checked={showHidden} onChange={(e) => setShowHidden(e.target.checked)} /> show filtered out{data?.hiddenCount ? ` (${data.hiddenCount})` : ""}</label>
          <label className="sub"><input type="checkbox" checked={showClosed} onChange={(e) => setShowClosed(e.target.checked)} /> show closed</label>
        </div>
      </div>

      {err && <div className="newbar" style={{ background: "var(--badbg)", color: "var(--bad)" }}>{err}</div>}
      {fresh.size > 0 && <div className="newbar">{fresh.size} new role{fresh.size > 1 ? "s" : ""} arrived while you were here (outlined below)</div>}

      {data && cards.length === 0 && <div className="empty">Nothing matches. Try a wider day range or lower the minimum score.</div>}

      <div className="grid">
        {cards.map((r) => {
          const d = r.detail;
          const cls = r.score >= 70 ? "hi" : r.score >= 45 ? "mid" : "lo";
          return (
            <article key={r.key} className={`card ${r.appliedAt ? "applied" : ""} ${r.closed ? "closed" : ""} ${fresh.has(r.key) ? "fresh" : ""}`}>
              <div className="head">
                <div>
                  <h2 className="title">{r.title}</h2>
                  <div className="co">{r.company}</div>
                </div>
                <div className={`score ${cls}`} title={d ? (d.ai ? `Claude fit ${d.fit}/100 x 0.8 + location ${d.loc}/20` : `Unscored by Claude yet. Rules: role ${d.title}/25 + skills ${d.skills}/25 + experience ${d.exp}/30 + location ${d.loc}/20`) : ""}>{r.score}</div>
              </div>
              <div className="chips">
                {r.isSf ? <span className="chip sf">San Francisco</span> : r.mode === "bay" ? <span className="chip ok">Bay Area</span> : <span className="chip warn">Remote</span>}
                <span className={`chip ${r.yearsReq && r.yearsReq >= 4 ? "bad" : r.yearsReq && r.yearsReq >= 3 ? "warn" : "ok"}`}>{r.yearsReq ? `${r.yearsReq}+ yrs` : d?.seniority && d.seniority >= 5 ? "senior title" : "no yrs listed"}</span>
                {d && !d.ai && <span className="chip" title="Claude has not read this posting yet; the score is a rough rule-based guess">unscored</span>}
                {!!d?.gaps?.length && <span className="chip warn" title="Required skills your resume does not show">gap: {d.gaps.join(", ")}</span>}
                {!!d?.languages?.length && <span className="chip bad" title="The posting requires fluency in another language">needs {d.languages.join(" / ")}</span>}
                {r.pay && <span className="chip">{r.pay}</span>}
                {r.closed && <span className="chip bad">closed</span>}
                {fills[r.key] && <span className={`chip ${/Filled/.test(fills[r.key].state) ? "ok" : /Opening|Loading/.test(fills[r.key].state) ? "" : "warn"}`} title={fills[r.key].message}>{fills[r.key].state}</span>}
                {r.contactedAt && <span className="chip ok">contacted</span>}
                {r.appliedAt && <span className="chip ok">applied</span>}
              </div>
              <div className="loc">{r.location}</div>
              {r.aiReason ? <p className="snip" title="Claude's read of the full posting">{r.aiReason}</p> : r.snippet && <p className="snip">{r.snippet}</p>}
              {d && (
                <div className="bars">
                  {((d.ai ? [["Fit", Math.round((d.fit ?? 0) * 0.8), 80], ["Where", d.loc, 20]] : [["Role", (d.title ?? 0) + (d.skills ?? 0), 50], ["Years", d.exp ?? 0, 30], ["Where", d.loc, 20]]) as [string, number, number][]).map(([l, v, mx]) => (
                    <div className="bar" key={l}><span>{l}</span><i><b style={{ width: `${(v / mx) * 100}%` }} /></i><span>{v}/{mx}</span></div>
                  ))}
                </div>
              )}
              <div className="time">{r.postedAt ? `Posted ${fmt(r.postedAt)}` : `First seen ${fmt(r.firstSeen)}`} · {ago(r.postedAt ?? r.firstSeen, tick)}</div>
              <div className="actions">
                {ext && /ashbyhq\.com|greenhouse\.io|lever\.co/.test(r.applyUrl) ? (
                  <>
                    <button className="apply" onClick={() => prefill([r])}>Open &amp; prefill</button>
                    <a className="btn small" href={r.applyUrl} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>Open only ↗</a>
                  </>
                ) : (
                  <a className="apply" href={r.applyUrl} target="_blank" rel="noopener noreferrer">Open application ↗</a>
                )}
                <button className={`btn small tog ${r.appliedAt ? "on" : ""}`} onClick={() => mark(r, { applied: !r.appliedAt })}>{r.appliedAt ? "✓ Applied" : "Mark applied"}</button>
                <button className={`btn small tog ${r.contactedAt ? "on" : ""}`} onClick={() => (r.contactedAt ? mark(r, { contacted: false }) : setNoteFor(noteFor === r.key ? null : r.key))}>{r.contactedAt ? "✓ Contacted" : "Contacted"}</button>
                <button className="btn small" onClick={() => toggleDesc(r)}>{open === r.key ? "Hide" : "Details"}</button>
              </div>
              {noteFor === r.key && !r.contactedAt && (
                <form className="note" onSubmit={(e) => { e.preventDefault(); const v = new FormData(e.currentTarget).get("n") as string; mark(r, { contacted: true, note: v }); setNoteFor(null); }}>
                  <input name="n" autoFocus placeholder="Who did you contact? (optional)" maxLength={500} />
                  <button className="btn small">Save</button>
                </form>
              )}
              {r.contactedAt && r.note && <div className="loc">Contacted: {r.note}</div>}
              {r.others.length > 0 && (
                <div>
                  <button className="btn small" onClick={() => setExpanded((x) => { const n = new Set(x); n.has(r.key) ? n.delete(r.key) : n.add(r.key); return n; })}>
                    {expanded.has(r.key) ? "Hide" : "+"} {r.others.length} more at {r.company}
                  </button>
                  {expanded.has(r.key) && (
                    <ul className="others">
                      {r.others.map((o) => (
                        <li key={o.key}>
                          <span className={`mini ${o.score >= 70 ? "hi" : o.score >= 45 ? "mid" : ""}`}>{o.score}</span>
                          <a href={o.applyUrl} target="_blank" rel="noopener noreferrer">{o.title}</a>
                          <span className="time">{o.isSf ? "SF" : o.mode === "remote" ? "Remote" : "Bay"}{o.yearsReq ? ` · ${o.yearsReq}+ yrs` : ""}{o.appliedAt ? " · applied" : ""}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {open === r.key && <div className="desc">{descs[r.key] ?? "Loading…"}</div>}
            </article>
          );
        })}
      </div>
    </div>
  );
}
