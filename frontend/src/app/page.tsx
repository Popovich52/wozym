"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { platformMe } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";

export default function Home() {
  const { token, isReady } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isReady) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await platformMe(token);
        if (!cancelled) router.replace("/platform");
      } catch {
        if (!cancelled) router.replace("/dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isReady, token, router]);

  return (
    <main className="mp-shell min-h-screen flex items-center justify-center">
      <section className="mp-card w-full max-w-xl p-8">
        <h1 className="text-3xl font-bold tracking-tight">WOzYm - AI платформа продаж Dashboard</h1>
        <p className="mt-2 text-sm text-[var(--mp-muted)]">Переадресация в рабочий кабинет...</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link className="mp-btn-primary" href="/dashboard">
            Dashboard
          </Link>
          <Link className="mp-btn-secondary" href="/login">
            Login
          </Link>
          <Link className="mp-btn-secondary" href="/register">
            Register
          </Link>
        </div>
      </section>
    </main>
  );
}

