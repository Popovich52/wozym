"use client";

import { type FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plug, Plus, UsersRound } from "lucide-react";

import { createTeam, ensurePersonalTeam, listTeams, type Team } from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

export default function TeamsPage() {
  const { token, isReady } = useAuth();
  const [teams, setTeams] = useState<Team[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token) return;
    listTeams(token)
      .then(async (rows) => {
        if (!rows.length) {
          const personalTeam = await ensurePersonalTeam(token);
          window.localStorage.setItem("dashboard:selectedTeamId", String(personalTeam.id));
          router.replace(`/teams/${personalTeam.id}/connections`);
          return;
        }
        setTeams(rows);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Не удалось загрузить команды");
      });
  }, [token, router]);

  async function onCreateTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    try {
      setIsCreating(true);
      setError(null);
      const team = await createTeam(token, { name: name.trim(), slug: slug.trim() || undefined });
      window.localStorage.setItem("dashboard:selectedTeamId", String(team.id));
      router.push(`/teams/${team.id}/connections`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать команду");
    } finally {
      setIsCreating(false);
    }
  }

  if (!isReady || !token) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <div className="mp-card p-6 text-sm">Загрузка...</div>
      </main>
    );
  }

  return (
    <main className="mp-shell space-y-5">
      <header className="mp-card p-5">
        <Link className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--mp-muted)]" href="/dashboard">
          <ArrowLeft className="h-4 w-4" />
          Вернуться в дашборд
        </Link>
        <h1 className="mt-2 text-2xl font-bold">Команды</h1>
        <p className="mt-1 text-sm text-[var(--mp-muted)]">
          Если команд нет, система автоматически создаст личное пространство пользователя и откроет подключения.
        </p>
      </header>

      <section className="mp-card p-5">
        <div className="flex items-center gap-2">
          <Plus className="h-5 w-5 text-[var(--mp-orange)]" />
          <h2 className="font-bold">Создать команду</h2>
        </div>
        <form className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_auto]" onSubmit={onCreateTeam}>
          <input
            className="mp-input"
            minLength={2}
            onChange={(event) => setName(event.target.value)}
            placeholder="Название, например ООО Ромашка"
            required
            value={name}
          />
          <input className="mp-input" onChange={(event) => setSlug(event.target.value)} placeholder="slug, опционально" value={slug} />
          <button className="mp-btn-primary inline-flex items-center justify-center gap-2" disabled={isCreating} type="submit">
            <Plus className="h-4 w-4" />
            Создать
          </button>
        </form>
        {error ? <p className="mt-3 mp-error">{error}</p> : null}
      </section>

      <section className="mp-card p-5">
        <h2 className="font-bold">Доступные команды</h2>
        {!teams.length ? (
          <p className="mt-3 rounded-lg border border-dashed border-[var(--mp-line)] p-4 text-sm text-[var(--mp-muted)]">
            Команд пока нет. Создайте команду выше, затем добавьте подключения OZON, Wildberries или Яндекс Маркет.
          </p>
        ) : null}
        <div className="mt-3 space-y-3">
          {teams.map((team) => (
            <article className="rounded-lg border border-[var(--mp-line)] p-4" key={team.id}>
              <h3 className="font-bold">{team.name}</h3>
              <p className="mt-1 text-sm text-[var(--mp-muted)]">slug: {team.slug}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link className="mp-btn-primary inline-flex items-center justify-center gap-2" href={`/teams/${team.id}/connections`}>
                  <Plug className="h-4 w-4" />
                  Подключения
                </Link>
                <Link className="mp-btn-secondary inline-flex items-center justify-center gap-2" href={`/teams/${team.id}/members`}>
                  <UsersRound className="h-4 w-4" />
                  Участники
                </Link>
                <Link className="mp-btn-secondary" href="/profile">
                  Профиль
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
