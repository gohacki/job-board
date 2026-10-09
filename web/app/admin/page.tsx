import Link from "next/link";

export default function Admin() {
  return (
    <main>
      <h1>Admin</h1>
      <ul>
        <li><Link href="/admin/export">Export</Link>: list existing postings as JSON, to check for duplicates first.</li>
        <li><Link href="/admin/import">Import</Link>: paste postings as JSON or CSV.</li>
        <li><Link href="/admin/status">Status</Link>: set applied or contacted and a note for one posting key.</li>
      </ul>
    </main>
  );
}
