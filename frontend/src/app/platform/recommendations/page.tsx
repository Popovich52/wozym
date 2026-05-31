"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  platformCreateRecommendation,
  platformDisableRecommendation,
  platformPatchRecommendation,
  platformRecommendations,
  type DashboardRecommendation,
} from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

export default function PlatformRecommendationsPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<DashboardRecommendation[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [ctaLabel, setCtaLabel] = useState("");
  const [ctaHref, setCtaHref] = useState("");
  const [priority, setPriority] = useState(100);
  const [targetMarketplace, setTargetMarketplace] = useState("");
  const [targetTeamRole, setTargetTeamRole] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadRows = useCallback(async (activeToken: string) => {
    const data = await platformRecommendations(activeToken);
    setRows(data);
  }, []);

  useEffect(() => {
    if (!token || !actor) return;
    Promise.resolve()
      .then(() => loadRows(token))
      .then(() => setLoadError(null))
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load recommendations"));
  }, [loadRows, token, actor]);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    try {
      setLoadError(null);
      await platformCreateRecommendation(token, {
        title,
        body,
        cta_label: ctaLabel || undefined,
        cta_href: ctaHref || undefined,
        priority,
        target_marketplace: targetMarketplace || undefined,
        target_team_role: targetTeamRole || undefined,
        is_active: true,
      });
      setTitle("");
      setBody("");
      setCtaLabel("");
      setCtaHref("");
      setPriority(100);
      setTargetMarketplace("");
      setTargetTeamRole("");
      setMessage("Recommendation created");
      await loadRows(token);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to create recommendation");
    }
  }

  async function onToggleActive(row: DashboardRecommendation) {
    if (!token) return;
    try {
      setLoadError(null);
      await platformPatchRecommendation(token, row.id, { is_active: !row.is_active });
      await loadRows(token);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to update recommendation");
    }
  }

  async function onDisable(rowId: number) {
    if (!token) return;
    try {
      setLoadError(null);
      await platformDisableRecommendation(token, rowId);
      await loadRows(token);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to disable recommendation");
    }
  }

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading recommendation admin...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="space-y-4">
      <article className="mp-card p-5">
        <h2 className="font-bold">Dashboard recommendations</h2>
        <p className="mt-1 text-sm text-[var(--mp-muted)]">Управление рекомендациями для клиентского дашборда.</p>
        <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
          <input className="mp-input" placeholder="Title" value={title} onChange={(event) => setTitle(event.target.value)} />
          <input className="mp-input" placeholder="CTA label" value={ctaLabel} onChange={(event) => setCtaLabel(event.target.value)} />
          <textarea className="mp-input min-h-24 md:col-span-2" placeholder="Body" value={body} onChange={(event) => setBody(event.target.value)} />
          <input className="mp-input" placeholder="CTA href" value={ctaHref} onChange={(event) => setCtaHref(event.target.value)} />
          <input
            className="mp-input"
            type="number"
            placeholder="Priority"
            value={priority}
            onChange={(event) => setPriority(Number(event.target.value))}
          />
          <input
            className="mp-input"
            placeholder="Target marketplace (WB/OZON)"
            value={targetMarketplace}
            onChange={(event) => setTargetMarketplace(event.target.value.toUpperCase())}
          />
          <input
            className="mp-input"
            placeholder="Target team role (OWNER/...)"
            value={targetTeamRole}
            onChange={(event) => setTargetTeamRole(event.target.value.toUpperCase())}
          />
          <button className="mp-btn-primary md:col-span-2" type="submit">
            Create recommendation
          </button>
        </form>
        {message ? <p className="mt-2 text-sm text-green-700">{message}</p> : null}
        {loadError ? <p className="mt-2 mp-error">{loadError}</p> : null}
      </article>

      <article className="mp-card p-5">
        <h3 className="font-bold">Configured recommendations</h3>
        <div className="mt-3 space-y-3">
          {rows.map((row) => (
            <div className="rounded-lg border border-[var(--mp-line)] p-3" key={row.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">
                  #{row.id} {row.title}
                </p>
                <div className="flex gap-2">
                  <button className="mp-btn-secondary" onClick={() => onToggleActive(row)} type="button">
                    {row.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button className="mp-btn-secondary" onClick={() => onDisable(row.id)} type="button">
                    Disable
                  </button>
                </div>
              </div>
              <p className="mt-1 text-sm text-[var(--mp-muted)]">{row.body}</p>
              <p className="mt-1 text-xs text-[var(--mp-muted)]">
                priority:{row.priority} role:{row.target_team_role || "*"} marketplace:{row.target_marketplace || "*"}
              </p>
            </div>
          ))}
          {!rows.length ? <p className="text-sm text-[var(--mp-muted)]">No recommendations configured.</p> : null}
        </div>
      </article>
    </section>
  );
}
