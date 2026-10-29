import HandshakeIcon from "@mui/icons-material/Handshake";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import EmptyState from "../components/EmptyState";
import IntroCard from "./IntroCard";
import { useIntros } from "./IntrosContext";

export default function IntrosPage() {
  const { t } = useTranslation();
  const { intros, loading, error, busyId, reload, respond } = useIntros();

  if (loading && intros.length === 0) {
    return <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
      <Alert severity="error" action={<Button color="inherit" size="small" onClick={() => void reload()}>
        {t("common.tryAgain", "Повторити")}
      </Button>}>
        {t("freigabeRequests.loadError", "Не вдалося завантажити запити.")}
      </Alert>
    );
  }

  if (intros.length === 0) {
    return (
      <EmptyState
        icon={<HandshakeIcon />}
        title={t("freigabeRequests.emptyTitle", "Запитів поки немає")}
        text={t("freigabeRequests.emptyText", "Коли інвестор захоче познайомитися, запит з’явиться тут. Контакти відкриваються лише після вашого рішення.")}
      />
    );
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h6" component="h2" sx={{ fontWeight: 800, color: "#166534", display: "flex", alignItems: "center", gap: 1 }}>
        <HandshakeIcon /> {t("freigabeRequests.sectionTitle", "Вхідні запити на знайомство (Freigabe)")}
      </Typography>
      {intros.map((item) => (
        <IntroCard key={item.id} item={item} busy={busyId === item.id} onRespond={respond} />
      ))}
    </Stack>
  );
}