import Link from "next/link";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <main className="mp-shell min-h-screen flex items-center justify-center">
      <section className="mp-card w-full max-w-md p-6">
        <div className="mb-6">
          <div className="inline-flex rounded-md border border-orange-200 bg-orange-50 px-2 py-1 text-xs font-bold text-orange-700">
            WOzYm - AI платформа продаж
          </div>
          <h1 className="mt-3 text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-[var(--mp-muted)]">{subtitle}</p>
        </div>
        {children}
        <div className="mt-6 border-t border-[var(--mp-line)] pt-4 text-xs text-[var(--mp-muted)]">
          <Link href="/login" className="underline decoration-orange-500 decoration-2 underline-offset-2">
            Login
          </Link>{" "}
          |{" "}
          <Link href="/register" className="underline decoration-orange-500 decoration-2 underline-offset-2">
            Register
          </Link>
        </div>
      </section>
    </main>
  );
}

