import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import de from "./locales/de.json";
import en from "./locales/en.json";
import uk from "./locales/uk.json";

export const LANGUAGES = [
  { code: "de", label: "DE" },
  { code: "en", label: "EN" },
  { code: "uk", label: "UA" },
] as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { de: { translation: de }, en: { translation: en }, uk: { translation: uk } },
    supportedLngs: ["de", "en", "uk"],
    nonExplicitSupportedLngs: true,
    fallbackLng: "de",
    interpolation: { escapeValue: false },
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
  });

const setHtmlLang = () => {
  document.documentElement.lang = i18n.resolvedLanguage ?? "de";
};
i18n.on("languageChanged", setHtmlLang);
setHtmlLang();

export default i18n;
