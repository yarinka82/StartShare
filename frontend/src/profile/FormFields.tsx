import { InputAdornment, MenuItem, TextField } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { Option } from "../api/types";
import { useProfile, type Name } from "./ProfileProvider";

export type DictKind = "sectors" | "stages" | "businessModels" | "countries";

export function SelectField({ name, items, kind, optional = false }: {
  name: Name; items: Option[]; kind: DictKind; optional?: boolean;
}) {
  const { t } = useTranslation();
  const { values, fieldErrors, change } = useProfile();
  return (
    <TextField
      data-field={name}
      select
      label={t(`profile.fields.${name}`) + (optional ? ` (${t("profile.optional")})` : "")}
      // a value that was removed from the approved list is shown as "not chosen"
      value={items.some((i) => i.code === values[name]) ? values[name] : ""}
      required={!optional}
      onChange={(e) => change(name, e.target.value)}
      error={!!fieldErrors[name]} helperText={fieldErrors[name]}
    >
      {optional && <MenuItem value=""><em>—</em></MenuItem>}
      {items.map((i) => (
        <MenuItem key={i.code} value={i.code}>
          {t(`dict.${kind}.${i.code}`, { defaultValue: i.name })}
        </MenuItem>
      ))}
    </TextField>
  );
}

export function NumberField({ name, eur, percent, optional, required }: {
  name: Name; eur?: boolean; percent?: boolean; optional?: boolean; required?: boolean;
}) {
  const { t } = useTranslation();
  const { values, fieldErrors, change } = useProfile();
  return (
    <TextField
      data-field={name}
      label={t(`profile.fields.${name}`) + (optional ? ` (${t("profile.optional")})` : "")}
      value={values[name]} required={required}
      onChange={(e) => change(name, e.target.value)}
      error={!!fieldErrors[name]} helperText={fieldErrors[name]}
      slotProps={{
        htmlInput: { inputMode: name === "team_size" ? "numeric" : "decimal" },
        input: {
          endAdornment: eur ? <InputAdornment position="end">{t("common.eur")}</InputAdornment>
            : percent ? <InputAdornment position="end">%</InputAdornment> : undefined,
        },
      }}
    />
  );
}