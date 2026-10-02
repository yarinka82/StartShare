import { Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function InvestorHomePage() {
  const { t } = useTranslation();
  return (
    <Paper variant="outlined" sx={{ p: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        {t("investor.title")}
      </Typography>
      <Typography color="text.secondary">{t("investor.text")}</Typography>
    </Paper>
  );
}
