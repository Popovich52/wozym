"use client";

import { useEffect, useState } from "react";

import { platformAudit } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformAuditPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !actor) return;
    platformAudit(token)
      .then((data) => {
        setRows(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load audit"));
  }, [token, actor]);

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading platform audit...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="mp-card p-5">
      <h2 className="font-bold">Platform audit</h2>
      {loadError ? <p className="mt-2 mp-error">{loadError}</p> : null}
      <p className="mt-2 text-sm">Events loaded: {rows.length}</p>
    </section>
  );
}
