import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLegalDocument } from "../hooks/useLegalDocument";
import LegalBody from "./LegalBody";

export type LegalDoc = "agb" | "datenschutz";

/**
 * Shows a legal document on top of the registration form, so the user never loses what they typed.
 * It shows the real text (the same one as the /legal/... page), not a placeholder.
 */
export default function LegalDialog({ doc, onClose }: { doc: LegalDoc | null; onClose: () => void }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const last = useRef<LegalDoc>("agb"); // keeps the content while the closing animation runs
  if (doc) last.current = doc;
  const shown = last.current;

  const { item, loading, error, retry, lang } = useLegalDocument(doc ? shown : null);

  return (
    <Dialog open={doc !== null} onClose={onClose} fullScreen={fullScreen} fullWidth maxWidth="md" scroll="paper">
      <DialogTitle>{item?.title ?? t(`legal.${shown}`)}</DialogTitle>
      <DialogContent dividers>
        <LegalBody item={item} loading={loading} error={error} onRetry={retry} lang={lang} />
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