import DynamicFeedOutlinedIcon from "@mui/icons-material/DynamicFeedOutlined";
import HistoryIcon from "@mui/icons-material/History";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControl,
  InputLabel, MenuItem, Select, Skeleton, Snackbar, Stack, TextField, Typography,
} from "@mui/material";
import { Navigate } from "react-router-dom";
import { useInvestor } from "./InvestorProvider";
import {useEffect, useState} from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import BlindTeaserCard from "../components/BlindTeaserCard";
import EmptyState from "../components/EmptyState";
import { FOOTER_HEIGHT } from "../components/footerConfig";
import MandateHistoryModal from "../components/MandateHistoryModal";
import { useFeed } from "./FeedContext";

const DECLINE_REASONS = [
  { code: "sector", labelKey: "matching.reasons.sector" },
  { code: "stage", labelKey: "matching.reasons.stage" },
  { code: "region", labelKey: "matching.reasons.region" },
  { code: "ticket", labelKey: "matching.reasons.ticket" },
  { code: "team", labelKey: "matching.reasons.team" },
  { code: "metrics", labelKey: "matching.reasons.metrics" },
  { code: "other", labelKey: "matching.reasons.other" },
];

type Toast = { severity: "success" | "error"; message: string } | null;

export default function FeedPage() {
  const { t } = useTranslation();
  const { profile } = useInvestor();
  const { cards, loading, loadError, reload: loadFeed, removeCard } = useFeed();

  useEffect(() => {
    void loadFeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const [historyOpen, setHistoryOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<Toast>(null);
  
  const [interestedModalOpen, setInterestedModalOpen] = useState(false);
  const [activeCardId, setActiveCardId] = useState<number | null>(null);
  const [investorMessage, setInvestorMessage] = useState("");

  const [declineModalOpen, setDeclineModalOpen] = useState(false);
  const [declineReason, setDeclineReason] = useState("sector");

  const failToast = (e: unknown) =>
    setToast({
      severity: "error",
      message: (e as Error)?.message || t("matching.respondError", "Не вдалося надіслати відповідь. Спробуйте ще раз."),
    });

  const handleInterestedClick = (id: string) => {
    const card = cards.find((c) => c.id === id);
    if (!card) return;
    setActiveCardId(card.card_id);
    setInvestorMessage("");
    setInterestedModalOpen(true);
  };

  const handleConfirmInterested = async () => {
    if (!activeCardId || busy) return;
    setBusy(true);
    try {
      await api.respondToCard({
        card_id: activeCardId,
        action: "interested",
        investor_message: investorMessage.trim() || undefined,
      });
      removeCard(activeCardId);
      setInterestedModalOpen(false);
      setActiveCardId(null);
      setToast({ severity: "success", message: t("matching.interestSent", "Запит надіслано стартапу.") });
    } catch (e) {
      failToast(e);
    } finally {
      setBusy(false);
    }
  };

  const handleDeclineClick = (id: string) => {
    const card = cards.find((c) => c.id === id);
    if (!card) return;
    setActiveCardId(card.card_id);
    setDeclineReason("sector");
    setDeclineModalOpen(true);
  };

  const handleConfirmDecline = async () => {
    if (!activeCardId || busy) return;
    setBusy(true);
    try {
      await api.respondToCard({ card_id: activeCardId, action: "declined", decline_reason: declineReason });
      removeCard(activeCardId);
      setDeclineModalOpen(false);
      setActiveCardId(null);
      setToast({ severity: "success", message: t("matching.declineSent", "Проєкт відхилено.") });
    } catch (e) {
      failToast(e);
    } finally {
      setBusy(false);
    }
  };
    if (!profile) return <Navigate to="/investor/profile" replace />;

  return (
<Stack spacing={3}>
      {/* ШАПКА З ЛІВИМ ВИРІВНЮВАННЯМ УСІХ ЕЛЕМЕНТІВ */}
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.5 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
          {t("investor.cabinetTitle", "Кабінет інвестора")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("investor.cabinetSubtitle", "Щотижневі підбірки 3–5 сліпих тизерів за вашим мандатом.")}
        </Typography>

        {/* ЛІВИЙ БЛОК: Кількість карток + Історія мандату в один рядок */}
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", flexWrap: "wrap", mt: 1.5 }}>
          {!loading && !loadError && cards.length > 0 && (
            <Chip
              label={t("investor.digestCount", { count: cards.length, defaultValue: "У поточному дайджесті: {{count}}" })}
              color="primary"
              variant="outlined"
              sx={{ fontWeight: 700 }}
            />
          )}

          {/* Кнопка історії зліва поруч із бейджем */}
          <Button
            variant="text"
            size="small"
            startIcon={<HistoryIcon />}
            onClick={() => setHistoryOpen(true)}
            sx={{
              textTransform: "none",
              color: "text.secondary",
              fontWeight: 600,
              fontSize: "0.85rem",
              px: 1,
              "&:hover": { color: "#17407a", bgcolor: "rgba(23, 64, 122, 0.05)" },
            }}
          >
            {t("investor.mandateHistoryBtn", "Історія версій мандату")}
          </Button>
        </Stack>
      </Box>

      <Box sx={{ maxWidth: 720 }}>
        {loading ? (
          <Stack spacing={3}>
            {[0, 1].map((i) => <Skeleton key={i} variant="rounded" height={240} sx={{ borderRadius: 3 }} />)}
          </Stack>
        ) : loadError ? (
          <Alert
            severity="error"
            action={<Button color="inherit" size="small" onClick={() => void loadFeed()}>{t("common.tryAgain", "Повторити")}</Button>}
          >
            {t("investor.feedLoadError", "Не вдалося завантажити дайджест.")}
          </Alert>
        ) : cards.length === 0 ? (
          <EmptyState
            icon={<DynamicFeedOutlinedIcon />}
            title={t("investor.emptyFeedTitle", "Нових тизерів поки немає")}
            text={t(
              "investor.emptyFeedAlert",
              "На цьому тижні немає нових тизерів або ви вже переглянули всі картки. Новий дайджест буде сформовано в понеділок о 08:00 (якщо буде від 3 до 5 відповідних проєктів).",
            )}
          />
        ) : (
          <Stack spacing={3}>
            {cards.map((card) => (
              <BlindTeaserCard
                key={card.id}
                id={card.id}
                sector={card.sector}
                stage={card.stage}
                region={card.region}
                targetAmountEur={card.target_amount}
                mrrEur={card.mrr}
                teamSize={card.team_size}
                headline={card.headline}
                problemSolution={card.problem_solution}
                teamSummary={card.team_summary}
                matchReasons={card.match_reasons ?? []}
                onInterested={handleInterestedClick}
                onDecline={handleDeclineClick}
              />
            ))}
          </Stack>
        )}

      </Box>

      {/* Діалог «Цікаво» */}
      <Dialog open={interestedModalOpen} onClose={() => !busy && setInterestedModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: "#0b2142" }}>
          {t("matching.interestedModalTitle", "Виявити інтерес до стартапу")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t(
              "matching.interestedModalHint",
              "Стартап отримає запит з назвою вашого фонду. Ви можете додати коротке персональне повідомлення (опціонально):",
            )}
          </Typography>
          <TextField
            fullWidth multiline rows={3}
            placeholder={t("matching.messagePlaceholder", "Наприклад: Цікавий проєкт, хотіли б поспілкуватися щодо бізнес-моделі...")}
            value={investorMessage}
            onChange={(e) => setInvestorMessage(e.target.value.slice(0, 500))}
            helperText={`${investorMessage.length}/500`}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setInterestedModalOpen(false)} color="inherit" disabled={busy}>
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button variant="contained" onClick={handleConfirmInterested} disabled={busy}>
            {t("matching.sendInterestBtn", "Надіслати запит на інтро")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Діалог «Ні» */}
      <Dialog open={declineModalOpen} onClose={() => !busy && setDeclineModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: "#0b2142" }}>
          {t("matching.declineTitle", "Чому цей проєкт не підійшов?")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("matching.declineHint", "Цей зворотний зв'язок допоможе оптимізувати наступні щотижневі дайджести.")}
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel id="decline-reason-label">{t("matching.reasonLabel", "Причина")}</InputLabel>
            <Select
              labelId="decline-reason-label"
              value={declineReason}
              label={t("matching.reasonLabel", "Причина")}
              onChange={(e) => setDeclineReason(e.target.value)}
            >
              {DECLINE_REASONS.map((r) => (
                <MenuItem key={r.code} value={r.code}>{t(r.labelKey, r.code)}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeclineModalOpen(false)} color="inherit" disabled={busy}>
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button onClick={handleConfirmDecline} variant="contained" color="error" disabled={busy}>
            {t("matching.declineBtn", "Відхилити проєкт")}
          </Button>
        </DialogActions>
      </Dialog>

      <MandateHistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />

      <Snackbar
        open={!!toast}
        autoHideDuration={3500}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        sx={{ bottom: { xs: FOOTER_HEIGHT + 8, sm: FOOTER_HEIGHT + 24 } }}
      >
        <Alert severity={toast?.severity ?? "success"} variant="filled" onClose={() => setToast(null)}>
          {toast?.message}
        </Alert>
      </Snackbar>
    </Stack>
  );
}