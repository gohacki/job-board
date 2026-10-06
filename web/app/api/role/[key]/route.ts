import { NextRequest, NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(_req: NextRequest, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  const [row] = await sql`SELECT description FROM listings WHERE key = ${key}`;
  if (!row) return NextResponse.json({ error: "not found" }, { status: 404 });
  return NextResponse.json({ description: row.description ?? "" });
}
