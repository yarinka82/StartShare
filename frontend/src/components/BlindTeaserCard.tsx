
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ThumbDownOutlinedIcon from "@mui/icons-material/ThumbDownOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import {
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

interface BlindTeaserProps {
  id: string;
  sector: string;
  stage: string;
  region: string;
  targetAmountEur: number;
  mrrEur?: number;
  teamSize?: number;
  headline: string;
  problemSolution: string;
  teamSummary: string;
  matchReasons: string[]; // Например: ["Сектор: B2B SaaS", "Стадия: Seed", "Регион: DACH"]
  onInterested: (id: string) => void;
  onDecline: (id: string) => void;
}

export default function BlindTeaserCard({
  id,
  sector,
  stage,
  region,
  targetAmountEur,
  mrrEur,
  teamSize,
  headline,
  problemSolution,
  teamSummary,
  matchReasons,
  onInterested,
  onDecline,
}: BlindTeaserProps) {
  const { t } = useTranslation();

  return (
    <Paper
      elevation={2}
      sx={{
        p: { xs: 2.5, sm: 3.5 },
        borderRadius: 3,
        maxWidth: 680,
        width: "100%",
        mx: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 2.5,
        border: "1px solid #e2e8f0",
      }}
    >
      {/* 1. ШАПКА: Жесткие фильтры (ЧИПСЫ) */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1 }}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          <Chip label={sector} color="primary" variant="filled" size="small" sx={{ fontWeight: 600 }} />
          <Chip label={stage} variant="outlined" size="small" />
          <Chip label={region} variant="outlined" size="small" />
        </Stack>

        <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#17407a" }}>
          €{(targetAmountEur / 1_000).toLocaleString()}k Seek
        </Typography>
      </Box>

      {/* 2. СТРОКА: "Почему вы это видите" (ТЗ: прозрачный матчинг) */}
      {matchReasons.length > 0 && (
        <Box sx={{ bgcolor: "#f8fafc", p: 1.5, borderRadius: 1.5, borderLeft: "3px solid #17407a" }}>
          <Typography variant="caption" sx={{ color: "text.secondary", display: "block", fontWeight: 600, mb: 0.25 }}>
            {t("matching.whyYouSeeThis", "Warum Sie dieses Profil sehen:")}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: "0.8rem", color: "#334155" }}>
            ✓ {matchReasons.join(" • ")}
          </Typography>
        </Box>
      )}

      {/* 3. АНОНИМНЫЙ КОНТЕНТ (Сгенерированный ШИ) */}
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "#0f172a", mb: 1 }}>
          {headline}
        </Typography>
        <Typography variant="body2" sx={{ color: "#334155", lineHeight: 1.6, mb: 2 }}>
          {problemSolution}
        </Typography>

        {/* Метрики в плашке */}
        <Box sx={{ display: "flex", gap: 3, py: 1.5, px: 2, bgcolor: "#f1f5f9", borderRadius: 2, mb: 2 }}>
          {mrrEur !== undefined && (
            <Box>
              <Typography variant="caption" color="text.secondary">MRR</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>€{mrrEur.toLocaleString()}</Typography>
            </Box>
          )}
          {teamSize && (
            <Box>
              <Typography variant="caption" color="text.secondary">Team</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{teamSize} FTE</Typography>
            </Box>
          )}
        </Box>

        <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase" }}>
          Team Background (anonymisiert)
        </Typography>
        <Typography variant="body2" sx={{ color: "#475569", mt: 0.5 }}>
          {teamSummary}
        </Typography>
      </Box>

      <Divider />

      {/* 4. КНОПКИ ДЕЙСТВИЯ */}
      <Stack direction="row" spacing={2} sx={{ pt: 0.5 }}>
        <Button
          variant="contained"
          fullWidth
          size="large"
          startIcon={<ThumbUpAltIcon />}
          onClick={() => onInterested(id)}
          sx={{
            bgcolor: "#17407a",
            fontWeight: 700,
            textTransform: "none",
            "&:hover": { bgcolor: "#0b2142" },
          }}
        >
          {t("matching.interested", "Interessiert")}
        </Button>
        <Button
          variant="outlined"
          color="inherit"
          fullWidth
          size="large"
          startIcon={<ThumbDownOutlinedIcon />}
          onClick={() => onDecline(id)}
          sx={{ textTransform: "none", color: "#64748b" }}
        >
          {t("matching.decline", "Nein")}
        </Button>
      </Stack>

      {/* 5. ВОТ ЗДЕСЬ СТОИТ ДИСКЛЕЙМЕР B (Текст B) */}
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          gap: 1,
          pt: 1,
          borderTop: "1px dashed #e2e8f0",
        }}
      >
        <InfoOutlinedIcon sx={{ fontSize: 15, color: "#94a3b8", mt: 0.2, flexShrink: 0 }} />
        <Typography
          variant="caption"
          sx={{
            color: "#64748b",
            fontSize: "0.72rem",
            lineHeight: 1.4,
            fontStyle: "italic",
          }}
        >
          {t("teaser.disclaimer")}
        </Typography>
      </Box>
    </Paper>
  );
}