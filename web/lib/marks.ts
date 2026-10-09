import { sql } from "@/lib/db";

export type MarkInput = { applied?: boolean; contacted?: boolean; note?: string };

/** Shared by /api/mark and /api/admin/status. Returns null when the listing key does not exist. */
export async function applyMark(key: string, b: MarkInput) {
  const [exists] = await sql`SELECT 1 FROM listings WHERE key = ${key}`;
  if (!exists) return null;
  await sql`INSERT INTO marks(key) VALUES (${key}) ON CONFLICT (key) DO NOTHING`;
  if (typeof b.applied === "boolean")
    await sql`UPDATE marks SET applied_at = ${b.applied ? sql`coalesce(applied_at, now())` : null} WHERE key = ${key}`;
  if (typeof b.contacted === "boolean")
    await sql`UPDATE marks SET contacted_at = ${b.contacted ? sql`coalesce(contacted_at, now())` : null},
              contact_note = ${b.contacted ? (typeof b.note === "string" ? b.note.slice(0, 500) : null) : null} WHERE key = ${key}`;
  else if (typeof b.note === "string")
    await sql`UPDATE marks SET contact_note = ${b.note.slice(0, 500)} WHERE key = ${key}`;
  const [m] = await sql`SELECT applied_at, contacted_at, contact_note FROM marks WHERE key = ${key}`;
  return { appliedAt: m.applied_at, contactedAt: m.contacted_at, note: m.contact_note };
}
