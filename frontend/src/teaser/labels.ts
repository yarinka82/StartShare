
import i18n from "i18next";
import type { FieldName, RiskPhrase } from "./types";

/**
 * Автоматично перекладає назви полів через i18n:
 * FIELD_LABELS["headline"] -> повертає переклад поточною мовою
 */
export const FIELD_LABELS = new Proxy({} as Record<FieldName, string>, {
  get: (_, prop: string) => i18n.t(`teaser.fields.${prop}`, { defaultValue: prop }),
});

/**
 * Автоматично перекладає повідомлення блокерів
 */
export const BLOCKER_MESSAGES = new Proxy({} as Record<string, string>, {
  get: (_, prop: string) => i18n.t(`teaser.blockers.${prop}`, { defaultValue: prop }),
});

/**
 * Автоматично перекладає системні помилки деку
 */
export const ERROR_MESSAGES = new Proxy({} as Record<string, string>, {
  get: (_, prop: string) => i18n.t(`teaser.errors.${prop}`, { defaultValue: prop }),
});

/**
 * Динамічна назва категорії ризику
 */
export function categoryLabel(categoryId: string): string {
  return i18n.t(`teaser.categories.${categoryId}`, {
    defaultValue: i18n.t("teaser.categories.default", "Унікальний ідентифікатор"),
  });
}

/**
 * Динамічна порада щодо виправлення витоку
 */
export function phraseAdvice(phrase: RiskPhrase): string {
  return i18n.t(`teaser.advice.${phrase.category_id}`, {
    defaultValue: i18n.t("teaser.advice.default", "Перефразуйте, щоб приховати унікальні деталі."),
  });
}