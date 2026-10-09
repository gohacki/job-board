"use client";
import { useState } from "react";

const EXAMPLE = `[{"company":"Acme","title":"Software Engineer","location":"San Francisco, CA","url":"https://example.com/jobs/1","source":"referral","posted":"2026-10-08","workmode":"hybrid","level":"entry","notes":"intro from Sam"}]`;

export default function ImportPage() {
  const [text, setText] = useState("");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setOut("Importing...");
    const r = await fetch("/api/admin/import", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ text }) });
    const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
    setOut(JSON.stringify(j, null, 2)); setBusy(false);
  }
  return (
    <main>
      <h1>Import postings</h1>
      <p className="sub">Paste a JSON array or CSV with a header row. Fields: company, title, location, url, source, posted (date), workmode (remote, hybrid or onsite), level, notes. Company and url are required. Hybrid and onsite roles must be in the Bay Area. Up to 500 rows per import.</p>
      <form onSubmit={submit}>
        <label htmlFor="import-text"><b>Postings (JSON or CSV)</b></label><br />
        <textarea id="import-text" name="import-text" rows={16} style={{ width: "100%", fontFamily: "monospace" }} value={text} onChange={(e) => setText(e.target.value)} placeholder={EXAMPLE} />
        <br />
        <button id="import-submit" className="primary" type="submit" disabled={busy || !text.trim()}>Import</button>
      </form>
      <h2>Result</h2>
      <label htmlFor="import-result" className="sub">Counts: added, updated, skippedDuplicate, plus per-row errors</label><br />
      <textarea id="import-result" name="import-result" rows={14} readOnly style={{ width: "100%", fontFamily: "monospace" }} value={out} />
    </main>
  );
}
