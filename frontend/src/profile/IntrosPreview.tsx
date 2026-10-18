import HandshakeIcon from "@mui/icons-material/Handshake";
import { Button, List, ListItemButton, ListItemText } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import { useIntros } from "./IntrosContext";
import SectionCard from "./SectionCard";

/** Overview block: shown only while there are requests waiting for a decision. */
export default function IntrosPreview() {
  const { t } = useTranslation();
  const { intros } = useIntros();
  if (intros.length === 0) return null;

  return (
    <SectionCard
      title={t("profile.overview.introsTitle", "Нові запити інвесторів")}
      hint={t("profile.overview.introsHint", "Потрібне ваше рішення")}
      icon={<HandshakeIcon fontSize="small" />}
    >
      <List disablePadding>
        {intros.slice(0, 3).map((i) => (
          <ListItemButton key={i.id} component={RouterLink} to="/profile/intros" sx={{ borderRadius: 1 }}>
            <ListItemText primary={i.investor_name} secondary={i.investor_type} />
          </ListItemButton>
        ))}
      </List>
      <Button variant="contained" size="small" component={RouterLink} to="/profile/intros" sx={{ mt: 1.5 }}>
        {t("profile.overview.introsAll", "Переглянути всі")} ({intros.length})
      </Button>
    </SectionCard>
  );
}