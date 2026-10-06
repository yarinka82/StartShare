
import { splitByPhrases } from "./highlight";
import { categoryLabel } from "./labels";
import { isBlocking, type RiskPhrase } from "./types";

export function HighlightedText({ text, phrases }: { text: string; phrases: RiskPhrase[] }) {
  return (
    <>
      {splitByPhrases(text, phrases).map((seg, i) =>
        seg.phrase ? (
          <mark
            key={i}
            className={isBlocking(seg.phrase) ? "tz-risk tz-risk--blocking" : "tz-risk"}
            title={categoryLabel(seg.phrase.category_id)}
          >
            {seg.text}
          </mark>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </>
  );
}