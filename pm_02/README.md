# Auth System - TypeScript + Python + Supabase

Полноценная система аутентификации с поддержкой email/password и OAuth (Google, GitHub).

## Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- Supabase аккаунт

### Локальная разработка

#### 1. Backend (FastAPI)

```bash
cd fastapi_backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env
cp .env.example .env
# Заполнить переменные (для SQLite тестов можно оставить как есть)

# Запустить
uvicorn app.main:app --reload
```

#### 2. Frontend (Next.js)

```bash
cd nextjs_frontend

# Установить зависимости
npm install  # или: pnpm install

# Создать .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Запустить
npm run dev
```

### Использование

1. Открыть `http://localhost:3000`
2. Зарегистрироваться или войти через OAuth
3. После успешной авторизации - переход на Dashboard

## Структура проекта

```
ts_py_auth/
├── docs/                    # Документация (ГОСТ)
│   ├── 01_architecture.md  # Архитектура системы
│   ├── 02_erd_diagram.md   # ER-диаграмма БД
│   └── 03_deployment.md    # Руководство по деплою
├── fastapi_backend/        # Python FastAPI
│   ├── app/
│   │   ├── main.py         # Точка входа
│   │   ├── config.py       # Конфигурация
│   │   ├── database.py     # Подключение к БД
│   │   ├── models.py       # SQLAlchemy модели
│   │   ├── schemas.py      # Pydantic схемы
│   │   ├── users.py        # Auth (fastapi-users)
│   │   └── oauth.py        # OAuth обработчики
│   ├── requirements.txt
│   └── .env.example
└── nextjs_frontend/        # Next.js + TypeScript
    ├── src/
    │   ├── app/            # App Router pages
    │   │   ├── page.tsx    # Login
    │   │   ├── register/   # Register page
    │   │   ├── dashboard/  # Protected dashboard
    │   │   └── api/auth/   # OAuth callbacks
    │   └── lib/
    │       └── api.ts      # API клиент
    └── package.json
```

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Frontend | Next.js 14+, React 18, TypeScript |
| Backend | FastAPI, Python 3.11+ |
| Database | Supabase PostgreSQL |
| ORM | SQLAlchemy 2.x (async) |
| Auth | fastapi-users + JWT |
| OAuth | Google, GitHub (через FastAPI) |

## OAuth настройка

### Google

1. [Google Cloud Console](https://console.cloud.google.com)
2. Создать проект → OAuth credentials
3. Добавить в `.env`:
   ```
   GOOGLE_CLIENT_ID=xxx
   GOOGLE_CLIENT_SECRET=xxx
   ```

### GitHub

1. [GitHub Developer Settings](https://github.com/settings/developers)
2. New OAuth App
3. Добавить в `.env`:
   ```
   GITHUB_CLIENT_ID=xxx
   GITHUB_CLIENT_SECRET=xxx
   ```

## Деплой

См. [docs/03_deployment.md](docs/03_deployment.md) для детальных инструкций:

- **Frontend**: Vercel
- **Backend**: Render
- **Database**: Supabase

## Лицензия

MIT