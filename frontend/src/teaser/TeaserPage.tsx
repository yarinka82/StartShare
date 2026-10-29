import { useTranslation } from "react-i18next";
import { ERROR_MESSAGES } from "./labels";
import { TeaserEditor } from "./TeaserEditor";
import { useDeckDraft } from "./useDeckDraft";
import { type TeaserApi, teaserApi } from "./api";

interface Props {
  deckId: number | null;
  api?: TeaserApi;
  onApproved?: () => void;
  /** FAILED state: lets the parent offer "upload another deck" (e.g. navigate to the deck page) */
  onReupload?: () => void;
}

// errors that are not the user's fault: another upload would not help, "try again later" does
const TECHNICAL_ERRORS = new Set(["llm_error", "llm_not_configured", "unexpected"]);

export function TeaserPage({ deckId, api, onApproved, onReupload }: Props) {
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
    const code = data.error_code ?? "unexpected";
    // ERROR_MESSAGES is a Proxy over i18n ("errors.<code>"), it translates and falls back by itself
    const message = ERROR_MESSAGES[code];
    const technical = TECHNICAL_ERRORS.has(code);

    return (
      <div role="alert" className="tz-banner tz-banner--error" style={{ marginBottom: 16 }}>
        <p style={{ margin: "0 0 8px 0" }}>{message}</p>
        {technical && (
          <p style={{ margin: "0 0 8px 0" }}>
            {t("teaser.errors.tryLater", "Це технічна проблема на нашому боці. Спробуйте пізніше.")}
          </p>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {technical && (
            <button type="button" onClick={refetch}>
              {t("common.checkAgain", "Перевірити знову")}
            </button>
          )}
          {!technical && onReupload && (
            <button type="button" onClick={onReupload}>
              {t("teaser.uploadAnother", "Завантажити інший дек")}
            </button>
          )}
        </div>
      </div>
    );
  }

  if (data?.state === "DRAFT_READY") {
    return <TeaserEditor deckId={deckId} draft={data} api={api} onApproved={onApproved} />;
  }

  // Queued / processing by the AI (QUEUED / PROCESSING)
  return (
    <p role="status" aria-busy={isPolling} className="tz-banner" style={{ margin: 0 }}>
      {data?.state === "PROCESSING"
        ? t("teaser.processing", "ШІ аналізує вашу презентацію…")
        : t("teaser.queued", "Вашу презентацію додано в чергу на аналіз…")}{" "}
      {t("teaser.processingEstimate", "Зазвичай це займає менше хвилини.")}
    </p>
  );
}