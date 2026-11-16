import { Alert, Box, CircularProgress, Container, Paper, Typography } from "@mui/material";
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
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || "de";
  const [item, setItem] = useState<{ title: string; body: string } | null>(null);
  const [error, setError] = useState(false);
  const [isFallback, setIsFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setIsFallback(false);
    setItem(null);

    const key = CODE[(doc ?? "").toLowerCase()] ?? (doc ?? "").toUpperCase();

    const load = async (l: string) => {
      const r = await fetch(`/api/auth/legal-documents/?lang=${l}`);
      if (!r.ok) return null;
      const data = await r.json();
      return data[key] ?? null;
    };

    (async () => {
      try {
        let found = await load(lang);
        let fallback = false;
        if (!found && lang !== "de") {
          found = await load("de");
          fallback = !!found;
        }
        if (cancelled) return;
        if (found) {
          setItem(found);
          setIsFallback(fallback);
        } else {
          setError(true);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [doc, lang]);

  return (
    <Container maxWidth="md" sx={{ py: { xs: 2, md: 4 } }}>
      <Paper
        elevation={3}
        sx={{
          p: { xs: 2, md: 4 },
          bgcolor: "#fff",
          color: "#1a1a1a",
          borderRadius: 2,
          minHeight: 300,
        }}
      >
        {error ? (
          <Alert severity="error">Dokument nicht gefunden.</Alert>
        ) : !item ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {isFallback && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {t("legal.germanOnly")}
              </Alert>
            )}
            <Typography variant="h4" gutterBottom sx={{ color: "inherit" }}>
              {item.title}
            </Typography>
            <Typography sx={{ whiteSpace: "pre-wrap", color: "inherit" }}>
              {item.body}
            </Typography>
          </>
        )}
      </Paper>
    </Container>
  );
}