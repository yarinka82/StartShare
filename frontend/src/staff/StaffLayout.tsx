import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import GavelIcon from "@mui/icons-material/Gavel";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import PeopleOutlineIcon from "@mui/icons-material/PeopleOutlined";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";
import ShieldIcon from "@mui/icons-material/Shield";
import { Box, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router-dom";
import SidebarLayout, { type SidebarItem } from "../components/SidebarLayout";

export default function StaffLayout() {
  const { t } = useTranslation();

  const items: SidebarItem[] = [
    { key: "moderation", to: "/staff/dashboard", end: true, icon: <GavelIcon />,
      label: t("staff.dashboard.tabs.moderation", "Модерація DSA (ст. 16)") },
    { key: "users", to: "/staff/dashboard/users", icon: <PeopleOutlineIcon />,
      label: t("staff.dashboard.tabs.users", "Користувачі та Інвестори") },
    { key: "consents", to: "/staff/dashboard/consents", icon: <FactCheckOutlinedIcon />,
      label: t("staff.dashboard.tabs.consents", "Аудит згод (DSGVO)") },
    { key: "events", to: "/staff/dashboard/events", icon: <HistoryOutlinedIcon />,
      label: t("staff.dashboard.tabs.events", "Журнал подій (Audit Log)") },
    { key: "config", to: "/staff/dashboard/config", icon: <SettingsSuggestOutlinedIcon />,
      label: t("staff.dashboard.tabs.config", "Налаштування платформи") },
  ];

  return (
    <SidebarLayout items={items} ariaLabel={t("staff.dashboard.title", "Адміністративна панель платформи")}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <ShieldIcon sx={{ fontSize: 40, color: "primary.main" }} />
          <Box>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
              {t("staff.dashboard.title", "Адміністративна панель платформи")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("staff.dashboard.subtitle", "Керування комплаєнсом DSA, модерація користувачів та аудит за стандартами Німеччини.")}
            </Typography>
          </Box>
        </Box>
        <Outlet />
      </Stack>
    </SidebarLayout>
  );
}