import { ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useTranslation } from "react-i18next";

import { LANGUAGES } from "../i18n";

/** `onDark` = white text for the blue app bar; set to false on light backgrounds. */
export default function LanguageSwitcher({ onDark = true }: { onDark?: boolean }) {
  const { i18n, t } = useTranslation();
  return (
    <ToggleButtonGroup
      size="small"
      exclusive
      value={i18n.resolvedLanguage}
      onChange={(_, code: string | null) => code && i18n.changeLanguage(code)}
      aria-label={t("nav.language")}
      sx={
        onDark
          ? { bgcolor: "rgba(255,255,255,0.12)", "& .MuiToggleButton-root": { color: "inherit", px: 1.2, py: 0.3 } }
          : { "& .MuiToggleButton-root": { px: 1.2, py: 0.3 } }
      }
    >
      {LANGUAGES.map((l) => (
        <ToggleButton key={l.code} value={l.code}>
          {l.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
