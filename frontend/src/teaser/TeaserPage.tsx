import { useTranslation } from "react-i18next";
import { ERROR_MESSAGES } from "./labels";
import { TeaserEditor } from "./TeaserEditor";
import { useDeckDraft } from "./useDeckDraft";
import { type TeaserApi, teaserApi } from "./api";

interface Props {
  deckId: number | null;
  api?: TeaserApi;
  onApproved?: () => void;
}

export function TeaserPage({ deckId, api, onApproved }: Props) {
  const { t } = useTranslation();
  const { data, error, timedOut, refetch, isPolling } = useDeckDraft(deckId, {
    fetchDraft: api ? api.getDraft : teaserApi.getDraft,
  });

  if (deckId === null) return null;

  if (error) {
    return (
      <div role="alert" className="tz-banner tz-banner--error" style={{ marginBottom: 16 }}>
        <p style={{ margin: "0 0 8px 0" }}>
          {t("teaser.statusLoadError", "Не вдалося завантажити статус обробки.")}
        </p>
        <button type="button" onClick={refetch}>
          {t("common.tryAgain", "Спробувати ще раз")}
        </button>
      </div>
    );
  }

  if (timedOut) {
    return (
      <div role="status" className="tz-banner" style={{ marginBottom: 16 }}>
        <p style={{ margin: "0 0 8px 0" }}>
          {t(
            "teaser.timedOutMessage",
            "Обробка триває довше, ніж зазвичай. Ви можете покинути цю сторінку та повернутися пізніше."
          )}
        </p>
        <button type="button" onClick={refetch}>
          {t("common.checkAgain", "Перевірити знову")}
        </button>
      </div>
    );
  }

  if (data?.state === "FAILED") {
    return (
      <p role="alert" className="tz-error">
        {ERROR_MESSAGES[data.error_code ?? "unexpected"]}
      </p>
    );
  }

  if (data?.state === "DRAFT_READY") {
    return (
      <TeaserEditor
        deckId={deckId}
        draft={data}
        api={api}
        onApproved={onApproved}
      />
    );
  }

  // Стан черги та обробки ШІ (QUEUED / PROCESSING)
  return (
    <p role="status" aria-busy={isPolling} className="tz-banner" style={{ margin: 0 }}>
      {data?.state === "PROCESSING"
        ? t("teaser.processing", "ШІ аналізує вашу презентацію…")
        : t("teaser.queued", "Вашу презентацію додано в чергу на аналіз…")}{" "}
      {t("teaser.processingEstimate", "Зазвичай це займає менше хвилини.")}
    </p>
  );
}