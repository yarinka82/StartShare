# StartShare

## Overview

StartShare is a Germany-focused matchmaking platform designed to connect startups and investors within a controlled, B2B-only environment. The system is intended to facilitate initial contact and reduce information asymmetry without acting as an investment advisor, intermediary in transactions, or fund custodian.

The platform is structured as an MVP with a narrow operational scope: startup profile creation, teaser generation, investor criteria configuration, rule-based matching, and consent-based contact disclosure.

## Product objectives

The core objective of StartShare is to enable efficient, privacy-preserving introduction between a startup and a professional investor while preserving the separation between platform mediation and commercial negotiation. The platform does not advise on investment decisions, does not negotiate terms, and does not execute capital flows.

## Business constraints and principles

- Only B2B participants are eligible. Retail investors are excluded.
- Platform mediation is informational only; it does not provide investment advice.
- AI supports content preparation but does not determine validity or approval.
- Contact information is disclosed only after mutual consent.
- Paid placements are not permitted in discovery or ranking lists.
- A reporting mechanism is available to flag inappropriate profiles in accordance with DSA requirements.

## Roles and lifecycle states

### Roles

- Startup
- Investor (fund, business angel, family office)
- Strategic partners and co-founders (future extension)

### Startup profile lifecycle

`DRAFT` → `LIVE` (after teaser approval) → `PAUSED` or `REMOVED`

### Introduction lifecycle

`SUGGESTED` → `INTERESTED` (investor clicks “Interested”) → `ACCEPTED` (startup approves disclosure) → `INTRODUCED`

Alternate outcomes:

- `DECLINED`
- `EXPIRED` (startup does not respond within [N] days)

---

## Product flow

### Startup flow

1. Registration and acknowledgment of AGB and Datenschutz notices.
2. Completion of startup profile: sector, stage, country, funding requirement, metrics (MRR, growth, team size).
3. Upload of pitch deck.
4. AI generates a draft blind teaser. This teaser hides brand identifiers, founder names, logos, external links, and visually emphasizes phrases that may reveal company identity.
5. The startup edits and approves each field and confirms the declaration in Legal Text A. Without this confirmation, the profile cannot transition to `LIVE`.
6. The original deck is removed after teaser generation unless the startup explicitly retains it.

### Investor flow

1. Registration and confirmation of professional investor status (Legal Text C).
2. Definition of mandate: sector, stage, region, check size, business model.
3. Weekly digest: 3–5 teaser cards delivered via email and dashboard.
4. Review of a blind card: sector, stage, funding ask, metrics, and team description without names.
5. Selection of “Interested” (optionally with a short note) or “No”.
6. If “No” is selected, the investor may specify a reason from a predefined list: sector, stage, region, check size, team, figures, other.

---

## Matching model

The matching logic is deterministic and rule-based rather than machine-learning based.

### Hard filters

- Sector
- Stage
- Region
- Check size

### Soft criteria

- Alignment across secondary filters
- Freshness of profile
- Match relevance to investor mandate

### Matching behavior

- Each teaser card includes a short explanatory line: “Why this match?”
- Investors do not see startups they have previously rejected
- Ranking is computed from the number of soft matches and profile recency

---

## Introduction and disclosure protocol

- Startup receives a request containing the fund name and investor type. Contact details remain hidden until approval.
- Startup can respond with “Freigabe”, “Nein”, or ignore the request; ignored requests transition to `EXPIRED`.
- If “Freigabe” is selected, both parties receive an email with contact details and a confidentiality reminder (Legal Text E).
- Data room, legal documentation, and negotiations remain outside the platform.

---

## Feedback loop

Feedback on rejected profiles is gathered and surfaced back to the investor. Example:

> “You rejected three profiles because of region. Would you like to adjust the criterion?”

The investor confirms such adjustments explicitly. Hidden score-based weighting is not used.

---

## Platform rules

- A startup may pause or remove its profile at any time.
- Report mechanism for profile complaints via “Melden” (DSA, Article 16).
- No paid listings or sponsored ranking positions.

---

## Legal text drafts

### A. Startup declaration

> Ich bestätige, dass die Angaben nach bestem Wissen richtig sind und ich zur Weitergabe dieser Informationen berechtigt bin. Das hochgeladene Material enthält keine Rechte Dritter oder personenbezogenen Daten Dritter, die ich nicht weitergeben darf. Mir ist bekannt, dass [Plattform] die Angaben nicht prüft.
>
> ☐ Ich bestätige diese Erklärung.

### B. Teaser disclaimer

> Angaben des Startups, nicht von [Plattform] geprüft. Keine Anlageberatung, keine Empfehlung und kein Angebot zum Erwerb von Beteiligungen.

### C. Investor confirmation

> Ich handle als professioneller Investor bzw. Business Angel im Rahmen meiner unternehmerischen Tätigkeit und nicht als Verbraucher.
>
> ☐ Ich bestätige diese Erklärung.

### D. Startup contact request

> [Fonds] hat Interesse an Ihrem Profil. Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben.

### E. Intro email signature

> [Plattform] vermittelt nur den Kontakt und ist nicht Partei von Gesprächen oder Verträgen. Bitte behandeln Sie ausgetauschte Informationen vertraulich.

### F. Profile selection criteria

