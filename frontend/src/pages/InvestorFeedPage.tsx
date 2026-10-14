
import HistoryIcon from "@mui/icons-material/History";
import TuneIcon from "@mui/icons-material/Tune";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api} from "../api/client";

import BlindTeaserCard from "../components/BlindTeaserCard";
import MandateHistoryModal from "../components/MandateHistoryModal";
import {DigestCardDto} from "../api/types";

const DECLINE_REASONS = [
  { code: "sector", labelKey: "matching.reasons.sector" },
  { code: "stage", labelKey: "matching.reasons.stage" },
  { code: "region", labelKey: "matching.reasons.region" },
  { code: "ticket", labelKey: "matching.reasons.ticket" },
  { code: "team", labelKey: "matching.reasons.team" },
  { code: "metrics", labelKey: "matching.reasons.metrics" },
  { code: "other", labelKey: "matching.reasons.other" },
];

export default function InvestorFeedPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [cards, setCards] = useState<DigestCardDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Модалка для "Цікаво" (повідомлення до 500 символів)
  const [interestedModalOpen, setInterestedModalOpen] = useState(false);
  const [activeCardId, setActiveCardId] = useState<number | null>(null);
  const [investorMessage, setInvestorMessage] = useState("");

  // Модалка для "Ні" (причина відмови)
  const [declineModalOpen, setDeclineModalOpen] = useState(false);
  const [declineReason, setDeclineReason] = useState("sector");

  const loadFeed = async () => {
    try {
      setLoading(true);
      const data = await api.getInvestorFeed();
      // Показуємо тільки картки, на які ще немає відповіді
      setCards(
        data.filter(
          (c) =>
            !c.action ||
            c.action === "none" ||
            c.action.toUpperCase() === "SUGGESTED"
        )
      );
    } catch {
      // помилка
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFeed();
  }, []);

  // 1. Клік на "Цікаво" -> відкриваємо модалку для повідомлення
  const handleInterestedClick = (id: string) => {
    const card = cards.find((c) => c.id === id);
    if (!card) return;
    setActiveCardId(card.card_id);
    setInvestorMessage("");
    setInterestedModalOpen(true);
  };

  const handleConfirmInterested = async () => {
    if (!activeCardId) return;
    try {
      await api.respondToCard({
        card_id: activeCardId,
        action: "interested",
        investor_message: investorMessage.trim() || undefined,
      });
      setCards((prev) => prev.filter((c) => c.card_id !== activeCardId));
    } finally {
      setInterestedModalOpen(false);
      setActiveCardId(null);
    }
  };

  // 2. Клік на "Ні" -> відкриваємо модалку для вибору причини
  const handleDeclineClick = (id: string) => {
    const card = cards.find((c) => c.id === id);
    if (!card) return;
    setActiveCardId(card.card_id);
    setDeclineReason("sector");
    setDeclineModalOpen(true);
  };

  const handleConfirmDecline = async () => {
    if (!activeCardId) return;
    try {
      await api.respondToCard({
        card_id: activeCardId,
        action: "declined",
        decline_reason: declineReason,
      });
      setCards((prev) => prev.filter((c) => c.card_id !== activeCardId));
    } finally {
      setDeclineModalOpen(false);
      setActiveCardId(null);
    }
  };

  // Мапінг кодів причин "Чому ви це бачите" у зрозумілі рядки
  const formatMatchReasons = (codes: string[]) => {
    const mapping: Record<string, string> = {
      sector: t("matching.tags.sector", "Сектор"),
      stage: t("matching.tags.stage", "Стадія"),
      region: t("matching.tags.region", "Регіон"),
      check_size: t("matching.tags.ticket", "Розмір чека"),
      business_model: t("matching.tags.businessModel", "Бажана бізнес-модель"),
    };
    return (codes || []).map((code) => mapping[code] || code);
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 760, mx: "auto", py: 4 }}>
      {/* ШАПКА КАБІНЕТУ ТА НАВІГАЦІЯ */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
            {t("investor.cabinetTitle", "Кабінет інвестора")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("investor.cabinetSubtitle", "Щотижневі підбірки 3–5 сліпих тизерів за вашим мандатом.")}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<HistoryIcon />}
            onClick={() => setHistoryOpen(true)}
            sx={{ textTransform: "none" }}
          >
            {t("investor.mandateHistoryBtn", "Історія мандату [B]")}
          </Button>
          <Button
            variant="contained"
            size="small"
            startIcon={<TuneIcon />}
            onClick={() => navigate("/investor")}
            sx={{ textTransform: "none", bgcolor: "#17407a", "&:hover": { bgcolor: "#0b2142" } }}
          >
            {t("investor.editMandateBtn", "Налаштувати мандат")}
          </Button>
        </Stack>
      </Box>

      {/* ТАБИ: ДАЙДЖЕСТ ТА МАНДАТ */}
      <Tabs value={0} textColor="primary" indicatorColor="primary">
        <Tab label={t("investor.tabDigest", "Поточний дайджест (3–5 тизерів)")} sx={{ fontWeight: 700 }} />
      </Tabs>

      {/* ЛЕНТА КАРТОК */}
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : cards.length === 0 ? (
        <Alert severity="info" variant="outlined" sx={{ borderRadius: 2 }}>
          {t(
            "investor.emptyFeedAlert",
            "На цьому тижні немає нових тизерів або ви вже переглянули всі картки. Новий дайджест буде сформовано в понеділок о 08:00 (якщо буде від 3 до 5 відповідних проєктів)."
          )}
        </Alert>
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
              matchReasons={formatMatchReasons(card.match_reasons)}
              onInterested={handleInterestedClick}
              onDecline={handleDeclineClick}
            />
          ))}
        </Stack>
      )}

      {/* МОДАЛКА: «ЦІКАВО» (ПОВІДОМЛЕННЯ ДЛЯ ФАУНДЕРА ДО 500 СИМВОЛІВ) */}
      <Dialog open={interestedModalOpen} onClose={() => setInterestedModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: "#0b2142" }}>
          {t("matching.interestedModalTitle", "Виявити інтерес до стартапу")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t(
              "matching.interestedModalHint",
              "Стартап отримає запит з назвою вашого фонду. Ви можете додати коротке персональне повідомлення (опціонально):"
            )}
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            placeholder={t("matching.messagePlaceholder", "Наприклад: Цікавий проєкт, хотіли б поспілкуватися щодо бізнес-моделі...")}
            value={investorMessage}
            onChange={(e) => setInvestorMessage(e.target.value.slice(0, 500))}
            helperText={`${investorMessage.length}/500`}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setInterestedModalOpen(false)} color="inherit">
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button
            variant="contained"
            onClick={handleConfirmInterested}
            sx={{ bgcolor: "#17407a", "&:hover": { bgcolor: "#0b2142" } }}
          >
            {t("matching.sendInterestBtn", "Надіслати запит на інтро")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* МОДАЛКА: «НІ» (ВИБІР ПРИЧИНИ ВІДХИЛЕННЯ ДЛЯ ЗБОРУ ЗВОРОТНОГО ЗВ'ЯЗКУ) */}
      <Dialog open={declineModalOpen} onClose={() => setDeclineModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: "#0b2142" }}>
          {t("matching.declineTitle", "Чому цей проєкт не підійшов?")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("matching.declineHint", "Цей зворотний зв'язок допоможе оптимізувати наступні щотижневі дайджести.")}
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>{t("matching.reasonLabel", "Причина")}</InputLabel>
            <Select
              value={declineReason}
              label={t("matching.reasonLabel", "Причина")}
              onChange={(e) => setDeclineReason(e.target.value)}
            >
              {DECLINE_REASONS.map((r) => (
                <MenuItem key={r.code} value={r.code}>
                  {t(r.labelKey, r.code)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeclineModalOpen(false)} color="inherit">
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button onClick={handleConfirmDecline} variant="contained" color="error">
            {t("matching.declineBtn", "Відхилити проєкт")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* МОДАЛКА: ІСТОРІЯ ВЕРСІЙ МАНДАТУ [B] */}
      <MandateHistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />
    </Stack>
  );
}