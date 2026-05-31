"use client";

import { Fragment, useEffect, useMemo, useState } from "react";

import { platformAiLogs, type AiGenerationLog } from "@/lib/api";
import { usePlatformGuard } from "@/lib/platform-auth";

function formatCost(value: number | null) {
  if (value === null || value === undefined) return "-";
  return `$${(value / 1_000_000).toFixed(6)}`;
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "success") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (normalized === "failed") return "border-rose-200 bg-rose-50 text-rose-700";
  if (normalized === "running") return "border-blue-200 bg-blue-50 text-blue-700";
  if (normalized === "queued") return "border-slate-200 bg-slate-50 text-slate-700";
  return "border-amber-200 bg-amber-50 text-amber-700";
}

function JsonBlock({ value }: { value: unknown }) {
  const rendered = useMemo(() => JSON.stringify(value ?? {}, null, 2), [value]);
  return (
    <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
      {rendered}
    </pre>
  );
}

export default function PlatformAiLogsPage() {
  const { token, isReady, actor, error, loading } = usePlatformGuard();
  const [rows, setRows] = useState<AiGenerationLog[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [operation, setOperation] = useState("");
  const [teamId, setTeamId] = useState("");
  const [connectionId, setConnectionId] = useState("");
  const [productRowId, setProductRowId] = useState("");

  useEffect(() => {
    if (!token || !actor) return;
    platformAiLogs(token, {
      status,
      operation,
      team_id: teamId,
      connection_id: connectionId,
      product_row_id: productRowId,
      limit: 200,
    })
      .then((data) => {
        setRows(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load AI logs"));
  }, [token, actor, status, operation, teamId, connectionId, productRowId]);

  if (!isReady || loading) {
    return <section className="mp-card p-5 text-sm">Loading AI logs...</section>;
  }
  if (error) {
    return <section className="mp-card p-5 mp-error">Access denied: {error}</section>;
  }

  return (
    <section className="mp-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">AI generation logs</h2>
          <p className="mt-1 text-sm text-[var(--mp-muted)]">Token usage, statuses and debug payloads for every AI generation.</p>
        </div>
        <p className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Rows: {rows.length}</p>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-5">
        <select className="h-10 rounded-md border border-[var(--mp-line)] px-3 text-sm" onChange={(event) => setStatus(event.target.value)} value={status}>
          <option value="">Any status</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="success">success</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
        <input className="h-10 rounded-md border border-[var(--mp-line)] px-3 text-sm" onChange={(event) => setOperation(event.target.value)} placeholder="operation" value={operation} />
        <input className="h-10 rounded-md border border-[var(--mp-line)] px-3 text-sm" onChange={(event) => setTeamId(event.target.value)} placeholder="team_id" value={teamId} />
        <input className="h-10 rounded-md border border-[var(--mp-line)] px-3 text-sm" onChange={(event) => setConnectionId(event.target.value)} placeholder="connection_id" value={connectionId} />
        <input className="h-10 rounded-md border border-[var(--mp-line)] px-3 text-sm" onChange={(event) => setProductRowId(event.target.value)} placeholder="product_row_id" value={productRowId} />
      </div>

      {loadError ? <p className="mt-3 mp-error">{loadError}</p> : null}

      <div className="mt-4 overflow-auto">
        <table className="w-full min-w-[1100px] text-xs">
          <thead className="bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Operation</th>
              <th className="px-3 py-2">Models</th>
              <th className="px-3 py-2 text-right">Tokens</th>
              <th className="px-3 py-2 text-right">Cost</th>
              <th className="px-3 py-2 text-right">Latency</th>
              <th className="px-3 py-2">Scope</th>
              <th className="px-3 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const expanded = expandedId === row.id;
              return (
                <Fragment key={row.id}>
                  <tr className="border-t border-[var(--mp-line)] align-top">
                    <td className="px-3 py-2">
                      <button className="font-semibold text-[var(--mp-indigo)] hover:underline" onClick={() => setExpandedId(expanded ? null : row.id)} type="button">
                        #{row.id}
                      </button>
                      {row.trace_id ? <p className="mt-1 truncate text-[10px] text-[var(--mp-muted)]">{row.trace_id}</p> : null}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusClass(row.status)}`}>{row.status}</span>
                    </td>
                    <td className="px-3 py-2">
                      <p className="font-semibold text-slate-800">{row.operation}</p>
                      <p className="text-[11px] text-[var(--mp-muted)]">{row.provider}</p>
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      <p>text: {row.model_text || "-"}</p>
                      <p>vision: {row.model_vision || "-"}</p>
                      {row.model_image ? <p>image: {row.model_image}</p> : null}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <p className="font-semibold">{row.total_tokens}</p>
                      <p className="text-[11px] text-[var(--mp-muted)]">in {row.prompt_tokens} / out {row.completion_tokens}</p>
                    </td>
                    <td className="px-3 py-2 text-right">{formatCost(row.estimated_cost_microusd)}</td>
                    <td className="px-3 py-2 text-right">{row.latency_ms === null ? "-" : `${row.latency_ms} ms`}</td>
                    <td className="px-3 py-2 text-slate-700">
                      <p>team: {row.team_id ?? "-"}</p>
                      <p>conn: {row.connection_id ?? "-"}</p>
                      <p>product: {row.product_row_id ?? "-"}</p>
                      <p>user: {row.user_id ?? "-"}</p>
                    </td>
                    <td className="px-3 py-2 text-slate-700">{new Date(row.created_at).toLocaleString("ru-RU")}</td>
                  </tr>
                  {expanded ? (
                    <tr className="border-t border-[var(--mp-line)] bg-slate-50">
                      <td className="px-3 py-3" colSpan={9}>
                        <div className="grid gap-3 lg:grid-cols-2">
                          <div>
                            <p className="mb-1 font-semibold">Request</p>
                            <JsonBlock value={row.request} />
                          </div>
                          <div>
                            <p className="mb-1 font-semibold">Response</p>
                            <JsonBlock value={row.response} />
                          </div>
                        </div>
                        {row.error_message ? <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{row.error_message}</p> : null}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {!rows.length && !loadError ? <p className="mt-4 text-sm text-[var(--mp-muted)]">AI logs are empty.</p> : null}
    </section>
  );
}
