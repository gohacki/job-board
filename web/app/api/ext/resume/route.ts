import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

// The extension asks for the tailored resume PDF for a role it is about to fill. Bearer EXTENSION_TOKEN.
function authorized(req: NextRequest) {
  const want = process.env.EXTENSION_TOKEN;
  const got = (req.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!want || !got) return false;
  const a = Buffer.from(got), b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function GET(req: NextRequest) {
  if (!authorized(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const key = req.nextUrl.searchParams.get("key") ?? "";
  if (!/^[0-9a-f]{16,64}$/.test(key)) return NextResponse.json({ error: "bad key" }, { status: 400 });
  const [r] = await sql`SELECT filename, encode(pdf, 'base64') AS b64, changes, created_at FROM resumes WHERE key = ${key}`;
  if (!r) return NextResponse.json({ error: "no tailored resume" }, { status: 404 });
  return NextResponse.json({ name: r.filename ?? "Miro_Gohacki_Resume.pdf", base64: String(r.b64).replace(/\n/g, ""), changes: r.changes, createdAt: r.created_at });
}
