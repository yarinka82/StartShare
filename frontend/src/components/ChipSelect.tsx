import CheckIcon from "@mui/icons-material/Check";
import { Box, Button, Chip, FormControl, FormHelperText, FormLabel, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";

import type { Option } from "../api/types";

interface Props {
  label: string;
  options: Option[];
  value: string[];
  onChange: (value: string[]) => void;
  /** visible text of an option (translated by code) */
  optionLabel: (option: Option) => string;
  helperText?: string;
  error?: boolean;
  required?: boolean;
  /** show "select all / clear" (useful for long lists) */
  bulk?: boolean;
}

/** Multi-select as toggle chips: all options visible at once, one tap to (de)select. */
export default function ChipSelect({ label, options, value, onChange, optionLabel, helperText, error, required, bulk }: Props) {
  const { t } = useTranslation();
  const selected = new Set(value);
  const toggle = (code: string) =>
    onChange(options.map((o) => o.code).filter((c) => (c === code ? !selected.has(c) : selected.has(c))));

  return (
    <FormControl error={error} required={required} fullWidth component="fieldset" variant="standard">
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <FormLabel component="legend">{label}</FormLabel>
        {bulk && (
          <Box>
            <Button size="small" onClick={() => onChange(options.map((o) => o.code))}>{t("investor.selectAll")}</Button>
            <Button size="small" onClick={() => onChange([])} disabled={value.length === 0}>{t("investor.clear")}</Button>
          </Box>
        )}
      </Box>
      <Stack direction="row" useFlexGap sx={{ flexWrap: "wrap", gap: 1 }} role="group" aria-label={label}>
        {options.map((o) => {
          const on = selected.has(o.code);
          return (
            <Chip
              key={o.code}
              label={optionLabel(o)}
              clickable
              aria-pressed={on}
              color={on ? "primary" : "default"}
              variant={on ? "filled" : "outlined"}
              icon={on ? <CheckIcon /> : undefined}
              onClick={() => toggle(o.code)}
            />
          );
        })}
      </Stack>
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
}
