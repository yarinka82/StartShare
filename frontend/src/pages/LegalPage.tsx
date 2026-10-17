
import { Alert, Box, CircularProgress, Container, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

const CODE: Record<string, string> = {
  agb: "AGB",
  datenschutz: "DSE",
  kriterien: "F",
};

export default function LegalPage() {
  const { doc } = useParams<{ doc: string }>();
  const { i18n } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || "de";
  const [item, setItem] = useState<{ title: string; body: string } | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    fetch(`/api/auth/legal-documents/?lang=${lang}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        const key = CODE[(doc ?? "").toLowerCase()] ?? (doc ?? "").toUpperCase();
        const found = data[key];
        if (!cancelled) found ? setItem(found) : setError(true);
      })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [doc, lang]);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {error ? (
        <Alert severity="error">Dokument nicht gefunden.</Alert>
      ) : !item ? (
        <Box sx={{ textAlign: "center" }}><CircularProgress /></Box>
      ) : (
        <>
          <Typography variant="h4" gutterBottom>{item.title}</Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>{item.body}</Typography>
        </>
      )}
    </Container>
  );
}