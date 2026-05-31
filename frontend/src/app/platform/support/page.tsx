"use client";

import { useEffect, useState } from "react";

import { platformSupportTickets, platformUpdateSupportTicket } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformSupportPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<Array<{ id?: number; status?: string }>>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !actor) return;
    platformSupportTickets(token)
      .then((data) => {
        setRows(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load tickets"));
  }, [token, actor]);

  async function onUpdatePlaceholder() {
    if (!token) return;
    try {
      const result = await platformUpdateSupportTicket(token, 1);
      setMessage(result.message);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to update ticket");
    }
  }

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading support workspace...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="mp-card p-5">
      <h2 className="font-bold">Support tickets</h2>
      <p className="mt-1 text-sm text-[var(--mp-muted)]">Placeholder endpoint is connected, real ticket backend will be added next phase.</p>
      <div className="mt-3 flex gap-2">
        <button className="mp-btn-primary" onClick={onUpdatePlaceholder} type="button">
          Call patch placeholder
        </button>
      </div>
      {message ? <p className="mt-2 text-sm text-green-700">{message}</p> : null}
      {loadError ? <p className="mt-2 mp-error">{loadError}</p> : null}
      <div className="mt-4 text-sm">
        Tickets loaded: <span className="font-semibold">{rows.length}</span>
      </div>
    </section>
  );
}
