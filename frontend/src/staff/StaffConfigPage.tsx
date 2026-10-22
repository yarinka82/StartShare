import SaveIcon from "@mui/icons-material/Save";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

type ProviderId = "gemini" | "openai" | "azure_openai";

interface ProviderOption {
  id: ProviderId;
  label: string;
  models: { id: string; label: string }[]; // для azure_openai — порожньо (модель = deployment на бекенді)
}

// Числові поля можуть бути тимчасово порожніми, поки користувач редагує.
type NumField = number | "";

interface ConfigDto {
  ai_provider: string;
  ai_model: string;
  ai_temperature: NumField;
  max_deck_size_mb: NumField;
  deck_retention_hours: NumField;
  draft_expiry_days: NumField;
  min_digest_cards: NumField;
  max_digest_cards: NumField;
  intro_request_expiry_days: NumField;
  updated_at?: string;
  ai_providers?: ProviderOption[]; // read-only, може приходити з бекенду
}

type NumKey =
  | "ai_temperature"
  | "max_deck_size_mb"
  | "deck_retention_hours"
  | "draft_expiry_days"
  | "min_digest_cards"
  | "max_digest_cards"
  | "intro_request_expiry_days";

// Запасний каталог, якщо бекенд не віддає ai_providers.
const FALLBACK_PROVIDERS: ProviderOption[] = [
  {
    id: "gemini",
    label: "Google Gemini",
    models: [
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash (Швидка / Рекомендована)" },
      { id: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
    ],
  },
  {
    id: "openai",
    label: "OpenAI",
    models: [{ id: "gpt-4o-mini", label: "GPT-4o-mini" }],
  },
  {
    id: "azure_openai",
    label: "Azure OpenAI",
    models: [],
  },
];

// Отримання CSRF-токена для безпечних PATCH-запитів
function getCsrfToken(): string {
  const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[2]) : "";
}

// DRF повертає або {detail: "..."}, або {field: ["..."]}.
function extractApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  const parts = Object.entries(obj).map(([field, value]) => {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    return `${field}: ${text}`;
  });
  return parts.length ? parts.join("; ") : fallback;
}

