# Технический проект: система аутентификации

## 1. Общие положения

### 1.1 Назначение системы

Система аутентификации пользователей с поддержкой:
- Регистрации по email/password
- OAuth 2.0 авторизации (Google, GitHub)
- JWT токенов для сессий
- Supabase PostgreSQL в качестве СУБД

### 1.2 Структура проекта

```
ts_py_auth/
├── docs/                    # Техническая документация
├── fastapi_backend/         # Python FastAPI сервер
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # Точка входа
│   │   ├── config.py        # Конфигурация
│   │   ├── database.py      # Подключение к SQLite
│   │   ├── models.py        # ORM модели
│   │   ├── schemas.py       # Pydantic схемы
│   │   ├── users.py        # UserManager и auth
│   │   ├── oauth.py        # OAuth провайдеры
│   │   └── routes/          # API эндпоинты
│   ├── requirements.txt
│   └── pyproject.toml
├── nextjs_frontend/         # Next.js приложение
│   ├── src/
│   │   ├── app/             # App Router
│   │   ├── components/      # UI компоненты
│   │   └── lib/            # Утилиты
│   └── package.json
└── README.md
```

---

## 2. Архитектура решения

### 2.1 Технологический стек

| Уровень | Технология | Версия |
|---------|------------|--------|
| Frontend | Next.js | 14+ |
| Language | TypeScript | 5.x |
| Backend | Python | 3.11+ |
| Framework | FastAPI | 0.110+ |
| Database | Supabase PostgreSQL | - |
| ORM | SQLAlchemy | 2.x (async) |
| DB Driver | asyncpg | 0.29.x |
| Auth | fastapi-users | 0.4.x |

### 2.2 Компонентная диаграмма

```
┌─────────────────────────────────────────────────────────────────┐
│                         Клиент (Next.js)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Login    │  │ Register │  │ OAuth    │  │ Dashboard    │    │
│  │ Page     │  │ Page     │  │ Callback │  │ (protected) │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
└───────┼─────────────┼─────────────┼───────────────┼────────────┘
        │             │             │               │
        └─────────────┴─────────────┴───────────────┘
                              │
                    HTTPS (localhost:3000)
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Auth Router  │  │ User Router  │  │ OAuth Router          │ │
│  │ /auth/jwt    │  │ /users       │  │ /auth/oauth/{provider}│ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                │                      │              │
│  ┌──────┴────────────────┴──────────────────────┴────────────┐ │
│  │                    UserManager (fastapi-users)             │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────┴─────────────────────────────────┐ │
│  │              SQLAlchemy + asyncpg (async)                   │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                 Supabase PostgreSQL
                 (db.xxx.supabase.co)
```

---

## 3. Функциональные требования

### 3.1 Аутентификация по паролю

- **Регистрация**: Email + Password
- **Валидация пароля**:
  - Минимум 8 символов
  - Минимум 1 заглавная буква
  - Минимум 1 специальный символ
  - Не содержит email
- **Login**: JWT токен с lifetime 1 час

### 3.2 OAuth 2.0 авторизация

| Провайдер | Тип | Callback |
|-----------|-----|----------|
| Google | OAuth2 | `/auth/oauth/google` |
| GitHub | OAuth2 | `/auth/oauth/github` |

**Flow OAuth 2.0:**
1. Клиент редиректит на `/auth/oauth/{provider}`
2. Пользователь авторизуется на стороне провайдера
3. Провайдер редиректит на `/auth/oauth/{provider}/callback`
4. Сервер обменивает code на tokens, создаёт/обновляет User
5. Сервер возвращает JWT токен

### 3.3 Управление пользователями

- GET /users/me - получить текущего пользователя
- PATCH /users/me - обновить данные пользователя

---

## 4. Безопасность

### 4.1 Токены

- **Access Token**: JWT (HS256), 1 час
- **Refresh Token**: не реализован (можно добавить)

### 4.2 CORS

Разрешённые источники: `http://localhost:3000`

### 4.3 Secrets

| Переменная | Назначение | Где получить |
|------------|------------|--------------|
| DATABASE_URL | Подключение к Supabase | Supabase → Settings → Database |
| SUPABASE_URL | URL проекта | Supabase → Settings → API |
| SUPABASE_ANON_KEY | Публичный ключ | Supabase → Settings → API |
| ACCESS_SECRET_KEY | Для JWT подписи | Генерировать: `openssl rand -hex 32` |
| GOOGLE_CLIENT_ID | OAuth Google | Google Cloud Console |
| GOOGLE_CLIENT_SECRET | OAuth Google | Google Cloud Console |
| GITHUB_CLIENT_ID | OAuth GitHub | GitHub Developer Settings |
| GITHUB_CLIENT_SECRET | OAuth GitHub | GitHub Developer Settings |
