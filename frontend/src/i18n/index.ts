
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// 1. Импортируем Day.js и языковые пакеты
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/uk';
import 'dayjs/locale/de';
import 'dayjs/locale/en';

import ukTranslation from './locales/uk.json';
import deTranslation from './locales/de.json';
import enTranslation from './locales/en.json';

// 2. Включаем плагин для фраз типа "vor 2 Jahren" / "2 роки тому"
dayjs.extend(relativeTime);

const resources = {
  uk: {
    translation: ukTranslation,
  },
  de: {
    translation: deTranslation,
  },
  en: {
    translation: enTranslation,
  },
};

const savedLanguage = localStorage.getItem('lang') || 'uk';

// 3. Устанавливаем язык дат при первом запуске
dayjs.locale(savedLanguage);

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: savedLanguage,
    fallbackLng: 'uk',
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'lang',
    },
  });

// 4. Слушаем смену языка в приложении и сразу переключаем Day.js
i18n.on('languageChanged', (lng) => {
  const currentLang = lng ? lng.split('-')[0] : 'uk';
  dayjs.locale(currentLang);
});

export default i18n;