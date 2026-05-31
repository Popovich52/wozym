"use client";

import { useEffect, useState } from "react";

import { platformTeams, type PlatformTeam } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformTeamsPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<PlatformTeam[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !actor) return;
    platformTeams(token)
      .then((data) => {
        setRows(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load teams"));
  }, [token, actor]);

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading teams...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="mp-card p-5">
      <h2 className="font-bold">Teams</h2>
      {loadError ? <p className="mt-2 mp-error">{loadError}</p> : null}
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--mp-line)]">
              <th className="py-2">ID</th>
              <th className="py-2">Slug</th>
              <th className="py-2">Name</th>
              <th className="py-2">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className="border-b border-[var(--mp-line)]" key={row.id}>
                <td className="py-2">{row.id}</td>
                <td className="py-2">{row.slug}</td>
                <td className="py-2">{row.name}</td>
                <td className="py-2">{row.is_active ? "yes" : "no"}</td>
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td className="py-2 text-[var(--mp-muted)]" colSpan={4}>
                  No teams
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
