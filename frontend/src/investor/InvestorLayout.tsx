import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import DynamicFeedOutlinedIcon from "@mui/icons-material/DynamicFeedOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import VerifiedUserOutlinedIcon from "@mui/icons-material/VerifiedUserOutlined";
import { Badge } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Outlet, useLocation } from "react-router-dom";
import SidebarLayout, { type SidebarItem } from "../components/SidebarLayout";
import { InvestorProvider, useInvestor } from "./InvestorProvider";
import StatusConfirm from "./StatusConfirm";
import {FeedProvider, useFeed} from "./FeedContext";

/** Navigation of a confirmed investor; the feed icon shows how many teasers wait for an answer. */
function ConfirmedShell() {
  const { t } = useTranslation();
  const { cards } = useFeed();

  const items: SidebarItem[] = [
    { key: "mandate", to: "/investor", end: true, icon: <AssignmentOutlinedIcon />, label: t("nav.mandate", "Мандат") },
    {
      key: "feed", to: "/investor/feed", label: t("nav.digest", "Дайджест"),
      icon: <Badge badgeContent={cards.length} color="success"><DynamicFeedOutlinedIcon /></Badge>,
    },
    { key: "privacy", to: "/investor/privacy", icon: <ShieldOutlinedIcon />, label: t("profile.nav.privacy", "Конфіденційність") },
  ];

  return (
    <SidebarLayout items={items} ariaLabel={t("investor.mandate.title")}>
      <Outlet />
    </SidebarLayout>
  );
}

function Shell() {
  const { t } = useTranslation();
  const { state } = useInvestor();
  const { pathname } = useLocation();

  // Step 1 (legal text C) comes first. Until it is confirmed only the status step and
  // privacy (data export / account deletion, GDPR) are reachable.
  if (!state.status_confirmed) {
    const items: SidebarItem[] = [
      {
        key: "status", to: "/investor", end: true, icon: <VerifiedUserOutlinedIcon />,
        label: t("investor.nav.status", "Підтвердження статусу"),
      },
      {
        key: "privacy", to: "/investor/privacy", icon: <ShieldOutlinedIcon />,
        label: t("profile.nav.privacy", "Конфіденційність"),
      },
    ];
    return (
      <SidebarLayout items={items} ariaLabel={t("investor.mandate.title")}>
        {pathname === "/investor/privacy" ? <Outlet /> : <StatusConfirm />}
      </SidebarLayout>
    );
  }

  return (
    <FeedProvider>
      <ConfirmedShell />
    </FeedProvider>
  );
}

export default function InvestorLayout() {
  return (
    <InvestorProvider>
      <Shell />
    </InvestorProvider>
  );
}