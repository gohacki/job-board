"use client";
import { useState } from "react";

export default function ExportPage() {
  const [q, setQ] = useState(""), [source, setSource] = useState("all"), [hidden, setHidden] = useState(false), [limit, setLimit] = useState("25000");
  const [out, setOut] = useState(""), [msg, setMsg] = useState(""), [busy, setBusy] = useState(false);
  async function load(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMsg("Loading..."); setOut("");
    const p = new URLSearchParams({ source, limit, ...(q ? { q } : {}), ...(hidden ? { hidden: "1" } : {}) });
    const r = await fetch(`/api/admin/export?${p}`);
    const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
    if (Array.isArray(j)) { setOut(JSON.stringify(j, null, 1)); setMsg(`${j.length} listings`); } else setMsg(j.error ?? "error");
    setBusy(false);
  }
  return (
    <main>
      <h1>Export listings</h1>
      <form onSubmit={load}>
        <div className="row">
          <label htmlFor="export-q">Contains (company, title or url)</label>
          <input id="export-q" name="export-q" type="text" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="row">
          <label htmlFor="export-source">Source</label>
          <select id="export-source" name="export-source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="all">All</option><option value="manual">Manual imports only</option><option value="scanned">Scanned only</option>
          </select>
          <label htmlFor="export-hidden">Include filtered-out roles</label>
          <input id="export-hidden" name="export-hidden" type="checkbox" checked={hidden} onChange={(e) => setHidden(e.target.checked)} />
          <label htmlFor="export-limit">Max rows</label>
          <input id="export-limit" name="export-limit" type="text" value={limit} onChange={(e) => setLimit(e.target.value)} size={7} />
        </div>
        <button id="export-load" className="primary" type="submit" disabled={busy}>Load listings</button>
      </form>
      <p id="export-count" className="sub">{msg}</p>
      <label htmlFor="export-output" className="sub">JSON: company, title, url, key, status</label><br />
      <textarea id="export-output" name="export-output" rows={22} readOnly style={{ width: "100%", fontFamily: "monospace" }} value={out} />
    </main>
  );
}
