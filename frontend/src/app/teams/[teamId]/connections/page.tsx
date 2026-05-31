"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlertCircle,
  ChevronDown,
  CheckCircle2,
  ExternalLink,
  HelpCircle,
  KeyRound,
  LoaderCircle,
  ShieldCheck,
  X,
} from "lucide-react";

import {
  createConnectionCredential,
  createTeamConnection,
  getTeam,
  listConnectionCredentials,
  listTeamConnections,
  patchConnectionCredential,
  patchTeamConnection,
  validateOzonPerformanceKey,
  validateOzonSellerKey,
  type MarketplaceConnection,
  type MarketplaceCredential,
  type MarketplaceKeyValidation,
  type Team,
} from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

const providerLabels: Record<string, string> = {
  WB: "Wildberries",
  OZON: "Ozon",
  YANDEX_MARKET: "Яндекс Маркет",
};

type OzonDraft = {
  name: string;
  sellerClientId: string;
  sellerApiKey: string;
  performanceClientId: string;
  performanceClientSecret: string;
};

const emptyOzonDraft: OzonDraft = {
  name: "",
  sellerClientId: "",
  sellerApiKey: "",
  performanceClientId: "",
  performanceClientSecret: "",
};

type ValidationState = "idle" | "checking" | "valid" | "invalid";

function formatDate(value: string | null) {
  if (!value) return "нет срока";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function secretSummary(credential: MarketplaceCredential) {
  const fields = [
    credential.client_id_plain ? "client id" : null,
    credential.api_key_plain ? "api key" : null,
    credential.client_secret_plain ? "secret" : null,
    credential.access_token_plain ? "access token" : null,
    credential.refresh_token_plain ? "refresh token" : null,
  ].filter(Boolean);
  return fields.length ? fields.join(", ") : "секреты не заполнены";
}

function CompactSwitch({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <button
      aria-pressed={checked}
      className={`h-5 w-9 rounded-full p-0.5 transition ${checked ? "bg-[var(--mp-orange)]" : "bg-slate-300"}`}
      onClick={() => onChange(!checked)}
      type="button"
    >
      <span className={`block h-4 w-4 rounded-full bg-white shadow transition ${checked ? "translate-x-4" : ""}`} />
    </button>
  );
}

function InstructionPreview({ title, text }: { title: string; text: string }) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="font-bold">{title}</h3>
        <p className="mt-1 text-sm text-slate-600">{text}</p>
      </div>
      <div className="relative h-[136px] overflow-hidden rounded-lg bg-gradient-to-br from-slate-200 to-slate-300">
        <div className="absolute left-5 top-5 h-3 w-28 rounded bg-white/70" />
        <div className="absolute left-5 top-10 h-3 w-48 rounded bg-white/50" />
        <div className="absolute bottom-5 left-5 right-5 h-16 rounded border border-white/60 bg-white/45 p-3">
          <div className="h-3 w-24 rounded bg-slate-500/40" />
          <div className="mt-3 h-3 w-56 rounded bg-slate-500/30" />
        </div>
        <div className="absolute right-7 top-12 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white">Скопировать</div>
      </div>
      <p className="text-center text-sm text-slate-600">
        Если информации не хватило, откройте{" "}
        <a className="inline-flex items-center gap-1 font-semibold text-blue-700" href="https://docs.ozon.ru/api/seller/" rel="noreferrer" target="_blank">
          подробную инструкцию
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </p>
    </div>
  );
}

