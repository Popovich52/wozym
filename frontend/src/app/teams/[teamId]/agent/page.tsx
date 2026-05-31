"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { agentChat, listTeamConnections, type AgentChatResult, type MarketplaceConnection } from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

export default function TeamAgentSandboxPage() {
  const { token, isReady } = useAuth();
  const params = useParams<{ teamId: string }>();
  const router = useRouter();
  const teamId = useMemo(() => Number(params.teamId), [params.teamId]);
  const [connections, setConnections] = useState<MarketplaceConnection[]>([]);
  const [connectionId, setConnectionId] = useState<number | null>(null);
  const [message, setMessage] = useState("Подскажи риски по поставкам");
  const [executeTool, setExecuteTool] = useState(false);
  const [writeMode, setWriteMode] = useState(false);
  const [confirmWrite, setConfirmWrite] = useState("");
  const [result, setResult] = useState<AgentChatResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token || Number.isNaN(teamId)) return;
    listTeamConnections(token, teamId)
      .then((rows) => {
        setConnections(rows);
        if (rows.length) setConnectionId(rows[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load connections"));
  }, [token, teamId]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    if (executeTool && writeMode && confirmWrite.trim().toUpperCase() !== "CONFIRM") {
      setError("Для write mode введите CONFIRM");
      return;
    }
    try {
      setError(null);
      const payload = await agentChat(token, {
        team_id: teamId,
        connection_id: connectionId ?? undefined,
        message,
        execute_tool: executeTool,
        write_mode: writeMode,
      });
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent request failed");
    }
  }

  if (!isReady || !token || Number.isNaN(teamId)) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <section className="mp-card p-6 text-sm">Loading agent sandbox...</section>
      </main>
    );
  }

  return (
    <main className="mp-shell space-y-5">
      <header className="mp-card p-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agent Sandbox</h1>
          <p className="text-sm text-[var(--mp-muted)]">Read-only и write-mode с обязательным подтверждением.</p>
        </div>
        <Link className="mp-btn-secondary" href="/dashboard">
          Back to dashboard
        </Link>
      </header>

      <section className="mp-card p-5">
        <form className="space-y-3" onSubmit={onSubmit}>
          <div>
            <label className="text-xs font-semibold text-[var(--mp-muted)]">Connection</label>
            <select className="mp-input mt-1" value={connectionId ?? ""} onChange={(event) => setConnectionId(Number(event.target.value))}>
              {connections.map((connection) => (
                <option key={connection.id} value={connection.id}>
                  {connection.name} ({connection.provider})
                </option>
              ))}
            </select>
          </div>
          <textarea className="mp-input min-h-28" value={message} onChange={(event) => setMessage(event.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input checked={executeTool} onChange={(event) => setExecuteTool(event.target.checked)} type="checkbox" />
            Execute tool
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input checked={writeMode} onChange={(event) => setWriteMode(event.target.checked)} type="checkbox" />
            Write mode
          </label>
          {executeTool && writeMode ? (
            <input
              className="mp-input"
              placeholder='Type "CONFIRM" to allow write action'
              value={confirmWrite}
              onChange={(event) => setConfirmWrite(event.target.value)}
            />
          ) : null}
          {error ? <p className="mp-error">{error}</p> : null}
          <button className="mp-btn-primary" type="submit">
            Send to agent
          </button>
        </form>
      </section>

      {result ? (
        <section className="mp-card p-5">
          <h2 className="font-bold">Response</h2>
          <p className="mt-2 text-sm">{result.message}</p>
          <pre className="mt-3 overflow-auto rounded-lg border border-[var(--mp-line)] bg-[#fff7f0] p-3 text-xs">
            {JSON.stringify(result.context, null, 2)}
          </pre>
        </section>
      ) : null}
    </main>
  );
}
