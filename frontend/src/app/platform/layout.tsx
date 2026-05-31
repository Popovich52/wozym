import Link from "next/link";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mp-shell space-y-5">
      <header className="mp-card p-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Platform Console</h1>
          <p className="text-sm text-[var(--mp-muted)]">System operations and support workspace.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="mp-btn-secondary" href="/platform">
            Dashboard
          </Link>
          <Link className="mp-btn-secondary" href="/platform/users">
            Users
          </Link>
          <Link className="mp-btn-secondary" href="/platform/teams">
            Teams
          </Link>
          <Link className="mp-btn-secondary" href="/platform/support">
            Support
          </Link>
          <Link className="mp-btn-secondary" href="/platform/recommendations">
            Recos
          </Link>
          <Link className="mp-btn-secondary" href="/platform/audit">
            Audit
          </Link>
          <Link className="mp-btn-secondary" href="/platform/ai-logs">
            AI Logs
          </Link>
          <Link className="mp-btn-secondary" href="/profile">
            Client LK
          </Link>
        </div>
      </header>
      {children}
    </main>
  );
}
