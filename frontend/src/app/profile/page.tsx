"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Crown, ImageIcon, Rocket, ShieldCheck, Sparkles, UsersRound, Video, X } from "lucide-react";

import { listSessions, listTeams, logout, platformMe, resendEmail, revokeSession, updateMe, type SessionItem, type Team } from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

type ProfileTab = "account" | "subscription" | "invoices" | "requests" | "team";

const subscriptionPlans = [
  {
    id: "corporate",
    title: "Корпоративный",
    price: "49 990",
    oldPrice: "99 980",
    badge: "Максимум",
    icon: Crown,
    gradient: "from-[#ff8a1f] via-[#f97316] to-[#c2410c]",
    description: "Для команд, сетей магазинов и агентств с несколькими маркетплейсами.",
    examples: ["Командные роли и доступы", "Расширенная аналитика Ozon/WB/Yandex", "AI-рекомендации по карточкам", "Приоритетная поддержка"],
    limits: ["Доступны все модули", "До 10 кабинетов", "До 10 сотрудников", "Лимиты можно докупить", "Личный менеджер"],
    discount: "-20% при оплате за 12 мес.",
  },
  {
    id: "business",
    title: "Бизнес",
    price: "24 990",
    oldPrice: "49 980",
    badge: "Популярный",
    icon: Rocket,
    gradient: "from-[#fb923c] via-[#ea580c] to-[#9a3412]",
    description: "Для активных продавцов, которым нужны рост карточек и контроль продвижения.",
    examples: ["Мои карточки с AI-аудитом", "Внешняя реклама WB/Ozon", "Аудитор SKU 360", "Управление ценой"],
    limits: ["Доступны все модули", "До 5 кабинетов", "До 3 сотрудников", "Лимиты можно докупить", "Личный менеджер"],
    discount: "-15% при оплате за 6 мес.",
  },
  {
    id: "basic",
    title: "Базовый",
    price: "9 990",
    oldPrice: "19 980",
    badge: "Старт",
    icon: ShieldCheck,
    gradient: "from-[#fdba74] via-[#f97316] to-[#ea580c]",
    description: "Для старта: ключевые модули аналитики и улучшения карточек.",
    examples: ["Мои карточки", "SEO WB/Ozon", "Кабинет WB", "Плагин для браузера"],
    limits: ["Доступны все модули", "До 1 кабинета", "Без дополнительных сотрудников", "Лимиты нельзя докупить", "Личный менеджер недоступен"],
    discount: "-10% при оплате за 3 мес.",
  },
  {
    id: "ai-editor",
    title: "Фото и Видеоредактор AI",
    price: "1 990",
    oldPrice: "3 980",
    badge: "AI pack",
    icon: Sparkles,
    gradient: "from-[#ff6a00] via-[#f43f1a] to-[#be123c]",
    description: "Отдельный пакет лимитов для генерации медиа и быстрых визуальных тестов.",
    examples: ["100 фото за 1 990 ₽", "20 видео за 1 990 ₽", "Ozon-ready 900×1200 JPG", "Draft-режим перед сохранением"],
    limits: ["100 AI-фото", "20 AI-видео", "Публичные ссылки для Ozon", "Можно докупить отдельно", "Без смены тарифа"],
    discount: "Пакет без подписки",
  },
] as const;

