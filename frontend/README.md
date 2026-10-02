# Frontend: Этап 1 (React + TypeScript + Vite + MUI)

## Запуск
```bash
npm install
npm run dev        # http://localhost:5173, /api проксируется на http://localhost:8000
npm run build      # typecheck + production-сборка
```
Бэкенд должен быть запущен (см. `backend/README.md`). Письма в dev выводятся в консоль Django.

## Экраны
`/register`, `/login`, `/verify-email`, `/forgot-password`, `/reset-password`,
`/profile` (стартап: форма + загрузка деки), `/investor` (заглушка), `/legal/agb|datenschutz` (заглушки).

## Языки (DE / EN / UA)
- Файлы: `src/i18n/locales/{de,en,uk}.json`. Язык по умолчанию DE, выбор запоминается в localStorage.
- Заголовок `Accept-Language` уходит с каждым запросом, поэтому тексты ошибок Django тоже переводятся.
- Коды ошибок бэкенда (`deck_too_large`, `accept_agb_required` …) переводятся ключами `errors.*`.
- Значения справочников переводятся по `code` (`dict.sectors.*`, `dict.countries.*`);
  если перевода нет, показывается `name` из API. Новое значение в админке работает сразу.

## Как устроено
- `src/api/client.ts`: fetch с cookie-сессией и CSRF (`X-CSRFToken`), загрузка деки через XHR с прогрессом.
- `src/api/errors.ts`: разбор ответов бэкенда, перевод кодов.
- Форма профиля автосохраняется (debounce 800 мс, PATCH только изменённых полей, сохранение при уходе со страницы).
- Лимит деки на клиенте: `VITE_DECK_MAX_MB` (по умолчанию 20), должен совпадать с бэкендом. Решает сервер.
