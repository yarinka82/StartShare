
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { HighlightedText } from "./HighlightedText";
import { FIELD_LABELS, categoryLabel, phraseAdvice } from "./labels";
import { isBlocking, type FieldName, type RiskPhrase } from "./types";

const REQUIRED: FieldName[] = ["headline", "problem", "solution"];
const maxLength = (f: FieldName) => (f === "headline" ? 200 : 800);

interface Props {
  name: FieldName;
  value: string;
  phrases: RiskPhrase[];
  reviewed: boolean;
  locked: boolean;
  busy: boolean;
  notFoundInDeck: boolean;
  onSave: (value: string) => Promise<string | null>;
  onConfirm: () => Promise<string | null>;
}

export function FieldCard({
  name,
  value,
  phrases,
  reviewed,
  locked,
  busy,
  notFoundInDeck,
  onSave,
  onConfirm,
}: Props) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);
  const [error, setError] = useState<string | null>(null);

  const required = REQUIRED.includes(name);
  const hasBlocking = phrases.some(isBlocking);
  const trimmed = text.trim();
  const canSave = !busy && trimmed !== value && text.length <= maxLength(name) && (!required || trimmed !== "");

  const startEdit = () => {
    setText(value);
    setError(null);
    setEditing(true);
  };

  const save = async () => {
    const err = await onSave(trimmed);
    setError(err);
    if (!err) setEditing(false);
  };

  const confirm = async () => setError(await onConfirm());

  return (
    <section className="tz-field" data-testid={`field-${name}`}>
      <header className="tz-field__head">
        <h3>
          {FIELD_LABELS[name]}
          {required && <span aria-hidden="true"> *</span>}
        </h3>
        {reviewed || locked ? (
          <span className="tz-badge tz-badge--ok">{t("teaser.status.confirmed", "Підтверджено")}</span>
        ) : value ? (
          <span className="tz-badge">{t("teaser.status.notConfirmed", "Не підтверджено")}</span>
        ) : null}
      </header>

      {editing ? (
        <div style={{ marginTop: 8 }}>
          <textarea
            aria-label={FIELD_LABELS[name]}
            value={text}
            rows={name === "headline" ? 2 : 5}
            onChange={(e) => setText(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px 12px",
              borderRadius: 6,
              border: "1.5px solid #17407a",
              fontFamily: "inherit",
              fontSize: "0.95rem",
              lineHeight: 1.5,
              outline: "none",
            }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
            <small style={{ color: "#64748b", fontSize: "0.8rem" }}>
              {t("teaser.editHint", "Видаліть або перефразуйте виділені фрази:")}
            </small>
            <small className="tz-counter">
              {text.length}/{maxLength(name)}
            </small>
          </div>

          {/* ЖИВИЙ ПОПЕРЕДНІЙ ПЕРЕГЛЯД ПІД ЧАС ВВЕДЕННЯ */}
          {phrases.length > 0 && (
            <div style={{
              background: "#f8fafc",
              border: "1px dashed #cbd5e1",
              borderRadius: 6,
              padding: "10px 14px",
              marginTop: 10,
            }}>
              <small style={{ display: "block", color: "#475569", fontWeight: 700, marginBottom: 4, fontSize: "0.75rem", textTransform: "uppercase" }}>
                {t("teaser.livePreview", "Попередній перегляд підсвітки в реальному часі:")}
              </small>
              <div style={{ margin: 0, fontSize: "0.9rem", color: "#1e293b" }}>
                <HighlightedText text={text} phrases={phrases} />
              </div>
            </div>
          )}
        </div>
      ) : value ? (
        <p className="tz-text">
          <HighlightedText text={value} phrases={phrases} />
        </p>
      ) : (
        <p className="tz-empty">
          {notFoundInDeck
            ? t("teaser.notFoundInDeck", "ШІ не знайшов інформації в деку. Додайте власноруч або залиште порожнім.")
            : t("teaser.empty", "Порожньо.")}
        </p>
      )}

      {/* СПИСОК РИЗИКІВ (ТЕПЕР ВИДИМИЙ І В РЕЖИМІ РЕДАГУВАННЯ!) */}
      {phrases.length > 0 && (
        <div style={{ marginTop: 12, borderTop: "1px solid #f1f5f9", paddingTop: 8 }}>
          <ul className="tz-risks" style={{ margin: 0, paddingLeft: 18 }}>
            {phrases.map((p, i) => {
              // Перевіряємо в реальному часі, чи слово ще є в інпуті
              const stillInText = editing
                ? text.toLowerCase().includes(p.quote.toLowerCase())
                : value.toLowerCase().includes(p.quote.toLowerCase());

              return (
                <li
                  key={i}
                  className={isBlocking(p) ? "tz-risks__item tz-risks__item--blocking" : "tz-risks__item"}
                  style={{ marginBottom: 6, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}
                >
                  <div>
                    <strong>{categoryLabel(p.category_id)}:</strong> “{p.quote}”. {phraseAdvice(p)}
                  </div>

                  {/* Живий бейдж статусу виправлення */}
                  {editing && (
                    <span
                      style={{
                        fontSize: "0.75rem",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontWeight: 700,
                        backgroundColor: stillInText ? (isBlocking(p) ? "#fee2e2" : "#fef08a") : "#dcfce7",
                        color: stillInText ? (isBlocking(p) ? "#991b1b" : "#854d0e") : "#166534",
                      }}
                    >
                      {stillInText
                        ? (isBlocking(p) ? "🔴 Блокує підтвердження" : "🟡 Попередження")
                        : "🟢 Виправлено (видалено)"}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {error && <p role="alert" className="tz-error">{error}</p>}

      {/* КНОПКИ ДІЙ */}
      {!locked && (
        <div className="tz-actions" style={{ marginTop: 14 }}>
          {editing ? (
            <>
              <button
                type="button"
                onClick={save}
                disabled={!canSave}
                style={{ background: canSave ? "#17407a" : "#cbd5e1", color: "#fff", border: "none" }}
              >
                {t("common.save", "Зберегти")}
              </button>
              <button type="button" onClick={() => setEditing(false)} disabled={busy}>
                {t("common.cancel", "Скасувати")}
              </button>
            </>
          ) : (
            <>
              <button type="button" onClick={startEdit} disabled={busy}>
                {t("common.edit", "Редагувати")}
              </button>
              <button
                type="button"
                onClick={confirm}
                disabled={busy || !value || reviewed || hasBlocking}
                style={{
                  background: (!busy && value && !reviewed && !hasBlocking) ? "#166534" : undefined,
                  color: (!busy && value && !reviewed && !hasBlocking) ? "#fff" : undefined,
                  border: (!busy && value && !reviewed && !hasBlocking) ? "none" : undefined,
                }}
              >
                {t("teaser.confirm", "Підтвердити")}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}