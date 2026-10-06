
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FieldCard } from "./FieldCard";
import { BLOCKER_MESSAGES, FIELD_LABELS } from "./labels";
import { teaserApi, type TeaserApi } from "./api";
import { FIELD_NAMES, type DeckDraftResponse } from "./types";
import { useTeaser } from "./useTeaser";
import { useLegalText } from "../hooks/useLegalText";

interface Props {
  deckId: number;
  draft: DeckDraftResponse;
  api?: TeaserApi;
}

export function TeaserEditor({ deckId, draft, api = teaserApi }: Props) {
  const { t } = useTranslation();
  const { teaser, loadError, busy, saveField, confirmField, approve } = useTeaser(deckId, true, api);
  const [declared, setDeclared] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);
  const { statement, loading: legalLoading, error: legalError } = useLegalText("A");


  if (loadError) return <p role="alert" className="tz-error">{loadError}</p>;
  if (!teaser) return <p role="status">Loading your teaser…</p>;

  const locked = teaser.status === "APPROVED";
  const review = draft?.draft?.review;

  // Безпечні масиви за замовчуванням (захист від undefined)
  const blockers = teaser.approval_blockers ?? [];
  const reviewedList = teaser.reviewed ?? [];
  const riskPhrases = teaser.risk_phrases ?? [];
  const content = teaser.content ?? {};

  const legalUnavailable = !legalLoading && (!!legalError || !statement);
  const approveDisabled = busy || blockers.length > 0 || !declared || legalLoading || legalUnavailable;
  
  return (
    <div className="tz-editor">
      {locked && (
        <p role="status" className="tz-banner tz-banner--ok">
          Your teaser is approved and can no longer be edited.
        </p>
      )}
      {review && (review.image_slides?.length ?? 0) > 0 && (
        <p className="tz-banner">
          Slides {review.image_slides.join(", ")} contain images. We cannot analyse images yet, so please
          check them yourself for logos, names or screenshots.
        </p>
      )}

      {FIELD_NAMES.map((name) => (
        <FieldCard
          key={name}
          name={name}
          value={content[name] ?? ""}
          phrases={riskPhrases.filter((p) => p.field === name)}
          reviewed={reviewedList.includes(name)}
          locked={locked}
          busy={busy}
          notFoundInDeck={review?.blanked_fields?.includes(name) ?? false}
          onSave={(v) => saveField(name, v)}
          onConfirm={() => confirmField(name)}
        />
      ))}

      {!locked && (
        <section className="tz-approve">
          <h3 style={{ marginBottom: 12, fontSize: "1.15rem", fontWeight: 700, color: "#0b2142" }}>
            Approve teaser
          </h3>

          {/* Список відкритих блокерів */}
          {blockers.length > 0 && (
            <div style={{ background: "#fee4e2", border: "1px solid #fecdca", borderRadius: 8, padding: "12px 16px", marginBottom: 16 }}>
              <strong style={{ color: "#b42318", fontSize: "0.9rem" }}>
                Перед затвердженням виправте наступні зауваження:
              </strong>
              <ul style={{ margin: "8px 0 0 0", paddingLeft: 20, color: "#b42318", fontSize: "0.85rem" }}>
                {blockers.map((b, i) => (
                  <li key={i}>{FIELD_LABELS[b.field]} {BLOCKER_MESSAGES[b.code]}</li>
                ))}
              </ul>
            </div>
          )}

        {/* Декларація A */}
        <div style={{
          background: "#f8fafc",
          borderLeft: "4px solid #17407a",
          borderTop: "1px solid #e2e8f0",
          borderRight: "1px solid #e2e8f0",
          borderBottom: "1px solid #e2e8f0",
          borderRadius: 6,
          padding: 16,
          marginBottom: 16,
        }}>
          {legalLoading ? (
            <p style={{ margin: 0, fontSize: "0.88rem", color: "#64748b" }}>
              {t("common.loading", "Wird geladen…")}
            </p>
          ) : legalError || !statement ? (
            <p role="alert" className="tz-error" style={{ margin: 0 }}>
              {t("legal.unavailable", "Rechtstext konnte nicht geladen werden.")}
            </p>
          ) : (
            <>
              <p style={{ margin: "0 0 12px 0", fontSize: "0.88rem", color: "#1e293b", lineHeight: 1.6 }} lang="de">
                {statement}
              </p>

              <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontWeight: 600, fontSize: "0.9rem", color: "#0f172a" }}>
                <input
                  type="checkbox"
                  checked={declared}
                  onChange={(e) => setDeclared(e.target.checked)}
                  style={{ width: 18, height: 18, accentColor: "#17407a", cursor: "pointer" }}
                />
                <span lang="de">{t("legal.consent.confirm")}</span>
              </label>
            </>
          )}
        </div>

          {approveError && <p role="alert" className="tz-error">{approveError}</p>}


          <button
            type="button"
            disabled={approveDisabled}
            onClick={async () => setApproveError(await approve())}
            style={{
              background: approveDisabled ? "#94a3b8" : "#17407a",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "12px 24px",
              fontWeight: 700,
              fontSize: "1rem",
              cursor: approveDisabled ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {busy ? "Збереження..." : "Затвердити та опублікувати тизер (LIVE)"}
          </button>
        </section>
      )}
    </div>

  );
}