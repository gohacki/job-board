import { sql } from "@/lib/db";

let ready: Promise<unknown> | null = null;
/** Fixed-window counter in Postgres, so the limit holds across serverless instances. Returns true if allowed. */
export async function allow(bucket: string, max: number, windowSec: number) {
  ready ??= sql`CREATE TABLE IF NOT EXISTS rate_limits(bucket text PRIMARY KEY, count int NOT NULL, window_start timestamptz NOT NULL)`;
  await ready;
  const [r] = await sql`
    INSERT INTO rate_limits(bucket, count, window_start) VALUES (${bucket}, 1, now())
    ON CONFLICT (bucket) DO UPDATE SET
      count = CASE WHEN rate_limits.window_start < now() - make_interval(secs => ${windowSec}) THEN 1 ELSE rate_limits.count + 1 END,
      window_start = CASE WHEN rate_limits.window_start < now() - make_interval(secs => ${windowSec}) THEN now() ELSE rate_limits.window_start END
    RETURNING count`;
  return r.count <= max;
}
