import { Alert, Stack } from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import { useTranslation } from "react-i18next";
import type { Deck } from "../api/types";
import DeckUpload from "../components/DeckUpload";
import { useProfile } from "./ProfileProvider";
import SectionCard from "./SectionCard";

export default function DeckPage() {
  const { t } = useTranslation();
  const { meta, refreshMeta } = useProfile();
  const locked = meta.status === "LIVE";

  return (
    <Stack spacing={3}>
      {locked && (
        <Alert severity="info">
          {t("profile.deckLockedHint", "Поки профіль у LIVE, дек змінити не можна. Поставте профіль на паузу на сторінці «Огляд».")}
        </Alert>
      )}
      <SectionCard
        title={t("profile.sections.deck")}
        hint={t("profile.hints.deck", "Презентація, на основі якої ШІ готує тизер")}
        icon={<DescriptionOutlinedIcon fontSize="small" />}
      >
        <DeckUpload deck={meta.deck as Deck | null} onChanged={refreshMeta} locked={locked} />
      </SectionCard>
    </Stack>
  );
}