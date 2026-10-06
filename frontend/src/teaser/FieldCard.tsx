
import { useState } from "react";
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
  /** Поле очищено, потому что в деке для него не нашлось информации */
  notFoundInDeck: boolean;
  onSave: (value: string) => Promise<string | null>;
  onConfirm: () => Promise<string | null>;
}

export function FieldCard({ name, value, phrases, reviewed, locked, busy, notFoundInDeck, onSave, onConfirm }: Props) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const required = REQUIRED.includes(name);
  const hasBlocking = phrases.some(isBlocking);
  const trimmed = text.trim();
  const canSave = !busy && trimmed !== value && text.length <= maxLength(name) && (!required || trimmed !== "");

  const startEdit = () => { setText(value); setError(null); setEditing(true); };
  const save = async () => {
    const err = await onSave(trimmed);
    setError(err);
    if (!err) setEditing(false);
  };
  const confirm = async () => setError(await onConfirm());

  return (
    <section className="tz-field" data-testid={`field-${name}`}>
      <header className="tz-field__head">
        <h3>{FIELD_LABELS[name]}{required && <span aria-hidden="true"> *</span>}</h3>
        {reviewed ? <span className="tz-badge tz-badge--ok">Confirmed</span>
          : value ? <span className="tz-badge">Not confirmed</span> : null}
      </header>

      {editing ? (
        <>
          <textarea
            aria-label={FIELD_LABELS[name]}
            value={text}
            rows={name === "headline" ? 2 : 5}
            onChange={(e) => setText(e.target.value)}
          />
          <small className="tz-counter">{text.length}/{maxLength(name)}</small>
        </>
      ) : value ? (
        <p className="tz-text"><HighlightedText text={value} phrases={phrases} /></p>
      ) : (
        <p className="tz-empty">
          {notFoundInDeck
            ? "The AI could not find anything about this in your deck. Add it yourself or leave it empty."
            : "Empty."}
        </p>
      )}

      {!editing && phrases.length > 0 && (
        <ul className="tz-risks">
          {phrases.map((p, i) => (
            <li key={i} className={isBlocking(p) ? "tz-risks__item tz-risks__item--blocking" : "tz-risks__item"}>
              <strong>{categoryLabel(p.category_id)}:</strong> “{p.quote}”. {phraseAdvice(p)}
            </li>
          ))}
        </ul>
      )}

      {error && <p role="alert" className="tz-error">{error}</p>}

      {!locked && (
        <div className="tz-actions">
          {editing ? (
            <>
              <button type="button" onClick={save} disabled={!canSave}>Save</button>
              <button type="button" onClick={() => setEditing(false)} disabled={busy}>Cancel</button>
            </>
          ) : (
            <>
              <button type="button" onClick={startEdit} disabled={busy}>Edit</button>
              <button type="button" onClick={confirm} disabled={busy || !value || reviewed || hasBlocking}>
                Confirm
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}