import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Job board", description: "New roles, scored against my resume", robots: { index: false, follow: false } };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
