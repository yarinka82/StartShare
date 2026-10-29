import { Box, Paper, Typography } from "@mui/material";
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import LegalBody from "./LegalBody";
import { useLegalDocument } from "../hooks/useLegalDocument";

export default function LegalPage() {
  const { doc } = useParams<{ doc: string }>();
  const { item, loading, error, retry, lang } = useLegalDocument(doc);

  // the browser tab / search engines should show the document's name
  useEffect(() => {
    if (!item?.title) return;
    const previous = document.title;
    document.title = item.title;
    return () => { document.title = previous; };
  }, [item?.title]);

  return (
    // Layout already provides the Container, so no second one here
    <Paper variant="outlined" sx={{ p: { xs: 2.5, sm: 5 }, borderRadius: 3, bgcolor: "background.paper" }}>
      <Box sx={{ maxWidth: 760, mx: "auto" }}>
        {item && (
          <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 800, color: "#0b2142", mb: 3 }}>
            {item.title}
          </Typography>
        )}
        <LegalBody item={item} loading={loading} error={error} onRetry={retry} lang={lang} />
      </Box>
    </Paper>
  );
}