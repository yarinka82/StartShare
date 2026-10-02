# Платформа знакомства стартапов и инвесторов: Этап 1

- `backend/`: Django + DRF (аккаунты, согласия, профиль, справочники, дек)
- `frontend/`: React + TypeScript + Vite + MUI, языки DE/EN/UA

Быстрый старт: два терминала.
1. `cd backend && pip install -r requirements.txt && python manage.py migrate && python manage.py seed_dictionaries && python manage.py runserver`
2. `cd frontend && npm install && npm run dev`, затем открыть http://localhost:5173
