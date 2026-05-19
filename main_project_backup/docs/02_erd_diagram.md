# ER-диаграмма базы данных

## По ГОСТ Р 7.0.97-2018

### Версия: 1.0
### Дата: 2024

---

## 1. Общие сведения

ER-диаграмма (Entity-Relationship Diagram) разработана в соответствии с:
- ГОСТ Р 7.0.97-2018 «СИБИД. Издания. Оформление изданий»
- ГОСТ 34.602-89 «Техническое задание на создание автоматизированной системы»

### 1.1 Назначение

Документ определяет структуру данных системы аутентификации и используется для:
- Проектирования физической модели базы данных
- Разработки SQL-запросов и миграций
- Документирования связей между сущностями

---

## 2. Сущности и атрибуты

### 2.1 Сущность: User (Пользователь)

| Атрибут | Тип | Ограничения | Описание |
|---------|-----|-------------|-----------|
| id | UUID | PK, NOT NULL | Уникальный идентификатор |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Адрес электронной почты |
| hashed_password | VARCHAR | NULL | Хэшированный пароль |
| is_active | BOOLEAN | DEFAULT TRUE | Активность пользователя |
| is_superuser | BOOLEAN | DEFAULT FALSE | Флаг суперпользователя |
| is_verified | BOOLEAN | DEFAULT FALSE | Верификация email |
| google_id | VARCHAR | UNIQUE, NULL | ID пользователя Google |
| github_id | VARCHAR | UNIQUE, NULL | ID пользователя GitHub |
| oauth_email | VARCHAR | NULL | Email от OAuth провайдера |
| is_oauth_user | BOOLEAN | DEFAULT FALSE | OAuth пользователь |
| created_at | DATETIME | DEFAULT NOW() | Дата создания |

---

## 3. Диаграмма

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (Пользователь)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ PK  id                    UUID           NOT NULL, UNIQUE                   │
│     email                 VARCHAR(255)   NOT NULL, UNIQUE                   │
│     hashed_password       VARCHAR        NULL                               │
│     is_active             BOOLEAN        DEFAULT TRUE                       │
│     is_superuser          BOOLEAN        DEFAULT FALSE                     │
│     is_verified           BOOLEAN        DEFAULT FALSE                      │
│     google_id             VARCHAR        NULL, UNIQUE                       │
│     github_id             VARCHAR        NULL, UNIQUE                       │
│     oauth_email           VARCHAR        NULL                               │
│     is_oauth_user         BOOLEAN        DEFAULT FALSE                      │
│     created_at            DATETIME       DEFAULT CURRENT_TIMESTAMP         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Схема связей

```
┌─────────────┐
│    USER     │
└──────┬──────┘
       │
       │ 1:1
       │
       ▼
┌─────────────┐
│   AUTH      │  JWT Token (one-to-one via token_data)
└─────────────┘
       ▲
       │
       │ N:1
       │
┌─────────────┐
│   SESSION   │  (managed by fastapi-users)
└─────────────┘
```

---

## 4. Индексы

| Индекс | Колонка | Уникальный | Назначение |
|--------|---------|------------|------------|
| idx_user_email | email | Да | Поиск по email |
| idx_user_google | google_id | Да | Поиск Google OAuth |
| idx_user_github | github_id | Да | Поиск GitHub OAuth |
| idx_user_active | is_active | Нет | Фильтрация активных |

---

## 5. Ограничения (Constraints)

| Ограничение | Тип | Выражение |
|-------------|-----|-----------|
| chk_email_format | CHECK | email LIKE '%@%.%' |
| chk_password_hash | CHECK | hashed_password IS NOT NULL OR is_oauth_user = TRUE |

---

## 6. Версионность

| Версия | Дата | Автор | Изменения |
|--------|------|-------|------------|
| 1.0 | 2024-01 | Developer | Начальная версия |

---

## 7. Примечание

Таблица User наследует структуру от `SQLAlchemyBaseUserTableUUID` библиотеки fastapi-users.
Добавлены дополнительные поля для поддержки OAuth 2.0 авторизации (Google, GitHub).