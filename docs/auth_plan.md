# План аутентификации

## Текущее состояние

### Реализовано: Email + Password аутентификация

**Backend (FastAPI + Postgres):**

1. **Таблицы:**
   - `app.users` - пользователи (id UUID, email, phone, is_active, created_at, updated_at)
   - `app.auth_identities` - идентификаторы аутентификации (provider: email_password/phone_otp)
   - `app.refresh_tokens` - refresh токены с хешами
   - `app.verification_codes` - коды верификации для SMS/Email (готово для будущего использования)

2. **API Endpoints:**
   - `POST /auth/register` - регистрация с email + password
   - `POST /auth/login` - вход с email + password → возвращает access_token, refresh_token, user
   - `POST /auth/refresh` - обновление токенов (ротация refresh token)
   - `POST /auth/logout` - выход (отзыв refresh token)
   - `GET /auth/me` - получение текущего пользователя

3. **JWT токены:**
   - Access token: короткий срок жизни (15 минут по умолчанию)
   - Refresh token: длинный срок жизни (30 дней), хранится как hash в БД
   - Ротация refresh token при каждом обновлении

4. **Пароли:**
   - Хеширование через `argon2-cffi` (предпочтительно) или `passlib[bcrypt]`
   - Хранятся только hash в `auth_identities.password_hash`

5. **Совместимость с существующими endpoints:**
   - Все `/api/*` endpoints поддерживают два режима:
     * `Authorization: Bearer <access_token>` - JWT аутентификация (предпочтительно)
     * `X-User-Id: <uuid>` - fallback для dev режима
   - Единая dependency `require_user()` в `app/deps.py`

**Файлы:**
- `apps/api/app/models/` - SQLAlchemy модели
- `apps/api/app/auth/` - JWT и password hashing логика
- `apps/api/app/routes/auth.py` - auth endpoints
- `apps/api/app/deps.py` - dependency `require_user()` для JWT и X-User-Id

**Конфигурация (.env):**
- `JWT_SECRET` - секретный ключ для подписи JWT
- `JWT_ISSUER` - issuer для JWT (по умолчанию: service-analytics-api)
- `ACCESS_TTL_MIN` - время жизни access token в минутах (по умолчанию: 15)
- `REFRESH_TTL_DAYS` - время жизни refresh token в днях (по умолчанию: 30)
- `APP_ENV` - окружение (dev/production)
- `DEFAULT_DEV_USER_ID` - fallback user_id для dev режима

### Преимущества текущего подхода:
- ✅ Реальная аутентификация с JWT
- ✅ Безопасное хранение паролей (argon2)
- ✅ Refresh token ротация
- ✅ Гибкая архитектура для добавления phone_otp
- ✅ Обратная совместимость с X-User-Id (dev режим)

## План развития

### Этап 1: SMS OTP аутентификация (готово к добавлению)

**Архитектура уже поддерживает:**
- Таблица `verification_codes` для хранения OTP кодов
- `AuthProvider.PHONE_OTP` в `auth_identities`
- `VerificationChannel.SMS` в `verification_codes`

**Нужно добавить:**
1. Endpoints:
   - `POST /auth/phone/start` - инициировать OTP отправку
   - `POST /auth/phone/verify` - верифицировать OTP и создать/войти пользователя

2. Интеграция с SMS провайдером:
   - Выбрать провайдера (Twilio, AWS SNS, etc.)
   - Добавить отправку SMS в `app/auth/sms.py`
   - Генерация и хранение OTP кодов в `verification_codes`

3. Логика:
   - При `POST /auth/phone/start`: создать запись в `verification_codes`, отправить SMS
   - При `POST /auth/phone/verify`: проверить код, создать user + auth_identity (если новый), вернуть токены

**Важно:** Система спроектирована так, что добавление phone_otp не сломает существующую email_password аутентификацию.

### Этап 2: Дополнительные возможности

1. **Email verification** при регистрации
2. **Password reset** через email
3. **Rate limiting** на auth endpoints
4. **Session management** (просмотр активных сессий)
5. **Multi-factor authentication (MFA)**

### Этап 3: Расширенные возможности

1. **OAuth2** интеграция (Google, GitHub, etc.)
2. **Role-based access control (RBAC)**
3. **API keys** для сервисных аккаунтов

## Структура базы данных

```sql
-- Users table
CREATE TABLE app.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Auth identities (email_password or phone_otp)
CREATE TABLE app.auth_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'email_password' or 'phone_otp'
    identifier VARCHAR(255) NOT NULL, -- email or phone
    password_hash VARCHAR(255), -- NULL for phone_otp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Refresh tokens
CREATE TABLE app.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verification codes (for SMS/Email OTP)
CREATE TABLE app.verification_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app.users(id) ON DELETE CASCADE, -- NULL for pre-registration
    channel VARCHAR(50) NOT NULL, -- 'sms' or 'email'
    destination VARCHAR(255) NOT NULL, -- phone or email
    code_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Примеры использования

### Регистрация
```bash
POST /auth/register
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": "123e4567-...",
    "email": "user@example.com",
    "phone": null,
    "is_active": true,
    "created_at": "2025-01-17T..."
  }
}
```

### Вход
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response: (same as register)
```

### Использование токена
```bash
GET /api/shops
Authorization: Bearer <access_token>

# Или в dev режиме:
GET /api/shops
X-User-Id: 123e4567-...
```

### Обновление токена
```bash
POST /auth/refresh
{
  "refresh_token": "eyJ..."
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."  # новый токен
}
```

## Примечания

- Папка `apps/web/supabase/` оставлена для возможного использования в будущем, но не используется
- Frontend должен быть обновлен для использования JWT токенов вместо X-User-Id
- В production обязательно использовать HTTPS
- JWT_SECRET должен быть длинным и случайным (минимум 32 символа)
