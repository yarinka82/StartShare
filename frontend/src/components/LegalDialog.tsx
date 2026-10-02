import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useRef } from "react";
import { useTranslation } from "react-i18next";

export type LegalDoc = "agb" | "datenschutz";

/**
 * Shows a legal document on top of the registration form, so the user never loses what they typed.
 * Placeholder text until legal counsel provides the real documents.
 */
export default function LegalDialog({ doc, onClose }: { doc: LegalDoc | null; onClose: () => void }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const last = useRef<LegalDoc>("agb"); // keeps the title while the closing animation runs
  if (doc) last.current = doc;
  const shown = last.current;

  return (
    <Dialog open={doc !== null} onClose={onClose} fullScreen={fullScreen} fullWidth maxWidth="md" scroll="paper">
      <DialogTitle>{t(`legal.${shown}`)}</DialogTitle>
      <DialogContent dividers>
        <Alert severity="info">{t("legal.placeholder")}</Alert>
      </DialogContent>
      <DialogActions>
        <Button component="a" href={`/legal/${shown}`} target="_blank" rel="noopener" startIcon={<OpenInNewIcon />}>
          {t("legal.openInNewTab")}
        </Button>
        <Button variant="contained" onClick={onClose}>{t("legal.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
