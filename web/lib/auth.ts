// Single-user password gate. The cookie is an HMAC of a constant, so it only proves the
// password was known when the cookie was issued; rotate AUTH_SECRET to sign everyone out.
export const COOKIE = "jb_session";

async function hmac(secret: string, msg: string) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function sessionToken() {
  const secret = process.env.AUTH_SECRET;
  if (!secret) throw new Error("AUTH_SECRET is not set");
  return hmac(secret, "job-board:v1");
}

export async function passwordOk(input: string) {
  const expected = process.env.SITE_PASSWORD;
  if (!expected) return false;
  const [a, b] = await Promise.all([hmac("cmp", input), hmac("cmp", expected)]);
  let diff = a.length ^ b.length;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
