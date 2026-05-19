# Руководство по развёртыванию

## По ГОСТ 34.602-89

---

## 1. Общие сведения

Документ содержит пошаговые инструкции по развёртыванию системы в production.

### 1.1 Целевая архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │    Render       │     │   Supabase      │
│  (Frontend)     │────▶│   (Backend)     │────▶│  (PostgreSQL)   │
│   nextjs_frontend│     │  fastapi_backend│     │     Database    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       ▼                        │
         │               ┌─────────────────┐              │
         │               │  Environment    │              │
         │               │    Variables    │              │
         │               └─────────────────┘              │
         │                       │                        │
         └───────────────────────┘                        │
                              │                             │
                    ┌─────────┴─────────┐                   │
                    │   OAuth Providers │                   │
                    │  Google + GitHub  │                   │
                    └───────────────────┘                   │
```

---

## 2. Подготовка

### 2.1 Создание репозитория

```bash
cd ts_py_auth
git init
git add .
git commit -m "Initial commit"

# Создать репо на GitHub и запушить
git remote add origin https://github.com/yourusername/ts_py_auth.git
git branch -M main
git push -u origin main
```

---

## 3. Настройка Supabase

### 3.1 Регистрация и создание проекта

1. Перейти на [supabase.com](https://supabase.com)
2. Зарегистрироваться через GitHub
3. Нажать "New Project"
4. Заполнить:
   - **Name**: `auth-app`
   - **Database Password**: `your-secure-password` (запомнить!)
   - **Region**: `EU (Frankfurt)` или ближайшая
5. Дождаться создания ( ~2 минуты)

### 3.2 Получение Connection String

1. **Settings** → **Database**
2. Найти **Connection string** в формате URI
3. Скопировать строку вида:
   ```
   postgresql://postgres:[PASSWORD]@db.XXXX.supabase.co:5432/postgres
   ```
4. Заменить `[PASSWORD]` на ваш пароль из п.3.1

### 3.3 Создание таблиц

Таблицы создадутся автоматически при первом запуске FastAPI.
При необходимости создать вручную в Supabase SQL Editor:

```sql
-- Таблица пользователей (расширенная для OAuth)
CREATE TABLE IF NOT EXISTS public.user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    google_id VARCHAR UNIQUE,
    github_id VARCHAR UNIQUE,
    oauth_email VARCHAR,
    is_oauth_user BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_user_email ON public.user(email);
CREATE INDEX IF NOT EXISTS idx_user_google ON public.user(google_id);
CREATE INDEX IF NOT EXISTS idx_user_github ON public.user(github_id);
```

---

## 4. Настройка OAuth провайдеров

### 4.1 Google OAuth

1. Перейти [Google Cloud Console](https://console.cloud.google.com)
2. Создать проект
3. **APIs & Services** → **OAuth consent screen**
   - External → заполнить название
   - ДобавитьScopes: `email`, `profile`
4. **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: Web
   - Authorized redirect URI: `http://localhost:3000/api/auth/oauth/google/callback`
5. Получить **Client ID** и **Client Secret**

### 4.2 GitHub OAuth

1. Перейти [GitHub Developer Settings](https://github.com/settings/developers)
2. **New OAuth App**
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:3000/api/auth/oauth/github/callback`
3. Получить **Client ID** и **Client Secret**
4. Сгенерировать **Client secrets**

### 4.3 Добавление в Supabase (опционально)

Можно использовать Supabase Auth напрямую, но в нашем проекте
FastAPI обрабатывает OAuth самостоятельно.

---

## 5. Деплой Backend (Render)

### 5.1 Подготовка

```bash
# Создать .env файл для production
cp fastapi_backend/.env.example fastapi_backend/.env
```

Заполнить `.env`:
```
DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.XXXX.supabase.co:5432/postgres
SUPABASE_URL=https://XXXX.supabase.co
SUPABASE_ANON_KEY=your-anon-key

ACCESS_SECRET_KEY=$(openssl rand -hex 32)
RESET_PASSWORD_SECRET_KEY=$(openssl rand -hex 32)
VERIFICATION_SECRET_KEY=$(openssl rand -hex 32)

FRONTEND_URL=https://your-vercel-app.vercel.app

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### 5.2 Деплой на Render

1. Перейти [render.com](https://render.com)
2. Зарегистрироваться
3. **New** → **Web Service**
4. Подключить GitHub репозиторий
5. Настройки:
   - **Name**: `auth-backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `fastapi_backend`
6. **Advanced** → **Environment Variables**
   - Добавить все переменные из `.env`
7. Нажать **Deploy**

等待 ~5 минут для сборки.

---

## 6. Деплой Frontend (Vercel)

### 6.1 Деплой

1. Перейти [vercel.com](https://vercel.com)
2. Import Git Repository
3. Настройки:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `nextjs_frontend`
4. **Environment Variables**:
   - `NEXT_PUBLIC_API_URL` = `https://your-render-app.onrender.com`
5. **Deploy**

### 6.2 Настройка OAuth callback URLs

После деплоя обновить callback URLs:

**Google** (Cloud Console):
```
https://your-vercel-app.vercel.app/api/auth/oauth/google/callback
```

**GitHub** (Developer Settings):
```
https://your-vercel-app.vercel.app/api/auth/oauth/github/callback
```

---

## 7. Проверка работоспособности

### 7.1 Backend

```bash
# Проверить health endpoint
curl https://your-render-app.onrender.com/health
# Ответ: {"status":"healthy"}
```

### 7.2 Frontend

1. Открыть `https://your-vercel-app.vercel.app`
2. Попробовать регистрацию
3. Попробовать Login
4. Попробовать OAuth кнопки

---

## 8. Troubleshooting

### Ошибка: "Too many connections"
- Уменьшить количество соединений в pool
- Добавить `pool_size=5` в database.py

### Ошибка: "OAuth not configured"
- Проверить GOOGLE_CLIENT_ID в env переменных Render
- Перезапустить сервис после изменения env

### Ошибка: CORS
- Добавить домен Vercel в CORS_ORIGINS в config.py
- Пересобрать и деплоить

---

## 9. Версионность

| Версия | Дата | Автор | Изменения |
|--------|------|-------|------------|
| 1.0 | 2024 | Developer | Первая версия |