> Wir wählen Profile ausschließlich anhand der von Ihnen angegebenen Kriterien (Branche, Stadium, Region, Volumen). Es gibt keine bezahlten Platzierungen und keine Bewertung durch einen Score.

### G. AI disclosure notice

> Den Teaser-Entwurf erstellen wir mit Hilfe von KI aus Ihrem Deck. Sie prüfen und geben ihn frei. Ihr Deck wird nicht zum Training von KI-Modellen verwendet.

> Note: This notice is included only if the applicable AVV and contractual terms genuinely require it.

---

## Event logging specification

### Startup lifecycle events

| Event | Key fields | Purpose |
| --- | --- | --- |
| `registered`, `deck_uploaded`, `draft_generated`, `field_edited`, `teaser_approved`, `went_live`, `paused` | — | Activation and AI quality measurement |
| `ai_draft_created` | timestamp, number of risky phrases, cost | AI quality and cost analysis |

### Investor lifecycle events

| Event | Key fields | Purpose |
| --- | --- | --- |
| `registered`, `status_confirmed`, `mandate_saved`, `mandate_changed` | — | Activation and criterion evolution |
| `digest_sent`, `digest_opened` | `digest_id`, card count | Engagement analysis |
| `card_shown` | `card_id`, `digest_id`, position, reason | Matching evaluation |
| `interested`, `declined` | `card_id`, reason | Match quality analysis |
| `criterion_suggestion_shown`, `accepted` | criterion | Trust and system calibration |

### Introduction and feedback events

| Event | Key fields | Purpose |
| --- | --- | --- |
| `status_changed` | response time | Funnel analytics |
| `report_submitted` | type | Trust and moderation |
| `survey_answered` | 14/30 days, result | Value measurement |

---

## System architecture

### Backend

- Python 3.12+
- Django 6.1
- Django REST Framework
- PostgreSQL
- SQLite for local development
- django-cors-headers

### Frontend

- React 18+
- TypeScript
- Material-UI (MUI)
- Vite
- Axios
- i18next

---

## Project structure

```text
StartShare/
├── backend/                              # Django REST API
│   ├── config/
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # shared settings
│   │   │   ├── dev.py                    # SQLite/PostgreSQL, DEBUG=True
│   │   │   └── prod.py                   # PostgreSQL, DEBUG=False
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/                             # domain-driven Django apps
│   │   ├── startups/                     # startup profiles and teaser logic
│   │   ├── investors/                    # investor profiles and mandates
│   │   ├── matching/                     # matching logic and introduction states
│   │   ├── events/                       # event logging
│   │   └── core/                         # shared models, mixins, utilities
│   ├── manage.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── entrypoint.sh                     # waits for DB readiness and applies migrations
│
├── frontend/                             # React + Vite application
│   ├── src/
│   │   ├── components/                   # reusable UI components
│   │   ├── pages/                        # registration, digest, teaser views
│   │   ├── features/                     # domain-specific logic
│   │   ├── api/                          # Axios clients and DRF adapters
│   │   ├── locales/                      # i18next translations (uk, de, en)
│   │   ├── types/                        # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── .dockerignore
│
├── nginx/                                # optional frontend + API proxy configuration
│   └── default.conf
│
├── docker-compose.yml                    # production-like orchestration
├── docker-compose.dev.yml                # local development environment
├── .env                                  # environment configuration (not committed)
├── .env.example
├── .gitignore
├── README.md
└── LICENSE (optional)
```

---

## Requirements

- Python 3.12+
- Git
- Python virtual environment (recommended)
- Node.js 18+ for frontend development

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yarinka82/StartShare.git
cd StartShare
```

### 2. Backend setup

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Initialize the database

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

---

## Local execution

### Backend

```bash
cd backend
python manage.py runserver
```

Application endpoint:

```text
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm run dev
```

Application endpoint:

```text
http://127.0.0.1:5173
```

---

## Configuration

The main backend configuration is located under:

```text
backend/config/settings/
```

The standard structure consists of:

- `base.py` — shared configuration
- `dev.py` — development environment settings
- `prod.py` — production settings

For local execution, create a `.env` file from `.env.example`.

---

## Development roadmap

- MVP: onboarding, profile creation, teaser approval, matching, and introduction flow
- Expansion: profile partnership capabilities, refined matching logic, retention-driven scenarios
- Future phase: analytics layer, A/B testing, conversion optimization

---

## Notes

This README combines product specification, technical architecture, and deployment instructions. While a single uniform style is preferable for public repositories, the current structure is justified by the MVP context: the document simultaneously serves as product definition and implementation blueprint.


Структура коміту
git commit -m "type(scope): description"

Типи:
feat: нова функціональність
fix: виправлення помилки
docs: документація
style: форматування коду
refactor: рефакторинг
test: тести
chore: інші зміни
Приклад
git commit -m "feat(members): add member list view" git commit -m "fix(payments): fix payment calculation"

🛠 Корисні команди Backend

Запуск сервера
python manage.py runserver

Створення міграцій
python manage.py makemigrations

Застосування міграцій
python manage.py migrate

Створення суперкористувача
python manage.py createsuperuser

Перевірка помилок
python manage.py check

Вхід в оболонку Django
python manage.py shell

Вхід в базу даних
python manage.py dbshell

Очищення кешу
python manage.py clear_cache

====📝 Ліцензія=== Цей проект є власністю компанії Digital IT Hub Würzburg e .V. Всі права захищені.