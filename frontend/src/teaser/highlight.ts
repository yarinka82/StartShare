
import type { RiskPhrase } from "./types";

export interface TextSegment {
  text: string;
  phrase?: RiskPhrase;
}

/** Нарізає текст на звичайні частини та частини з ризиковими фразами */
export function splitByPhrases(text: string, phrases: RiskPhrase[]): TextSegment[] {
  if (!phrases || phrases.length === 0 || !text) {
    return [{ text }];
  }

  const segments: TextSegment[] = [];
  let currentIndex = 0;

  // Знаходимо всі позиції входжень
  const matches: { start: number; end: number; phrase: RiskPhrase }[] = [];
  for (const phrase of phrases) {
    if (!phrase.quote) continue;
    let idx = text.toLowerCase().indexOf(phrase.quote.toLowerCase());
    while (idx !== -1) {
      matches.push({
        start: idx,
        end: idx + phrase.quote.length,
        phrase,
      });
      idx = text.toLowerCase().indexOf(phrase.quote.toLowerCase(), idx + 1);
    }
  }

  // Сортуємо входження за позицією в тексті
  matches.sort((a, b) => a.start - b.start);

  for (const match of matches) {
    if (match.start < currentIndex) continue; // пропускаємо перекриття

    if (match.start > currentIndex) {
      segments.push({ text: text.slice(currentIndex, match.start) });
    }

    segments.push({
      text: text.slice(match.start, match.end),
      phrase: match.phrase,
    });

    currentIndex = match.end;
  }

  if (currentIndex < text.length) {
    segments.push({ text: text.slice(currentIndex) });
  }

  return segments;
}