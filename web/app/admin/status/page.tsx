"use client";
import { useState } from "react";

export default function StatusPage() {
  const [key, setKey] = useState(""), [status, setStatus] = useState("applied"), [note, setNote] = useState(""), [out, setOut] = useState(""), [busy, setBusy] = useState(false);
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setOut("Saving...");
    const r = await fetch("/api/admin/status", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ key, status, note }) });
    setOut(JSON.stringify(await r.json().catch(() => ({ error: `HTTP ${r.status}` })), null, 2)); setBusy(false);
  }
  return (
    <main>
      <h1>Set application status</h1>
      <p className="sub">Get a listing key from the Export page.</p>
      <form onSubmit={save}>
        <div className="row"><label htmlFor="status-key">Listing key</label><input id="status-key" name="status-key" type="text" size={70} value={key} onChange={(e) => setKey(e.target.value)} /></div>
        <div className="row"><label htmlFor="status-value">Status</label>
          <select id="status-value" name="status-value" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="none">None</option><option value="applied">Applied</option><option value="contacted">Contacted</option><option value="applied+contacted">Applied and contacted</option>
          </select></div>
        <div><label htmlFor="status-note">Note (kept with the contacted mark, up to 500 characters)</label><br />
          <textarea id="status-note" name="status-note" rows={4} style={{ width: "100%" }} value={note} onChange={(e) => setNote(e.target.value)} /></div>
        <button id="status-save" className="primary" type="submit" disabled={busy || !key.trim()}>Save status</button>
      </form>
      <label htmlFor="status-result" className="sub">Result</label><br />
      <textarea id="status-result" name="status-result" rows={8} readOnly style={{ width: "100%", fontFamily: "monospace" }} value={out} />
    </main>
  );
}
