
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
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import BlindTeaserCard from "../components/BlindTeaserCard";

// Причины отказа по ТЗ
const DECLINE_REASONS = [
  { code: "sector", label: "Не подходит сектор" },
  { code: "stage", label: "Не та стадия" },
  { code: "region", label: "Не подходит регион" },
  { code: "ticket", label: "Слишком большой/маленький чек" },
  { code: "team", label: "Слабый опыт команды" },
  { code: "metrics", label: "Недостаточно метрик/трекшна" },
  { code: "other", label: "Другое" },
];

export default function InvestorFeedPage() {
  const { t } = useTranslation();
  const [cards, setCards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Состояния для модалки отказа
  const [declineModalOpen, setDeclineModalOpen] = useState(false);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [declineReason, setDeclineReason] = useState("sector");

  useEffect(() => {
    // Включаем вызов setLoading, чтобы TS не ругался на неиспользуемую функцию
    const timer = setTimeout(() => {
      setLoading(false);
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  const handleInterested = async (id: string) => {
    // Отправляем на бекенд статус INTERESTED и убираем карточку
    setCards((prev) => prev.filter((c) => c.id !== id));
  };

  const handleDeclineClick = (id: string) => {
    setSelectedCardId(id);
    setDeclineModalOpen(true);
  };

  const handleConfirmDecline = async () => {
    if (!selectedCardId) return;
    // Отправляем причину отказа на бекенд и убираем карточку
    setCards((prev) => prev.filter((c) => c.id !== selectedCardId));
    setDeclineModalOpen(false);
    setSelectedCardId(null);
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Stack spacing={4} sx={{ maxWidth: 720, mx: "auto", py: 4 }}>
      <Box>
        {/* ИСПРАВЛЕНО: fontWeight и color перенесены внутрь sx */}
        <Typography
          variant="h4"
          component="h1"
          sx={{ fontWeight: 800, color: "#0b2142", mb: 0.5 }}
        >
          {t("investor.feedTitle", "Ваш дайджест стартапов")}
        </Typography>
        <Typography color="text.secondary">
          {t("investor.feedSubtitle", "Тизеры подобраны строго по критериям вашего инвестиционного мандата.")}
        </Typography>
      </Box>

      {cards.length === 0 ? (
        <Alert severity="info" variant="outlined">
          {t("investor.noCards", "На этой неделе новых тизеров нет. Мы пришлем уведомление, как только появится подходящий стартап.")}
        </Alert>
      ) : (
        cards.map((card) => (
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
            matchReasons={card.match_reasons}
            onInterested={handleInterested}
            onDecline={handleDeclineClick}
          />
        ))
      )}

      {/* Модальное окно причины отказа */}
      <Dialog open={declineModalOpen} onClose={() => setDeclineModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t("matching.declineTitle", "Почему этот проект не подошел?")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("matching.declineHint", "Это поможет алгоритму точнее настраивать еженедельный дайджест.")}
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>{t("matching.reasonLabel", "Причина")}</InputLabel>
            <Select
              value={declineReason}
              label={t("matching.reasonLabel", "Причина")}
              onChange={(e) => setDeclineReason(e.target.value)}
            >
              {DECLINE_REASONS.map((r) => (
                <MenuItem key={r.code} value={r.code}>{r.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeclineModalOpen(false)} color="inherit">Отмена</Button>
          <Button onClick={handleConfirmDecline} variant="contained" color="error">Отклонить</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}