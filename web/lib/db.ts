import postgres from "postgres";

const url = process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL is not set");
const local = /sslmode=disable|127\.0\.0\.1|localhost/.test(url);

const g = globalThis as unknown as { _sql?: ReturnType<typeof postgres> };
export const sql =
  g._sql ?? (g._sql = postgres(url, { ssl: local ? false : "require", max: 3, prepare: false, idle_timeout: 20 }));
