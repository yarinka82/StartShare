
import type { FieldName, RiskPhrase } from "./types";

/** Назви полів тизера */
export const FIELD_LABELS: Record<FieldName, string> = {
  headline: "Заголовок компанії (Headline)",
  problem: "Проблема (Problem)",
  solution: "Рішення та продукт (Solution)",
  business_model: "Модель монетизації (Business Model)",
  traction: "Метрики та результати (Traction)",
  market: "Ринок та конкуренція (Market)",
  team: "Досвід команди (Team Background)",
};

/** Повідомлення про відкриті блокери для затвердження тизера */
export const BLOCKER_MESSAGES: Record<string, string> = {
  required: "є обов'язковим і не може бути порожнім.",
  unconfirmed: "ще не підтверджено (натисніть Confirm).",
  blocking_risk: "містить критичну фразу-витік, яку потрібно відредагувати.",
  too_long: "перевищує ліміт символів.",
};

/** Повідомлення про помилки аналізу деку для TeaserPage */
export const ERROR_MESSAGES: Record<string, string> = {
  no_text: "Презентація містить лише графіку або скани без тексту. Будь ласка, заповніть форму вручну.",
  timeout: "Обробка деку зайняла більше часу, ніж очікувалося. Будь ласка, спробуйте ще раз.",
  corrupted: "Файл пошкоджено або захищено паролем. Завантажте коректний PDF.",
  unexpected: "Сталася непередбачена помилка під час аналізу деку. Спробуйте пізніше.",
};

/** Назви категорій ризикових фраз */
export function categoryLabel(categoryId: string): string {
  const categories: Record<string, string> = {
    R01: "Назва компанії / Бренд",
    R02: "Ім'я засновника / команди",
    R03: "URL / Веб-сайт",
    R04: "Контактні дані (Email / Телефон)",
    R05: "Номер патенту / Торгова марка",
    R06: "Конкретний клієнт / Партнер",
    R07: "Місто / Точна локація",
    R08: "Соцмережі / LinkedIn",
    R09: "Чутлива фінансова назва",
  };
  return categories[categoryId] || "Унікальний ідентифікатор";
}

/** Підказка фаундеру, як виправити конкретний ризик */
export function phraseAdvice(phrase: RiskPhrase): string {
  switch (phrase.category_id) {
    case "R01":
      return "Замініть на нейтральний опис, наприклад: «DACH-based B2B SaaS startup».";
    case "R02":
      return "Опишіть роль та досвід без імен (наприклад: «Ex-Google lead engineer з 8 роками досвіду»).";
    case "R03":
    case "R04":
      return "Видаліть посилання та контакти. Обмін контактами відбувається лише за взаємною згодою.";
    case "R06":
      return "Замініть на категорію, наприклад: «Top-3 німецький автовиробник» замість назви бренду.";
    default:
      return "Перефразуйте, щоб приховати унікальні деталі, за якими компанію можна знайти в пошуковику.";
  }
}