export default function StaffConfigPage() {
  const { t, i18n } = useTranslation();
  const [config, setConfig] = useState<ConfigDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToast, setSavedToast] = useState(false);

  useEffect(() => {
    fetch("/api/auth/staff/config/", { credentials: "include" })
      .then(async (res) => {
        if (!res.ok) throw new Error("Не вдалося завантажити налаштування.");
        return res.json();
      })
      .then(setConfig)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;

    // ai_providers — лише для читання, на бекенд не відправляємо.
    const { ai_providers: _catalog, updated_at: _updatedAt, ...payload } = config;

    const hasEmpty = Object.values(payload).some((v) => v === "" || (typeof v === "number" && Number.isNaN(v)));
    if (hasEmpty) {
      setError(t("staff.config.fillAll", "Заповніть усі числові поля."));
      return;
    }
    if (config.min_digest_cards !== "" && config.max_digest_cards !== "" && config.min_digest_cards > config.max_digest_cards) {
      setError(t("staff.config.digestRange", "Мінімум карток у дайджесті не може бути більшим за максимум."));
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/staff/config/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(extractApiError(body, "Помилка при збереженні."));
      }

      const updated = await res.json().catch(() => null);
      if (updated) setConfig((prev) => ({ ...(prev as ConfigDto), ...updated }));
      setSavedToast(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Помилка при збереженні.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!config) {
    return <Alert severity="error">{error || "Помилка завантаження конфігурації."}</Alert>;
  }

  const providers = config.ai_providers ?? FALLBACK_PROVIDERS;
  const currentProvider = providers.find((p) => p.id === config.ai_provider);
  const providerHasModels = !!currentProvider && currentProvider.models.length > 0;
  const modelValue = currentProvider?.models.some((m) => m.id === config.ai_model) ? config.ai_model : "";

  // При зміні провайдера модель скидаємо на першу з його списку.
  const handleProviderChange = (id: string) => {
    const p = providers.find((x) => x.id === id);
    setConfig({
      ...config,
      ai_provider: id,
      ai_model: p?.models[0]?.id ?? "",
    });
  };

  // Дозволяємо порожнє поле під час набору; валідація — при збереженні.
  const setNum = (key: NumKey, raw: string, parse: (s: string) => number) => {
    if (raw === "") {
      setConfig({ ...config, [key]: "" });
      return;
    }
    const v = parse(raw);
    setConfig({ ...config, [key]: Number.isNaN(v) ? "" : v });
  };

  return (
    <Paper variant="outlined" sx={{ p: { xs: 2.5, sm: 4 }, borderRadius: 3 }}>
      <Stack spacing={3.5}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800, color: "#0b2142", display: "flex", alignItems: "center", gap: 1 }}>
              <SettingsSuggestOutlinedIcon color="primary" />
              {t("staff.config.title", "Системні константи платформи")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("staff.config.subtitle", "Керування параметрами ШІ, лімітами файлів та правилами щотижневого матчингу.")}
            </Typography>
          </Box>
          {config.updated_at && (
            <Typography variant="caption" color="text.secondary">
              {t("staff.config.lastUpdated", "Останнє оновлення:")} {new Date(config.updated_at).toLocaleString(i18n.resolvedLanguage)}
            </Typography>
          )}
        </Box>

        {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}

        <Divider />

        {/* 1. СЕКЦІЯ ШІ */}
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#17407a", mb: 2 }}>
            🤖 {t("staff.config.aiSection", "Параметри ШІ (AI Generator & Model)")}
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" }, gap: 2.5 }}>
            <FormControl fullWidth size="small">
              <InputLabel id="ai-provider-label">{t("staff.config.aiProvider", "Провайдер ШІ")}</InputLabel>
              <Select
                labelId="ai-provider-label"
                value={currentProvider ? currentProvider.id : ""}
                label={t("staff.config.aiProvider", "Провайдер ШІ")}
                onChange={(e) => handleProviderChange(e.target.value)}
              >
                {providers.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {providerHasModels ? (
              <FormControl fullWidth size="small">
                <InputLabel id="ai-model-label">{t("staff.config.aiModel", "Модель ШІ")}</InputLabel>
                <Select
                  labelId="ai-model-label"
                  value={modelValue}
                  label={t("staff.config.aiModel", "Модель ШІ")}
                  onChange={(e) => setConfig({ ...config, ai_model: e.target.value })}
                >
                  {currentProvider!.models.map((m) => (
                    <MenuItem key={m.id} value={m.id}>
                      {m.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            ) : (
              <TextField
                size="small"
                disabled
                label={t("staff.config.aiModel", "Модель ШІ")}
                value={t("staff.config.azureDeployment", "Визначається деплоєм Azure")}
                helperText={t("staff.config.azureHelper", "Змінна AZURE_OPENAI_DEPLOYMENT на сервері")}
              />
            )}

            <TextField
              label={t("staff.config.temperature", "Температура (0.0 — суворі факти, 1.0 — креатив)")}
              size="small"
              type="number"
              slotProps={{
                htmlInput: { step: 0.1, min: 0, max: 1 },
              }}
              value={config.ai_temperature}
              onChange={(e) => setNum("ai_temperature", e.target.value, parseFloat)}
            />
          </Box>
        </Box>

        <Divider />

        {/* 2. СЕКЦІЯ ЛІМІТІВ ФАЙЛІВ */}
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#17407a", mb: 2 }}>
            📁 {t("staff.config.filesSection", "Файли та політика зберігання (GDPR / TTL)")}
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" }, gap: 2.5 }}>
            <TextField
              label={t("staff.config.maxDeckSize", "Макс. розмір деку (МБ)")}
              size="small"
              type="number"
              value={config.max_deck_size_mb}
              onChange={(e) => setNum("max_deck_size_mb", e.target.value, (s) => parseInt(s, 10))}
            />
            <TextField
              label={t("staff.config.retentionHours", "Автовидалення деку (години)")}
              size="small"
              type="number"
              value={config.deck_retention_hours}
              onChange={(e) => setNum("deck_retention_hours", e.target.value, (s) => parseInt(s, 10))}
              helperText={t("staff.config.retentionHelper", "За ТЗ: 24 години")}
            />
            <TextField
              label={t("staff.config.draftExpiryDays", "Таймаут чернетки (дні)")}
              size="small"
              type="number"
              value={config.draft_expiry_days}
              onChange={(e) => setNum("draft_expiry_days", e.target.value, (s) => parseInt(s, 10))}
              helperText={t("staff.config.draftHelper", "За ТЗ: 30 днів")}
            />
          </Box>
        </Box>

        <Divider />

        {/* 3. СЕКЦІЯ ПРАВИЛ МАТЧИНГУ ТА ДАЙДЖЕСТУ */}
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#17407a", mb: 2 }}>
            🎯 {t("staff.config.matchingSection", "Правила тижневого дайджесту та знайомств")}
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" }, gap: 2.5 }}>
            <TextField
              label={t("staff.config.minDigestCards", "Мін. карток для відправки")}
              size="small"
              type="number"
              value={config.min_digest_cards}
              onChange={(e) => setNum("min_digest_cards", e.target.value, (s) => parseInt(s, 10))}
              helperText={t("staff.config.minDigestHelper", "За ТЗ: 3 тизери")}
            />
            <TextField
              label={t("staff.config.maxDigestCards", "Макс. карток у дайджесті")}
              size="small"
              type="number"
              value={config.max_digest_cards}
              onChange={(e) => setNum("max_digest_cards", e.target.value, (s) => parseInt(s, 10))}
              helperText={t("staff.config.maxDigestHelper", "За ТЗ: 5 тизерів")}
            />
            <TextField
              label={t("staff.config.introExpiryDays", "Таймаут інтро для стартапу (дні)")}
              size="small"
              type="number"
              value={config.intro_request_expiry_days}
              onChange={(e) => setNum("intro_request_expiry_days", e.target.value, (s) => parseInt(s, 10))}
              helperText={t("staff.config.introExpiryHelper", "За ТЗ: 7 днів")}
            />
          </Box>
        </Box>

        {/* КНОПКА ЗБЕРЕЖЕННЯ */}
        <Box sx={{ pt: 1 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={saving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving}
            sx={{ bgcolor: "#17407a", fontWeight: 700, textTransform: "none", px: 4, "&:hover": { bgcolor: "#0b2142" } }}
          >
            {saving ? t("common.saving", "Збереження...") : t("staff.config.saveBtn", "Зберегти налаштування")}
          </Button>
        </Box>
      </Stack>

      <Snackbar
        open={savedToast}
        autoHideDuration={3000}
        onClose={() => setSavedToast(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success" variant="filled" onClose={() => setSavedToast(false)}>
          {t("staff.config.savedSuccess", "Налаштування платформи успішно оновлено!")}
        </Alert>
      </Snackbar>
    </Paper>
  );
}