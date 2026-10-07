import { NextRequest, NextResponse } from "next/server";
import { COOKIE, sessionToken } from "@/lib/auth";

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname === "/login" || pathname === "/api/login" || pathname.startsWith("/api/ext/")) return NextResponse.next(); // /api/ext/* checks its own bearer token
  const ok = req.cookies.get(COOKIE)?.value === (await sessionToken());
  if (ok) return NextResponse.next();
  if (pathname.startsWith("/api/")) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  return NextResponse.redirect(new URL("/login", req.url));
}

export const config = { matcher: ["/((?!_next/|favicon.ico).*)"] };
