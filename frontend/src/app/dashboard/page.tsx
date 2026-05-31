"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  Bell,
  Building2,
  ChevronDown,
  CreditCard,
  FileText,
  Grid3X3,
  Handshake,
  Lightbulb,
  LogOut,
  MoreVertical,
  Pencil,
  Plug,
  ReceiptText,
  RefreshCw,
  Search,
  Send,
  Settings,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";

import {
  ensurePersonalTeam,
  getTeamDashboard,
  listConnectionProducts,
  listConnectionCredentials,
  listTeamConnections,
  listTeams,
  logout,
  runConnectionSync,
  createAiCardDraft,
  generateAiMediaImage,
  getAiMediaImageStatus,
  createOzonProduct,
  getOzonAttributeValues,
  getOzonAttributes,
  refreshOzonContentRating,
  saveOzonProductMedia,
  type AiCardDraftResult,
  type MarketplaceConnection,
  type MarketplaceCredential,
  type MarketplaceProductItem,
  type OzonAttribute,
  type OzonAttributeValue,
  type Team,
  type TeamDashboard,
} from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";
import { AnalyticsMainChart } from "@/components/analytics-main-chart";

type ProviderFilter = "ALL" | "WB" | "OZON" | "YANDEX_MARKET";
type ProviderKey = Exclude<ProviderFilter, "ALL">;
type ProviderStatusDot = "green" | "yellow" | "red" | "none";
type ProductStatusFilter = "ALL" | "ACTIVE" | "ARCHIVED" | "UNKNOWN";
type ProductWizardTab = "info" | "characteristics" | "media" | "preview";
type MediaTab = "photo" | "video" | "cover";
type ProductEditorMode = "create" | "edit";
type ProductEditorEntryMode = "edit" | "ai" | "ai_media";
type AiFieldUiStatus = "normal" | "ai_applied" | "ai_suggestion" | "ai_low_confidence" | "ai_error";
type AiFieldAction = "auto_apply" | "show_only" | "skip";

type AiFieldRecommendation = {
  field: string;
  currentValue: string;
  suggestedValue: string;
  hasRecommendation: boolean;
  confidence: number;
  reason: string;
  source: string;
  action: AiFieldAction;
};

type AiFieldState = {
  previousValue: string;
  recommendation: AiFieldRecommendation;
  status: AiFieldUiStatus;
};

type AiMediaRecommendation = {
  type: string;
  prompt: string;
  reason: string;
  confidence: number;
  action: "generate" | "show_prompt_only" | "skip";
};

type AiMediaDraft = {
  id: string;
  sourceImage: string;
  generatedImage: string | null;
  prompt: string;
  reference: string;
  createdAt: string;
  logId?: number;
  model?: string;
  status: "queued" | "running" | "generated" | "failed";
  progress: number;
  error?: string;
};

const AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.85;
const SHOW_SUGGESTION_CONFIDENCE_THRESHOLD = 0.55;
const AI_MEDIA_DRAFT_PREFIX = "ai-draft://";

function makeAiMediaDraftPlaceholder(logId: number) {
  return `${AI_MEDIA_DRAFT_PREFIX}${logId}`;
}

function getAiMediaDraftLogIdFromPhoto(url: string) {
  if (!url.startsWith(AI_MEDIA_DRAFT_PREFIX)) return null;
  const value = Number(url.slice(AI_MEDIA_DRAFT_PREFIX.length));
  return Number.isFinite(value) ? value : null;
}

function isAiMediaDraftPlaceholder(url: string) {
  return getAiMediaDraftLogIdFromPhoto(url) !== null;
}
type CharacteristicDictionaryState = {
  tnved: OzonAttributeValue[];
  material: OzonAttributeValue[];
  color: OzonAttributeValue[];
  warranty: OzonAttributeValue[];
  country: OzonAttributeValue[];
};
type CharacteristicDictionaryIds = {
  tnved: number;
  material: number;
  color: number;
  warranty: number;
  country: number;
};
const TEAM_STORAGE_KEY = "dashboard:selectedTeamId";
const OZON_ATTRIBUTE_IDS = {
  brand: [85, 31],
  modelName: [9048, 8292, 4180],
  tnved: [22232],
  hashtags: [23171],
  annotation: [4191],
  partnerCode: [9024],
  material: [6383],
  color: [10096],
  warrantyTerm: [4385],
  warranty: [10400],
  country: [4389],
};

function normalizeProvider(provider: string): ProviderFilter {
  const value = provider.trim().toUpperCase();
  if (value.includes("WB") || value.includes("WILDBERRIES")) return "WB";
  if (value.includes("OZON")) return "OZON";
  if (value.includes("YANDEX") || value.includes("YM") || value.includes("MARKET")) return "YANDEX_MARKET";
  return "ALL";
}

function pickPreferredConnectionId(
  rows: MarketplaceConnection[],
  credentialsByConnection: Record<number, MarketplaceCredential[]>,
): number | null {
  if (!rows.length) return null;
  const activeWithKeys = rows.find((row) => {
    if (row.is_disabled || row.status.toUpperCase() === "DISABLED") return false;
    const credentials = credentialsByConnection[row.id] || [];
    return credentials.some((credential) => credential.is_active);
  });
  if (activeWithKeys) return activeWithKeys.id;

  const firstActive = rows.find((row) => !row.is_disabled && row.status.toUpperCase() !== "DISABLED");
  if (firstActive) return firstActive.id;
  return rows[0].id;
}

function isConnectionUsable(row: MarketplaceConnection, credentialsByConnection: Record<number, MarketplaceCredential[]>): boolean {
  if (row.is_disabled || row.status.toUpperCase() === "DISABLED") return false;
  const credentials = credentialsByConnection[row.id] || [];
  return credentials.some((credential) => credential.is_active);
}

function makeOfferIdDraft() {
  return `NEW_${Date.now()}`;
}

