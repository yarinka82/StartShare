# 🏢 CRM_Verien

Система управління для Verien - CRM для клієнтів, членів клубу та платежів.

---

## 📋 Зміст

- [Технології](#-технології)
- [Вимоги](#-вимоги)
- [Встановлення](#-встановлення)
- [Налаштування](#-налаштування)
- [Запуск](#-запуск)
- [Структура проекту](#-структура-проекту)
- [Робота з Git](#-робота-з-git)
- [Корисні команди](#-корисні-команди)
- [Поширені проблеми](#-поширені-проблеми)
- [Підтримка](#-підтримка)

---

## 🚀 Технології

### Backend
- **Python 3.12+**
- **Django 6.1** - веб-фреймворк
- **Django REST Framework** - API
- **SQLite** - база даних (для розробки)
- **django-cors-headers** - CORS підтримка

### Frontend
- **React 18+**
- **TypeScript**
- **Material-UI (MUI)** - компоненти
- **Vite** - збірка
- **Axios** - HTTP клієнт
- **i18next** - інтернаціоналізація

---

## 📦 Вимоги

- Python 3.12 або вище
- Node.js 18+ та npm/yarn/pnpm
- Git
- Віртуальне середовище Python (рекомендовано)

---

========== 🔧 Встановлення

========== Клонування репозиторію


git clone https://github.com/your-username/CRM_Verien.git
cd CRM_Verien

===== Backend
Створення віртуального середовища

# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate

Встановлення залежностей

cd backend
pip install -r requirements.txt

Ініціалізація бази даних

# Створіть міграції
python manage.py makemigrations

# Застосуйте міграції
python manage.py migrate

# Створіть суперкористувача
python manage.py createsuperuser

⚙️ Налаштування
Структура backend/config/settings.py
Основні налаштування знаходяться у файлі backend/config/settings.py


==== Запуск
--Backend--
bash
cd backend
python manage.py runserver
Сервер буде доступний за адресою: http://127.0.0.1:8000

--Frontend--
bash
cd frontend
npm run dev
# або
yarn dev
# або
pnpm dev
Додаток буде доступний за адресою: http://localhost:5173


==== Структура проекту

CRM_Verien/
├── backend/
│   ├── apps/
│   │   ├── core/              # Основна логіка
│   │   ├── members/           # Учасники/клієнти
│   │   │   ├── migrations/    # 📁 Локальні міграції
│   │   │   ├── admin.py       # Адмін-панель
│   │   │   ├── forms.py       # Форми
│   │   │   ├── models.py      # 
│   │   │   ├── urls.py        # Маршрути
│   │   │   ├── views.py       # Контролери
│   │   │   └── templates/     # HTML шаблони
│   │   ├── payments/          # Платежі
│   │   └── users/             # Користувачі
│   ├── config/                # Налаштування Django
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── templates/             # Глобальні шаблони
│   ├── .env                   # 🔒 Змінні середовища (не в Git)
│   ├── db.sqlite3             # 🔒 База даних (не в Git)
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # API запити
│   │   ├── components/        # React компоненти
│   │   ├── hooks/             # Кастомні хуки
│   │   ├── pages/             # Сторінки
│   │   ├── types/             # TypeScript типи
│   │   ├── utils/             # Утиліти
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
├── README.md
└── LICENSE

=========Правила комітів

# Структура коміту
git commit -m "type(scope): description"

# Типи:
# feat: нова функціональність
# fix: виправлення помилки
# docs: документація
# style: форматування коду
# refactor: рефакторинг
# test: тести
# chore: інші зміни

# Приклад
git commit -m "feat(members): add member list view"
git commit -m "fix(payments): fix payment calculation"

🛠 Корисні команди
Backend

# Запуск сервера
python manage.py runserver

# Створення міграцій
python manage.py makemigrations

# Застосування міграцій
python manage.py migrate

# Створення суперкористувача
python manage.py createsuperuser

# Перевірка помилок
python manage.py check

# Вхід в оболонку Django
python manage.py shell

# Вхід в базу даних
python manage.py dbshell

# Очищення кешу
python manage.py clear_cache

====📝 Ліцензія===
Цей проект є власністю компанії Digital IT Hub Würzburg e .V. Всі права захищені.

