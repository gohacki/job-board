import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

// Session-protected view of a tailored resume (PDF), or ?changes=1 for the list of edits made.
export async function GET(req: NextRequest, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  if (req.nextUrl.searchParams.get("changes") === "1") {
    const [c] = await sql`SELECT changes FROM resumes WHERE key = ${key}`;
    return c ? NextResponse.json({ changes: c.changes ?? [] }) : NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const [r] = await sql`SELECT pdf FROM resumes WHERE key = ${key}`;
  if (!r) return NextResponse.json({ error: "not found" }, { status: 404 });
  return new NextResponse(new Uint8Array(r.pdf as Buffer), { headers: { "content-type": "application/pdf", "content-disposition": 'inline; filename="Miro_Gohacki_Resume.pdf"' } });
}
