import { NextRequest, NextResponse } from "next/server";
import { COOKIE, passwordOk, sessionToken } from "@/lib/auth";
import { allow } from "@/lib/ratelimit";

export async function POST(req: NextRequest) {
  const ip = (req.headers.get("x-forwarded-for") ?? "unknown").split(",")[0].trim();
  if (!(await allow(`login:${ip}`, 10, 600))) return NextResponse.json({ error: "too many attempts, wait a few minutes" }, { status: 429 });
  const { password } = await req.json().catch(() => ({ password: "" }));
  if (!(await passwordOk(String(password ?? "")))) {
    await new Promise((r) => setTimeout(r, 600));
    return NextResponse.json({ error: "wrong password" }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE, await sessionToken(), { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 60 * 60 * 24 * 90 });
  return res;
}
