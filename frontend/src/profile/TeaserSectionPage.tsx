import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import { Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import type { Deck } from "../api/types";
import EmptyState from "../components/EmptyState";
import { TeaserPage } from "../teaser";
import "../teaser/editor.css";
import { useProfile } from "./ProfileProvider";
import SectionCard from "../components/SectionCard";


export default function TeaserSectionPage() {
  const { t } = useTranslation();
  const { meta, readOnly, refreshMeta } = useProfile();
  const navigate = useNavigate();

  if (readOnly) {
    return (
      <EmptyState
        icon={<AutoAwesomeOutlinedIcon />}
        title={t("profile.teaserRemoved.title", "Профіль видалено")}
        text={t("profile.teaserRemoved.text", "Редагування тизера для видаленого профілю недоступне.")}
      />
    );
  }

  if (!meta.deck) {
    return (
      <EmptyState
        icon={<AutoAwesomeOutlinedIcon />}
        title={t("profile.teaserEmpty.title", "Тизера ще немає")}
        text={t("profile.teaserNeedsDeck", "Тизер створюється на основі деку. Спочатку завантажте pitch deck.")}
        action={
          <Button variant="contained" component={RouterLink} to="/profile/deck">
            {t("profile.teaserEmpty.action", "Завантажити дек")}
          </Button>
        }
      />
    );
  }

  return (
    <SectionCard
      title={t("profile.sections.teaser", "Blind-Teaser (KI-Entwurf & Freigabe)")}
      hint={t("profile.hints.teaser", "Чернетка від ШІ: перевірте та затвердіть перед публікацією")}
      icon={<AutoAwesomeOutlinedIcon fontSize="small" />}
    >
      <TeaserPage
        deckId={Number((meta.deck as Deck).id)}
        onApproved={refreshMeta}
        onReupload={() => navigate("/profile/deck")}
      />
    </SectionCard>
  );
}