"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import {
  getTeam,
  getTeamAudit,
  getTeamMembers,
  inviteTeamMember,
  patchTeamMember,
  removeTeamMember,
  type Team,
  type TeamAudit,
  type TeamMember,
} from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

const roles = ["ADMIN", "MANAGER", "ANALYST", "VIEWER", "AGENT"];
const statuses = ["ACTIVE", "SUSPENDED", "REMOVED"];

export default function TeamMembersPage() {
  const { token, isReady } = useAuth();
  const params = useParams<{ teamId: string }>();
  const router = useRouter();
  const teamId = useMemo(() => Number(params.teamId), [params.teamId]);

  const [team, setTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [audit, setAudit] = useState<TeamAudit[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("VIEWER");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token || Number.isNaN(teamId)) return;
    Promise.all([getTeam(token, teamId), getTeamMembers(token, teamId), getTeamAudit(token, teamId)])
      .then(([teamRow, memberRows, auditRows]) => {
        setTeam(teamRow);
        setMembers(memberRows);
        setAudit(auditRows.slice(0, 10));
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load team data");
      });
  }, [token, teamId]);

  async function onInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    try {
      setError(null);
      const invited = await inviteTeamMember(token, teamId, { email: inviteEmail, role: inviteRole });
      setMessage(`Invite created #${invited.id}`);
      setInviteEmail("");
      const refreshed = await getTeamMembers(token, teamId);
      setMembers(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to invite member");
    }
  }

  async function onChangeMember(memberId: number, role: string, status: string) {
    if (!token) return;
    try {
      setError(null);
      const updated = await patchTeamMember(token, teamId, memberId, { role, status });
      setMembers((prev) => prev.map((row) => (row.id === memberId ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update member");
    }
  }

  async function onRemove(memberId: number) {
    if (!token) return;
    try {
      setError(null);
      await removeTeamMember(token, teamId, memberId);
      setMembers((prev) => prev.filter((row) => row.id !== memberId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  }

  if (!isReady || !token || Number.isNaN(teamId)) {
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
          <h1 className="text-2xl font-bold">{team?.name || "Team"}</h1>
          <p className="text-sm text-[var(--mp-muted)]">Members, roles and recent IAM activity.</p>
        </div>
        <Link className="mp-btn-secondary" href="/teams">
          Back
        </Link>
      </header>

      <section className="mp-card p-5">
        <h2 className="font-bold">Invite member</h2>
        <form className="mt-3 grid gap-3 md:grid-cols-[1fr_180px_auto]" onSubmit={onInvite}>
          <input className="mp-input" placeholder="Email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
          <select className="mp-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
            {roles.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          <button className="mp-btn-primary" type="submit">
            Invite
          </button>
        </form>
        {message ? <p className="mt-2 text-sm text-green-700">{message}</p> : null}
        {error ? <p className="mt-2 mp-error">{error}</p> : null}
      </section>

      <section className="mp-card p-5">
        <h2 className="font-bold">Members</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--mp-line)]">
                <th className="py-2">User ID</th>
                <th className="py-2">Role</th>
                <th className="py-2">Status</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr className="border-b border-[var(--mp-line)]" key={member.id}>
                  <td className="py-2">{member.user_id}</td>
                  <td className="py-2">
                    <select
                      className="mp-input"
                      value={member.role}
                      onChange={(e) => onChangeMember(member.id, e.target.value, member.status)}
                    >
                      {["OWNER", ...roles].map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2">
                    <select
                      className="mp-input"
                      value={member.status}
                      onChange={(e) => onChangeMember(member.id, member.role, e.target.value)}
                    >
                      {statuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2">
                    <button className="mp-btn-secondary" onClick={() => onRemove(member.id)} type="button">
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {!members.length ? (
                <tr>
                  <td className="py-2 text-[var(--mp-muted)]" colSpan={4}>
                    No members
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mp-card p-5">
        <h2 className="font-bold">Recent audit</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {audit.map((event) => (
            <li className="border-b border-[var(--mp-line)] pb-2" key={event.id}>
              <span className="font-semibold">{event.action}</span> <span className="text-[var(--mp-muted)]">user:{event.user_id ?? "-"}</span>
            </li>
          ))}
          {!audit.length ? <li className="text-[var(--mp-muted)]">No events</li> : null}
        </ul>
      </section>
    </main>
  );
}