export default function ProfilePage() {
  const { token, user, isReady, clearAuth, refreshUser } = useAuth();
  const nameRef = useRef<HTMLInputElement>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = (["account", "subscription", "invoices", "requests", "team"].includes(searchParams.get("tab") || "")
    ? searchParams.get("tab")
    : "account") as ProfileTab;

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token) return;
    platformMe(token)
      .then(() => {
        router.replace("/platform");
      })
      .catch(() => null);
    listSessions(token).then(setSessions).catch(() => setSessions([]));
    listTeams(token)
      .then((rows) => {
        setTeams(rows);
        if (rows.length) setSelectedTeam(rows[0].id);
      })
      .catch(() => setTeams([]));
  }, [token, router]);

  const selectedTeamPath = useMemo(() => (selectedTeam ? `/teams/${selectedTeam}/members` : "/teams"), [selectedTeam]);
  const profileTabs = [
    { id: "account", label: "Аккаунт", href: "/profile" },
    { id: "subscription", label: "Моя подписка", href: "/profile?tab=subscription" },
    { id: "invoices", label: "Счета", href: "/profile?tab=invoices" },
    { id: "requests", label: "История запросов", href: "/profile?tab=requests" },
    { id: "team", label: "Моя команда", href: selectedTeamPath },
  ] as const;

  async function onSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const nextName = nameRef.current?.value?.trim();
    if (!nextName) {
      setError("Name is required");
      return;
    }
    try {
      setError(null);
      await updateMe(token, nextName);
      await refreshUser();
      setMessage("Профиль сохранен");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    }
  }

  async function onResendEmail() {
    if (!token) return;
    try {
      setError(null);
      const result = await resendEmail(token);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend email");
    }
  }

  async function onRevokeSession(sessionId: number) {
    if (!token) return;
    try {
      await revokeSession(token, sessionId);
      setSessions((prev) => prev.filter((item) => item.id !== sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke session");
    }
  }

  async function onLogout() {
    if (!token) return;
    await logout(token).catch(() => null);
    clearAuth();
    router.push("/login");
  }

  if (!isReady || !token || !user) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <section className="mp-card p-6 text-sm">Loading profile...</section>
      </main>
    );
  }

  return (
    <main className="mp-shell mp-shell-wide space-y-5">
      <header className="mp-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold">Личный кабинет</h1>
            <span className="rounded-full bg-orange-100 px-2 py-1 text-xs font-semibold text-orange-700">Обновлен</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="mp-input w-auto min-w-[180px]"
              value={selectedTeam ?? ""}
              onChange={(e) => setSelectedTeam(Number(e.target.value))}
            >
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
            <Link className="mp-btn-secondary" href={selectedTeamPath}>
              Моя команда
            </Link>
            <button className="mp-btn-primary" onClick={onLogout} type="button">
              Выйти
            </button>
          </div>
        </div>
        <nav className="mt-4 flex flex-wrap gap-6 border-t border-[var(--mp-line)] pt-3 text-sm font-semibold">
          {profileTabs.map((tab) => (
            <Link
              className={`border-b-2 pb-2 transition ${
                activeTab === tab.id ? "border-[var(--mp-orange)] text-slate-950" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
              href={tab.href}
              key={tab.id}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </header>

      {activeTab === "subscription" ? (
        <section className="space-y-8">
          <div className="text-center">
            <span className="inline-flex rounded-full bg-pink-600 px-2.5 py-1 text-xs font-black text-white">Обновили</span>
            <h2 className="mt-3 text-4xl font-black text-slate-950">Тарифы</h2>
            <p className="mt-3 text-sm text-slate-600">До 50% скидки на тарифы и AI-модули. Скидки по срокам суммируются.</p>
            <Link className="mt-2 inline-flex text-sm font-semibold text-[var(--mp-orange)] hover:underline" href="#subscription-plans">
              Получить скидку
            </Link>
          </div>
          <div className="flex justify-center">
            <div className="inline-flex rounded-full border border-slate-300 bg-white p-1 text-sm font-bold shadow-sm">
              {["1 мес.", "3 мес. -10%", "6 мес. -15%", "12 мес. -20%"].map((period, idx) => (
                <button
                  className={`rounded-full px-5 py-2 ${idx === 0 ? "bg-slate-950 text-white" : "text-slate-700 hover:bg-orange-50"}`}
                  key={period}
                  type="button"
                >
                  {period}
                </button>
              ))}
            </div>
          </div>

          <section className="space-y-5" id="subscription-plans">
            <div className="grid gap-4 xl:grid-cols-4">
              {subscriptionPlans.map((plan) => {
                const Icon = plan.icon;
                const highlighted = plan.id === "business";
                return (
                  <article className={`flex min-h-[610px] flex-col rounded-2xl border bg-white p-5 transition hover:-translate-y-1 hover:shadow-[0_22px_45px_rgba(234,88,12,0.14)] ${highlighted ? "border-orange-400 shadow-[0_0_0_1px_rgba(249,115,22,0.18)]" : "border-slate-200"}`} key={plan.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-2xl font-black text-slate-950">{plan.title}</h3>
                        <p className="mt-2 min-h-10 text-sm text-slate-600">{plan.description}</p>
                      </div>
                      <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${plan.gradient} text-white shadow-lg`}>
                        <Icon className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="mt-7">
                      <p className="text-sm font-bold text-slate-800">Итого за 1 месяц</p>
                      <p className="mt-2 text-3xl font-black text-slate-950">{plan.price} ₽</p>
                      <p className="mt-1 text-sm text-slate-500">без дополнительной скидки</p>
                      <div className="mt-3 flex items-center gap-2">
                        <span className="text-2xl font-black text-[var(--mp-orange)]">{plan.price} ₽</span>
                        <span className="text-sm text-slate-400 line-through">{plan.oldPrice} ₽</span>
                        <span className="rounded bg-violet-600 px-1.5 py-0.5 text-xs font-black text-white">50%</span>
                      </div>
                      <Link className="mt-1 inline-flex text-sm font-semibold text-[var(--mp-orange)] hover:underline" href="#subscription-plans">
                        Получить скидку
                      </Link>
                    </div>
                    <button className="mt-7 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-black text-white transition hover:bg-emerald-700" type="button">
                      Оплатить
                    </button>
                    <p className="mt-7 min-h-10 text-sm text-slate-600">{plan.examples[0]}</p>
                    <div className="mt-5 space-y-4">
                      {plan.limits.map((item, idx) => (
                        <div className="flex gap-3 text-sm text-slate-800" key={item}>
                          {plan.id === "basic" && idx >= 2 ? (
                            <X className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                          ) : (
                            <Check className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                          )}
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                    {plan.id === "ai-editor" ? (
                      <div className="mt-auto grid gap-2 rounded-2xl bg-orange-50 p-3 text-sm">
                        <div className="flex items-center gap-2 font-bold text-orange-800">
                          <ImageIcon className="h-4 w-4" />
                          Фото редактор AI: 100 фото
                        </div>
                        <div className="flex items-center gap-2 font-bold text-orange-800">
                          <Video className="h-4 w-4" />
                          Видео редактор AI: 20 видео
                        </div>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
            <button className="mx-auto flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-[var(--mp-orange)]" type="button">
              <span>Показать лимиты</span>
              <span>⌄</span>
            </button>
          </section>

          <section className="mx-auto max-w-md rounded-full border border-orange-100 bg-white p-3 shadow-sm">
            <div className="flex items-center justify-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-orange-100 text-orange-700">
                <UsersRound className="h-5 w-5" />
              </div>
              <p className="text-sm font-bold">Нужна помощь менеджера?</p>
            </div>
          </section>

          <section className="rounded-2xl border border-orange-100 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold">Лимиты в модулях</h2>
                <p className="mt-1 text-sm text-[var(--mp-muted)]">Лимиты показывают, что доступно в выбранном тарифе и AI-пакетах.</p>
              </div>
              <button className="mp-btn-secondary" type="button">
                Докупить лимиты
              </button>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="font-bold">Лимиты Фоторедактор AI</p>
                <p className="mt-1 text-sm text-slate-600">100 генераций фото за 1 990 ₽</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="font-bold">Лимиты Видеоредактор AI</p>
                <p className="mt-1 text-sm text-slate-600">20 генераций видео за 1 990 ₽</p>
              </div>
            </div>
          </section>
        </section>
      ) : null}

      {activeTab === "account" ? (
      <>
      <section className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <article className="mp-card p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xl font-bold">Личные данные</h2>
            <button className="mp-btn-secondary" form="profile-form" type="submit">
              Изменить
            </button>
          </div>
          <form className="mt-4 grid gap-4 md:grid-cols-2" id="profile-form" onSubmit={onSaveProfile}>
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Имя</p>
              <input className="mp-input" defaultValue={user.name || ""} ref={nameRef} />
            </div>
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Телефон</p>
              <p className="text-lg font-semibold">{user.phone}</p>
              <p className="text-xs text-[var(--mp-muted)]">{user.phone_verified_at ? "Телефон подтвержден" : "Телефон не подтвержден"}</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Почта</p>
              <p className="text-lg font-semibold">{user.email}</p>
              <p className="text-xs text-[var(--mp-muted)]">{user.email_verified_at ? "Email подтвержден" : "Email не подтвержден"}</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Мессенджеры</p>
              <p className="text-sm">Telegram: not linked</p>
              <p className="text-sm">MAX: not linked</p>
            </div>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              {!user.email_verified_at ? (
                <button className="mp-btn-secondary" onClick={onResendEmail} type="button">
                  Resend email
                </button>
              ) : null}
              {!user.phone_verified_at ? (
                <Link className="mp-btn-secondary" href="/verify-phone">
                  Verify phone
                </Link>
              ) : null}
            </div>
          </form>
          {message ? <p className="mt-3 text-sm text-green-700">{message}</p> : null}
          {error ? <p className="mt-3 mp-error">{error}</p> : null}
        </article>

        <aside className="mp-card p-5">
          <h3 className="text-lg font-bold">Поддержка</h3>
          <p className="mt-4 text-sm text-[var(--mp-muted)]">Телефон</p>
          <p className="font-semibold">+7 (495) 320-77-77</p>
          <p className="mt-3 text-sm text-[var(--mp-muted)]">Почта</p>
          <p className="font-semibold">help@wozym.io</p>
          <p className="mt-3 text-sm text-[var(--mp-muted)]">График</p>
          <p className="font-semibold">пн-пт, 9:00-18:00</p>
          <div className="mt-4 grid gap-2">
            <button className="mp-btn-primary" type="button">
              Онлайн-чат
            </button>
            <button className="mp-btn-secondary" type="button">
              Заказать звонок
            </button>
          </div>
        </aside>
      </section>

      <section className="mp-card p-5">
        <h3 className="text-xl font-bold">Активные сессии</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--mp-line)]">
                <th className="py-2">ID</th>
                <th className="py-2">IP</th>
                <th className="py-2">UA</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr className="border-b border-[var(--mp-line)]" key={session.id}>
                  <td className="py-2">{session.id}</td>
                  <td className="py-2">{session.ip_address || "-"}</td>
                  <td className="py-2">{session.user_agent || "-"}</td>
                  <td className="py-2">
                    <button className="mp-btn-secondary" onClick={() => onRevokeSession(session.id)} type="button">
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
              {!sessions.length ? (
                <tr>
                  <td className="py-2 text-[var(--mp-muted)]" colSpan={4}>
                    No active sessions
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
      </>
      ) : null}

      {activeTab !== "account" && activeTab !== "subscription" ? (
        <section className="mp-card p-6">
          <h2 className="text-xl font-bold">Раздел в разработке</h2>
          <p className="mt-2 text-sm text-[var(--mp-muted)]">Скоро здесь появятся данные по выбранной вкладке.</p>
        </section>
      ) : null}
    </main>
  );
}

