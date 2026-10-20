import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import { Alert, Badge, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router-dom";
import SidebarLayout, { type SidebarItem } from "../components/SidebarLayout";

import {missingCompany} from "../components/Sections";
import {Meta, ProfileProvider, useProfile} from "../profile/ProfileProvider";
import {IntrosProvider, useIntros} from "../profile/IntrosContext";

type NavStatus = "done" | "todo" | "locked" | null;
type NavDef = { key: string; to: string; end?: boolean; icon: ReactElement; status: (m: Meta) => NavStatus };

const NAV: NavDef[] = [
  { key: "overview", to: "/profile", end: true, icon: <DashboardOutlinedIcon />, status: () => null },
  { key: "company", to: "/profile/company", icon: <BusinessOutlinedIcon />,
    status: (m) => (missingCompany(m).length ? "todo" : "done") },
  { key: "deck", to: "/profile/deck", icon: <DescriptionOutlinedIcon />,
    status: (m) => (m.deck ? "done" : "todo") },
  { key: "teaser", to: "/profile/teaser", icon: <AutoAwesomeOutlinedIcon />,
    status: (m) => (m.deck ? null : "locked") },
  { key: "intros", to: "/profile/intros", icon: <InboxOutlinedIcon />, status: () => null },
  { key: "privacy", to: "/profile/privacy", icon: <ShieldOutlinedIcon />, status: () => null },
];

const NAV_DEFAULTS: Record<string, string> = {
  overview: "Огляд",
  company: "Дані компанії",
  deck: "Pitch Deck",
  teaser: "Blind-Teaser",
  intros: "Запити інвесторів",
  privacy: "Конфіденційність",
};

function StatusMark({ status }: { status: NavStatus }) {
  if (status === "done") return <CheckCircleIcon fontSize="small" color="success" />;
  if (status === "todo") return <FiberManualRecordIcon sx={{ fontSize: 12 }} color="warning" />;
  if (status === "locked") return <LockOutlinedIcon fontSize="small" color="disabled" />;
  return null;
}

function SaveIndicator() {
  const { t } = useTranslation();
  const { saveState } = useProfile();
  return (
    <Typography variant="body2" color="text.secondary" sx={{ display: "flex", alignItems: "center", gap: 0.75, minHeight: 24 }}>
      {{
        idle: null,
        saving: <><CircularProgress size={14} /> {t("profile.saving")}</>,
        saved: <><CheckCircleIcon fontSize="inherit" color="success" /> {t("profile.saved")}</>,
        error: <><ErrorOutlineIcon fontSize="inherit" color="error" /> {t("profile.saveError")}</>,
      }[saveState]}
    </Typography>
  );
}

function Shell() {
  const { t } = useTranslation();
  const { meta } = useProfile();
  const { intros } = useIntros();

  const items: SidebarItem[] = NAV.map((n) => ({
    key: n.key,
    to: n.to,
    end: n.end,
    label: t(`profile.nav.${n.key}`, NAV_DEFAULTS[n.key]),
    icon: n.key === "intros" ? <Badge badgeContent={intros.length} color="success">{n.icon}</Badge> : n.icon,
    trailing: <StatusMark status={n.status(meta)} />,
  }));

  return (
    <SidebarLayout items={items} ariaLabel={t("profile.title")}>
      <Stack spacing={3}>
        <Stack
          direction="row" spacing={2} useFlexGap
          sx={{ alignItems: "center", flexWrap: "wrap", position: "sticky", top: 0, zIndex: 10, bgcolor: "grey.100", py: 1.5 }}
        >
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1, fontWeight: 800, color: "#0b2142" }}>
            {t("profile.title")}
          </Typography>
          <SaveIndicator />
          <Chip
            label={t(`profile.status.${meta.status}`)}
            color={meta.status === "LIVE" ? "success" : meta.status === "PAUSED" ? "warning" : meta.status === "REMOVED" ? "error" : "default"}
            sx={{ fontWeight: 700 }}
          />
        </Stack>

        {meta.status === "PAUSED" && (
          <Alert severity="warning">
            {t("profile.pausedAlert", "Ваш профіль зараз на паузі. Інвестори не бачать ваш тизер у щотижневих дайджестах.")}
          </Alert>
        )}
        {meta.status === "REMOVED" && (
          <Alert severity="error">
            {t("profile.removedAlert", "Профіль видалено з платформи (REMOVED). Показ інвесторам зупинено.")}
          </Alert>
        )}

        <Outlet />
      </Stack>
    </SidebarLayout>
  );
}

export default function ProfileLayout() {
  return (
    <ProfileProvider>
      <IntrosProvider>
        <Shell />
      </IntrosProvider>
    </ProfileProvider>
  );
}