function parsePositiveIntInput(raw: string): number {
  const normalized = (raw || "").trim();
  if (!normalized) return 0;
  const direct = Number(normalized);
  if (Number.isFinite(direct) && direct > 0) return Math.floor(direct);
  const match = normalized.match(/\d+/g);
  if (!match || !match.length) return 0;
  const fromDigits = Number(match.join(""));
  if (Number.isFinite(fromDigits) && fromDigits > 0) return Math.floor(fromDigits);
  return 0;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function stripHtmlTags(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function normalizeTextForMatch(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function pickAttributeValue(attributesRaw: unknown, attributeIds: number[]): string {
  const attributes = Array.isArray(attributesRaw) ? attributesRaw : [];
  for (const row of attributes) {
    const attr = asRecord(row);
    const id = Number(attr.id || 0);
    if (!attributeIds.includes(id)) continue;
    const values = Array.isArray(attr.values) ? attr.values : [];
    const rendered = values
      .map((valueItem) => {
        const valueRow = asRecord(valueItem);
        const raw = valueRow.value ?? valueRow.dictionary_value ?? valueRow.value_id ?? "";
        return asString(raw).trim();
      })
      .filter(Boolean);
    if (rendered.length) return rendered.join("; ");
  }
  return "";
}

function findAttributeIdByName(attributes: OzonAttribute[], aliases: string[], fallbackId: number): number {
  const normalizedAliases = aliases.map(normalizeTextForMatch);
  const row = attributes.find((item) => {
    const name = normalizeTextForMatch(item.name || "");
    return normalizedAliases.some((alias) => name.includes(alias));
  });
  return row?.id || fallbackId;
}

function collectAttributeIdsByAliases(attributes: OzonAttribute[], aliases: string[], fallbackId: number): number[] {
  const normalizedAliases = aliases.map(normalizeTextForMatch);
  const matched = attributes
    .filter((item) => {
      const name = normalizeTextForMatch(item.name || "");
      return normalizedAliases.some((alias) => name.includes(alias));
    })
    .map((item) => item.id)
    .filter((id) => Number.isFinite(id) && id > 0);
  const merged = [...matched, fallbackId].filter((id) => Number.isFinite(id) && id > 0);
  return Array.from(new Set(merged));
}

function colorSwatchStyle(colorName: string): { backgroundColor?: string; backgroundImage?: string; backgroundSize?: string } {
  const value = normalizeTextForMatch(colorName);
  if (!value) return { backgroundColor: "#e5e7eb" };
  if (value.includes("прозрач")) {
    return {
      backgroundImage:
        "linear-gradient(45deg,#ffffff 25%,#d1d5db 25%,#d1d5db 50%,#ffffff 50%,#ffffff 75%,#d1d5db 75%,#d1d5db 100%)",
      backgroundSize: "8px 8px",
    };
  }
  if (value.includes("бел")) return { backgroundColor: "#ffffff" };
  if (value.includes("черн")) return { backgroundColor: "#111827" };
  if (value.includes("сереб") || value.includes("метал")) return { backgroundColor: "#9ca3af" };
  if (value.includes("сер")) return { backgroundColor: "#6b7280" };
  if (value.includes("золот")) return { backgroundColor: "#d4a017" };
  if (value.includes("беж")) return { backgroundColor: "#d8c3a5" };
  if (value.includes("корич")) return { backgroundColor: "#7c4a2d" };
  if (value.includes("крас")) return { backgroundColor: "#dc2626" };
  if (value.includes("розов")) return { backgroundColor: "#ec4899" };
  if (value.includes("фиолет") || value.includes("пурпур")) return { backgroundColor: "#7c3aed" };
  if (value.includes("син")) return { backgroundColor: "#2563eb" };
  if (value.includes("голуб")) return { backgroundColor: "#0ea5e9" };
  if (value.includes("зелен")) return { backgroundColor: "#16a34a" };
  if (value.includes("желт")) return { backgroundColor: "#facc15" };
  if (value.includes("оранж")) return { backgroundColor: "#f97316" };
  return { backgroundColor: "#94a3b8" };
}

function getContentRating(item: MarketplaceProductItem | null): {
  rating: number | null;
  fetchedAt: string | null;
  groups: Array<Record<string, unknown>>;
} {
  if (!item) return { rating: null, fetchedAt: null, groups: [] };
  const payload = asRecord(item.payload);
  const contentRating = asRecord(payload.content_rating);
  const groups = Array.isArray(contentRating.groups)
    ? contentRating.groups.filter((group): group is Record<string, unknown> => !!group && typeof group === "object" && !Array.isArray(group))
    : [];
  return {
    rating: asNumber(contentRating.rating),
    fetchedAt: asString(contentRating.fetched_at || "") || null,
    groups,
  };
}

function contentRatingBadge(rating: number | null): { label: string; cls: string } {
  if (rating === null) return { label: "нет данных", cls: "border-slate-200 bg-slate-100 text-slate-600" };
  if (rating >= 75) return { label: "высокий", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" };
  if (rating >= 45) return { label: "базовый", cls: "border-amber-200 bg-amber-50 text-amber-700" };
  return { label: "низкий", cls: "border-rose-200 bg-rose-50 text-rose-700" };
}

function contentRatingBarColor(rating: number | null): string {
  if (rating === null) return "#cbd5e1";
  if (rating >= 75) return "#16a34a";
  if (rating >= 45) return "#f59e0b";
  return "#dc2626";
}

export default function DashboardPage() {
  const { token, user, isReady, clearAuth } = useAuth();
  const router = useRouter();
  const [teams, setTeams] = useState<Team[]>([]);
  const [connections, setConnections] = useState<MarketplaceConnection[]>([]);
  const [credentialsByConnection, setCredentialsByConnection] = useState<Record<number, MarketplaceCredential[]>>({});
  const [products, setProducts] = useState<MarketplaceProductItem[]>([]);
  const [dashboard, setDashboard] = useState<TeamDashboard | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [isRefreshingMarketplace, setIsRefreshingMarketplace] = useState(false);
  const [isRefreshingContentRating, setIsRefreshingContentRating] = useState(false);
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>("ALL");
  const [productSearch, setProductSearch] = useState("");
  const [productStatusFilter, setProductStatusFilter] = useState<ProductStatusFilter>("ALL");
  const [mediaProduct, setMediaProduct] = useState<MarketplaceProductItem | null>(null);
  const [productEditorMode, setProductEditorMode] = useState<ProductEditorMode>("edit");
  const [productEditorEntryMode, setProductEditorEntryMode] = useState<ProductEditorEntryMode>("edit");
  const [wizardTab, setWizardTab] = useState<ProductWizardTab>("info");
  const [mediaTab, setMediaTab] = useState<MediaTab>("photo");
  const [activePhotoIndex, setActivePhotoIndex] = useState(0);
  const [mediaDraftPhotos, setMediaDraftPhotos] = useState<string[]>([]);
  const [dragPhotoIndex, setDragPhotoIndex] = useState<number | null>(null);
  const [mediaDraftVideos, setMediaDraftVideos] = useState<string[]>([]);
  const [mediaDraftCover, setMediaDraftCover] = useState<string>("");
  const [mediaPhotoInput, setMediaPhotoInput] = useState("");
  const [mediaVideoInput, setMediaVideoInput] = useState("");
  const [isPhotoDropActive, setIsPhotoDropActive] = useState(false);
  const [isVideoDropActive, setIsVideoDropActive] = useState(false);
  const [isCoverDropActive, setIsCoverDropActive] = useState(false);
  const [showPhotoOrderHint, setShowPhotoOrderHint] = useState(true);
  const [isSavingMedia, setIsSavingMedia] = useState(false);
  const [isSavingProduct, setIsSavingProduct] = useState(false);
  const [mediaNotice, setMediaNotice] = useState<string | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiReferenceNote, setAiReferenceNote] = useState("");
  const [aiMediaPrompt, setAiMediaPrompt] = useState("");
  const [aiMediaReferenceNote, setAiMediaReferenceNote] = useState("");
  const [aiMediaDrafts, setAiMediaDrafts] = useState<AiMediaDraft[]>([]);
  const [isGeneratingAiDraft, setIsGeneratingAiDraft] = useState(false);
  const [isGeneratingAiMediaImage, setIsGeneratingAiMediaImage] = useState(false);
  const [aiDraftResult, setAiDraftResult] = useState<AiCardDraftResult | null>(null);
  const [aiFieldStates, setAiFieldStates] = useState<Record<string, AiFieldState>>({});
  const [aiMediaRecommendations, setAiMediaRecommendations] = useState<AiMediaRecommendation[]>([]);
  const [productOfferId, setProductOfferId] = useState("");
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productDescriptionCategoryId, setProductDescriptionCategoryId] = useState("");
  const [productTypeId, setProductTypeId] = useState("");
  const [productBarcode, setProductBarcode] = useState("");
  const [productPrice, setProductPrice] = useState("");
  const [productOldPrice, setProductOldPrice] = useState("");
  const [packageLength, setPackageLength] = useState("");
  const [packageWidth, setPackageWidth] = useState("");
  const [packageHeight, setPackageHeight] = useState("");
  const [packageWeight, setPackageWeight] = useState("");
  const [productAttributesJson, setProductAttributesJson] = useState("[]");
  const [productComplexAttributesJson, setProductComplexAttributesJson] = useState("[]");
  const [ozonRequiredAttributes, setOzonRequiredAttributes] = useState<OzonAttribute[]>([]);
  const [ozonAttributeValuesById, setOzonAttributeValuesById] = useState<Record<number, OzonAttributeValue[]>>({});
  const [ozonAttributeInputValues, setOzonAttributeInputValues] = useState<Record<number, string>>({});
  const [isLoadingOzonAttributes, setIsLoadingOzonAttributes] = useState(false);
  const [charBrand, setCharBrand] = useState("");
  const [charModelName, setCharModelName] = useState("");
  const [charTnved, setCharTnved] = useState("");
  const [charProductWeight, setCharProductWeight] = useState("");
  const [charQuantityUei, setCharQuantityUei] = useState("");
  const [charMinWholesaleQty, setCharMinWholesaleQty] = useState("");
  const [charHashtags, setCharHashtags] = useState("");
  const [charAnnotation, setCharAnnotation] = useState("");
  const [charSimilarProducts, setCharSimilarProducts] = useState("");
  const [charPartnerCode, setCharPartnerCode] = useState("");
  const [charOemNumber, setCharOemNumber] = useState("");
  const [charCableLength, setCharCableLength] = useState("");
  const [charPower, setCharPower] = useState("");
  const [charMaterial, setCharMaterial] = useState("");
  const [charColor, setCharColor] = useState("");
  const [charWarrantyTerm, setCharWarrantyTerm] = useState("");
  const [charWarranty, setCharWarranty] = useState("");
  const [charCountry, setCharCountry] = useState("");
  const [charComplectation, setCharComplectation] = useState("");
  const [charFactoryPackageCount, setCharFactoryPackageCount] = useState("");
  const [charDictionaryOptions, setCharDictionaryOptions] = useState<CharacteristicDictionaryState>({
    tnved: [],
    material: [],
    color: [],
    warranty: [],
    country: [],
  });
  const [charDictionaryIds, setCharDictionaryIds] = useState<CharacteristicDictionaryIds>({
    tnved: OZON_ATTRIBUTE_IDS.tnved[0],
    material: OZON_ATTRIBUTE_IDS.material[0],
    color: OZON_ATTRIBUTE_IDS.color[0],
    warranty: OZON_ATTRIBUTE_IDS.warranty[0],
    country: OZON_ATTRIBUTE_IDS.country[0],
  });
  const [isColorDropdownOpen, setIsColorDropdownOpen] = useState(false);
  const [isTnvedDropdownOpen, setIsTnvedDropdownOpen] = useState(false);
  const [tnvedHoverText, setTnvedHoverText] = useState<string | null>(null);
  const [isLoadingCharDictionaries, setIsLoadingCharDictionaries] = useState(false);
  const photoInputRef = useRef<HTMLInputElement | null>(null);
  const videoInputRef = useRef<HTMLInputElement | null>(null);
  const coverInputRef = useRef<HTMLInputElement | null>(null);
  const colorDropdownRef = useRef<HTMLDivElement | null>(null);
  const tnvedDropdownRef = useRef<HTMLDivElement | null>(null);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);
  const charDictionaryKeyRef = useRef("");
  const photoOrderAutosaveTimeoutRef = useRef<number | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token) return;
    listTeams(token)
      .then(async (rows) => {
        const availableTeams = rows.length ? rows : [await ensurePersonalTeam(token)];
        setTeams(availableTeams);
        if (selectedTeamId !== null && availableTeams.some((team) => team.id === selectedTeamId)) {
          return;
        }
        const savedRaw = window.localStorage.getItem(TEAM_STORAGE_KEY);
        const savedId = savedRaw ? Number(savedRaw) : NaN;
        if (Number.isFinite(savedId) && availableTeams.some((team) => team.id === savedId)) {
          setSelectedTeamId(savedId);
          return;
        }
        setSelectedTeamId(availableTeams[0].id);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load teams"));
  }, [token, selectedTeamId]);

  useEffect(() => {
    if (selectedTeamId === null) return;
    window.localStorage.setItem(TEAM_STORAGE_KEY, String(selectedTeamId));
  }, [selectedTeamId]);

  useEffect(() => {
    if (!token || !selectedTeamId) return;
    Promise.resolve()
      .then(async () => {
        const rows = await listTeamConnections(token, selectedTeamId);
        const credentialPairs = await Promise.all(
          rows.map(async (row) => [row.id, await listConnectionCredentials(token, selectedTeamId, row.id)] as const),
        );
        const nextCredentialsByConnection = Object.fromEntries(credentialPairs);
        setConnections(rows);
        setCredentialsByConnection(nextCredentialsByConnection);
        setSelectedConnectionId((currentId) => {
          if (!rows.length) return null;
          const preferredId = pickPreferredConnectionId(rows, nextCredentialsByConnection);
          if (currentId) {
            const selected = rows.find((row) => row.id === currentId);
            if (selected) {
              const selectedCredentials = nextCredentialsByConnection[selected.id] || [];
              const selectedHasActiveKey = selectedCredentials.some((credential) => credential.is_active);
              const selectedIsDisabled = selected.is_disabled || selected.status.toUpperCase() === "DISABLED";
              if (!selectedIsDisabled && selectedHasActiveKey) return currentId;
            }
          }
          return preferredId;
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load connections"));
  }, [token, selectedTeamId]);

  const filteredConnections = useMemo(
    () => (providerFilter === "ALL" ? connections : connections.filter((row) => normalizeProvider(row.provider) === providerFilter)),
    [connections, providerFilter],
  );
  const effectiveSelectedConnectionId = useMemo(() => {
    if (!filteredConnections.length) return null;
    if (selectedConnectionId) {
      const selected = filteredConnections.find((row) => row.id === selectedConnectionId);
      if (selected && isConnectionUsable(selected, credentialsByConnection)) {
        return selectedConnectionId;
      }
    }
    return pickPreferredConnectionId(filteredConnections, credentialsByConnection);
  }, [filteredConnections, selectedConnectionId, credentialsByConnection]);

  useEffect(() => {
    if (!token || !selectedTeamId) return;
    Promise.all([
      getTeamDashboard(token, selectedTeamId, effectiveSelectedConnectionId),
      effectiveSelectedConnectionId ? listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 60) : Promise.resolve([] as MarketplaceProductItem[]),
    ])
      .then(([dashboardPayload, productRows]) => {
        setDashboard(dashboardPayload);
        setProducts(productRows);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      });
  }, [token, selectedTeamId, effectiveSelectedConnectionId]);

  const selectedConnection = useMemo(
    () => connections.find((row) => row.id === effectiveSelectedConnectionId) || null,
    [connections, effectiveSelectedConnectionId],
  );

  const filteredProducts = useMemo(() => {
    const query = productSearch.trim().toLowerCase();
    return products.filter((item) => {
      const normalizedStatus = (item.status || "").toUpperCase();
      const derivedStatus: ProductStatusFilter =
        normalizedStatus.includes("ARCHIVE") || normalizedStatus.includes("DISABLE") ? "ARCHIVED" : normalizedStatus ? "ACTIVE" : "UNKNOWN";
      if (productStatusFilter !== "ALL" && derivedStatus !== productStatusFilter) return false;
      if (!query) return true;
      const haystack = [
        item.name || "",
        item.external_sku || "",
        item.external_offer_id || "",
        item.external_product_id || "",
        item.barcode || "",
        item.brand || "",
        item.category_name || "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [products, productSearch, productStatusFilter]);

  useEffect(() => {
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 60_000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId || !mediaProduct) return;
    const pendingDrafts = aiMediaDrafts.filter((draft) => draft.logId && (draft.status === "queued" || draft.status === "running"));
    if (!pendingDrafts.length) return;

    let cancelled = false;
    const poll = async () => {
      const results = await Promise.allSettled(
        pendingDrafts.map((draft) => getAiMediaImageStatus(token, selectedTeamId, effectiveSelectedConnectionId, mediaProduct.id, draft.logId as number)),
      );
      if (cancelled) return;
      setAiMediaDrafts((prev) => {
        let changed = false;
        const next = prev.map((draft) => {
          if (!draft.logId) return draft;
          const index = pendingDrafts.findIndex((pending) => pending.logId === draft.logId);
          if (index < 0) return draft;
          const result = results[index];
          if (result.status !== "fulfilled") return draft;
          const payload = result.value;
          if (payload.status === "success" && payload.image_url) {
            changed = true;
            const placeholderUrl = makeAiMediaDraftPlaceholder(draft.logId);
            setMediaDraftPhotos((photos) => photos.map((url) => (url === placeholderUrl ? payload.image_url as string : url)));
            return {
              ...draft,
              generatedImage: payload.image_url,
              prompt: payload.revised_prompt || draft.prompt,
              model: payload.model,
              status: "generated" as const,
              progress: 100,
            };
          }
          if (payload.status === "failed") {
            changed = true;
            return {
              ...draft,
              status: "failed" as const,
              progress: 100,
              error: payload.error_message || "AI image generation failed",
            };
          }
          const nextStatus: AiMediaDraft["status"] = payload.status === "queued" ? "queued" : "running";
          const nextProgress = Math.max(draft.progress, payload.progress || 5);
          if (draft.status === nextStatus && draft.progress === nextProgress) return draft;
          changed = true;
          return {
            ...draft,
            status: nextStatus,
            progress: nextProgress,
          };
        });
        return changed ? next : prev;
      });
    };

    poll();
    const intervalId = window.setInterval(poll, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [aiMediaDrafts, effectiveSelectedConnectionId, mediaProduct, selectedTeamId, token]);

  useEffect(() => {
    return () => {
      if (photoOrderAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(photoOrderAutosaveTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      const target = event.target as Node;
      if (colorDropdownRef.current && !colorDropdownRef.current.contains(target)) {
        setIsColorDropdownOpen(false);
      }
      if (tnvedDropdownRef.current && !tnvedDropdownRef.current.contains(target)) {
        setIsTnvedDropdownOpen(false);
        setTnvedHoverText(null);
      }
      if (accountMenuRef.current && !accountMenuRef.current.contains(target)) {
        setIsAccountMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (wizardTab !== "characteristics") return;
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    if (normalizeProvider(selectedConnection?.provider || "") !== "OZON") return;
    const descriptionCategoryId = parsePositiveIntInput(productDescriptionCategoryId);
    const typeId = parsePositiveIntInput(productTypeId);
    if (descriptionCategoryId <= 0 || typeId <= 0) return;
    const cacheKey = `${effectiveSelectedConnectionId}:${descriptionCategoryId}:${typeId}`;
    if (charDictionaryKeyRef.current === cacheKey) return;
    charDictionaryKeyRef.current = cacheKey;

    let cancelled = false;
    setIsLoadingCharDictionaries(true);
    Promise.resolve()
      .then(async () => {
        const attributes = await getOzonAttributes(token, selectedTeamId, effectiveSelectedConnectionId, descriptionCategoryId, typeId);
        const tnvedCandidates = collectAttributeIdsByAliases(
          attributes,
          ["тн вэд коды еаэс", "тн вэд", "код тн вэд", "еаэс"],
          OZON_ATTRIBUTE_IDS.tnved[0],
        );
        const materialCandidates = collectAttributeIdsByAliases(attributes, ["материал"], OZON_ATTRIBUTE_IDS.material[0]);
        const colorCandidates = collectAttributeIdsByAliases(attributes, ["цвет товара", "цвет"], OZON_ATTRIBUTE_IDS.color[0]);
        const warrantyCandidates = collectAttributeIdsByAliases(attributes, ["гарантия"], OZON_ATTRIBUTE_IDS.warranty[0]);
        const countryCandidates = collectAttributeIdsByAliases(
          attributes,
          ["страна-изготовитель", "страна изготовитель", "страна производства", "страна"],
          OZON_ATTRIBUTE_IDS.country[0],
        );

        const loadFirstNonEmpty = async (attributeIds: number[]) => {
          let lastValues: OzonAttributeValue[] = [];
          let lastId = attributeIds[0] || 0;
          for (const attributeId of attributeIds) {
            lastId = attributeId;
            try {
              const values = await getOzonAttributeValues(
                token,
                selectedTeamId,
                effectiveSelectedConnectionId,
                attributeId,
                descriptionCategoryId,
                typeId,
                250,
              );
              if (values.length) {
                return { attributeId, values };
              }
              lastValues = values;
            } catch {
              // try next candidate id
            }
          }
          return { attributeId: lastId, values: lastValues };
        };

        const dictionaryRows = await Promise.all([
          loadFirstNonEmpty(tnvedCandidates),
          loadFirstNonEmpty(materialCandidates),
          loadFirstNonEmpty(colorCandidates),
          loadFirstNonEmpty(warrantyCandidates),
          loadFirstNonEmpty(countryCandidates),
        ]);

        const ids: CharacteristicDictionaryIds = {
          tnved: dictionaryRows[0].attributeId || findAttributeIdByName(attributes, ["тн вэд", "еаэс"], OZON_ATTRIBUTE_IDS.tnved[0]),
          material: dictionaryRows[1].attributeId || findAttributeIdByName(attributes, ["материал"], OZON_ATTRIBUTE_IDS.material[0]),
          color: dictionaryRows[2].attributeId || findAttributeIdByName(attributes, ["цвет товара", "цвет"], OZON_ATTRIBUTE_IDS.color[0]),
          warranty: dictionaryRows[3].attributeId || findAttributeIdByName(attributes, ["гарантия"], OZON_ATTRIBUTE_IDS.warranty[0]),
          country: dictionaryRows[4].attributeId || findAttributeIdByName(attributes, ["страна", "страна-изготовитель"], OZON_ATTRIBUTE_IDS.country[0]),
        };
        return { ids, dictionaryRows };
      })
      .then(({ ids, dictionaryRows }) => {
        if (cancelled) return;
        const tnved = dictionaryRows[0]?.values || [];
        const material = dictionaryRows[1]?.values || [];
        const color = dictionaryRows[2]?.values || [];
        const warranty = dictionaryRows[3]?.values || [];
        const country = dictionaryRows[4]?.values || [];
        setCharDictionaryIds(ids);
        setCharDictionaryOptions({ tnved, material, color, warranty, country });
      })
      .catch(() => {
        if (cancelled) return;
        setCharDictionaryIds({
          tnved: OZON_ATTRIBUTE_IDS.tnved[0],
          material: OZON_ATTRIBUTE_IDS.material[0],
          color: OZON_ATTRIBUTE_IDS.color[0],
          warranty: OZON_ATTRIBUTE_IDS.warranty[0],
          country: OZON_ATTRIBUTE_IDS.country[0],
        });
        setCharDictionaryOptions({ tnved: [], material: [], color: [], warranty: [], country: [] });
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingCharDictionaries(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    wizardTab,
    token,
    selectedTeamId,
    effectiveSelectedConnectionId,
    selectedConnection?.provider,
    productDescriptionCategoryId,
    productTypeId,
  ]);

  function openMediaModal(item: MarketplaceProductItem, entryMode: ProductEditorEntryMode = "edit") {
    if (photoOrderAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(photoOrderAutosaveTimeoutRef.current);
      photoOrderAutosaveTimeoutRef.current = null;
    }
    const payload = asRecord(item.payload);
    const infoItem = asRecord(payload.info_item);
    const attrsItem = asRecord(payload.attributes_item);

    setProductEditorMode("edit");
    setProductEditorEntryMode(entryMode);
    setWizardTab(entryMode === "ai_media" ? "media" : "info");
    setMediaTab("photo");
    setActivePhotoIndex(0);
    setDragPhotoIndex(null);
    setMediaDraftPhotos(item.image_urls || []);
    setMediaDraftVideos(item.video_urls || []);
    setMediaDraftCover(item.image_urls?.[0] || "");
    setShowPhotoOrderHint(true);
    setMediaPhotoInput("");
    setMediaVideoInput("");
    setMediaNotice(null);
    setMediaError(null);
    setAiPrompt("");
    setAiReferenceNote("");
    setAiMediaPrompt("");
    setAiMediaReferenceNote("");
    setAiMediaDrafts([]);
    setAiDraftResult(null);
    setAiFieldStates({});
    setAiMediaRecommendations([]);
    setProductOfferId(asString(infoItem.offer_id || item.external_offer_id || item.external_sku || ""));
    setProductName(asString(infoItem.name || item.name || ""));
    setProductDescription(asString(infoItem.description || ""));
    setProductDescriptionCategoryId(asString(infoItem.description_category_id || attrsItem.description_category_id || "").replace("category:", ""));
    setProductTypeId(asString(infoItem.type_id || attrsItem.type_id || ""));
    setProductBarcode(asString((Array.isArray(infoItem.barcodes) && infoItem.barcodes.length ? infoItem.barcodes[0] : "") || attrsItem.barcode || item.barcode || ""));
    setProductPrice(asString(infoItem.price || ""));
    setProductOldPrice(asString(infoItem.old_price || ""));
    setPackageLength(asString(attrsItem.depth || ""));
    setPackageWidth(asString(attrsItem.width || ""));
    setPackageHeight(asString(attrsItem.height || ""));
    setPackageWeight(asString(attrsItem.weight || ""));
    setProductAttributesJson(JSON.stringify(Array.isArray(attrsItem.attributes) ? attrsItem.attributes : [], null, 2));
    setProductComplexAttributesJson(JSON.stringify(Array.isArray(attrsItem.complex_attributes) ? attrsItem.complex_attributes : [], null, 2));
    setOzonRequiredAttributes([]);
    setOzonAttributeValuesById({});
    setOzonAttributeInputValues({});
    const rawAttributes = Array.isArray(attrsItem.attributes) ? attrsItem.attributes : [];
    setCharBrand(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.brand) || item.brand || "");
    setCharModelName(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.modelName) || asString(infoItem.name || item.name || ""));
    setCharTnved(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.tnved));
    setCharProductWeight(asString(attrsItem.weight || ""));
    setCharQuantityUei(pickAttributeValue(rawAttributes, [4355]));
    setCharMinWholesaleQty(pickAttributeValue(rawAttributes, [4384]));
    setCharHashtags(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.hashtags));
    setCharAnnotation(stripHtmlTags(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.annotation)));
    setCharSimilarProducts(pickAttributeValue(rawAttributes, [7435]));
    setCharPartnerCode(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.partnerCode) || asString(infoItem.offer_id || item.external_offer_id || ""));
    setCharOemNumber("");
    setCharCableLength("");
    setCharPower("");
    setCharMaterial(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.material));
    setCharColor(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.color));
    setCharWarrantyTerm(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.warrantyTerm));
    setCharWarranty(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.warranty));
    setCharCountry(pickAttributeValue(rawAttributes, OZON_ATTRIBUTE_IDS.country));
    setCharComplectation(pickAttributeValue(rawAttributes, [7434]));
    setCharFactoryPackageCount(pickAttributeValue(rawAttributes, [4404]));
    charDictionaryKeyRef.current = "";
    setIsColorDropdownOpen(false);
    setIsTnvedDropdownOpen(false);
    setTnvedHoverText(null);
    setCharDictionaryOptions({ tnved: [], material: [], color: [], warranty: [], country: [] });
    setCharDictionaryIds({
      tnved: OZON_ATTRIBUTE_IDS.tnved[0],
      material: OZON_ATTRIBUTE_IDS.material[0],
      color: OZON_ATTRIBUTE_IDS.color[0],
      warranty: OZON_ATTRIBUTE_IDS.warranty[0],
      country: OZON_ATTRIBUTE_IDS.country[0],
    });
    setMediaProduct(item);
  }

  function openCreateProductModal() {
    if (photoOrderAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(photoOrderAutosaveTimeoutRef.current);
      photoOrderAutosaveTimeoutRef.current = null;
    }
    setProductEditorMode("create");
    setProductEditorEntryMode("edit");
    setWizardTab("info");
    setMediaTab("photo");
    setActivePhotoIndex(0);
    setDragPhotoIndex(null);
    setMediaDraftPhotos([]);
    setMediaDraftVideos([]);
    setMediaDraftCover("");
    setShowPhotoOrderHint(true);
    setMediaPhotoInput("");
    setMediaVideoInput("");
    setMediaNotice(null);
    setMediaError(null);
    setAiPrompt("");
    setAiReferenceNote("");
    setAiMediaPrompt("");
    setAiMediaReferenceNote("");
    setAiMediaDrafts([]);
    setAiDraftResult(null);
    setAiFieldStates({});
    setAiMediaRecommendations([]);
    setProductOfferId(makeOfferIdDraft());
    setProductName("");
    setProductDescription("");
    setProductDescriptionCategoryId("");
    setProductTypeId("");
    setProductBarcode("");
    setProductPrice("");
    setProductOldPrice("");
    setPackageLength("");
    setPackageWidth("");
    setPackageHeight("");
    setPackageWeight("");
    setProductAttributesJson("[]");
    setProductComplexAttributesJson("[]");
    setOzonRequiredAttributes([]);
    setOzonAttributeValuesById({});
    setOzonAttributeInputValues({});
    setCharBrand("");
    setCharModelName("");
    setCharTnved("");
    setCharProductWeight("");
    setCharQuantityUei("");
    setCharMinWholesaleQty("");
    setCharHashtags("");
    setCharAnnotation("");
    setCharSimilarProducts("");
    setCharPartnerCode("");
    setCharOemNumber("");
    setCharCableLength("");
    setCharPower("");
    setCharMaterial("");
    setCharColor("");
    setCharWarrantyTerm("");
    setCharWarranty("");
    setCharCountry("");
    setCharComplectation("");
    setCharFactoryPackageCount("");
    charDictionaryKeyRef.current = "";
    setIsColorDropdownOpen(false);
    setIsTnvedDropdownOpen(false);
    setTnvedHoverText(null);
    setCharDictionaryOptions({ tnved: [], material: [], color: [], warranty: [], country: [] });
    setCharDictionaryIds({
      tnved: OZON_ATTRIBUTE_IDS.tnved[0],
      material: OZON_ATTRIBUTE_IDS.material[0],
      color: OZON_ATTRIBUTE_IDS.color[0],
      warranty: OZON_ATTRIBUTE_IDS.warranty[0],
      country: OZON_ATTRIBUTE_IDS.country[0],
    });
    setMediaProduct({
      id: -1,
      connection_id: effectiveSelectedConnectionId || 0,
      provider: "OZON",
      external_product_id: null,
      external_offer_id: null,
      external_sku: null,
      barcode: null,
      name: null,
      brand: null,
      category_name: null,
      status: null,
      payload: {},
      image_urls: [],
      video_urls: [],
      is_current: true,
      valid_from: new Date().toISOString(),
      valid_to: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }

  function normalizeUrlInput(value: string) {
    const candidate = value.trim();
    if (!candidate) return null;
    if (!candidate.startsWith("http://") && !candidate.startsWith("https://")) return null;
    return candidate;
  }

  function readFileAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          resolve(reader.result);
          return;
        }
        reject(new Error("Не удалось прочитать файл"));
      };
      reader.onerror = () => reject(new Error("Не удалось прочитать файл"));
      reader.readAsDataURL(file);
    });
  }

  async function filesToDataUrls(files: File[], kind: "image" | "video"): Promise<string[]> {
    const allowed = files.filter((file) => file.type.startsWith(`${kind}/`));
    if (!allowed.length) return [];
    const urls = await Promise.all(allowed.map((file) => readFileAsDataUrl(file)));
    return urls.filter((url) => url.startsWith(`data:${kind}/`));
  }

  async function addPhotoFiles(files: File[]) {
    try {
      const dataUrls = await filesToDataUrls(files, "image");
      if (!dataUrls.length) {
        setMediaError("Выберите изображения (JPG/PNG/WEBP/HEIC)");
        return;
      }
      setMediaDraftPhotos((prev) => [...prev, ...dataUrls.filter((url) => !prev.includes(url))]);
      setMediaDraftCover((prev) => prev || dataUrls[0] || "");
      setMediaError(null);
    } catch {
      setMediaError("Не удалось прочитать изображения");
    }
  }

  async function addVideoFiles(files: File[]) {
    try {
      const dataUrls = await filesToDataUrls(files, "video");
      if (!dataUrls.length) {
        setMediaError("Выберите видеофайл (MP4/MOV/WEBM)");
        return;
      }
      setMediaDraftVideos((prev) => [...prev, ...dataUrls.filter((url) => !prev.includes(url))]);
      setMediaError(null);
    } catch {
      setMediaError("Не удалось прочитать видео");
    }
  }

  async function setCoverFile(file: File | null) {
    if (!file) return;
    try {
      const urls = await filesToDataUrls([file], "image");
      if (!urls.length) {
        setMediaError("Для обложки нужен файл изображения");
        return;
      }
      const cover = urls[0];
      setMediaDraftCover(cover);
      setMediaDraftPhotos((prev) => (prev.includes(cover) ? prev : [cover, ...prev]));
      setMediaError(null);
    } catch {
      setMediaError("Не удалось прочитать файл обложки");
    }
  }

  function buildAttributesFromDynamicInputs(
    attrs: OzonAttribute[],
    inputValues: Record<number, string>,
    valuesById: Record<number, OzonAttributeValue[]>,
  ) {
    const result: Array<Record<string, unknown>> = [];
    for (const attr of attrs) {
      const raw = (inputValues[attr.id] || "").trim();
      if (!raw) continue;
      const tokens = attr.is_collection
        ? raw.split(/[;,]/g).map((item) => item.trim()).filter(Boolean)
        : [raw];
      if (!tokens.length) continue;
      const dictionary = valuesById[attr.id] || [];
      const values = tokens.map((token) => {
        const hit = dictionary.find((item) => item.value.toLowerCase() === token.toLowerCase());
        if (hit && hit.id > 0) {
          return { dictionary_value_id: hit.id, value: hit.value };
        }
        return { value: token };
      });
      result.push({
        id: attr.id,
        values,
      });
    }
    return result;
  }

  function updateOzonAttributeInput(attributeId: number, value: string) {
    setOzonAttributeInputValues((prev) => {
      const next = { ...prev, [attributeId]: value };
      const dynamic = buildAttributesFromDynamicInputs(ozonRequiredAttributes, next, ozonAttributeValuesById);
      if (dynamic.length) {
        setProductAttributesJson(JSON.stringify(dynamic, null, 2));
      }
      return next;
    });
  }

  async function loadOzonRequiredAttributes() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    const descriptionCategoryId = parsePositiveIntInput(productDescriptionCategoryId);
    const typeId = parsePositiveIntInput(productTypeId);
    if (descriptionCategoryId <= 0 || typeId <= 0) {
      setMediaError(
        `Укажите корректные description_category_id и type_id (числа). Сейчас: description_category_id="${productDescriptionCategoryId || "-"}", type_id="${productTypeId || "-"}".`,
      );
      return;
    }
    try {
      setIsLoadingOzonAttributes(true);
      setMediaError(null);
      const attrs = await getOzonAttributes(token, selectedTeamId, effectiveSelectedConnectionId, descriptionCategoryId, typeId);
      const required = attrs.filter((item) => item.is_required);
      setOzonRequiredAttributes(required);
      const valuePairs = await Promise.all(
        required
          .filter((item) => (item.dictionary_id || 0) > 0)
          .map(async (item) => [
            item.id,
            await getOzonAttributeValues(token, selectedTeamId, effectiveSelectedConnectionId, item.id, descriptionCategoryId, typeId, 30),
          ] as const),
      );
      const valuesMap = Object.fromEntries(valuePairs);
      setOzonAttributeValuesById(valuesMap);
      const dynamic = buildAttributesFromDynamicInputs(required, ozonAttributeInputValues, valuesMap);
      setProductAttributesJson(JSON.stringify(dynamic, null, 2));
      setMediaNotice(`Загружено обязательных атрибутов: ${required.length}`);
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Не удалось загрузить атрибуты категории Ozon");
    } finally {
      setIsLoadingOzonAttributes(false);
    }
  }

  function addPhotoUrl() {
    const normalized = normalizeUrlInput(mediaPhotoInput);
    if (!normalized) return;
    setMediaDraftPhotos((prev) => (prev.includes(normalized) ? prev : [...prev, normalized]));
    setMediaPhotoInput("");
  }

  function addVideoUrl() {
    const normalized = normalizeUrlInput(mediaVideoInput);
    if (!normalized) return;
    setMediaDraftVideos((prev) => (prev.includes(normalized) ? prev : [...prev, normalized]));
    setMediaVideoInput("");
  }

  function removePhotoUrl(url: string) {
    setMediaDraftPhotos((prev) => prev.filter((item) => item !== url));
    if (mediaDraftCover === url) {
      setMediaDraftCover("");
    }
  }

  function reorderPhoto(fromIndex: number, toIndex: number) {
    if (fromIndex === toIndex) return;
    let nextPhotos: string[] | null = null;
    setMediaDraftPhotos((prev) => {
      if (fromIndex < 0 || toIndex < 0 || fromIndex >= prev.length || toIndex >= prev.length) return prev;
      const next = [...prev];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      nextPhotos = next;
      return next;
    });
    setActivePhotoIndex((prev) => {
      if (prev === fromIndex) return toIndex;
      if (fromIndex < prev && toIndex >= prev) return prev - 1;
      if (fromIndex > prev && toIndex <= prev) return prev + 1;
      return prev;
    });
    setMediaNotice("Порядок фото обновлен. Первое фото будет главным на Ozon.");
    if (nextPhotos && productEditorMode !== "create") {
      schedulePhotoOrderAutosave(nextPhotos);
    }
  }

  function removeVideoUrl(url: string) {
    setMediaDraftVideos((prev) => prev.filter((item) => item !== url));
  }

  function schedulePhotoOrderAutosave(nextPhotos: string[]) {
    if (nextPhotos.some(isAiMediaDraftPlaceholder)) return;
    if (photoOrderAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(photoOrderAutosaveTimeoutRef.current);
    }
    photoOrderAutosaveTimeoutRef.current = window.setTimeout(async () => {
      if (!token || !selectedTeamId || !effectiveSelectedConnectionId || !mediaProduct) return;
      if (productEditorMode === "create") return;
      if (normalizeProvider(selectedConnection?.provider || "") !== "OZON") return;
      try {
        setMediaError(null);
        const result = await saveOzonProductMedia(token, selectedTeamId, effectiveSelectedConnectionId, mediaProduct.id, {
          image_urls: getSavablePhotoUrls(nextPhotos),
          video_urls: mediaDraftVideos,
          video_cover_url: mediaDraftCover || null,
        });
        setMediaNotice(`${result.message} (автосохранение порядка фото)`);
      } catch (err) {
        setMediaError(err instanceof Error ? err.message : "Не удалось автосохранить порядок фото");
      }
    }, 900);
  }

  async function onSaveMediaToOzon() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId || !mediaProduct) return;
    if (productEditorMode === "create") {
      setMediaError("Сначала сохраните новую позицию на вкладке «Параметры», затем медиа можно будет редактировать отдельно.");
      return;
    }
    if (mediaDraftPhotos.some(isAiMediaDraftPlaceholder)) {
      setMediaError("Дождитесь завершения AI draft перед сохранением медиа.");
      return;
    }
    try {
      setIsSavingMedia(true);
      setMediaError(null);
      setMediaNotice(null);
      const payload = {
        image_urls: getSavablePhotoUrls(),
        video_urls: mediaDraftVideos,
        video_cover_url: mediaDraftCover || null,
      };
      const result = await saveOzonProductMedia(token, selectedTeamId, effectiveSelectedConnectionId, mediaProduct.id, payload);
      setMediaNotice(result.message);
      const refreshed = await listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 200, true);
      setProducts(refreshed);
      const updated = refreshed.find((item) => item.id === mediaProduct.id) || null;
      if (updated) {
        setMediaProduct(updated);
        setMediaDraftPhotos(updated.image_urls || []);
        setMediaDraftVideos(updated.video_urls || []);
        setMediaDraftCover(updated.image_urls?.[0] || mediaDraftCover);
        clearSavedAiDraftAnnotations(updated.image_urls || []);
      }
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Не удалось сохранить медиа");
    } finally {
      setIsSavingMedia(false);
    }
  }

  async function onSaveProductToOzon() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    if (productEditorMode !== "create") {
      setMediaNotice("Редактирование параметров существующей карточки добавим следующим шагом. Сейчас доступно создание новой позиции.");
      return;
    }
    if (normalizeProvider(selectedConnection?.provider || "") !== "OZON") {
      setMediaError("Создание позиции через эту форму доступно только для Ozon.");
      return;
    }
    try {
      const descriptionCategoryId = parsePositiveIntInput(productDescriptionCategoryId);
      const typeId = parsePositiveIntInput(productTypeId);
      if (!productOfferId.trim() || !productName.trim()) {
        setMediaError("Заполните offer_id и название товара.");
        return;
      }
      if (descriptionCategoryId <= 0 || typeId <= 0) {
        setMediaError("Нужно указать корректные description_category_id и type_id.");
        return;
      }
      let attributes: Array<Record<string, unknown>> = [];
      let complexAttributes: Array<Record<string, unknown>> = [];
      try {
        const parsed = JSON.parse(productAttributesJson || "[]");
        attributes = Array.isArray(parsed) ? parsed : [];
      } catch {
        setMediaError("Поле attributes должно быть валидным JSON массивом.");
        return;
      }
      try {
        const parsed = JSON.parse(productComplexAttributesJson || "[]");
        complexAttributes = Array.isArray(parsed) ? parsed : [];
      } catch {
        setMediaError("Поле complex_attributes должно быть валидным JSON массивом.");
        return;
      }
      const upsertAttributeValue = (id: number, raw: string, isCollection = false) => {
        const normalized = raw.trim();
        if (!normalized) return;
        const values = isCollection
          ? normalized
              .split(/[;,]+/)
              .map((item) => item.trim())
              .filter(Boolean)
              .map((value) => ({ value }))
          : [{ value: normalized }];
        if (!values.length) return;
        const existingIndex = attributes.findIndex((row) => Number((row as Record<string, unknown>).id || 0) === id);
        if (existingIndex >= 0) {
          attributes[existingIndex] = { ...attributes[existingIndex], id, values };
          return;
        }
        attributes.push({ id, values });
      };

      upsertAttributeValue(OZON_ATTRIBUTE_IDS.brand[0], charBrand);
      upsertAttributeValue(OZON_ATTRIBUTE_IDS.modelName[0], charModelName);
      upsertAttributeValue(charDictionaryIds.tnved || OZON_ATTRIBUTE_IDS.tnved[0], charTnved);
      upsertAttributeValue(4497, charProductWeight);
      upsertAttributeValue(OZON_ATTRIBUTE_IDS.hashtags[0], charHashtags, true);
      upsertAttributeValue(OZON_ATTRIBUTE_IDS.partnerCode[0], charPartnerCode);
      upsertAttributeValue(charDictionaryIds.material || OZON_ATTRIBUTE_IDS.material[0], charMaterial, true);
      upsertAttributeValue(charDictionaryIds.color || OZON_ATTRIBUTE_IDS.color[0], charColor, true);
      upsertAttributeValue(OZON_ATTRIBUTE_IDS.warrantyTerm[0], charWarrantyTerm);
      upsertAttributeValue(charDictionaryIds.warranty || OZON_ATTRIBUTE_IDS.warranty[0], charWarranty);
      upsertAttributeValue(charDictionaryIds.country || OZON_ATTRIBUTE_IDS.country[0], charCountry, true);
      upsertAttributeValue(4404, charFactoryPackageCount);
      upsertAttributeValue(7434, charComplectation);
      upsertAttributeValue(7435, charSimilarProducts);
      upsertAttributeValue(4355, charQuantityUei);
      upsertAttributeValue(4384, charMinWholesaleQty);

      if (!attributes.length) {
        setMediaError("Заполните хотя бы обязательные характеристики Ozon.");
        return;
      }

      setIsSavingProduct(true);
      setMediaError(null);
      setMediaNotice(null);
      const result = await createOzonProduct(token, selectedTeamId, effectiveSelectedConnectionId, {
        offer_id: productOfferId.trim(),
        name: productName.trim(),
        description: productDescription.trim() || charAnnotation.trim() || null,
        description_category_id: descriptionCategoryId,
        type_id: typeId,
        barcode: productBarcode.trim() || null,
        image_urls: getSavablePhotoUrls(),
        video_urls: mediaDraftVideos,
        video_cover_url: mediaDraftCover || null,
        attributes,
        complex_attributes: complexAttributes,
        depth: parsePositiveIntInput(packageLength) || 100,
        width: parsePositiveIntInput(packageWidth) || 100,
        height: parsePositiveIntInput(packageHeight) || 100,
        weight: parsePositiveIntInput(packageWeight) || 100,
        price: productPrice.trim() || null,
        old_price: productOldPrice.trim() || null,
      });
      const errorCount = result.errors?.length || 0;
      setMediaNotice(`${result.message} ${result.task_id ? `task_id: ${result.task_id}.` : ""} ${errorCount ? `Ошибок валидации: ${errorCount}.` : ""}`);
      const refreshed = await listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 200, true);
      setProducts(refreshed);
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Не удалось создать позицию в Ozon");
    } finally {
      setIsSavingProduct(false);
    }
  }

  function buildAiCurrentFields() {
    return {
      offer_id: productOfferId,
      name: productName,
      description: productDescription,
      description_category_id: productDescriptionCategoryId,
      type_id: productTypeId,
      barcode: productBarcode,
      price: productPrice,
      old_price: productOldPrice,
      package_length: packageLength,
      package_width: packageWidth,
      package_height: packageHeight,
      package_weight: packageWeight,
      brand: charBrand,
      model_name: charModelName,
      tnved: charTnved,
      product_weight: charProductWeight,
      hashtags: charHashtags,
      annotation: charAnnotation,
      partner_code: charPartnerCode,
      material: charMaterial,
      color: charColor,
      warranty_term: charWarrantyTerm,
      warranty: charWarranty,
      country: charCountry,
      complectation: charComplectation,
      factory_package_count: charFactoryPackageCount,
    };
  }

  function normalizeAiFieldRecommendation(raw: Record<string, unknown>): AiFieldRecommendation {
    const rawAction = asString(raw.action).trim();
    const action: AiFieldAction = rawAction === "auto_apply" || rawAction === "skip" ? rawAction : "show_only";
    return {
      field: asString(raw.field).trim(),
      currentValue: asString(raw.currentValue ?? raw.current_value ?? ""),
      suggestedValue: asString(raw.suggestedValue ?? raw.suggested_value ?? ""),
      hasRecommendation: Boolean(raw.hasRecommendation ?? raw.has_recommendation ?? raw.suggestedValue ?? raw.suggested_value),
      confidence: Math.max(0, Math.min(1, asNumber(raw.confidence) ?? 0)),
      reason: asString(raw.reason),
      source: asString(raw.source || "ai"),
      action,
    };
  }

  function normalizeAiMediaRecommendation(raw: Record<string, unknown>): AiMediaRecommendation {
    const rawAction = asString(raw.action).trim();
    return {
      type: asString(raw.type),
      prompt: asString(raw.prompt),
      reason: asString(raw.reason),
      confidence: Math.max(0, Math.min(1, asNumber(raw.confidence) ?? 0)),
      action: rawAction === "generate" || rawAction === "skip" ? rawAction : "show_prompt_only",
    };
  }

  function getAiFieldValue(field: string) {
    return asString((buildAiCurrentFields() as Record<string, unknown>)[field] ?? "");
  }

  function setAiFieldValue(field: string, value: string) {
    const setters: Record<string, (next: string) => void> = {
      name: setProductName,
      description: setProductDescription,
      barcode: setProductBarcode,
      price: setProductPrice,
      old_price: setProductOldPrice,
      package_length: setPackageLength,
      package_width: setPackageWidth,
      package_height: setPackageHeight,
      package_weight: setPackageWeight,
      brand: setCharBrand,
      model_name: setCharModelName,
      tnved: setCharTnved,
      product_weight: setCharProductWeight,
      hashtags: setCharHashtags,
      annotation: setCharAnnotation,
      partner_code: setCharPartnerCode,
      material: setCharMaterial,
      color: setCharColor,
      warranty_term: setCharWarrantyTerm,
      warranty: setCharWarranty,
      country: setCharCountry,
      complectation: setCharComplectation,
      factory_package_count: setCharFactoryPackageCount,
    };
    setters[field]?.(value);
  }

  function applyAiRecommendationToField(rec: AiFieldRecommendation, options?: { markAccepted?: boolean }) {
    if (!rec.field || !rec.hasRecommendation || !rec.suggestedValue) return;
    const previousValue = getAiFieldValue(rec.field);
    setAiFieldValue(rec.field, rec.suggestedValue);
    setAiFieldStates((prev) => ({
      ...prev,
      [rec.field]: {
        previousValue,
        recommendation: rec,
        status: "ai_applied",
      },
    }));
    if (options?.markAccepted) {
      setMediaNotice(`AI-рекомендация применена: ${rec.field}`);
    }
  }

  function rollbackAiField(field: string) {
    const state = aiFieldStates[field];
    if (!state) return;
    setAiFieldValue(field, state.previousValue);
    setAiFieldStates((prev) => ({
      ...prev,
      [field]: {
        ...state,
        status: state.recommendation.confidence >= SHOW_SUGGESTION_CONFIDENCE_THRESHOLD ? "ai_suggestion" : "ai_low_confidence",
      },
    }));
    setMediaNotice(`Поле ${field} возвращено к старому значению.`);
  }

  function processAiRecommendations(result: AiCardDraftResult) {
    const sourceRecommendations = result.field_recommendations?.length
      ? result.field_recommendations
      : result.field_checks.map((row) => {
          const record = asRecord(row);
          return {
            field: record.field,
            currentValue: record.current_value,
            suggestedValue: record.suggested_value,
            hasRecommendation: Boolean(record.suggested_value),
            confidence: record.confidence,
            reason: record.reason,
            source: "field_check",
            action: "show_only",
          };
        });
    const normalized = sourceRecommendations.map((row) => normalizeAiFieldRecommendation(asRecord(row))).filter((row) => row.field);
    const nextStates: Record<string, AiFieldState> = {};
    normalized.forEach((rec) => {
      if (!rec.hasRecommendation) return;
      const currentValue = getAiFieldValue(rec.field);
      if (rec.confidence < SHOW_SUGGESTION_CONFIDENCE_THRESHOLD) {
        nextStates[rec.field] = { previousValue: currentValue, recommendation: rec, status: "ai_low_confidence" };
        return;
      }
      const shouldAutoApply = rec.action === "auto_apply" && rec.confidence >= AUTO_APPLY_CONFIDENCE_THRESHOLD && rec.suggestedValue;
      if (shouldAutoApply) {
        setAiFieldValue(rec.field, rec.suggestedValue);
        nextStates[rec.field] = { previousValue: currentValue, recommendation: rec, status: "ai_applied" };
        return;
      }
      nextStates[rec.field] = { previousValue: currentValue, recommendation: rec, status: "ai_suggestion" };
    });
    setAiFieldStates(nextStates);
    setAiMediaRecommendations((result.media_recommendations || []).map((row) => normalizeAiMediaRecommendation(asRecord(row))).filter((row) => row.type));
  }

  function aiFieldInputClass(field: string, baseClass: string) {
    const status = aiFieldStates[field]?.status;
    if (status === "ai_applied") return `${baseClass} border-orange-300 bg-orange-50/30 ring-2 ring-orange-100`;
    if (status === "ai_error") return `${baseClass} border-red-300 bg-red-50/30 ring-2 ring-red-100`;
    return baseClass;
  }

  function renderAiFieldHint(field: string) {
    const state = aiFieldStates[field];
    if (!state) return null;
    const rec = state.recommendation;
    const confidence = Math.round(rec.confidence * 100);
    const lowConfidence = state.status === "ai_low_confidence";
    if (lowConfidence) return null;
    return (
      <div className={`mt-1 rounded-lg border px-2 py-1.5 text-xs ${state.status === "ai_applied" ? "border-orange-200 bg-orange-50 text-orange-800" : "border-orange-100 bg-white text-orange-700"}`}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-orange-100 px-2 py-0.5 font-semibold text-orange-700">
            {state.status === "ai_applied" ? `Было: ${state.previousValue || "-"}` : "AI предлагает"}
          </span>
          <span className="font-semibold">{confidence}%</span>
          <span>Источник: {rec.source || "AI"}</span>
        </div>
        {state.status !== "ai_applied" ? <p className="mt-1 font-semibold">{rec.suggestedValue}</p> : null}
        <p className="mt-1 text-orange-700">{rec.reason || "Без пояснения"}</p>
        <div className="mt-1 flex flex-wrap gap-2">
          {state.status !== "ai_applied" ? (
            <button className="rounded bg-orange-100 px-2 py-0.5 font-semibold text-orange-700" onClick={() => applyAiRecommendationToField(rec, { markAccepted: true })} type="button">
              Применить
            </button>
          ) : (
            <button className="rounded bg-white px-2 py-0.5 font-semibold text-orange-700" onClick={() => rollbackAiField(field)} type="button">
              Откатить
            </button>
          )}
        </div>
      </div>
    );
  }

  async function onGenerateAiCardDraft(mode: "full" | "validate" = "full") {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId || !mediaProduct) return;
    if (productEditorMode === "create") {
      setMediaError("AI-заполнение сейчас доступно для уже загруженных карточек товара.");
      return;
    }
    if (!mediaDraftPhotos.length) {
      setMediaError("Для AI-анализа нужно хотя бы одно фото товара.");
      return;
    }
    try {
      setIsGeneratingAiDraft(true);
      setMediaError(null);
      setMediaNotice(null);
      const result = await createAiCardDraft(token, selectedTeamId, effectiveSelectedConnectionId, mediaProduct.id, {
        current_fields: buildAiCurrentFields(),
        image_urls: mediaDraftPhotos.slice(0, 5),
        template_id: "market-clean-01",
        user_prompt: aiPrompt.trim() || (mode === "validate" ? "Проверь заполненные параметры по фото и отметь конфликты." : null),
        reference: aiReferenceNote.trim() ? { note: aiReferenceNote.trim() } : {},
        goals: {
          improve_content_rating: true,
          generate_visual_cards: mode === "full",
          validate_only: mode === "validate",
        },
      });
      setAiDraftResult(result);
      processAiRecommendations(result);
      setMediaNotice(`AI-черновик готов. log #${result.log_id}, tokens: ${String(result.usage.total_tokens || 0)}.`);
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Не удалось создать AI-черновик");
    } finally {
      setIsGeneratingAiDraft(false);
    }
  }

  function applyAiDraftToForm() {
    const candidates = Object.values(aiFieldStates)
      .filter((state) => state.status === "ai_suggestion")
      .map((state) => state.recommendation)
      .filter((rec) => rec.hasRecommendation && rec.confidence >= AUTO_APPLY_CONFIDENCE_THRESHOLD && rec.suggestedValue && rec.action !== "skip");
    candidates.forEach((rec) => applyAiRecommendationToField(rec));
    setMediaNotice(candidates.length ? `Применено уверенных AI-рекомендаций: ${candidates.length}.` : "Нет дополнительных уверенных AI-рекомендаций для применения.");
  }

  function getAiMediaDraftForPhoto(url: string) {
    const placeholderLogId = getAiMediaDraftLogIdFromPhoto(url);
    if (placeholderLogId !== null) return aiMediaDrafts.find((draft) => draft.logId === placeholderLogId) || null;
    return aiMediaDrafts.find((draft) => draft.generatedImage === url) || null;
  }

  function getSavablePhotoUrls(photos = mediaDraftPhotos) {
    return photos.filter((url) => !isAiMediaDraftPlaceholder(url));
  }

  function clearSavedAiDraftAnnotations(savedUrls: string[]) {
    const saved = new Set(savedUrls);
    setAiMediaDrafts((prev) => prev.filter((draft) => !draft.generatedImage || !saved.has(draft.generatedImage)));
  }

  async function createAiMediaDraft() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId || !mediaProduct) {
      setMediaError("AI медиа генерация доступна для уже загруженной карточки товара.");
      return;
    }
    const sourceImage = mediaDraftPhotos[activePhotoIndex] || "";
    if (!sourceImage) {
      setMediaError("Выберите изображение для AI медиа драфта.");
      return;
    }
    if (isAiMediaDraftPlaceholder(sourceImage)) {
      setMediaError("Дождитесь завершения генерации draft или выберите исходное изображение.");
      return;
    }
    if (!aiMediaPrompt.trim()) {
      setMediaError("Введите промт для редактирования выбранного изображения.");
      return;
    }
    try {
      setIsGeneratingAiMediaImage(true);
      setMediaError(null);
      setMediaNotice("Генерируем изображение. Это может занять до 2-3 минут.");
      const result = await generateAiMediaImage(token, selectedTeamId, effectiveSelectedConnectionId, mediaProduct.id, {
        source_image_url: sourceImage,
        prompt: aiMediaPrompt.trim(),
        reference: aiMediaReferenceNote.trim() ? { note: aiMediaReferenceNote.trim() } : {},
        output_format: "png",
        size: "1024x1024",
      });
      const placeholderUrl = makeAiMediaDraftPlaceholder(result.log_id);
      setAiMediaDrafts((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${prev.length}`,
          sourceImage,
          generatedImage: result.image_url,
          prompt: result.revised_prompt || aiMediaPrompt.trim(),
          reference: aiMediaReferenceNote.trim(),
          createdAt: new Date().toISOString(),
          logId: result.log_id,
          model: result.model,
          status: result.status === "success" && result.image_url ? "generated" : "queued",
          progress: result.progress || 5,
        },
      ]);
      setMediaDraftPhotos((prev) => {
        const draftUrl = result.image_url || placeholderUrl;
        if (prev.includes(draftUrl)) return prev;
        setActivePhotoIndex(prev.length);
        return [...prev, draftUrl];
      });
      setMediaNotice(`AI генерация поставлена в очередь. log #${result.log_id}. Прогресс будет обновляться автоматически.`);
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Не удалось сгенерировать AI изображение");
    } finally {
      setIsGeneratingAiMediaImage(false);
    }
  }

  const providerHealth = useMemo(() => {
    const providers: ProviderKey[] = ["WB", "OZON", "YANDEX_MARKET"];
    const result: Record<ProviderKey, { hasKeys: boolean; dot: ProviderStatusDot }> = {
      WB: { hasKeys: false, dot: "none" },
      OZON: { hasKeys: false, dot: "none" },
      YANDEX_MARKET: { hasKeys: false, dot: "none" },
    };

    for (const provider of providers) {
      const rows = connections.filter((connection) => normalizeProvider(connection.provider) === provider);
      let hasKeys = false;
      let latestSuccessMs = 0;
      for (const connection of rows) {
        const credentials = credentialsByConnection[connection.id] || [];
        if (credentials.some((credential) => credential.is_active)) {
          hasKeys = true;
        }
        if (connection.last_success_at) {
          const timestamp = new Date(connection.last_success_at).getTime();
          if (Number.isFinite(timestamp) && timestamp > latestSuccessMs) {
            latestSuccessMs = timestamp;
          }
        }
      }

      if (!hasKeys) {
        result[provider] = { hasKeys: false, dot: "none" };
        continue;
      }
      if (!latestSuccessMs) {
        result[provider] = { hasKeys: true, dot: "red" };
        continue;
      }

      const ageHours = (nowMs - latestSuccessMs) / 3_600_000;
      if (ageHours <= 1) {
        result[provider] = { hasKeys: true, dot: "green" };
      } else if (ageHours <= 4) {
        result[provider] = { hasKeys: true, dot: "yellow" };
      } else {
        result[provider] = { hasKeys: true, dot: "red" };
      }
    }

    return result;
  }, [connections, credentialsByConnection, nowMs]);

  function onProviderButtonClick(provider: ProviderKey) {
    const health = providerHealth[provider];
    if (!selectedTeamId) return;
    if (!health.hasKeys) {
      router.push(`/teams/${selectedTeamId}/connections`);
      return;
    }
    setProviderFilter(provider);
    const scoped = connections.filter((row) => normalizeProvider(row.provider) === provider);
    const preferredId = pickPreferredConnectionId(scoped, credentialsByConnection);
    if (preferredId) {
      setSelectedConnectionId(preferredId);
    }
  }

  function dotClass(dot: ProviderStatusDot) {
    if (dot === "green") return "bg-emerald-500";
    if (dot === "yellow") return "bg-amber-400";
    if (dot === "red") return "bg-red-500";
    return "";
  }

  function renderStatusBadge(status: string | null) {
    const value = (status || "UNKNOWN").toUpperCase();
    const isActive = !value.includes("ARCHIVE") && !value.includes("DISABLE") && value !== "UNKNOWN";
    return (
      <span
        className={
          isActive
            ? "inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700"
            : "inline-flex rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600"
        }
      >
        {isActive ? "Готов к продаже" : value === "UNKNOWN" ? "Не определен" : "Отключен"}
      </span>
    );
  }

  async function onRunSync() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    try {
      setError(null);
      const result = await runConnectionSync(token, selectedTeamId, effectiveSelectedConnectionId, { dry_run: true, stage: "READY" });
      setMessage(`Sync job #${result.id} executed (${result.status})`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run sync");
    }
  }

  async function onRefreshMarketplace() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    try {
      setIsRefreshingMarketplace(true);
      setError(null);
      const result = await runConnectionSync(token, selectedTeamId, effectiveSelectedConnectionId, {
        dry_run: false,
        stage: "FORCE_REFRESH",
      });
      setMessage(`Обновление запущено: job #${result.id}`);
      const [rows, productRows] = await Promise.all([
        listTeamConnections(token, selectedTeamId),
        listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 60),
      ]);
      const credentialPairs = await Promise.all(
        rows.map(async (row) => [row.id, await listConnectionCredentials(token, selectedTeamId, row.id)] as const),
      );
      setConnections(rows);
      setCredentialsByConnection(Object.fromEntries(credentialPairs));
      setProducts(productRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh marketplace");
    } finally {
      setIsRefreshingMarketplace(false);
    }
  }

  async function onRefreshContentRating() {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    if (normalizeProvider(selectedConnection?.provider || "") !== "OZON") {
      setError("Контент-рейтинг доступен только для Ozon.");
      return;
    }
    try {
      setIsRefreshingContentRating(true);
      setError(null);
      const result = await refreshOzonContentRating(token, selectedTeamId, effectiveSelectedConnectionId, { limit: 300 });
      setMessage(
        result.updated_count > 0
          ? result.message
          : "Ozon не вернул рейтинг для выбранных SKU. Проверьте, что у товара есть корректный SKU в карточке.",
      );
      const refreshedProducts = await listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 300, true);
      setProducts(refreshedProducts);
      if (mediaProduct) {
        const updated = refreshedProducts.find((item) => item.id === mediaProduct.id);
        if (updated) {
          setMediaProduct(updated);
        } else {
          const ratingItem = result.items.find((item) => item.product_row_id === mediaProduct.id);
          if (ratingItem) {
            const payload = asRecord(mediaProduct.payload);
            setMediaProduct({
              ...mediaProduct,
              payload: {
                ...payload,
                content_rating: {
                  sku: ratingItem.sku,
                  rating: ratingItem.rating,
                  groups: ratingItem.groups,
                  fetched_at: ratingItem.fetched_at,
                },
              },
            });
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить контент-рейтинг");
    } finally {
      setIsRefreshingContentRating(false);
    }
  }

  useEffect(() => {
    if (!token || !selectedTeamId || !effectiveSelectedConnectionId) return;
    const intervalId = window.setInterval(() => {
      runConnectionSync(token, selectedTeamId, effectiveSelectedConnectionId, { dry_run: true, stage: "HEALTHCHECK_5M" })
        .then(async () => {
          const [rows, productRows] = await Promise.all([
            listTeamConnections(token, selectedTeamId),
            listConnectionProducts(token, selectedTeamId, effectiveSelectedConnectionId, 60),
          ]);
          const credentialPairs = await Promise.all(
            rows.map(async (row) => [row.id, await listConnectionCredentials(token, selectedTeamId, row.id)] as const),
          );
          setConnections(rows);
          setCredentialsByConnection(Object.fromEntries(credentialPairs));
          setProducts(productRows);
        })
        .catch(() => null);
    }, 300_000);

    return () => window.clearInterval(intervalId);
  }, [token, selectedTeamId, effectiveSelectedConnectionId]);

  async function onLogout() {
    if (!token) return;
    try {
      setIsLoggingOut(true);
      await logout(token);
    } catch {
      // ignore and clear local auth anyway
    } finally {
      clearAuth();
      router.push("/login");
      setIsLoggingOut(false);
    }
  }

  function renderContentRatingSidebar() {
    const rating = getContentRating(mediaProduct);
    const activeGroupKey = wizardTab === "info" ? "description" : wizardTab === "characteristics" ? "characteristics" : wizardTab === "media" ? "media" : "";
    const normalizeGroupKey = (rawKey: string, rawName: string) => {
      const key = rawKey.toLowerCase();
      const name = rawName.toLowerCase();
      if (key.includes("media") || name.includes("медиа")) return "media";
      if (key.includes("character") || name.includes("характер")) return "characteristics";
      if (key.includes("description") || name.includes("описан")) return "description";
      return key;
    };
    const groups = rating.groups.map((group) => {
      const row = asRecord(group);
      const key = normalizeGroupKey(asString(row.key), asString(row.name));
      const name = asString(row.name) || key || "Группа";
      const ratingValue = asNumber(row.rating) ?? 0;
      const weightValue = asNumber(row.weight) ?? 0;
      const improveAtLeast = asNumber(row.improve_at_least) ?? 0;
      const missingConditions = Array.isArray(row.missing_conditions)
        ? row.missing_conditions
            .map((item) => asRecord(item))
            .map((item) => asString(item.description || item.key))
            .filter(Boolean)
        : [];
      const improveAttributes = Array.isArray(row.improve_attributes)
        ? row.improve_attributes
            .map((item) => asRecord(item))
            .map((item) => asString(item.name))
            .filter(Boolean)
        : [];
      return { key, name, ratingValue, weightValue, improveAtLeast, missingConditions, improveAttributes };
    });
    const groupOrder: Record<string, number> = { media: 1, characteristics: 2, description: 3 };
    groups.sort((a, b) => (groupOrder[a.key] || 99) - (groupOrder[b.key] || 99));
    const activeGroup = groups.find((item) => item.key === activeGroupKey) || null;
    const badge = contentRatingBadge(rating.rating);
    const missingToBaseline = rating.rating === null ? null : Math.max(0, Number((45 - rating.rating).toFixed(1)));
    const ratingPercent = Math.max(0, Math.min(100, asNumber(rating.rating) ?? 0));
    const ringColor = ratingPercent >= 75 ? "#16a34a" : ratingPercent >= 45 ? "#f59e0b" : "#dc2626";
    const arcLength = Math.PI * 50;
    const arcProgress = Math.max(0, Math.min(arcLength, (arcLength * ratingPercent) / 100));
    const stepTips =
      wizardTab === "info"
        ? {
            title: "Отображение названия на Ozon",
            rows: [
              { title: "Что увидят покупатели", body: "В выдаче и карточке будет показано первое предложение названия и ключевые параметры товара." },
              { title: "Как подобрать название", body: "Добавьте тип товара, назначение и модель в первые 60-90 символов без лишних повторов." },
            ],
          }
        : wizardTab === "characteristics"
          ? {
              title: "Объединение товаров",
              rows: [
                { title: "Как это работает?", body: "Товары объединяются в одну карточку по совпадающим ключевым характеристикам и модели." },
                { title: "Какие поля нужно заполнить?", body: "Сначала заполните обязательные атрибуты, затем важные дополнительные параметры из справочников." },
              ],
            }
          : {
              title: "Медиа и порядок",
              rows: [
                { title: "Как улучшить фото", body: "Добавьте минимум 8 качественных фото: общий план, детали, комплектация и применение." },
                { title: "Как повысить балл за видео", body: "Загрузите короткое видео товара в использовании и добавьте релевантную видеообложку." },
              ],
            };

    return (
      <aside className="space-y-3">
        <div className="rounded-2xl border border-[var(--mp-line)] bg-slate-50 p-4">
          <p className="text-xs text-[var(--mp-muted)]">Контент-рейтинг</p>
          <div className="mt-1 flex items-center justify-between gap-3">
            <div>
              <p className="text-4xl font-bold leading-none">{rating.rating ?? "-"}</p>
              <span className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${badge.cls}`}>{badge.label}</span>
            </div>
            <div className="relative h-16 w-24">
              <svg className="h-16 w-24" viewBox="0 0 120 70">
                <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="#e5e7eb" strokeLinecap="round" strokeWidth="10" />
                <path
                  d="M10 60 A50 50 0 0 1 110 60"
                  fill="none"
                  stroke={ringColor}
                  strokeDasharray={`${arcProgress} ${arcLength}`}
                  strokeLinecap="round"
                  strokeWidth="10"
                />
              </svg>
              <div className="absolute left-1/2 top-8 -translate-x-1/2 rounded-full bg-white px-2 py-0.5 text-base font-semibold leading-none text-slate-800">
                {rating.rating === null ? "-" : Math.round(asNumber(rating.rating) ?? 0)}
              </div>
            </div>
          </div>
          <p className="mt-2 text-xs text-[var(--mp-muted)]">
            {rating.rating === null ? "Данные рейтинга ещё не загружены." : `${missingToBaseline} балла до базового`}
          </p>
          <button
            className="mt-3 w-full rounded-md border border-[var(--mp-line)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
            disabled={isRefreshingContentRating || normalizeProvider(selectedConnection?.provider || "") !== "OZON"}
            onClick={onRefreshContentRating}
            type="button"
          >
            {isRefreshingContentRating ? "Обновляем..." : "Обновить контент-рейтинг"}
          </button>
        </div>
        <div className="rounded-2xl border border-[var(--mp-line)] bg-white p-3">
          <div className="space-y-2">
            {groups.length ? (
              groups.map((group) => {
                const isActive = group.key === activeGroupKey;
                return (
                  <details className={`rounded-lg border ${isActive ? "border-orange-200 bg-orange-50" : "border-[var(--mp-line)] bg-slate-50"}`} key={`${group.key}-${group.name}`} open={isActive}>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-2 py-1.5 text-sm">
                    <span className={isActive ? "font-semibold text-slate-900" : "text-slate-700"}>{group.name}</span>
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-[var(--mp-muted)]">{group.ratingValue} из {group.weightValue}</span>
                  </summary>
                    <div className="border-t border-[var(--mp-line)] px-2 py-2 text-xs text-slate-700">
                      <p className="mb-1 font-semibold">Не хватает минимум: {group.improveAtLeast || 0}</p>
                      <ul className="list-disc space-y-1 pl-4">
                        {group.improveAttributes.map((name, idx) => (
                          <li key={`imp-${group.key}-${idx}`}>{name}</li>
                        ))}
                        {group.missingConditions.map((name, idx) => (
                          <li key={`cond-${group.key}-${idx}`}>{name}</li>
                        ))}
                        {!group.improveAttributes.length && !group.missingConditions.length ? <li>Проблем не найдено.</li> : null}
                      </ul>
                    </div>
                  </details>
                );
              })
            ) : (
              <p className="text-xs text-[var(--mp-muted)]">Группы рейтинга появятся после обновления.</p>
            )}
          </div>
          {activeGroup ? (
            <div className="mt-3 max-h-48 overflow-auto rounded-lg border border-[var(--mp-line)] bg-slate-50 p-2">
              <p className="text-xs font-semibold">Чего не хватает в блоке «{activeGroup.name}»</p>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-700">
                {activeGroup.improveAttributes.map((name, idx) => (
                  <li key={`imp-${idx}`}>{name}</li>
                ))}
                {activeGroup.missingConditions.map((name, idx) => (
                  <li key={`cond-${idx}`}>{name}</li>
                ))}
                {!activeGroup.improveAttributes.length && !activeGroup.missingConditions.length ? <li>Проблем не найдено.</li> : null}
              </ul>
            </div>
          ) : null}
        </div>
        <div className="rounded-2xl border border-[var(--mp-line)] bg-white p-3">
          <p className="text-lg font-semibold">{stepTips.title}</p>
          <div className="mt-2 divide-y divide-[var(--mp-line)]">
            {stepTips.rows.map((row, idx) => (
              <details className="group py-1.5" key={row.title} open={idx === 0}>
                <summary className="flex cursor-pointer list-none items-center justify-between text-left text-sm text-slate-700 hover:text-slate-900">
                  <span>{row.title}</span>
                  <ChevronDown className="h-4 w-4 text-slate-500 transition group-open:rotate-180" />
                </summary>
                <p className="mt-1 text-xs text-[var(--mp-muted)]">{row.body}</p>
              </details>
            ))}
          </div>
        </div>
      </aside>
    );
  }

  if (!isReady || !token) {
    return (
      <main className="mp-shell min-h-screen flex items-center justify-center">
        <section className="mp-card p-6 text-sm">Loading dashboard...</section>
      </main>
    );
  }

  const accountMenuEmail = user?.email || user?.phone || "Аккаунт";
  const accountMenuItems = [
    { label: "Аккаунт", href: "/profile", icon: UserRound },
    { label: "Моя подписка", href: "/profile?tab=subscription", icon: CreditCard, alert: true },
    { label: "Счета", href: "/profile", icon: ReceiptText },
    { label: "Тарифы", href: "/profile", icon: FileText, badge: "Обновили" },
    { label: "Подключения", href: selectedTeamId ? `/teams/${selectedTeamId}/connections` : "/teams", icon: Plug },
    { label: "Команда и доступы", href: selectedTeamId ? `/teams/${selectedTeamId}/members` : "/teams", icon: UsersRound },
    { label: "Партнерская программа", href: "/profile", icon: Handshake },
    { label: "Предложить идею", href: "/profile", icon: Lightbulb },
  ];

  return (
    <main className="mp-shell mp-shell-wide space-y-5">
      <div className="sticky top-0 z-40 bg-[var(--mp-background)]/95 pb-1 pt-1 backdrop-blur">
        <header className="mp-card p-4" data-code-ref="frontend/src/app/dashboard/page.tsx:172">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">Основной дашборд</h1>
              <p className="text-sm text-[var(--mp-muted)]">Сводка по продажам, рекомендации и быстрые действия.</p>
            </div>
            <div
              className="min-w-0 flex flex-1 items-center justify-end overflow-x-auto"
              data-code-ref="frontend/src/app/dashboard/page.tsx:236"
            >
              <div className="flex items-center gap-2 whitespace-nowrap">
                {teams.length ? (
                  <div className="w-[220px] flex-shrink-0">
                    <select
                      className="mp-input h-10 py-1.5 text-sm"
                      value={selectedTeamId ?? ""}
                      onChange={(event) => setSelectedTeamId(Number(event.target.value))}
                    >
                      {teams.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}
                <div className="min-w-0">
                  <div className="flex items-center gap-2 whitespace-nowrap">
                    <div className="inline-flex items-center gap-2 rounded-xl border border-[var(--mp-line)] bg-white p-1.5">
                      {(
                        [
                          { key: "WB", title: "WB", src: "/icons/wb.webp", alt: "WB" },
                          { key: "OZON", title: "Ozon", src: "/icons/ozon.webp", alt: "Ozon" },
                          { key: "YANDEX_MARKET", title: "Yandex", src: "/icons/yandex.webp", alt: "Yandex Market" },
                        ] as const
                      ).map((item) => {
                        const health = providerHealth[item.key];
                        const isActive = providerFilter === item.key;
                        return (
                          <button
                            className={`relative inline-flex h-10 min-w-[58px] items-center justify-center rounded-lg border px-3 text-sm font-semibold transition ${
                              !health.hasKeys
                                ? "border-[var(--mp-line)] bg-slate-100 text-slate-400"
                                : isActive
                                  ? "border-2 border-[var(--mp-orange)] bg-white text-slate-800 shadow-[0_0_0_1px_rgba(223,114,32,0.12)]"
                                  : "border-[var(--mp-line)] bg-white text-slate-600 hover:bg-slate-50"
                            }`}
                            key={item.key}
                            onClick={() => onProviderButtonClick(item.key)}
                            title={health.hasKeys ? item.title : `${item.title}: настройте ключи`}
                            type="button"
                          >
                            <Image alt={item.alt} className="rounded-md" height={34} src={item.src} width={34} />
                            {health.hasKeys ? (
                              <span className={`absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-white ${dotClass(health.dot)}`} />
                            ) : null}
                          </button>
                        );
                      })}
                      <span className="h-7 w-px bg-[var(--mp-line)]" />
                      <Link
                        aria-label="Редактировать подключения"
                        className="inline-flex h-10 min-w-[48px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-3 text-slate-600 transition hover:bg-slate-50"
                        href={selectedTeamId ? `/teams/${selectedTeamId}/connections` : "/teams"}
                        title="Редактировать подключения"
                      >
                        <Settings size={24} strokeWidth={1.9} />
                      </Link>
                      <button
                        aria-label="Обновить данные"
                        className="inline-flex h-10 min-w-[48px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-3 text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                        disabled={!effectiveSelectedConnectionId || isRefreshingMarketplace}
                        onClick={onRefreshMarketplace}
                        title="Принудительно обновить данные с маркетплейса"
                        type="button"
                      >
                        <RefreshCw className={isRefreshingMarketplace ? "h-5 w-5 animate-spin" : "h-5 w-5"} />
                      </button>
                      <button
                        aria-label="Обновить контент-рейтинг"
                        className="inline-flex h-10 min-w-[48px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-3 text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                        disabled={!effectiveSelectedConnectionId || normalizeProvider(selectedConnection?.provider || "") !== "OZON" || isRefreshingContentRating}
                        onClick={onRefreshContentRating}
                        title="Обновить контент-рейтинг Ozon"
                        type="button"
                      >
                        <BarChart3 className={isRefreshingContentRating ? "h-5 w-5 animate-pulse" : "h-5 w-5"} />
                      </button>
                    </div>

                    <button
                      className={`inline-flex h-10 min-w-[58px] items-center justify-center whitespace-nowrap rounded-lg border px-3 text-sm font-semibold ${
                        providerFilter === "ALL" ? "border-orange-300 bg-orange-100 text-orange-700" : "border-[var(--mp-line)] bg-white text-slate-600"
                      }`}
                      onClick={() => setProviderFilter("ALL")}
                      type="button"
                    >
                      Все
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link className="inline-flex h-10 min-w-[58px] items-center justify-center rounded-lg bg-[var(--mp-orange)] px-3 text-sm font-semibold text-white" href={selectedTeamId ? `/teams/${selectedTeamId}/agent` : "/teams"}>
                AI
              </Link>
              <a
                aria-label="Telegram"
                className="inline-flex h-10 min-w-[58px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-3 text-[#1f3a73] transition hover:bg-slate-50"
                href="https://t.me/wozym"
                rel="noreferrer"
                target="_blank"
                title="Telegram"
              >
                <Send size={24} strokeWidth={1.9} />
              </a>
              <a
                aria-label="MAX"
                className="inline-flex h-10 min-w-[58px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-3 transition hover:bg-slate-50"
                href="https://max.ru/"
                rel="noreferrer"
                target="_blank"
                title="MAX"
              >
                <Image alt="MAX" height={28} src="/icons/max-logo.svg" width={28} />
              </a>
              <button
                aria-label="Приложения"
                className="inline-flex h-10 min-w-[44px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-2 text-slate-500 transition hover:bg-slate-50"
                title="Приложения"
                type="button"
              >
                <Grid3X3 size={20} strokeWidth={1.9} />
              </button>
              <button
                aria-label="Уведомления"
                className="relative inline-flex h-10 min-w-[44px] items-center justify-center rounded-lg border border-[var(--mp-line)] bg-white px-2 text-slate-500 transition hover:bg-slate-50"
                title="Уведомления"
                type="button"
              >
                <Bell size={20} strokeWidth={1.9} />
                <span className="absolute right-1.5 top-1.5 h-2.5 w-2.5 rounded-full border border-white bg-emerald-400" />
              </button>
              <div className="relative" ref={accountMenuRef}>
                <button
                  aria-expanded={isAccountMenuOpen}
                  aria-label="Личный кабинет"
                  className={`relative inline-flex h-10 min-w-[48px] items-center justify-center rounded-lg border px-3 text-[#1f3a73] transition ${
                    isAccountMenuOpen ? "border-orange-200 bg-orange-50" : "border-[var(--mp-line)] bg-white hover:bg-slate-50"
                  }`}
                  onClick={() => setIsAccountMenuOpen((prev) => !prev)}
                  title="Личный кабинет"
                  type="button"
                >
                  <UserRound size={24} strokeWidth={1.9} />
                  <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-white bg-red-600 px-1 text-[10px] font-bold leading-none text-white">
                    1
                  </span>
                </button>
                {isAccountMenuOpen ? (
                  <div className="absolute right-0 top-12 z-50 w-[292px] overflow-hidden rounded-xl border border-slate-200 bg-white text-sm shadow-[0_18px_45px_rgba(15,23,42,0.18)]">
                    <div className="relative overflow-hidden bg-gradient-to-br from-[#ff7a1a] via-[#f04f12] to-[#b91c1c] px-4 py-4 text-white">
                      <div className="absolute -left-8 -top-10 h-28 w-28 rounded-full bg-yellow-300/35 blur-xl" />
                      <div className="absolute -bottom-10 right-8 h-24 w-24 rounded-full bg-orange-200/35 blur-xl" />
                      <div className="relative z-10 max-w-[178px]">
                        <p className="text-[15px] font-extrabold leading-tight">Откройте все возможности системы с AI</p>
                        <p className="mt-1 text-xs font-semibold text-orange-50">Анализ карточек, фото и рекомендации в один клик</p>
                      </div>
                      <div className="absolute bottom-3 right-4 h-16 w-16 rotate-12 rounded-3xl bg-white/95 shadow-[0_12px_28px_rgba(124,45,18,0.32)]">
                        <div className="absolute left-3 top-3 h-10 w-10 rounded-2xl bg-gradient-to-br from-orange-300 to-yellow-200" />
                        <div className="absolute left-5 top-5 h-6 w-6 rounded-full bg-orange-600/90" />
                        <div className="absolute left-7 top-1 h-2 w-2 rounded-full bg-white" />
                        <div className="absolute right-2 top-6 h-2 w-2 rounded-full bg-yellow-400" />
                      </div>
                      <div className="absolute bottom-4 right-16 flex h-12 w-12 -rotate-12 items-center justify-center rounded-2xl border-2 border-white/80 bg-orange-900/25 shadow-lg">
                        <span className="text-lg font-black tracking-tight">AI</span>
                      </div>
                      <Building2 className="absolute right-5 top-4 h-7 w-7 rotate-12 text-white/40" strokeWidth={1.8} />
                    </div>
                    <div className="py-2">
                      {accountMenuItems.map((item) => {
                        const Icon = item.icon;
                        return (
                          <Link
                            className="flex h-9 items-center gap-3 px-3 text-slate-700 transition hover:bg-slate-50"
                            href={item.href}
                            key={item.label}
                            onClick={() => setIsAccountMenuOpen(false)}
                          >
                            <Icon className="h-4 w-4 text-slate-500" strokeWidth={1.8} />
                            <span className="min-w-0 flex-1 truncate">{item.label}</span>
                            {item.label === "Аккаунт" ? <span className="max-w-[120px] truncate text-xs text-slate-500">{accountMenuEmail}</span> : null}
                            {item.alert ? <span className="h-2 w-2 rounded-full bg-red-600" /> : null}
                            {item.badge ? <span className="rounded-full bg-pink-600 px-2 py-0.5 text-[11px] font-bold text-white">{item.badge}</span> : null}
                          </Link>
                        );
                      })}
                    </div>
                    <div className="border-t border-slate-200">
                      <button
                        className="flex h-10 w-full items-center gap-3 px-3 text-left text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                        disabled={isLoggingOut}
                        onClick={() => {
                          setIsAccountMenuOpen(false);
                          void onLogout();
                        }}
                        type="button"
                      >
                        <LogOut className="h-4 w-4 text-slate-500" strokeWidth={1.8} />
                        <span>Выйти</span>
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

        </header>
      </div>

      {!selectedConnection ? (
        <section className="mp-card p-5 border-orange-200 bg-orange-50" data-code-ref="frontend/src/app/dashboard/page.tsx:315">
          <h2 className="font-bold">Подключение не выбрано</h2>
          <p className="mt-1 text-sm text-[var(--mp-muted)]">Добавьте и выберите подключение для отображения отчетов и рекомендаций.</p>
        </section>
      ) : null}

      <div data-code-ref="frontend/src/components/analytics-main-chart.tsx:1">
        <AnalyticsMainChart ordersTotal={dashboard?.orders_total ?? 0} revenueTotal={dashboard?.revenue_total ?? 0} />
      </div>

      <section>
        <article className="mp-card p-5" data-code-ref="frontend/src/app/dashboard/page.tsx:324">
          <h2 className="font-bold">Сводка</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-[var(--mp-line)] p-3">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Товаров</p>
              <p className="mt-1 text-2xl font-bold">{dashboard?.products_total ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[var(--mp-line)] p-3">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Заказы</p>
              <p className="mt-1 text-2xl font-bold">{dashboard?.orders_total ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[var(--mp-line)] p-3">
              <p className="text-xs uppercase tracking-wide text-[var(--mp-muted)]">Выручка</p>
              <p className="mt-1 text-2xl font-bold">{dashboard?.revenue_total ?? 0} ₽</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="mp-btn-primary" disabled={!selectedConnection} onClick={onRunSync} type="button">
              Dry-run sync
            </button>
            <Link
              className="mp-btn-secondary"
              href={selectedTeamId && effectiveSelectedConnectionId ? `/teams/${selectedTeamId}/connections/${effectiveSelectedConnectionId}/access` : "/teams"}
            >
              Доступы к подключению
            </Link>
          </div>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <article className="mp-card p-5">
          <h2 className="font-bold">Товары выбранного маркетплейса</h2>
          <div className="mt-3 rounded-lg border border-[var(--mp-line)]">
            <div className="grid gap-2 border-b border-[var(--mp-line)] p-2.5 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-center">
              <div className="relative min-w-0">
                <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--mp-muted)]" />
                <input
                  className="h-9 w-full rounded-md border border-[var(--mp-line)] bg-white pl-8 pr-3 text-xs outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                  onChange={(event) => setProductSearch(event.target.value)}
                  placeholder="Название, артикул, SKU, штрихкод"
                  value={productSearch}
                />
              </div>
              <div className="min-w-0">
                <select
                  className="h-9 w-full rounded-md border border-[var(--mp-line)] bg-white px-3 text-xs outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200 md:min-w-[220px]"
                  onChange={(event) => setProductStatusFilter(event.target.value as ProductStatusFilter)}
                  value={productStatusFilter}
                >
                  <option value="ALL">Все статусы</option>
                  <option value="ACTIVE">Готов к продаже</option>
                  <option value="ARCHIVED">Отключен/архив</option>
                  <option value="UNKNOWN">Не определен</option>
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 text-xs text-[var(--mp-muted)] md:whitespace-nowrap">
                <span>Показано: {filteredProducts.length}</span>
                <button
                  className="rounded-md border border-[var(--mp-line)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  onClick={openCreateProductModal}
                  type="button"
                >
                  Добавить позицию
                </button>
              </div>
            </div>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full table-fixed text-xs">
                <colgroup>
                  <col style={{ width: "5%" }} />
                  <col style={{ width: "10%" }} />
                  <col style={{ width: "16%" }} />
                  <col style={{ width: "9%" }} />
                  <col style={{ width: "8%" }} />
                  <col style={{ width: "9%" }} />
                  <col style={{ width: "9%" }} />
                  <col style={{ width: "7%" }} />
                  <col style={{ width: "12%" }} />
                  <col style={{ width: "9%" }} />
                  <col style={{ width: "10%" }} />
                </colgroup>
                <thead className="sticky top-0 z-10 bg-[#f7f9fc] text-[11px] font-semibold text-slate-600">
                  <tr>
                    <th className="px-3 py-2 text-left">Фото</th>
                    <th className="px-3 py-2 text-left">Артикул</th>
                    <th className="px-3 py-2 text-left">Название товара</th>
                    <th className="px-3 py-2 text-left">Статус</th>
                    <th className="px-3 py-2 text-left">Бренд</th>
                    <th className="px-3 py-2 text-left">Категория</th>
                    <th className="px-3 py-2 text-left">Штрихкод</th>
                    <th className="px-3 py-2 text-right">Фото/Видео</th>
                    <th className="px-3 py-2 text-left">Обновлено</th>
                    <th className="px-3 py-2 text-left">Контент-рейтинг</th>
                    <th className="px-3 py-2 text-center">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((item) => (
                    <tr className="border-t border-[var(--mp-line)] align-top" key={item.id}>
                      <td className="px-3 py-2">
                        <button
                          className="block"
                          onClick={() => openMediaModal(item)}
                          title="Открыть медиа"
                          type="button"
                        >
                          {item.image_urls[0] ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              alt={item.name || "Товар"}
                              className="h-12 w-12 rounded-md border border-[var(--mp-line)] object-cover transition hover:opacity-85"
                              src={item.image_urls[0]}
                            />
                          ) : (
                            <div className="flex h-12 w-12 items-center justify-center rounded-md border border-dashed border-[var(--mp-line)] text-[10px] text-[var(--mp-muted)]">
                              нет
                            </div>
                          )}
                        </button>
                      </td>
                      <td className="px-3 py-2">
                        <p className="font-semibold text-slate-800">{item.external_offer_id || item.external_sku || "-"}</p>
                        <p className="mt-0.5 truncate text-[11px] text-[var(--mp-muted)]">SKU {item.external_sku || item.external_product_id || "-"}</p>
                      </td>
                      <td className="px-3 py-2">
                        <p className="truncate font-semibold text-slate-900">{item.name || `Товар #${item.id}`}</p>
                      </td>
                      <td className="px-3 py-2">{renderStatusBadge(item.status)}</td>
                      <td className="px-3 py-2 text-slate-700">{item.brand ? <span className="block truncate">{item.brand}</span> : "-"}</td>
                      <td className="px-3 py-2 text-slate-700">{item.category_name ? <span className="block truncate">{item.category_name}</span> : "-"}</td>
                      <td className="px-3 py-2 text-slate-700">{item.barcode ? <span className="block truncate">{item.barcode}</span> : "-"}</td>
                      <td className="px-3 py-2 text-right font-medium text-slate-700">
                        {item.image_urls.length} / {item.video_urls.length}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        <span className="block truncate">{new Date(item.updated_at).toLocaleString("ru-RU")}</span>
                      </td>
                      <td className="px-3 py-2">
                        {(() => {
                          const rating = getContentRating(item).rating;
                          const numeric = rating === null ? null : Math.max(0, Math.min(100, rating));
                          const barColor = contentRatingBarColor(rating);
                          return (
                            <div className="space-y-1">
                              <p className="text-xs font-semibold text-slate-800">{numeric === null ? "-" : `${numeric.toFixed(1)}`}</p>
                              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${numeric ?? 0}%`,
                                    backgroundColor: barColor,
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center justify-center gap-1 text-[var(--mp-indigo)]">
                          <button
                            className="flex h-7 w-7 items-center justify-center rounded border border-orange-200 bg-orange-50 text-[10px] font-bold text-orange-700 hover:bg-orange-100"
                            onClick={() => openMediaModal(item, "ai")}
                            title="AI-заполнение карточки"
                            type="button"
                          >
                            AI
                          </button>
                          <button
                            className="flex h-7 w-7 items-center justify-center rounded border border-orange-200 bg-white text-[10px] font-bold text-orange-700 hover:bg-orange-50"
                            onClick={() => openMediaModal(item, "ai_media")}
                            title="AI медиа редактор"
                            type="button"
                          >
                            IMG
                          </button>
                          <button className="rounded p-1 hover:bg-slate-100" title="Статистика" type="button">
                            <BarChart3 className="h-3.5 w-3.5" />
                          </button>
                          <button className="rounded p-1 hover:bg-slate-100" onClick={() => openMediaModal(item)} title="Редактировать" type="button">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button className="rounded p-1 hover:bg-slate-100" title="Ещё" type="button">
                            <MoreVertical className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!products.length ? <p className="p-3 text-sm text-[var(--mp-muted)]">Товары пока не загружены для выбранного подключения.</p> : null}
            {products.length > 0 && !filteredProducts.length ? (
              <p className="p-3 text-sm text-[var(--mp-muted)]">По фильтру ничего не найдено.</p>
            ) : null}
          </div>
          {message ? <p className="mt-2 text-sm text-green-700">{message}</p> : null}
          {error ? <p className="mt-2 mp-error">{error}</p> : null}
        </article>

        <article className="mp-card p-5" data-code-ref="frontend/src/app/dashboard/page.tsx:386">
          <h2 className="font-bold">Рекомендации</h2>
          <div className="mt-3 space-y-3">
            {(dashboard?.recommendations ?? []).map((item) => (
              <div className="rounded-lg border border-[var(--mp-line)] p-3" key={item.id}>
                <p className="font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-[var(--mp-muted)]">{item.body}</p>
                {item.cta_label ? (
                  <div className="mt-2">
                    <a className="text-sm font-semibold text-[var(--mp-orange)] underline underline-offset-2" href={item.cta_href || "#"}>
                      {item.cta_label}
                    </a>
                  </div>
                ) : null}
              </div>
            ))}
            {!dashboard?.recommendations?.length ? <p className="text-sm text-[var(--mp-muted)]">Рекомендации пока не настроены.</p> : null}
          </div>
        </article>
      </section>

      {mediaProduct ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/45 p-4">
          <div className="flex max-h-[calc(100vh-2rem)] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="shrink-0 border-b border-[var(--mp-line)] px-6 py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-3xl font-bold leading-none">{productEditorMode === "create" ? "Добавление позиции" : "Редактирование позиции"}</h3>
                  <p className="mt-2 text-sm text-[var(--mp-muted)]">{mediaProduct.name || mediaProduct.external_offer_id || "Товар"}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
                      productEditorEntryMode === "ai"
                        ? "border-orange-200 bg-orange-50 text-orange-700"
                        : "border-[var(--mp-line)] bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => setProductEditorEntryMode((prev) => (prev === "ai" ? "edit" : "ai"))}
                    type="button"
                  >
                    AI режим
                  </button>
                  <button
                    className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
                      productEditorEntryMode === "ai_media"
                        ? "border-orange-200 bg-orange-50 text-orange-700"
                        : "border-[var(--mp-line)] bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => {
                      setProductEditorEntryMode((prev) => (prev === "ai_media" ? "edit" : "ai_media"));
                      setWizardTab("media");
                      setMediaTab("photo");
                    }}
                    type="button"
                  >
                    AI медиа
                  </button>
                  <button
                    className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                    onClick={() => setMediaProduct(null)}
                    title="Закрыть"
                    type="button"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
                <button
                  className={wizardTab === "info" ? "inline-flex items-center gap-2 rounded-full bg-black px-3 py-1 text-white" : "inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-slate-500"}
                  onClick={() => setWizardTab("info")}
                  type="button"
                >
                  <span className="text-xs">1</span> Информация о товаре
                </button>
                <button
                  className={wizardTab === "characteristics" ? "inline-flex items-center gap-2 rounded-full bg-black px-3 py-1 text-white" : "inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-slate-500"}
                  onClick={() => setWizardTab("characteristics")}
                  type="button"
                >
                  <span className="text-xs">2</span> Характеристики
                </button>
                <button
                  className={wizardTab === "media" ? "inline-flex items-center gap-2 rounded-full bg-black px-3 py-1 text-white" : "inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-slate-500"}
                  onClick={() => setWizardTab("media")}
                  type="button"
                >
                  <span className="text-xs">3</span> Медиа
                </button>
                <button
                  className={wizardTab === "preview" ? "inline-flex items-center gap-2 rounded-full bg-black px-3 py-1 text-white" : "inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-slate-500"}
                  onClick={() => setWizardTab("preview")}
                  type="button"
                >
                  <span className="text-xs">4</span> Предварительный просмотр
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              {wizardTab === "info" ? (
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                  <div className="space-y-5">
                  <h4 className="text-2xl font-semibold">Информация о товаре</h4>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">Название *</label>
                    <input
                      className={aiFieldInputClass("name", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                      onChange={(event) => setProductName(event.target.value)}
                      placeholder="Введите название товара"
                      value={productName}
                    />
                    {renderAiFieldHint("name")}
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">Категория и тип *</label>
                    <div className="grid gap-3 md:grid-cols-2">
                      <input
                        className="h-11 rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                        onChange={(event) => setProductDescriptionCategoryId(event.target.value)}
                        placeholder="description_category_id"
                        value={productDescriptionCategoryId}
                      />
                      <input
                        className="h-11 rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                        onChange={(event) => setProductTypeId(event.target.value)}
                        placeholder="type_id"
                        value={productTypeId}
                      />
                    </div>
                    <p className="mt-1 text-xs text-[var(--mp-muted)]">Поля заполняются из Ozon. Используются для загрузки обязательных характеристик.</p>
                  </div>
                  <div className="rounded-lg border border-[var(--mp-line)] bg-slate-50 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button className="mp-btn-secondary" disabled={isLoadingOzonAttributes} onClick={loadOzonRequiredAttributes} type="button">
                        {isLoadingOzonAttributes ? "Загружаем..." : "Загрузить обязательные характеристики Ozon"}
                      </button>
                      <span className="text-xs text-[var(--mp-muted)]">по description_category_id + type_id</span>
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Штрихкод</label>
                      <input
                        className={aiFieldInputClass("barcode", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                        onChange={(event) => setProductBarcode(event.target.value)}
                        placeholder="Введите штрихкод"
                        value={productBarcode}
                      />
                      {renderAiFieldHint("barcode")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Артикул *</label>
                      <input
                        className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                        onChange={(event) => setProductOfferId(event.target.value)}
                        placeholder="Введите артикул"
                        value={productOfferId}
                      />
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Ваша цена, ₽ *</label>
                      <input
                        className={aiFieldInputClass("price", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                        onChange={(event) => setProductPrice(event.target.value)}
                        placeholder="Например 550"
                        value={productPrice}
                      />
                      {renderAiFieldHint("price")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Старая цена, ₽</label>
                      <input
                        className={aiFieldInputClass("old_price", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                        onChange={(event) => setProductOldPrice(event.target.value)}
                        placeholder="Опционально"
                        value={productOldPrice}
                      />
                      {renderAiFieldHint("old_price")}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <h5 className="text-xl font-semibold">Габариты и вес</h5>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <label className="mb-1 block text-xs text-[var(--mp-muted)]">Длина упаковки, мм *</label>
                        <input
                          className={aiFieldInputClass("package_length", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                          onChange={(event) => setPackageLength(event.target.value)}
                          placeholder="Например 150"
                          value={packageLength}
                        />
                        {renderAiFieldHint("package_length")}
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-[var(--mp-muted)]">Ширина упаковки, мм *</label>
                        <input
                          className={aiFieldInputClass("package_width", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                          onChange={(event) => setPackageWidth(event.target.value)}
                          placeholder="Например 90"
                          value={packageWidth}
                        />
                        {renderAiFieldHint("package_width")}
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-[var(--mp-muted)]">Высота упаковки, мм *</label>
                        <input
                          className={aiFieldInputClass("package_height", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                          onChange={(event) => setPackageHeight(event.target.value)}
                          placeholder="Например 80"
                          value={packageHeight}
                        />
                        {renderAiFieldHint("package_height")}
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-[var(--mp-muted)]">Вес в упаковке, г *</label>
                        <input
                          className={aiFieldInputClass("package_weight", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                          onChange={(event) => setPackageWeight(event.target.value)}
                          placeholder="Например 100"
                          value={packageWeight}
                        />
                        {renderAiFieldHint("package_weight")}
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">Описание</label>
                    <textarea
                      className={aiFieldInputClass("description", "min-h-24 w-full rounded-md border border-[var(--mp-line)] px-3 py-2 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                      onChange={(event) => setProductDescription(event.target.value)}
                      placeholder="Описание товара"
                      value={productDescription}
                    />
                    {renderAiFieldHint("description")}
                  </div>
                  </div>
                  {renderContentRatingSidebar()}
                </div>
              ) : null}

              {wizardTab === "characteristics" ? (
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                  <div className="space-y-5">
                  <h4 className="text-2xl font-semibold">Характеристики</h4>
                  {ozonRequiredAttributes.length ? (
                    <div className="rounded-lg border border-[var(--mp-line)] bg-slate-50 p-3">
                      <p className="mb-2 text-sm font-semibold">Обязательные атрибуты Ozon</p>
                      <div className="grid gap-3 md:grid-cols-2">
                        {ozonRequiredAttributes.map((attr) => (
                          <div key={attr.id}>
                            <label className="mb-1 block text-xs text-[var(--mp-muted)]">
                              {attr.name} (id: {attr.id}) *
                            </label>
                            <input
                              className="h-10 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                              list={ozonAttributeValuesById[attr.id]?.length ? `attr-values-${attr.id}` : undefined}
                              onChange={(event) => updateOzonAttributeInput(attr.id, event.target.value)}
                              placeholder={attr.is_collection ? "значения через ;" : "значение"}
                              value={ozonAttributeInputValues[attr.id] || ""}
                            />
                            {ozonAttributeValuesById[attr.id]?.length ? (
                              <datalist id={`attr-values-${attr.id}`}>
                                {ozonAttributeValuesById[attr.id].map((item) => (
                                  <option key={`${attr.id}-${item.id}`} value={item.value} />
                                ))}
                              </datalist>
                            ) : null}
                            <p className="mt-1 text-[11px] text-[var(--mp-muted)]">{attr.type || "String"}{attr.is_collection ? ", множественный" : ""}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-dashed border-[var(--mp-line)] p-3 text-sm text-[var(--mp-muted)]">
                      Сначала загрузите обязательные характеристики на шаге «Информация о товаре».
                    </div>
                  )}
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Бренд</label>
                      <input className={aiFieldInputClass("brand", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharBrand(e.target.value)} placeholder="Например Нет бренда" value={charBrand} />
                      {renderAiFieldHint("brand")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Название модели (для объединения в одну карточку) *</label>
                      <input className={aiFieldInputClass("model_name", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharModelName(e.target.value)} placeholder="Название модели" value={charModelName} />
                      {renderAiFieldHint("model_name")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">ТН ВЭД коды ЕАЭС *</label>
                      <div className="relative" ref={tnvedDropdownRef}>
                        <button
                          className="flex h-11 w-full items-center justify-between rounded-md border border-[var(--mp-line)] bg-white px-3 text-left text-sm outline-none transition focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                          onClick={() => setIsTnvedDropdownOpen((prev) => !prev)}
                          type="button"
                        >
                          <span className={`truncate ${charTnved ? "text-slate-900" : "text-slate-400"}`}>
                            {charTnved || "Выберите из справочника Ozon"}
                          </span>
                          <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition ${isTnvedDropdownOpen ? "rotate-180" : ""}`} />
                        </button>
                        {isTnvedDropdownOpen ? (
                          <div className="absolute z-40 mt-1 w-full rounded-md border border-[var(--mp-line)] bg-white shadow-lg">
                            <div className="max-h-64 overflow-auto">
                              {!charDictionaryOptions.tnved.length && charTnved ? (
                                <button
                                  className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                                  onClick={() => {
                                    setIsTnvedDropdownOpen(false);
                                    setTnvedHoverText(null);
                                  }}
                                  onMouseEnter={() => setTnvedHoverText(charTnved)}
                                  onMouseLeave={() => setTnvedHoverText(null)}
                                  type="button"
                                >
                                  <span className="block truncate">{charTnved}</span>
                                </button>
                              ) : null}
                              {charDictionaryOptions.tnved.map((item) => (
                                <button
                                  className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                                  key={`tnved-opt-${item.id}-${item.value}`}
                                  onClick={() => {
                                    setCharTnved(item.value);
                                    setIsTnvedDropdownOpen(false);
                                    setTnvedHoverText(null);
                                  }}
                                  onMouseEnter={() => setTnvedHoverText(item.value)}
                                  onMouseLeave={() => setTnvedHoverText(null)}
                                  type="button"
                                >
                                  <span className="block truncate">{item.value}</span>
                                </button>
                              ))}
                            </div>
                            {tnvedHoverText ? (
                              <div className="border-t border-[var(--mp-line)] bg-slate-50 px-3 py-2 text-xs text-slate-700">
                                <p className="max-h-20 overflow-auto whitespace-normal break-words">{tnvedHoverText}</p>
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Вес товара, г</label>
                      <input className={aiFieldInputClass("product_weight", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharProductWeight(e.target.value)} placeholder="Например 100" value={charProductWeight} />
                      {renderAiFieldHint("product_weight")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Количество товара в УЕИ</label>
                      <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharQuantityUei(e.target.value)} placeholder="Например 1" value={charQuantityUei} />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Минимальное количество оптом</label>
                      <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharMinWholesaleQty(e.target.value)} placeholder="Например 1" value={charMinWholesaleQty} />
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">#Хештеги</label>
                    <input className={aiFieldInputClass("hashtags", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharHashtags(e.target.value)} placeholder="#gbt #charger" value={charHashtags} />
                    {renderAiFieldHint("hashtags")}
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">Аннотация</label>
                    <textarea className={aiFieldInputClass("annotation", "min-h-36 w-full rounded-md border border-[var(--mp-line)] px-3 py-2 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharAnnotation(e.target.value)} placeholder="Описание товара" value={charAnnotation} />
                    {renderAiFieldHint("annotation")}
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--mp-muted)]">Объединить в похожие товары</label>
                    <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharSimilarProducts(e.target.value)} placeholder="Служебный идентификатор или артикул группы" value={charSimilarProducts} />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Партномер (артикул производителя)</label>
                      <input className={aiFieldInputClass("partner_code", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharPartnerCode(e.target.value)} placeholder="Партномер" value={charPartnerCode} />
                      {renderAiFieldHint("partner_code")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">OEM-номер</label>
                      <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharOemNumber(e.target.value)} placeholder="OEM-номер" value={charOemNumber} />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Длина кабеля, м</label>
                      <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharCableLength(e.target.value)} placeholder="Например 1.5" value={charCableLength} />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Мощность, Вт</label>
                      <input className="h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(e) => setCharPower(e.target.value)} placeholder="Например 1200" value={charPower} />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Материал</label>
                      <input className={aiFieldInputClass("material", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} list={charDictionaryOptions.material.length ? "ozon-material-values" : undefined} onChange={(e) => setCharMaterial(e.target.value)} placeholder="Выберите из справочника Ozon" value={charMaterial} />
                      {charDictionaryOptions.material.length ? (
                        <datalist id="ozon-material-values">
                          {charDictionaryOptions.material.map((item) => (
                            <option key={`material-${item.id}`} value={item.value} />
                          ))}
                        </datalist>
                      ) : null}
                      {renderAiFieldHint("material")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Цвет товара</label>
                      <div className="relative" ref={colorDropdownRef}>
                        <button
                          className={aiFieldInputClass("color", "flex h-11 w-full items-center justify-between rounded-md border border-[var(--mp-line)] px-3 text-left text-sm outline-none transition focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                          onClick={() => setIsColorDropdownOpen((prev) => !prev)}
                          type="button"
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            {charColor ? <span className="h-3 w-3 rounded-full border border-slate-300" style={colorSwatchStyle(charColor)} /> : null}
                            <span className={`truncate ${charColor ? "text-slate-900" : "text-slate-400"}`}>
                              {charColor || "Выберите из справочника Ozon"}
                            </span>
                          </span>
                          <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition ${isColorDropdownOpen ? "rotate-180" : ""}`} />
                        </button>
                        {isColorDropdownOpen && charDictionaryOptions.color.length ? (
                          <div className="absolute z-40 mt-1 max-h-64 w-full overflow-auto rounded-md border border-[var(--mp-line)] bg-white shadow-lg">
                            {charDictionaryOptions.color.map((item) => (
                              <button
                                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                                key={`color-opt-${item.id}`}
                                onClick={() => {
                                  setCharColor(item.value);
                                  setIsColorDropdownOpen(false);
                                }}
                                type="button"
                              >
                                <span className="h-3 w-3 rounded-full border border-slate-300" style={colorSwatchStyle(item.value)} />
                                <span>{item.value}</span>
                              </button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                      {renderAiFieldHint("color")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Гарантийный срок</label>
                      <input className={aiFieldInputClass("warranty_term", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharWarrantyTerm(e.target.value)} placeholder="Например 12 месяцев" value={charWarrantyTerm} />
                      {renderAiFieldHint("warranty_term")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Гарантия</label>
                      <input className={aiFieldInputClass("warranty", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} list={charDictionaryOptions.warranty.length ? "ozon-warranty-values" : undefined} onChange={(e) => setCharWarranty(e.target.value)} placeholder="Выберите из справочника Ozon" value={charWarranty} />
                      {charDictionaryOptions.warranty.length ? (
                        <datalist id="ozon-warranty-values">
                          {charDictionaryOptions.warranty.map((item) => (
                            <option key={`warranty-${item.id}`} value={item.value} />
                          ))}
                        </datalist>
                      ) : null}
                      {renderAiFieldHint("warranty")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Страна-изготовитель</label>
                      <select
                        className={aiFieldInputClass("country", "h-11 w-full rounded-md border border-[var(--mp-line)] bg-white px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")}
                        onChange={(e) => setCharCountry(e.target.value)}
                        value={charCountry}
                      >
                        <option value="">Выберите из справочника Ozon</option>
                        {!charDictionaryOptions.country.some((item) => item.value === charCountry) && charCountry ? (
                          <option value={charCountry}>{charCountry}</option>
                        ) : null}
                        {charDictionaryOptions.country.map((item) => (
                          <option key={`country-${item.id}-${item.value}`} value={item.value}>
                            {item.value}
                          </option>
                        ))}
                      </select>
                      {renderAiFieldHint("country")}
                    </div>
                    <div className="md:col-span-2">
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Комплектация</label>
                      <input className={aiFieldInputClass("complectation", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharComplectation(e.target.value)} placeholder="Перечислите, что входит в комплект" value={charComplectation} />
                      {renderAiFieldHint("complectation")}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-[var(--mp-muted)]">Количество заводских упаковок</label>
                      <input className={aiFieldInputClass("factory_package_count", "h-11 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200")} onChange={(e) => setCharFactoryPackageCount(e.target.value)} placeholder="Например 1" value={charFactoryPackageCount} />
                      {renderAiFieldHint("factory_package_count")}
                    </div>
                  </div>
                  <p className="text-xs text-[var(--mp-muted)]">
                    {isLoadingCharDictionaries
                      ? "Загружаем значения справочников Ozon..."
                      : `Справочники Ozon: ТН ВЭД ${charDictionaryOptions.tnved.length}, материал ${charDictionaryOptions.material.length}, цвет ${charDictionaryOptions.color.length}, гарантия ${charDictionaryOptions.warranty.length}, страна ${charDictionaryOptions.country.length}.`}
                  </p>
                  <details className="rounded-lg border border-[var(--mp-line)] bg-slate-50 p-3">
                    <summary className="cursor-pointer text-sm font-semibold">Технические атрибуты Ozon (JSON)</summary>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <textarea className="min-h-40 w-full rounded-md border border-[var(--mp-line)] px-3 py-2 font-mono text-xs outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(event) => setProductAttributesJson(event.target.value)} placeholder='attributes JSON: [{"id":31,"values":[{"value":"Нет бренда"}]}]' value={productAttributesJson} />
                      <textarea className="min-h-40 w-full rounded-md border border-[var(--mp-line)] px-3 py-2 font-mono text-xs outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200" onChange={(event) => setProductComplexAttributesJson(event.target.value)} placeholder='complex_attributes JSON: [{"id":21845,"complex_id":100002,"values":[{"value":"https://...mp4"}]}]' value={productComplexAttributesJson} />
                    </div>
                  </details>
                  </div>
                  {renderContentRatingSidebar()}
                </div>
              ) : null}

              {wizardTab === "media" ? (
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                  <div>
                  <div className="mb-4 flex items-center gap-4 text-sm">
                    <button className={mediaTab === "photo" ? "border-b-2 border-[var(--mp-indigo)] pb-1 font-semibold text-[var(--mp-indigo)]" : "pb-1 text-slate-500"} onClick={() => setMediaTab("photo")} type="button">Фото</button>
                    <button className={mediaTab === "video" ? "border-b-2 border-[var(--mp-indigo)] pb-1 font-semibold text-[var(--mp-indigo)]" : "pb-1 text-slate-500"} onClick={() => setMediaTab("video")} type="button">Видео</button>
                    <button className={mediaTab === "cover" ? "border-b-2 border-[var(--mp-indigo)] pb-1 font-semibold text-[var(--mp-indigo)]" : "pb-1 text-slate-500"} onClick={() => setMediaTab("cover")} type="button">Видеообложка</button>
                  </div>

              {mediaTab === "photo" ? (
                <div>
                  <p className="text-sm text-[var(--mp-muted)]">Добавьте фото ссылкой или перетащите файл с компьютера.</p>
                  <input
                    accept="image/*"
                    className="hidden"
                    multiple
                    onChange={async (event) => {
                      const files = Array.from(event.target.files || []);
                      await addPhotoFiles(files);
                      event.currentTarget.value = "";
                    }}
                    ref={photoInputRef}
                    type="file"
                  />
                  <div
                    className={`mt-3 cursor-pointer rounded-xl border border-dashed p-4 transition ${isPhotoDropActive ? "border-[var(--mp-orange)] bg-orange-50" : "border-[var(--mp-line)] bg-white"}`}
                    onClick={() => photoInputRef.current?.click()}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      setIsPhotoDropActive(false);
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setIsPhotoDropActive(true);
                    }}
                    onDrop={async (event) => {
                      event.preventDefault();
                      setIsPhotoDropActive(false);
                      const files = Array.from(event.dataTransfer.files || []);
                      await addPhotoFiles(files);
                    }}
                  >
                    <p className="text-sm font-semibold">Выберите или перетащите фото в эту область</p>
                    <p className="mt-1 text-xs text-[var(--mp-muted)]">JPG, PNG, WEBP, HEIC. Рекомендуемый размер до 10 МБ.</p>
                  </div>
                  <div className="mt-3 rounded-xl border border-dashed border-[var(--mp-line)] p-3">
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <input
                        className="h-10 flex-1 rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                        onChange={(event) => setMediaPhotoInput(event.target.value)}
                        placeholder="https://...jpg"
                        value={mediaPhotoInput}
                      />
                      <button className="mp-btn-primary" onClick={addPhotoUrl} type="button">
                        Добавить фото
                      </button>
                    </div>
                    <p className="mt-2 text-xs text-[var(--mp-muted)]">Поддерживаются публичные URL и загруженные с ПК файлы.</p>
                  </div>
                  {mediaDraftPhotos.length ? (
                    <div className="mt-3 space-y-3">
                      <div
                        className={`flex h-[320px] items-center justify-center rounded-xl border bg-slate-50 ${dragPhotoIndex !== null ? "border-[var(--mp-orange)]" : "border-[var(--mp-line)]"}`}
                        onDragOver={(event) => {
                          event.preventDefault();
                        }}
                        onDrop={(event) => {
                          event.preventDefault();
                          if (dragPhotoIndex === null) return;
                          reorderPhoto(dragPhotoIndex, 0);
                          setDragPhotoIndex(null);
                        }}
                      >
                        {(() => {
                          const selectedPhoto = mediaDraftPhotos[activePhotoIndex] || mediaDraftPhotos[0];
                          const draft = getAiMediaDraftForPhoto(selectedPhoto);
                          if (isAiMediaDraftPlaceholder(selectedPhoto)) {
                            return (
                              <div className="flex h-full w-full flex-col items-center justify-center rounded-lg bg-slate-200 text-slate-500">
                                <div className="h-20 w-24 animate-pulse rounded-xl bg-slate-300" />
                                <div className="mt-5 h-2 w-48 overflow-hidden rounded-full bg-slate-300">
                                  <div className="h-full rounded-full bg-orange-400 transition-all" style={{ width: `${Math.max(5, Math.min(100, draft?.progress || 5))}%` }} />
                                </div>
                                <span className="mt-2 text-xs font-semibold">AI draft · {Math.max(5, Math.min(100, draft?.progress || 5))}%</span>
                                {draft?.error ? <span className="mt-2 text-xs text-red-600">{draft.error}</span> : null}
                              </div>
                            );
                          }
                          return (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              alt={mediaProduct.name || "Товар"}
                              className="max-h-full max-w-full rounded-lg object-contain"
                              src={selectedPhoto}
                            />
                          );
                        })()}
                      </div>
                      <div className="grid grid-cols-6 gap-2">
                        {mediaDraftPhotos.map((url, idx) => (
                          <div
                            className={`min-w-0 space-y-1 rounded ${dragPhotoIndex === idx ? "opacity-60" : ""}`}
                            draggable
                            key={`${url}-${idx}`}
                            onDragEnd={() => setDragPhotoIndex(null)}
                            onDragOver={(event) => {
                              event.preventDefault();
                            }}
                            onDragStart={() => setDragPhotoIndex(idx)}
                            onDrop={(event) => {
                              event.preventDefault();
                              if (dragPhotoIndex === null) return;
                              reorderPhoto(dragPhotoIndex, idx);
                              setDragPhotoIndex(null);
                            }}
                          >
                            {(() => {
                              const draft = getAiMediaDraftForPhoto(url);
                              const isDraft = Boolean(draft);
                              const isPendingDraft = isAiMediaDraftPlaceholder(url);
                              const progress = Math.max(5, Math.min(100, draft?.progress || 5));
                              return (
                                <>
                            <button
                              className={`relative block w-full overflow-hidden rounded-md border ${idx === activePhotoIndex ? "border-[var(--mp-indigo)] ring-2 ring-indigo-200" : "border-[var(--mp-line)]"}`}
                              onClick={() => setActivePhotoIndex(idx)}
                              type="button"
                            >
                              {isPendingDraft ? (
                                <div className="flex h-20 min-w-0 w-full flex-col items-stretch justify-center bg-slate-200 px-2 text-[10px] font-semibold text-slate-500">
                                  <div className="h-6 w-8 animate-pulse rounded bg-slate-300" />
                                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-300">
                                    <div className="h-full rounded-full bg-orange-400 transition-all" style={{ width: `${progress}%` }} />
                                  </div>
                                  <span className="mt-1 text-center">{progress}%</span>
                                </div>
                              ) : (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img alt={`preview-${idx + 1}`} className="h-20 w-full object-cover" src={url} />
                              )}
                              {isDraft ? <span className="absolute left-1 top-1 rounded bg-orange-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">draft</span> : null}
                            </button>
                            <div className="flex items-center gap-1">
                              <button
                                className={`rounded px-1.5 py-0.5 text-[10px] ${mediaDraftCover === url ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"}`}
                                disabled={isPendingDraft}
                                onClick={() => setMediaDraftCover(url)}
                                type="button"
                              >
                                Обложка
                              </button>
                              <button
                                className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600"
                                onClick={() => removePhotoUrl(url)}
                                type="button"
                              >
                                Удалить
                              </button>
                            </div>
                                </>
                              );
                            })()}
                          </div>
                        ))}
                      </div>
                      {productEditorEntryMode === "ai_media" ? (
                        <div className="rounded-2xl border border-orange-200 bg-orange-50 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <p className="text-sm font-semibold text-orange-800">AI медиа редактор</p>
                              <p className="mt-1 text-xs text-orange-700">
                                Промт относится к выбранному изображению #{Math.min(activePhotoIndex + 1, mediaDraftPhotos.length || 1)}.
                              </p>
                            </div>
                            <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-orange-700">
                              {mediaDraftPhotos[activePhotoIndex] ? "изображение выбрано" : "нет изображения"}
                            </span>
                          </div>
                          <textarea
                            className="mt-3 min-h-20 w-full rounded-xl border border-orange-200 bg-white px-3 py-2 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                            onChange={(event) => setAiMediaPrompt(event.target.value)}
                            placeholder="Например: сделай инфографику с размерами, добавь плашки преимуществ, сохрани товар без искажений, стиль премиальный маркетплейс."
                            value={aiMediaPrompt}
                          />
                          <input
                            className="mt-2 h-10 w-full rounded-md border border-orange-200 bg-white px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                            onChange={(event) => setAiMediaReferenceNote(event.target.value)}
                            placeholder="Референс: ссылка, описание стиля или что взять за направление"
                            value={aiMediaReferenceNote}
                          />
                          <div className="mt-2 flex flex-wrap gap-2">
                            {["Главное фото", "Инфографика", "Размеры", "Преимущества", "Товар в использовании"].map((chip) => (
                              <button
                                className="rounded-full border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-orange-700 hover:bg-orange-100"
                                key={chip}
                                onClick={() => setAiMediaPrompt((prev) => (prev ? `${prev}; ${chip}` : chip))}
                                type="button"
                              >
                                {chip}
                              </button>
                            ))}
                          </div>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <button className="mp-btn-primary" disabled={isGeneratingAiMediaImage} onClick={createAiMediaDraft} type="button">
                              {isGeneratingAiMediaImage ? "Ставим в очередь..." : "Сгенерировать draft"}
                            </button>
                            <button className="mp-btn-secondary" disabled={isSavingMedia || productEditorMode === "create" || mediaDraftPhotos.some(isAiMediaDraftPlaceholder)} onClick={onSaveMediaToOzon} type="button">
                              {isSavingMedia ? "Сохраняем..." : "Сохранить"}
                            </button>
                            <span className="text-xs text-orange-700">Новый AI draft добавится к текущим изображениям с пометкой draft.</span>
                          </div>
                        </div>
                      ) : null}
                      {showPhotoOrderHint ? (
                      <div className="rounded-2xl border border-slate-200 bg-slate-100 p-4">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-base font-semibold">Управляйте порядком фото</p>
                            <p className="mt-1 text-sm text-slate-700">
                              Чтобы сделать фото главным, перетащите его на первое место. Остальные фото расставьте в том порядке, который должен отображаться на сайте.
                            </p>
                          </div>
                          <button
                            className="text-slate-400 hover:text-slate-600"
                            onClick={() => setShowPhotoOrderHint(false)}
                            title="Закрыть подсказку"
                            type="button"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      ) : null}
                    </div>
                  ) : (
                    <div className="mt-3 rounded-lg border border-dashed border-[var(--mp-line)] p-4 text-sm text-[var(--mp-muted)]">Фото не найдены.</div>
                  )}
                </div>
              ) : null}

              {mediaTab === "video" ? (
                <div>
                  <p className="text-sm text-[var(--mp-muted)]">Добавьте видео ссылкой или перетащите файл с компьютера.</p>
                  <input
                    accept="video/*"
                    className="hidden"
                    multiple
                    onChange={async (event) => {
                      const files = Array.from(event.target.files || []);
                      await addVideoFiles(files);
                      event.currentTarget.value = "";
                    }}
                    ref={videoInputRef}
                    type="file"
                  />
                  <div
                    className={`mt-3 cursor-pointer rounded-xl border border-dashed p-4 transition ${isVideoDropActive ? "border-[var(--mp-orange)] bg-orange-50" : "border-[var(--mp-line)] bg-white"}`}
                    onClick={() => videoInputRef.current?.click()}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      setIsVideoDropActive(false);
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setIsVideoDropActive(true);
                    }}
                    onDrop={async (event) => {
                      event.preventDefault();
                      setIsVideoDropActive(false);
                      const files = Array.from(event.dataTransfer.files || []);
                      await addVideoFiles(files);
                    }}
                  >
                    <p className="text-sm font-semibold">Выберите или перетащите видео в эту область</p>
                    <p className="mt-1 text-xs text-[var(--mp-muted)]">MP4, MOV, WEBM. Рекомендуемый размер до 100 МБ.</p>
                  </div>
                  <div className="mt-3 rounded-xl border border-dashed border-[var(--mp-line)] p-3">
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <input
                        className="h-10 flex-1 rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                        onChange={(event) => setMediaVideoInput(event.target.value)}
                        placeholder="https://...mp4"
                        value={mediaVideoInput}
                      />
                      <button className="mp-btn-primary" onClick={addVideoUrl} type="button">
                        Добавить видео
                      </button>
                    </div>
                    <p className="mt-2 text-xs text-[var(--mp-muted)]">Рекомендуется MP4 ссылка с публичным доступом или файл с ПК.</p>
                  </div>
                  {mediaDraftVideos.length ? (
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      {mediaDraftVideos.map((url, idx) => (
                        <div className="rounded-xl border border-[var(--mp-line)] p-2" key={`${url}-${idx}`}>
                          <video className="h-56 w-full rounded-md bg-black object-contain" controls preload="metadata" src={url} />
                          <div className="mt-2 flex items-center justify-between gap-2">
                            <p className="truncate text-xs text-[var(--mp-muted)]">{url}</p>
                            <button className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600" onClick={() => removeVideoUrl(url)} type="button">
                              Удалить
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-3 rounded-lg border border-dashed border-[var(--mp-line)] p-4 text-sm text-[var(--mp-muted)]">Видео не найдены.</div>
                  )}
                </div>
              ) : null}

              {mediaTab === "cover" ? (
                <div>
                  <p className="text-sm text-[var(--mp-muted)]">Выберите URL обложки для видео. Позже добавим AI-генерацию обложки.</p>
                  <input
                    accept="image/*"
                    className="hidden"
                    onChange={async (event) => {
                      const file = event.target.files?.[0] ?? null;
                      await setCoverFile(file);
                      event.currentTarget.value = "";
                    }}
                    ref={coverInputRef}
                    type="file"
                  />
                  <div
                    className={`mt-3 cursor-pointer rounded-xl border border-dashed p-4 transition ${isCoverDropActive ? "border-[var(--mp-orange)] bg-orange-50" : "border-[var(--mp-line)] bg-white"}`}
                    onClick={() => coverInputRef.current?.click()}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      setIsCoverDropActive(false);
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setIsCoverDropActive(true);
                    }}
                    onDrop={async (event) => {
                      event.preventDefault();
                      setIsCoverDropActive(false);
                      const file = event.dataTransfer.files?.[0] ?? null;
                      await setCoverFile(file);
                    }}
                  >
                    <p className="text-sm font-semibold">Выберите или перетащите изображение для обложки</p>
                    <p className="mt-1 text-xs text-[var(--mp-muted)]">JPG, PNG, WEBP, HEIC.</p>
                  </div>
                  <div className="mt-3">
                    <input
                      className="h-10 w-full rounded-md border border-[var(--mp-line)] px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                      onChange={(event) => setMediaDraftCover(event.target.value)}
                      placeholder="https://...jpg"
                      value={mediaDraftCover}
                    />
                  </div>
                  <div className="mt-3 flex h-[280px] items-center justify-center rounded-xl border border-[var(--mp-line)] bg-slate-50">
                    {mediaDraftCover ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img alt="cover" className="max-h-full max-w-full rounded-lg object-contain" src={mediaDraftCover} />
                    ) : (
                      <span className="text-sm text-[var(--mp-muted)]">Нет фото для обложки</span>
                    )}
                  </div>
                </div>
              ) : null}
                </div>
                {renderContentRatingSidebar()}
                </div>
              ) : null}

              {wizardTab === "preview" ? (
                <div className="space-y-4">
                  <h4 className="text-2xl font-semibold">Предварительный просмотр</h4>
                  <div className="grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
                    <div className="rounded-lg border border-[var(--mp-line)] bg-slate-50 p-2">
                      {mediaDraftPhotos[0] ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img alt="preview-main" className="h-52 w-full rounded-md object-cover" src={mediaDraftPhotos[0]} />
                      ) : (
                        <div className="flex h-52 items-center justify-center text-sm text-[var(--mp-muted)]">Нет фото</div>
                      )}
                    </div>
                    <div className="space-y-2 text-sm">
                      <p><span className="text-[var(--mp-muted)]">Название:</span> {productName || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Артикул:</span> {productOfferId || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Штрихкод:</span> {productBarcode || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Категория:</span> {productDescriptionCategoryId || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Тип:</span> {productTypeId || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Цена:</span> {productPrice || "-"}</p>
                      <p><span className="text-[var(--mp-muted)]">Фото:</span> {mediaDraftPhotos.length} / Видео: {mediaDraftVideos.length}</p>
                    </div>
                  </div>
                  <div className="rounded-lg border border-[var(--mp-line)] p-3">
                    <p className="mb-1 text-sm font-semibold">Описание</p>
                    <p className="whitespace-pre-wrap text-sm text-slate-700">{(productDescription || charAnnotation || "-").toString()}</p>
                  </div>
                </div>
              ) : null}
            </div>

            {productEditorEntryMode === "ai" ? (
              <div className="max-h-[42vh] shrink-0 overflow-y-auto border-t border-orange-100 bg-orange-50/60 px-6 py-4">
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
                  <div>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">AI режим</span>
                      {aiDraftResult ? <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">Есть AI-черновик #{aiDraftResult.log_id}</span> : null}
                      <span className="text-xs text-[var(--mp-muted)]">Промт и референс не публикуются в Ozon, они нужны только для черновика.</span>
                    </div>
                    <textarea
                      className="min-h-20 w-full rounded-xl border border-orange-200 bg-white px-3 py-2 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                      onChange={(event) => setAiPrompt(event.target.value)}
                      placeholder="Что нужно сделать с карточкой? Например: проверь параметры по фото, заполни описание, сделай премиальные карточки с акцентом на размеры и комплектацию."
                      value={aiPrompt}
                    />
                    <div className="mt-2 flex flex-wrap gap-2">
                      {["Проверить поля", "Заполнить описание", "Сделать инфографику", "Премиальный стиль", "Акцент на характеристиках"].map((chip) => (
                        <button
                          className="rounded-full border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-orange-700 hover:bg-orange-100"
                          key={chip}
                          onClick={() => setAiPrompt((prev) => (prev ? `${prev}; ${chip}` : chip))}
                          type="button"
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                    <input
                      className="mt-2 h-10 w-full rounded-md border border-orange-200 bg-white px-3 text-sm outline-none focus:border-[var(--mp-orange)] focus:ring-2 focus:ring-orange-200"
                      onChange={(event) => setAiReferenceNote(event.target.value)}
                      placeholder="Референс или пожелание к стилю: ссылка, описание, что взять за направление"
                      value={aiReferenceNote}
                    />
                  </div>
                  <div className="space-y-2">
                    <button
                      className="mp-btn-primary w-full"
                      disabled={isGeneratingAiDraft || !mediaDraftPhotos.length}
                      onClick={() => onGenerateAiCardDraft("full")}
                      type="button"
                    >
                      {isGeneratingAiDraft ? "Генерируем..." : "Запустить AI"}
                    </button>
                    <button
                      className="mp-btn-secondary w-full"
                      disabled={isGeneratingAiDraft || !mediaDraftPhotos.length}
                      onClick={() => onGenerateAiCardDraft("validate")}
                      type="button"
                    >
                      Только проверить
                    </button>
                    {aiDraftResult ? (
                      <button className="mp-btn-secondary w-full" onClick={applyAiDraftToForm} type="button">
                        Применить уверенные
                      </button>
                    ) : null}
                    {!mediaDraftPhotos.length ? <p className="text-xs text-red-600">Для AI нужен минимум один снимок товара.</p> : null}
                  </div>
                </div>
                {aiDraftResult ? (
                  <div className="mt-3 grid gap-3 lg:grid-cols-3">
                    <div className="rounded-xl border border-orange-100 bg-white p-3">
                      <p className="text-sm font-semibold">Проверка полей</p>
                      <div className="mt-2 max-h-44 space-y-2 overflow-auto text-xs">
                        {Object.values(aiFieldStates).map((state, idx) => {
                          const rec = state.recommendation;
                          return (
                            <div className="rounded-lg bg-slate-50 p-2" key={`ai-check-${idx}`}>
                              <p className="font-semibold">{rec.field}: {state.status} · {Math.round(rec.confidence * 100)}%</p>
                              <p className="text-slate-600">{rec.reason || "Без пояснения"}</p>
                              {state.status === "ai_low_confidence" ? <p className="mt-1 text-orange-700">Низкая уверенность: {rec.suggestedValue || "-"}</p> : null}
                            </div>
                          );
                        })}
                        {!Object.values(aiFieldStates).length ? <p className="text-[var(--mp-muted)]">Проверки не вернулись.</p> : null}
                      </div>
                    </div>
                    <div className="rounded-xl border border-orange-100 bg-white p-3">
                      <p className="text-sm font-semibold">AI media recommendations</p>
                      <div className="mt-2 max-h-44 space-y-2 overflow-auto text-xs text-slate-700">
                        {aiMediaRecommendations.map((item, idx) => (
                          <div className="rounded-lg bg-slate-50 p-2" key={`ai-media-${idx}`}>
                            <p className="font-semibold">{item.type}: {item.action} · {Math.round(item.confidence * 100)}%</p>
                            <p className="text-slate-600">{item.reason}</p>
                            <p className="mt-1 text-orange-700">{item.prompt}</p>
                          </div>
                        ))}
                        {!aiMediaRecommendations.length ? <p className="text-[var(--mp-muted)]">Медиа-рекомендации не вернулись.</p> : null}
                      </div>
                    </div>
                    <div className="rounded-xl border border-orange-100 bg-white p-3">
                      <p className="text-sm font-semibold">Итог перед сохранением</p>
                      <div className="mt-2 space-y-1 text-xs text-slate-700">
                        {(() => {
                          const states = Object.values(aiFieldStates);
                          const applied = states.filter((item) => item.status === "ai_applied");
                          const pending = states.filter((item) => item.status === "ai_suggestion");
                          const low = states.filter((item) => item.status === "ai_low_confidence");
                          const mediaGenerate = aiMediaRecommendations.filter((item) => item.action === "generate");
                          return (
                            <>
                              <p><span className="font-semibold">Изменены AI:</span> {applied.map((item) => item.recommendation.field).join(", ") || "-"}</p>
                              <p><span className="font-semibold">Не применены:</span> {pending.map((item) => item.recommendation.field).join(", ") || "-"}</p>
                              <p><span className="font-semibold">Низкая уверенность:</span> {low.map((item) => item.recommendation.field).join(", ") || "-"}</p>
                              <p><span className="font-semibold">Медиа к генерации:</span> {mediaGenerate.map((item) => item.type).join(", ") || "-"}</p>
                              <p><span className="font-semibold">Warnings:</span> {aiDraftResult.warnings.length ? aiDraftResult.warnings.join("; ") : "-"}</p>
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="shrink-0 flex items-center justify-end gap-2 border-t border-[var(--mp-line)] px-6 py-4">
              {mediaError ? <p className="mr-auto text-sm text-red-600">{mediaError}</p> : null}
              {mediaNotice ? <p className="mr-auto text-sm text-emerald-700">{mediaNotice}</p> : null}
              <button className="mp-btn-secondary" onClick={() => setMediaProduct(null)} type="button">
                Отмена
              </button>
              <button
                className="mp-btn-secondary"
                onClick={() => {
                  const order: ProductWizardTab[] = ["info", "characteristics", "media", "preview"];
                  const idx = order.indexOf(wizardTab);
                  if (idx > 0) setWizardTab(order[idx - 1]);
                }}
                type="button"
              >
                Назад
              </button>
              <button
                className="mp-btn-secondary"
                onClick={() => {
                  const order: ProductWizardTab[] = ["info", "characteristics", "media", "preview"];
                  const idx = order.indexOf(wizardTab);
                  if (idx < order.length - 1) setWizardTab(order[idx + 1]);
                }}
                type="button"
              >
                Далее
              </button>
              <button className="mp-btn-secondary" disabled={isSavingProduct} onClick={onSaveProductToOzon} type="button">
                {isSavingProduct ? "Сохраняем..." : productEditorMode === "create" ? "Отправить на модерацию" : "Сохранить как новую"}
              </button>
              <button className="mp-btn-primary" disabled={isSavingMedia || productEditorMode === "create" || mediaDraftPhotos.some(isAiMediaDraftPlaceholder)} onClick={onSaveMediaToOzon} type="button">
                {isSavingMedia ? "Сохраняем..." : "Сохранить в Ozon"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

