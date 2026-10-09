import Link from "next/link";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="wrap" style={{ maxWidth: 900 }}>
      <nav className="row" aria-label="Admin" style={{ marginBottom: 16 }}>
        <Link className="btn" href="/">Board</Link>
        <Link className="btn" href="/admin/import">Import</Link>
        <Link className="btn" href="/admin/export">Export</Link>
        <Link className="btn" href="/admin/status">Status</Link>
      </nav>
      {children}
    </div>
  );
}
