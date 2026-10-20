import { Alert, Box, Button, CircularProgress, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { LegalItem } from "../hooks/useLegalDocument";

/** Loading / error / text of a legal document. Shared by the full page and the registration dialog. */
export default function LegalBody({ item, loading, error, onRetry, lang }: {
  item: LegalItem | null; loading: boolean; error: boolean; onRetry: () => void; lang: string;
}) {
  const { t } = useTranslation();

  if (error) {
    return (
      <Alert
        severity="error"
        action={<Button color="inherit" size="small" onClick={onRetry}>{t("common.tryAgain", "Erneut versuchen")}</Button>}
      >
        {t("legal.notFound", "Dokument nicht gefunden.")}
      </Alert>
    );
  }
  if (loading || !item) {
    return <Box sx={{ textAlign: "center", py: 4 }}><CircularProgress /></Box>;
  }
  return (
    // lang: screen readers and hyphenation need to know the language of the legal text
    <Typography lang={lang} sx={{ whiteSpace: "pre-wrap", lineHeight: 1.75, fontSize: "0.97rem", color: "#1e293b" }}>
      {item.body}
    </Typography>
  );
}