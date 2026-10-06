"use client";
import { useState } from "react";

export default function Login() {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const r = await fetch("/api/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ password: pw }) });
    if (r.ok) location.href = "/";
    else { setErr("Wrong password"); setBusy(false); }
  }
  return (
    <main className="login">
      <form onSubmit={submit} className="loginbox">
        <h1>Job board</h1>
        <input type="password" autoFocus placeholder="Password" value={pw} onChange={(e) => setPw(e.target.value)} aria-label="Password" />
        <button className="primary" disabled={busy || !pw}>Enter</button>
        {err && <p className="err">{err}</p>}
      </form>
    </main>
  );
}
