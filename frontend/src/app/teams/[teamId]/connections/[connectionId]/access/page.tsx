"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import {
  createAccessScope,
  createConnectionAccess,
  deleteAccessScope,
  deleteConnectionAccess,
  getTeamMembers,
  listAccessScopes,
  listConnectionAccess,
  patchAccessScope,
  patchConnectionAccess,
  type AccessScope,
  type ConnectionAccess,
  type TeamMember,
} from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

const accessModes = ["FULL", "SCOPED", "READ_ONLY", "NONE", "DISABLED"];
const scopeTypes = ["BRAND", "CATEGORY", "SKU", "WAREHOUSE"];

export default function ConnectionAccessPage() {
  const { token, isReady } = useAuth();
  const params = useParams<{ teamId: string; connectionId: string }>();
  const router = useRouter();
  const teamId = useMemo(() => Number(params.teamId), [params.teamId]);
  const connectionId = useMemo(() => Number(params.connectionId), [params.connectionId]);

  const [members, setMembers] = useState<TeamMember[]>([]);
  const [accessRows, setAccessRows] = useState<ConnectionAccess[]>([]);
  const [scopes, setScopes] = useState<AccessScope[]>([]);
  const [selectedAccessId, setSelectedAccessId] = useState<number | null>(null);
  const [memberId, setMemberId] = useState<number | null>(null);
  const [accessMode, setAccessMode] = useState("SCOPED");
  const [scopeType, setScopeType] = useState("BRAND");
  const [scopeValue, setScopeValue] = useState("");
  const [scopeExcluded, setScopeExcluded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  const loadAccess = useCallback(async (activeToken: string) => {
    const rows = await listConnectionAccess(activeToken, teamId, connectionId);
    setAccessRows(rows);
    if (!rows.length) {
      setSelectedAccessId(null);
      setScopes([]);
      return;
    }
    const nextSelected = rows.some((row) => row.id === selectedAccessId) ? selectedAccessId : rows[0].id;
    if (!nextSelected) return;
    setSelectedAccessId(nextSelected);
    const scopeRows = await listAccessScopes(activeToken, teamId, connectionId, nextSelected);
    setScopes(scopeRows);
  }, [connectionId, selectedAccessId, teamId]);

  useEffect(() => {
    if (!token || Number.isNaN(teamId) || Number.isNaN(connectionId)) return;
    Promise.resolve()
      .then(() => Promise.all([getTeamMembers(token, teamId), loadAccess(token)]))
      .then(([memberRows]) => {
        setMembers(memberRows.filter((row) => row.status === "ACTIVE"));
        setMemberId(memberRows.length ? memberRows[0].id : null);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load connection access");
      });
  }, [connectionId, loadAccess, teamId, token]);

  async function onGrant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || memberId === null) return;
    try {
      setError(null);
      await createConnectionAccess(token, teamId, connectionId, { team_member_id: memberId, access_mode: accessMode });
      await loadAccess(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to grant access");
    }
  }

  async function onPatchAccess(accessId: number, nextMode: string, isActive: boolean) {
    if (!token) return;
    try {
      setError(null);
      const updated = await patchConnectionAccess(token, teamId, connectionId, accessId, { access_mode: nextMode, is_active: isActive });
      setAccessRows((prev) => prev.map((row) => (row.id === accessId ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update access");
    }
  }

  async function onDeleteAccess(accessId: number) {
    if (!token) return;
    try {
      setError(null);
      await deleteConnectionAccess(token, teamId, connectionId, accessId);
      await loadAccess(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete access");
    }
  }

  async function onSelectAccess(accessId: number) {
    if (!token) return;
    try {
      setSelectedAccessId(accessId);
      const rows = await listAccessScopes(token, teamId, connectionId, accessId);
      setScopes(rows);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scopes");
    }
  }

  async function onAddScope(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || selectedAccessId === null) return;
    try {
      setError(null);
      await createAccessScope(token, teamId, connectionId, selectedAccessId, {
        subject_type: scopeType,
        subject_value: scopeValue,
        is_excluded: scopeExcluded,
      });
      setScopeValue("");
      const rows = await listAccessScopes(token, teamId, connectionId, selectedAccessId);
      setScopes(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add scope");
    }
  }

  async function onToggleScope(scope: AccessScope) {
    if (!token || selectedAccessId === null) return;
    try {
      setError(null);
      const updated = await patchAccessScope(token, teamId, connectionId, selectedAccessId, scope.id, {
        is_excluded: !scope.is_excluded,
      });
      setScopes((prev) => prev.map((row) => (row.id === scope.id ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update scope");
    }
  }

  async function onDeleteScope(scopeId: number) {
    if (!token || selectedAccessId === null) return;
    try {
      setError(null);
      await deleteAccessScope(token, teamId, connectionId, selectedAccessId, scopeId);
      setScopes((prev) => prev.filter((row) => row.id !== scopeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete scope");
    }
  }

  if (!isReady || !token || Number.isNaN(teamId) || Number.isNaN(connectionId)) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <div className="mp-card p-6 text-sm">Loading...</div>
      </main>
    );
  }

  return (
    <main className="mp-shell space-y-5">
      <header className="mp-card p-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Connection access</h1>
          <p className="text-sm text-[var(--mp-muted)]">Team-level sharing and scope restrictions.</p>
        </div>
        <Link className="mp-btn-secondary" href={`/teams/${teamId}/connections`}>
          Back
        </Link>
      </header>

      <section className="mp-card p-5">
        <h2 className="font-bold">Grant access</h2>
        <form className="mt-3 grid gap-3 md:grid-cols-[1fr_200px_auto]" onSubmit={onGrant}>
          <select className="mp-input" value={memberId ?? ""} onChange={(event) => setMemberId(Number(event.target.value))}>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                member #{member.id} (user {member.user_id}, {member.role})
              </option>
            ))}
          </select>
          <select className="mp-input" value={accessMode} onChange={(event) => setAccessMode(event.target.value)}>
            {accessModes.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
          <button className="mp-btn-primary" type="submit">
            Grant
          </button>
        </form>
        {error ? <p className="mt-2 mp-error">{error}</p> : null}
      </section>

      <section className="mp-card p-5">
        <h2 className="font-bold">Access list</h2>
        <div className="mt-3 space-y-2">
          {accessRows.map((row) => (
            <article className="border border-[var(--mp-line)] rounded-lg p-3 space-y-2" key={row.id}>
              <div className="flex flex-wrap items-center gap-2">
                <button className="mp-btn-secondary" onClick={() => onSelectAccess(row.id)} type="button">
                  Scopes
                </button>
                <span className="text-sm">member #{row.team_member_id}</span>
                <select
                  className="mp-input"
                  value={row.access_mode}
                  onChange={(event) => onPatchAccess(row.id, event.target.value, row.is_active)}
                >
                  {accessModes.map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
                <label className="text-sm flex items-center gap-2">
                  <input
                    checked={row.is_active}
                    onChange={(event) => onPatchAccess(row.id, row.access_mode, event.target.checked)}
                    type="checkbox"
                  />
                  active
                </label>
                <button className="mp-btn-secondary" onClick={() => onDeleteAccess(row.id)} type="button">
                  Revoke
                </button>
              </div>
            </article>
          ))}
          {!accessRows.length ? <p className="text-sm text-[var(--mp-muted)]">No access grants.</p> : null}
        </div>
      </section>

      <section className="mp-card p-5">
        <h2 className="font-bold">Scopes for access #{selectedAccessId ?? "-"}</h2>
        <form className="mt-3 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]" onSubmit={onAddScope}>
          <select className="mp-input" value={scopeType} onChange={(event) => setScopeType(event.target.value)}>
            {scopeTypes.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="mp-input" value={scopeValue} onChange={(event) => setScopeValue(event.target.value)} placeholder="Scope value" />
          <label className="text-sm flex items-center gap-2">
            <input checked={scopeExcluded} onChange={(event) => setScopeExcluded(event.target.checked)} type="checkbox" />
            excluded
          </label>
          <button className="mp-btn-primary" disabled={selectedAccessId === null} type="submit">
            Add
          </button>
        </form>
        <div className="mt-3 space-y-2">
          {scopes.map((scope) => (
            <article className="border border-[var(--mp-line)] rounded-lg p-3 flex flex-wrap items-center gap-2" key={scope.id}>
              <span className="text-sm font-semibold">{scope.subject_type}</span>
              <span className="text-sm">{scope.subject_value}</span>
              <button className="mp-btn-secondary" onClick={() => onToggleScope(scope)} type="button">
                {scope.is_excluded ? "Set include" : "Set exclude"}
              </button>
              <button className="mp-btn-secondary" onClick={() => onDeleteScope(scope.id)} type="button">
                Delete
              </button>
            </article>
          ))}
          {!scopes.length ? <p className="text-sm text-[var(--mp-muted)]">No scopes.</p> : null}
        </div>
      </section>
    </main>
  );
}
