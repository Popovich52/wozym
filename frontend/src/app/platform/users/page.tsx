"use client";

import { useEffect, useState } from "react";

import { platformUsers, type PlatformUser } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformUsersPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<PlatformUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !actor) return;
    platformUsers(token)
      .then((data) => {
        setRows(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load users"));
  }, [token, actor]);

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading users...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="mp-card p-5">
      <h2 className="font-bold">User Administration Dashboard</h2>
      <p className="mt-1 text-sm text-[var(--mp-muted)]">Основные параметры пользователей для администрирования.</p>
      {loadError ? <p className="mt-2 mp-error">{loadError}</p> : null}
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--mp-line)]">
              <th className="py-2">ID</th>
              <th className="py-2">Email</th>
              <th className="py-2">TG</th>
              <th className="py-2">MAX</th>
              <th className="py-2">Registered</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className="border-b border-[var(--mp-line)]" key={row.id}>
                <td className="py-2">{row.id}</td>
                <td className="py-2">{row.email}</td>
                <td className="py-2">{row.telegram || "-"}</td>
                <td className="py-2">{row.max || "-"}</td>
                <td className="py-2">{new Date(row.registered_at).toLocaleString()}</td>
                <td className="py-2">{row.status}</td>
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td className="py-2 text-[var(--mp-muted)]" colSpan={6}>
                  No users
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
