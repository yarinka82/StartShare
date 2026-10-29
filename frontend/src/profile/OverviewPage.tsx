import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ChecklistOutlinedIcon from "@mui/icons-material/ChecklistOutlined";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import {
  Box, Button, Chip, LinearProgress, List, ListItemButton, ListItemIcon, ListItemText, Stack, Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import IntrosPreview from "./IntrosPreview";
import SectionCard from "./SectionCard";
import { useProfile } from "./ProfileProvider";
import { missingCompany } from "./Sections";

export default function OverviewPage() {
  const { t } = useTranslation();
  const { meta, togglePause } = useProfile();
  const label = (n: string) => t(`profile.fields.${n}`);
  const missing = missingCompany(meta);

  const steps = [
    {
      key: "data", to: "/profile/company", done: missing.length === 0, focus: missing[0],
      title: t("profile.overview.stepData", "Заповнити дані компанії"),
      hint: missing.length ? missing.map(label).join(", ") : undefined,
    },
    {
      key: "deck", to: "/profile/deck", done: !!meta.deck,
      title: t("profile.overview.stepDeck", "Завантажити pitch deck"),
    },
    {
      key: "live", to: "/profile/teaser", done: meta.status === "LIVE",
      title: t("profile.overview.stepLive", "Затвердити тизер і опублікувати профіль"),
    },
  ];
  const progress = Math.round((steps.filter((s) => s.done).length / steps.length) * 100);

  return (
    <Stack spacing={3}>
      <Typography color="text.secondary">{t("profile.intro")}</Typography>

      <SectionCard
        title={t("profile.overview.status", "Статус профілю")}
        icon={<FlagOutlinedIcon fontSize="small" />}
      >
        <Stack direction="row" spacing={2} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap" }}>
          <Chip
            label={t(`profile.status.${meta.status}`)}
            color={meta.status === "LIVE" ? "success" : meta.status === "PAUSED" ? "warning" : meta.status === "REMOVED" ? "error" : "default"}
            sx={{ fontWeight: 700 }}
          />
          <Box sx={{ flexGrow: 1 }} />
          {meta.status === "LIVE" && (
            <Button variant="outlined" color="warning" size="small" onClick={togglePause}>
              {t("profile.actions.pause", "Поставити на паузу (PAUSE)")}
            </Button>
          )}
          {meta.status === "PAUSED" && (
            <Button variant="contained" color="success" size="small" onClick={togglePause}>
              {t("profile.actions.resume", "Відновити показ (LIVE)")}
            </Button>
          )}
          {meta.status === "REMOVED" && (
            <Button variant="contained" size="small" onClick={togglePause}>
              {t("profile.actions.restore", "Відновити профіль")}
            </Button>
          )}
        </Stack>
      </SectionCard>

      <IntrosPreview />

      <SectionCard
        title={t("profile.overview.readiness", "Готовність профілю")}
        hint={t("profile.overview.readinessHint", "Пройдіть кроки, щоб профіль потрапив до інвесторів")}
        icon={<ChecklistOutlinedIcon fontSize="small" />}
      >
        <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 4, mb: 1 }} />
        <Typography variant="body2" color="text.secondary">{progress}%</Typography>
        <List disablePadding sx={{ mt: 1 }}>
          {steps.map((s) => (
            <ListItemButton
              key={s.key} component={RouterLink} to={s.to}
              state={s.focus ? { focus: s.focus } : undefined}
              sx={{ borderRadius: 1 }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                {s.done ? <CheckCircleIcon color="success" /> : <RadioButtonUncheckedIcon color="disabled" />}
              </ListItemIcon>
              <ListItemText primary={s.title} secondary={s.hint} />
            </ListItemButton>
          ))}
        </List>
      </SectionCard>
    </Stack>
  );
}