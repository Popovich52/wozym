"use client";

import { useEffect, useState } from "react";

import { platformStats, type PlatformStats } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformDashboardPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !actor) return;
    platformStats(token)
      .then((row) => {
        setStats(row);
        setStatsError(null);
      })
      .catch((err) => setStatsError(err instanceof Error ? err.message : "Failed to load stats"));
  }, [token, actor]);

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading platform console...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <>
      <section className="mp-card p-5">
        <h2 className="font-bold">Platform actor</h2>
        <p className="mt-2 text-sm">User ID: {actor?.user_id}</p>
        <p className="text-sm">Role: {actor?.role}</p>
        <p className="text-sm">Status: {actor?.status}</p>
      </section>
      <section className="grid gap-4 md:grid-cols-2">
        <article className="mp-card p-5">
          <h3 className="font-bold">Users</h3>
          <p className="mt-2 text-3xl font-bold">{stats?.users_total ?? "-"}</p>
        </article>
        <article className="mp-card p-5">
          <h3 className="font-bold">Teams</h3>
          <p className="mt-2 text-3xl font-bold">{stats?.teams_total ?? "-"}</p>
        </article>
      </section>
      {statsError ? <section className="mp-card p-5 mp-error">{statsError}</section> : null}
    </>
  );
}