export default function TeamConnectionsPage() {
  const { token, isReady } = useAuth();
  const params = useParams<{ teamId: string }>();
  const router = useRouter();
  const teamId = useMemo(() => Number(params.teamId), [params.teamId]);

  const [team, setTeam] = useState<Team | null>(null);
  const [connections, setConnections] = useState<MarketplaceConnection[]>([]);
  const [credentialsByConnection, setCredentialsByConnection] = useState<Record<number, MarketplaceCredential[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showOnlyActiveKeys, setShowOnlyActiveKeys] = useState(true);
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const [isOzonModalOpen, setIsOzonModalOpen] = useState(false);
  const [ozonStep, setOzonStep] = useState<1 | 2>(1);
  const [ozonDraft, setOzonDraft] = useState<OzonDraft>(emptyOzonDraft);
  const [showSellerInstruction, setShowSellerInstruction] = useState(false);
  const [showPerformanceInstruction, setShowPerformanceInstruction] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sellerValidation, setSellerValidation] = useState<MarketplaceKeyValidation | null>(null);
  const [sellerValidationState, setSellerValidationState] = useState<ValidationState>("idle");
  const [validatedSellerFingerprint, setValidatedSellerFingerprint] = useState("");
  const [lastSellerCheckFingerprint, setLastSellerCheckFingerprint] = useState("");
  const [performanceValidation, setPerformanceValidation] = useState<MarketplaceKeyValidation | null>(null);
  const [performanceValidationState, setPerformanceValidationState] = useState<ValidationState>("idle");
  const [validatedPerformanceFingerprint, setValidatedPerformanceFingerprint] = useState("");
  const [lastPerformanceCheckFingerprint, setLastPerformanceCheckFingerprint] = useState("");

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  const loadData = useCallback(
    async (activeToken: string) => {
      setIsLoading(true);
      const [teamRow, connectionRows] = await Promise.all([getTeam(activeToken, teamId), listTeamConnections(activeToken, teamId)]);
      const credentialPairs = await Promise.all(
        connectionRows.map(async (connection) => [connection.id, await listConnectionCredentials(activeToken, teamId, connection.id)] as const),
      );
      setTeam(teamRow);
      setConnections(connectionRows);
      setCredentialsByConnection(Object.fromEntries(credentialPairs));
      setIsLoading(false);
    },
    [teamId],
  );

  useEffect(() => {
    if (!token || Number.isNaN(teamId)) return;
    Promise.resolve()
      .then(() => loadData(token))
      .catch((err) => {
        setIsLoading(false);
        setError(err instanceof Error ? err.message : "Не удалось загрузить подключения");
      });
  }, [loadData, token, teamId]);

  const sellerFingerprint = `${ozonDraft.sellerClientId.trim()}::${ozonDraft.sellerApiKey.trim()}`;
  const performanceFingerprint = `${ozonDraft.performanceClientId.trim()}::${ozonDraft.performanceClientSecret.trim()}`;
  const visibleConnections = useMemo(() => {
    if (!showOnlyActiveKeys) return connections;
    return connections.filter((connection) => !connection.is_disabled && connection.status === "ACTIVE");
  }, [connections, showOnlyActiveKeys]);

  const validateSellerKey = useCallback(async () => {
    if (!token || !ozonDraft.sellerClientId.trim() || !ozonDraft.sellerApiKey.trim()) {
      setSellerValidation(null);
      setSellerValidationState("idle");
      setValidatedSellerFingerprint("");
      return null;
    }

    setSellerValidationState("checking");
    const result = await validateOzonSellerKey(token, teamId, {
      client_id: ozonDraft.sellerClientId.trim(),
      api_key: ozonDraft.sellerApiKey.trim(),
    });
    setSellerValidation(result);
    setSellerValidationState(result.is_valid ? "valid" : "invalid");
    setValidatedSellerFingerprint(result.is_valid ? sellerFingerprint : "");
    setLastSellerCheckFingerprint(sellerFingerprint);
    return result;
  }, [ozonDraft.sellerApiKey, ozonDraft.sellerClientId, sellerFingerprint, teamId, token]);

  const validatePerformanceKey = useCallback(async () => {
    if (!token || !ozonDraft.performanceClientId.trim() || !ozonDraft.performanceClientSecret.trim()) {
      setPerformanceValidation(null);
      setPerformanceValidationState("idle");
      setValidatedPerformanceFingerprint("");
      setLastPerformanceCheckFingerprint("");
      return null;
    }

    setPerformanceValidationState("checking");
    const result = await validateOzonPerformanceKey(token, teamId, {
      client_id: ozonDraft.performanceClientId.trim(),
      client_secret: ozonDraft.performanceClientSecret.trim(),
    });
    setPerformanceValidation(result);
    setPerformanceValidationState(result.is_valid ? "valid" : "invalid");
    setValidatedPerformanceFingerprint(result.is_valid ? performanceFingerprint : "");
    setLastPerformanceCheckFingerprint(performanceFingerprint);
    return result;
  }, [ozonDraft.performanceClientId, ozonDraft.performanceClientSecret, performanceFingerprint, teamId, token]);

  useEffect(() => {
    if (!isOzonModalOpen || ozonStep !== 1) return;
    if (!ozonDraft.sellerClientId.trim() || !ozonDraft.sellerApiKey.trim()) {
      return;
    }
    if (validatedSellerFingerprint === sellerFingerprint && sellerValidationState === "valid") return;
    if (lastSellerCheckFingerprint === sellerFingerprint && sellerValidationState !== "idle") return;
    if (sellerValidationState === "checking") return;

    const timeoutId = window.setTimeout(() => {
      validateSellerKey().catch((err) => {
        setSellerValidation(null);
        setSellerValidationState("invalid");
        setValidatedSellerFingerprint("");
        setLastSellerCheckFingerprint(sellerFingerprint);
        setModalError(err instanceof Error ? err.message : "Не удалось проверить Seller API ключ.");
      });
    }, 700);

    return () => window.clearTimeout(timeoutId);
  }, [isOzonModalOpen, lastSellerCheckFingerprint, ozonDraft.sellerApiKey, ozonDraft.sellerClientId, ozonStep, sellerFingerprint, sellerValidationState, validateSellerKey, validatedSellerFingerprint]);

  useEffect(() => {
    if (!isOzonModalOpen || ozonStep !== 2) return;
    if (!ozonDraft.performanceClientId.trim() || !ozonDraft.performanceClientSecret.trim()) return;
    if (validatedPerformanceFingerprint === performanceFingerprint && performanceValidationState === "valid") return;
    if (lastPerformanceCheckFingerprint === performanceFingerprint && performanceValidationState !== "idle") return;
    if (performanceValidationState === "checking") return;

    const timeoutId = window.setTimeout(() => {
      validatePerformanceKey().catch((err) => {
        setPerformanceValidation(null);
        setPerformanceValidationState("invalid");
        setValidatedPerformanceFingerprint("");
        setLastPerformanceCheckFingerprint(performanceFingerprint);
        setModalError(err instanceof Error ? err.message : "Не удалось проверить Performance API ключ.");
      });
    }, 700);

    return () => window.clearTimeout(timeoutId);
  }, [
    isOzonModalOpen,
    lastPerformanceCheckFingerprint,
    ozonDraft.performanceClientId,
    ozonDraft.performanceClientSecret,
    ozonStep,
    performanceFingerprint,
    performanceValidationState,
    validatePerformanceKey,
    validatedPerformanceFingerprint,
  ]);

  function openOzonModal() {
    setIsAddMenuOpen(false);
    setError(null);
    setModalError(null);
    setOzonStep(1);
    setOzonDraft(emptyOzonDraft);
    setShowSellerInstruction(false);
    setShowPerformanceInstruction(false);
    setSellerValidation(null);
    setSellerValidationState("idle");
    setValidatedSellerFingerprint("");
    setLastSellerCheckFingerprint("");
    setPerformanceValidation(null);
    setPerformanceValidationState("idle");
    setValidatedPerformanceFingerprint("");
    setLastPerformanceCheckFingerprint("");
    setIsOzonModalOpen(true);
  }

  function updateOzonDraft(patch: Partial<OzonDraft>) {
    setOzonDraft((prev) => ({ ...prev, ...patch }));
    if ("sellerClientId" in patch || "sellerApiKey" in patch) {
      setSellerValidation(null);
      setSellerValidationState("idle");
      setValidatedSellerFingerprint("");
      setLastSellerCheckFingerprint("");
      setModalError(null);
    }
    if ("performanceClientId" in patch || "performanceClientSecret" in patch) {
      setPerformanceValidation(null);
      setPerformanceValidationState("idle");
      setValidatedPerformanceFingerprint("");
      setLastPerformanceCheckFingerprint("");
      setModalError(null);
    }
  }

  function closeOzonModal() {
    if (isSubmitting) return;
    setIsOzonModalOpen(false);
    setModalError(null);
  }

  async function onToggleConnection(connection: MarketplaceConnection, isActive: boolean) {
    if (!token) return;
    try {
      setError(null);
      const updated = await patchTeamConnection(token, teamId, connection.id, {
        status: isActive ? "ACTIVE" : "DISABLED",
        is_disabled: !isActive,
      });
      setConnections((prev) => prev.map((row) => (row.id === connection.id ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить подключение");
    }
  }

  async function onToggleCredential(connectionId: number, credential: MarketplaceCredential, isActive: boolean) {
    if (!token) return;
    try {
      setError(null);
      const updated = await patchConnectionCredential(token, teamId, connectionId, credential.id, { is_active: isActive });
      setCredentialsByConnection((prev) => ({
        ...prev,
        [connectionId]: (prev[connectionId] || []).map((row) => (row.id === credential.id ? updated : row)),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить ключ");
    }
  }

  async function onSellerSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ozonDraft.name.trim() || !ozonDraft.sellerClientId.trim() || !ozonDraft.sellerApiKey.trim()) {
      setModalError("Заполните название, Client ID и ключ доступа Seller API.");
      return;
    }
    try {
      setModalError(null);
      const result =
        validatedSellerFingerprint === sellerFingerprint && sellerValidation?.is_valid ? sellerValidation : await validateSellerKey();
      if (!result?.is_valid) {
        setModalError(result?.message || "Seller API ключ не прошел проверку.");
        return;
      }
      setOzonStep(2);
    } catch (err) {
      setSellerValidationState("invalid");
      setModalError(err instanceof Error ? err.message : "Не удалось проверить Seller API ключ.");
    }
  }

  async function onOzonSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    if (!ozonDraft.performanceClientId.trim() || !ozonDraft.performanceClientSecret.trim()) {
      setModalError("Заполните Client ID и Client Secret Performance API.");
      return;
    }
    try {
      setIsSubmitting(true);
      setModalError(null);
      setError(null);
      const validationResult =
        validatedPerformanceFingerprint === performanceFingerprint && performanceValidation?.is_valid
          ? performanceValidation
          : await validatePerformanceKey();
      if (!validationResult?.is_valid) {
        setModalError(validationResult?.message || "Performance API ключ не прошел проверку.");
        return;
      }
      const connection = await createTeamConnection(token, teamId, { provider: "OZON", name: ozonDraft.name.trim() });
      await createConnectionCredential(token, teamId, connection.id, {
        credential_kind: "OZON_SELLER",
        auth_scheme: "API_KEY",
        name: "Seller API",
        client_id_plain: ozonDraft.sellerClientId.trim(),
        api_key_plain: ozonDraft.sellerApiKey.trim(),
        scopes_json: {},
        token_meta_json: {},
        is_primary: true,
        is_active: true,
      });
      await createConnectionCredential(token, teamId, connection.id, {
        credential_kind: "OZON_PERFORMANCE",
        auth_scheme: "CLIENT_CREDENTIALS",
        name: "Performance API",
        client_id_plain: ozonDraft.performanceClientId.trim(),
        client_secret_plain: ozonDraft.performanceClientSecret.trim(),
        scopes_json: {},
        token_meta_json: {},
        is_primary: false,
        is_active: true,
      });
      setIsOzonModalOpen(false);
      setOzonDraft(emptyOzonDraft);
      await loadData(token);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Не удалось добавить Ozon");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isReady || !token || Number.isNaN(teamId) || isLoading) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <div className="mp-card p-6 text-sm">Загрузка...</div>
      </main>
    );
  }

  return (
    <main className="mp-shell-wide space-y-5">
      <header className="mp-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <Link className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--mp-muted)]" href="/dashboard">
              <ArrowLeft className="h-4 w-4" />
              Вернуться в дашборд
            </Link>
            <h1 className="text-2xl font-bold">Подключения маркетплейсов</h1>
            <p className="text-sm text-[var(--mp-muted)]">
              {team?.name || "Личное пространство"}: подключите кабинет Ozon, Wildberries или Яндекс Маркет.
            </p>
          </div>
          <Link className="mp-btn-secondary inline-flex items-center justify-center gap-2" href={`/teams/${teamId}/members`}>
            <ShieldCheck className="h-4 w-4" />
            Участники команды
          </Link>
        </div>
      </header>

      <section className="mp-card p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-bold">Новое подключение</h2>
            <p className="mt-1 text-sm text-[var(--mp-muted)]">Выберите тип подключения. Для Ozon настройка проходит в 2 шага.</p>
          </div>
          <div className="relative">
            <button className="mp-btn-primary inline-flex items-center justify-center gap-2" onClick={() => setIsAddMenuOpen((value) => !value)} type="button">
              Добавить
              <ChevronDown className={`h-4 w-4 transition ${isAddMenuOpen ? "rotate-180" : ""}`} />
            </button>
            {isAddMenuOpen ? (
              <div className="absolute right-0 z-20 mt-2 w-64 overflow-hidden rounded-lg border border-[var(--mp-line)] bg-white py-2 shadow-xl">
                <div className="border-b border-[var(--mp-line)] px-4 py-2 text-sm font-bold">Интеграция с Wildberries</div>
                <button className="block w-full px-4 py-2 text-left text-sm hover:bg-slate-50" onClick={() => setError("Подключение Wildberries добавим следующим шагом.")} type="button">
                  Настроить интеграцию
                </button>
                <div className="border-y border-[var(--mp-line)] px-4 py-2 text-sm font-bold">Другие подключения</div>
                <button className="block w-full px-4 py-2 text-left text-sm hover:bg-slate-50" onClick={() => setError("Кабинет WB добавим следующим шагом.")} type="button">
                  Кабинет WB
                </button>
                <button className="block w-full px-4 py-2 text-left text-sm hover:bg-slate-50" onClick={openOzonModal} type="button">
                  Кабинет Ozon
                </button>
                {["Внешняя реклама", "WB: Мои карточки", "WB: Автоответы", "WB: Биддер", "WB: Управление ценой", "Ozon: Управление ценой", "WB: Рука на пульсе"].map((item) => (
                  <button className="block w-full px-4 py-2 text-left text-sm text-slate-600 hover:bg-slate-50" key={item} onClick={() => setError(`${item}: подключение будет добавлено позже.`)} type="button">
                    {item}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        {error ? <p className="mt-3 mp-error">{error}</p> : null}
      </section>

      <section className="mp-card p-4">
        <label className="flex cursor-pointer items-center justify-between gap-4">
          <div>
            <span className="font-bold">Фильтр ключей</span>
            <p className="mt-1 text-sm text-[var(--mp-muted)]">Показывать только активные ключи в карточках подключений.</p>
          </div>
          <span className="inline-flex items-center gap-3">
            <span className="text-sm font-semibold text-[var(--mp-muted)]">{showOnlyActiveKeys ? "Только активные" : "Все ключи"}</span>
            <input
              checked={showOnlyActiveKeys}
              className="sr-only peer"
              onChange={(event) => setShowOnlyActiveKeys(event.target.checked)}
              type="checkbox"
            />
            <span className="h-7 w-12 rounded-full bg-slate-300 p-1 transition peer-checked:bg-[var(--mp-orange)]">
              <span className={`block h-5 w-5 rounded-full bg-white shadow transition ${showOnlyActiveKeys ? "translate-x-5" : ""}`} />
            </span>
          </span>
        </label>
      </section>

      <section className="space-y-4">
        {visibleConnections.map((connection) => {
            const credentials = credentialsByConnection[connection.id] || [];
            const visibleCredentials = credentials;

            return (
              <article className="mp-card overflow-hidden" key={connection.id}>
              <div className="border-b border-[var(--mp-line)] bg-[#fff8f1] p-3">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[var(--mp-ink)] px-2.5 py-0.5 text-[11px] font-bold text-white">
                        {providerLabels[connection.provider] || connection.provider}
                      </span>
                      <span className="rounded-full border border-[var(--mp-line)] bg-white px-2.5 py-0.5 text-[11px] font-bold">
                        {connection.status}
                      </span>
                      {connection.is_disabled ? (
                        <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[11px] font-bold text-red-700">Отключено</span>
                      ) : null}
                    </div>
                    <h2 className="text-base font-bold">{connection.name}</h2>
                    <p className="text-xs text-[var(--mp-muted)]">
                      ID {connection.id}
                      {connection.external_account_name ? `, аккаунт ${connection.external_account_name}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-2 rounded-lg border border-[var(--mp-line)] bg-white px-2.5 py-1.5 text-xs font-semibold">
                      Активно
                      <CompactSwitch checked={!connection.is_disabled && connection.status === "ACTIVE"} onChange={(checked) => onToggleConnection(connection, checked)} />
                    </span>
                    <Link className="mp-btn-secondary inline-flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs" href={`/teams/${teamId}/connections/${connection.id}/access`}>
                      <ShieldCheck className="h-4 w-4" />
                      Доступы
                    </Link>
                  </div>
                </div>
              </div>

              <div className="p-3">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-[var(--mp-orange)]" />
                  <h3 className="text-sm font-bold">Ключи и токены</h3>
                </div>
                <div className="mt-2 grid gap-2 lg:grid-cols-2">
                  {visibleCredentials.map((credential) => (
                    <div className="rounded-lg border border-[var(--mp-line)] px-3 py-2" key={credential.id}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-sm font-bold">{credential.name}</span>
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold">{credential.credential_kind}</span>
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold">{credential.auth_scheme}</span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                credential.is_active ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                              }`}
                            >
                              {credential.is_active ? "активен" : "отключен"}
                            </span>
                          </div>
                          <p className="mt-1 truncate text-xs text-[var(--mp-muted)]">
                            {secretSummary(credential)}; срок: {formatDate(credential.expires_at)}
                          </p>
                        </div>
                        <CompactSwitch checked={credential.is_active} onChange={(checked) => onToggleCredential(connection.id, credential, checked)} />
                      </div>
                    </div>
                  ))}
                  {!credentials.length ? (
                    <p className="rounded-lg border border-dashed border-[var(--mp-line)] p-3 text-xs text-[var(--mp-muted)]">Ключи еще не добавлены.</p>
                  ) : null}
                </div>
              </div>
              </article>
            );
          })}
        {!connections.length ? (
          <div className="mp-card p-8 text-center text-sm text-[var(--mp-muted)]">Подключений пока нет. Нажмите `Добавить` и выберите кабинет.</div>
        ) : null}
        {connections.length > 0 && !visibleConnections.length ? (
          <div className="mp-card p-8 text-center text-sm text-[var(--mp-muted)]">
            Нет активных подключений. Отключите фильтр, чтобы увидеть остальные карточки.
          </div>
        ) : null}
      </section>

      {isOzonModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/45 px-4 py-8">
          <section className="w-full max-w-[620px] rounded-lg bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-2xl font-bold">Подключение Кабинета Ozon</h2>
              <button className="rounded-lg p-1 text-slate-500 hover:bg-slate-100" onClick={closeOzonModal} type="button">
                <X className="h-6 w-6" />
              </button>
            </div>

            {ozonStep === 1 ? (
              <form className="mt-7 space-y-4" onSubmit={onSellerSubmit}>
                <label className="block space-y-2 text-sm font-bold">
                  Придумайте название
                  <input
                    className="mp-input"
                    onChange={(event) => updateOzonDraft({ name: event.target.value })}
                    placeholder="Например, ООО «Ромашка» или название вашего бренда"
                    value={ozonDraft.name}
                  />
                </label>
                <div>
                  <div className="flex items-center gap-1 text-sm font-bold">
                    Создайте ключ Seller API
                    <HelpCircle className="h-4 w-4 text-slate-400" />
                  </div>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5 text-slate-500">
                    <li>
                      Перейдите в{" "}
                      <a className="font-semibold text-blue-700" href="https://seller.ozon.ru/app/settings/api-keys" rel="noreferrer" target="_blank">
                        Seller API
                      </a>{" "}
                      Кабинета селлера Ozon. Скопируйте Client ID и вставьте его ниже.
                    </li>
                    <li>Сгенерируйте ключ API. В настройках ключа укажите цель использования “Для внешнего сервиса” и название сервиса “WOzYm - AI платформа продаж”.</li>
                    <li>Скопируйте ключ доступа и вставьте его в поле ниже.</li>
                  </ol>
                </div>
                <label className="block space-y-2 text-sm">
                  Client ID
                  <input
                    className="mp-input"
                    onChange={(event) => updateOzonDraft({ sellerClientId: event.target.value })}
                    placeholder="Скопируйте на Ozon и вставьте здесь"
                    value={ozonDraft.sellerClientId}
                  />
                </label>
                <label className="block space-y-2 text-sm">
                  Ключ доступа
                  <input
                    className="mp-input"
                    onChange={(event) => updateOzonDraft({ sellerApiKey: event.target.value })}
                    placeholder="Скопируйте на Ozon и вставьте здесь"
                    value={ozonDraft.sellerApiKey}
                  />
                </label>
                {sellerValidationState !== "idle" || sellerValidation ? (
                  <div
                    className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${
                      sellerValidationState === "valid"
                        ? "border-green-200 bg-green-50 text-green-800"
                        : sellerValidationState === "checking"
                          ? "border-blue-200 bg-blue-50 text-blue-800"
                          : "border-red-200 bg-red-50 text-red-800"
                    }`}
                  >
                    {sellerValidationState === "valid" ? <CheckCircle2 className="mt-0.5 h-4 w-4" /> : null}
                    {sellerValidationState === "checking" ? <LoaderCircle className="mt-0.5 h-4 w-4 animate-spin" /> : null}
                    {sellerValidationState === "invalid" ? <AlertCircle className="mt-0.5 h-4 w-4" /> : null}
                    <span>
                      {sellerValidationState === "checking"
                        ? "Проверяем ключ в Ozon Seller API..."
                        : sellerValidation?.message || "Seller API ключ не прошел проверку."}
                    </span>
                  </div>
                ) : null}
                <button className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700" onClick={() => setShowSellerInstruction((value) => !value)} type="button">
                  {showSellerInstruction ? "Скрыть инструкцию" : "Посмотреть инструкцию"}
                  <ChevronDown className={`h-4 w-4 transition ${showSellerInstruction ? "rotate-180" : ""}`} />
                </button>
                {showSellerInstruction ? (
                  <InstructionPreview title="Перейдите на Ozon. Скопируйте Client ID" text="Зайдите в кабинет селлера Ozon, раздел Seller API, скопируйте Client ID и API key." />
                ) : null}
                {modalError ? <p className="mp-error">{modalError}</p> : null}
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm font-semibold text-slate-600">Шаг 1 из 2</span>
                  <div className="flex gap-3">
                    <button className="mp-btn-secondary" onClick={closeOzonModal} type="button">
                      Отмена
                    </button>
                    <button className="mp-btn-primary bg-green-600 hover:bg-green-700" disabled={sellerValidationState === "checking"} type="submit">
                      {sellerValidationState === "checking" ? "Проверяем..." : "Продолжить"}
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              <form className="mt-7 space-y-4" onSubmit={onOzonSubmit}>
                <div>
                  <div className="flex items-center gap-1 text-sm font-bold">
                    Создайте ключ Performance API
                    <HelpCircle className="h-4 w-4 text-slate-400" />
                  </div>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5 text-slate-500">
                    <li>
                      Перейдите в{" "}
                      <a className="font-semibold text-blue-700" href="https://seller.ozon.ru/app/settings/api-keys" rel="noreferrer" target="_blank">
                        Performance API
                      </a>{" "}
                      Кабинета селлера Ozon и откройте сервисный аккаунт.
                    </li>
                    <li>Нажмите “Добавить ключ”. Скопируйте Client ID и Client Secret, вставьте их в поля ниже.</li>
                  </ol>
                </div>
                <label className="block space-y-2 text-sm">
                  Client ID
                  <input
                    className="mp-input"
                    onChange={(event) => updateOzonDraft({ performanceClientId: event.target.value })}
                    placeholder="Скопируйте на Ozon и вставьте здесь"
                    value={ozonDraft.performanceClientId}
                  />
                </label>
                <label className="block space-y-2 text-sm">
                  Client Secret
                  <input
                    className="mp-input"
                    onChange={(event) => updateOzonDraft({ performanceClientSecret: event.target.value })}
                    placeholder="Скопируйте на Ozon и вставьте здесь"
                    value={ozonDraft.performanceClientSecret}
                  />
                </label>
                {performanceValidationState !== "idle" || performanceValidation ? (
                  <div
                    className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${
                      performanceValidationState === "valid"
                        ? "border-green-200 bg-green-50 text-green-800"
                        : performanceValidationState === "checking"
                          ? "border-blue-200 bg-blue-50 text-blue-800"
                          : "border-red-200 bg-red-50 text-red-800"
                    }`}
                  >
                    {performanceValidationState === "valid" ? <CheckCircle2 className="mt-0.5 h-4 w-4" /> : null}
                    {performanceValidationState === "checking" ? <LoaderCircle className="mt-0.5 h-4 w-4 animate-spin" /> : null}
                    {performanceValidationState === "invalid" ? <AlertCircle className="mt-0.5 h-4 w-4" /> : null}
                    <span>
                      {performanceValidationState === "checking"
                        ? "Проверяем ключ в Ozon Performance API..."
                        : performanceValidation?.message || "Performance API ключ не прошел проверку."}
                    </span>
                  </div>
                ) : null}
                <button className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700" onClick={() => setShowPerformanceInstruction((value) => !value)} type="button">
                  {showPerformanceInstruction ? "Скрыть инструкцию" : "Посмотреть инструкцию"}
                  <ChevronDown className={`h-4 w-4 transition ${showPerformanceInstruction ? "rotate-180" : ""}`} />
                </button>
                {showPerformanceInstruction ? (
                  <InstructionPreview title="Перейдите на Ozon. Откройте сервисный аккаунт" text="В разделе Performance API откройте активный сервисный аккаунт или создайте его, затем добавьте ключ." />
                ) : null}
                {modalError ? <p className="mp-error">{modalError}</p> : null}
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm font-semibold text-slate-600">Шаг 2 из 2</span>
                  <div className="flex gap-3">
                    <button className="mp-btn-secondary" disabled={isSubmitting} onClick={() => setOzonStep(1)} type="button">
                      Назад
                    </button>
                    <button className="mp-btn-primary bg-green-600 hover:bg-green-700" disabled={isSubmitting || performanceValidationState === "checking"} type="submit">
                      {performanceValidationState === "checking" ? "Проверяем..." : isSubmitting ? "Добавляем..." : "Добавить"}
                    </button>
                  </div>
                </div>
              </form>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}

