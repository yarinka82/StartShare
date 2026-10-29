import { Box, MenuItem, Stack, TextField } from "@mui/material";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { NumberField, SelectField } from "./FormFields";
import { useProfile } from "./ProfileProvider";
import SectionCard from "./SectionCard";

const grid = { display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } } as const;

export default function CompanyPage() {
  const { t } = useTranslation();
  const { values, dicts, fieldErrors, change } = useProfile();
  const { state } = useLocation() as { state: { focus?: string } | null };

  // arriving from the checklist: scroll to and focus the first missing field
  useEffect(() => {
    const name = state?.focus;
    if (!name) return;
    const root = document.querySelector<HTMLElement>(`[data-field="${name}"]`);
    root?.scrollIntoView({ behavior: "smooth", block: "center" });
    root?.querySelector<HTMLElement>("input, [role='combobox'], [tabindex='0']")?.focus({ preventScroll: true });
  }, [state]);

  return (
    <Stack spacing={3}>
      <SectionCard
        title={t("profile.sections.basics")}
        hint={t("profile.hints.basics", "Галузь, стадія, країна та обсяг залучення")}
        icon={<BusinessOutlinedIcon fontSize="small" />}
      >
        <Box sx={grid}>
          <TextField
            label={t("profile.fields.company_name") + ` (${t("profile.optional")})`}
            value={values.company_name}
            onChange={(e) => change("company_name", e.target.value)}
            helperText={t("profile.companyHelper")}
            slotProps={{ htmlInput: { maxLength: 200 } }}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          />
          <SelectField name="sector" items={dicts.sectors} kind="sectors" />
          <SelectField name="stage" items={dicts.stages} kind="stages" />
          <SelectField name="business_model" items={dicts.business_models} kind="businessModels" optional />
          <SelectField name="country" items={dicts.countries} kind="countries" />
          <NumberField name="amount_sought" eur required />
          <NumberField name="team_size" required />
        </Box>
      </SectionCard>

      <SectionCard
        title={t("profile.sections.metrics")}
        hint={t("profile.hints.metrics", "Необов’язкові показники: MRR та зростання")}
        icon={<InsightsOutlinedIcon fontSize="small" />}
      >
        <Box sx={grid}>
          <NumberField name="mrr" eur optional />
          <Box />
          <NumberField name="growth_percent" percent optional />
          <TextField
            data-field="growth_period"
            select
            label={t("profile.fields.growth_period")}
            value={values.growth_period}
            onChange={(e) => change("growth_period", e.target.value)}
            error={!!fieldErrors.growth_period}
            helperText={fieldErrors.growth_period}
          >
            <MenuItem value=""><em>—</em></MenuItem>
            {dicts.growth_periods.map((g) => (
              <MenuItem key={g.code} value={g.code}>
                {t(`profile.growthPeriods.${g.code}`, { defaultValue: g.name })}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      </SectionCard>
    </Stack>
  );
}