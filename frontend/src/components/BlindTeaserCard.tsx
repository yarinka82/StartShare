import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ThumbDownOutlinedIcon from "@mui/icons-material/ThumbDownOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import {
  Box, Button, Chip, Divider, IconButton, Paper, Stack, Tooltip, Typography,
} from "@mui/material";
import type { TFunction } from "i18next";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ReportModal from "./ReportModal";

// codes -> readable labels (kept outside the component so it is not recreated on every render)
function formatMatchReasons(codes: string[] | undefined, t: TFunction): string[] {
  const labels: Record<string, string> = {
    sector: t("matching.matchLabels.sector"),
    stage: t("matching.matchLabels.stage"),
    check_size: t("matching.matchLabels.ticket"),
    region: t("matching.matchLabels.region"),
    business_model: t("matching.matchLabels.businessModel"),
  };
  return (codes ?? []).map((c) => labels[c] || c);
}

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
  /** raw reason codes, e.g. ["sector", "stage", "region"]; the card translates them itself */
  matchReasons: string[];
  onInterested: (id: string) => void;
  onDecline: (id: string) => void;
}

export default function BlindTeaserCard({
  id, sector, stage, region, targetAmountEur, mrrEur, teamSize,
  headline, problemSolution, teamSummary, matchReasons, onInterested, onDecline,
}: BlindTeaserProps) {
  const { t, i18n } = useTranslation();
  const [reportOpen, setReportOpen] = useState(false);
  const formattedReasons = useMemo(() => formatMatchReasons(matchReasons, t), [matchReasons, t]);
  const number = (n: number) => Number(n).toLocaleString(i18n.resolvedLanguage);
  const hasMetrics = mrrEur != null || teamSize != null;

  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 2.5, sm: 3.5 }, borderRadius: 3, width: "100%",
        display: "flex", flexDirection: "column", gap: 2.5,
        border: "1px solid", borderColor: "divider",
        boxShadow: "0 1px 2px rgba(16,24,40,0.04), 0 4px 12px rgba(16,24,40,0.04)",
      }}
    >
      {/* 1. Hard filters (chips), amount and report button */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1 }}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          <Chip label={sector} color="primary" variant="filled" size="small" sx={{ fontWeight: 600 }} />
          <Chip label={stage} variant="outlined" size="small" />
          <Chip label={region} variant="outlined" size="small" />
        </Stack>

        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#17407a" }}>
            {t("teaser.seekAmount", "€{{amount}}k Seek", {
              amount: targetAmountEur != null ? number(Math.round(Number(targetAmountEur) / 1_000)) : 0,
            })}
          </Typography>
          {/* Report button (DSA Art. 16) */}
          <Tooltip title={t("dsa.reportTooltip", "Profil melden (Art. 16 DSA)")}>
            <IconButton
              size="small"
              aria-label={t("dsa.reportTooltip", "Profil melden (Art. 16 DSA)")}
              onClick={() => setReportOpen(true)}
              sx={{ color: "#94a3b8", "&:hover": { color: "#dc2626" } }}
            >
              <FlagOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* 2. "Why you see this" */}
      {formattedReasons.length > 0 && (
        <Box sx={{ bgcolor: "#f8fafc", p: 1.5, borderRadius: 1.5, borderLeft: "3px solid #17407a" }}>
          <Typography variant="caption" sx={{ color: "text.secondary", display: "block", fontWeight: 600, mb: 0.25 }}>
            {t("matching.whyYouSeeThis", "Warum Sie dieses Profil sehen:")}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: "0.8rem", color: "#334155" }}>
            ✓ {formattedReasons.join(" • ")}
          </Typography>
        </Box>
      )}

      {/* 3. Anonymous content */}
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "#0f172a", mb: 1 }}>{headline}</Typography>
        <Typography variant="body2" sx={{ color: "#334155", lineHeight: 1.6, mb: 2 }}>{problemSolution}</Typography>

        {hasMetrics && (
          <Box sx={{ display: "flex", gap: 3, py: 1.5, px: 2, bgcolor: "#f1f5f9", borderRadius: 2, mb: 2 }}>
            {mrrEur != null && (
              <Box>
                <Typography variant="caption" color="text.secondary">{t("teaser.mrr", "MRR")}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>€{number(mrrEur)}</Typography>
              </Box>
            )}
            {teamSize != null && (
              <Box>
                <Typography variant="caption" color="text.secondary">{t("teaser.team", "Team")}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {t("teaser.fte", "{{count}} FTE", { count: teamSize })}
                </Typography>
              </Box>
            )}
          </Box>
        )}

        <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase" }}>
          {t("teaser.teamBackground", "Team Background (anonymisiert)")}
        </Typography>
        <Typography variant="body2" sx={{ color: "#475569", mt: 0.5 }}>{teamSummary}</Typography>
      </Box>

      <Divider />

      {/* 4. Actions */}
      <Stack direction="row" spacing={2} sx={{ pt: 0.5 }}>
        <Button
          variant="contained" fullWidth size="large" startIcon={<ThumbUpAltIcon />}
          onClick={() => onInterested(id)}
          sx={{ fontWeight: 700 }}
        >
          {t("matching.interested", "Interessiert")}
        </Button>
        <Button
          variant="outlined" color="inherit" fullWidth size="large" startIcon={<ThumbDownOutlinedIcon />}
          onClick={() => onDecline(id)}
          sx={{ textTransform: "none", color: "#64748b" }}
        >
          {t("matching.decline", "Nein")}
        </Button>
      </Stack>

      {/* 5. Disclaimer */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, pt: 1, borderTop: "1px dashed #e2e8f0" }}>
        <InfoOutlinedIcon sx={{ fontSize: 15, color: "#94a3b8", mt: 0.2, flexShrink: 0 }} />
        <Typography variant="caption" sx={{ color: "#64748b", fontSize: "0.72rem", lineHeight: 1.4, fontStyle: "italic" }}>
          {t("teaser.disclaimer")}
        </Typography>
      </Box>

      <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} startupPublicId={id} />
    </Paper>
  );
}