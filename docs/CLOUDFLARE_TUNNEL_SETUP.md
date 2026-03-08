# Настройка Cloudflare Tunnel (cloudflared) для profiboard.uz

Пошаговая инструкция: как открыть приложение (frontend + API) через домен без VPS, без проброса портов и без белого IP. Postgres остаётся только в локальной сети.

---

## 1. Как сейчас запускается проект

| Компонент | Как запускается | Порт |
|-----------|-----------------|------|
| **Frontend** | Vite dev‑сервер: `npm run dev` в `apps/web` | **8080** (задано в `apps/web/vite.config.ts`) |
| **Backend** | FastAPI (uvicorn): из `apps/api` — `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | **8000** |
| **Postgres** | Локально (localhost или LAN), наружу не публикуется | 5432 |

Дополнительно в проекте есть:
- `docker-compose.yml` — при необходимости можно поднять сервисы в Docker, но для туннеля достаточно запуска как выше.
- В `apps/web` есть proxy в Vite: запросы с фронта к `/api` проксируются на `http://127.0.0.1:8000` (при работе через один домен в dev). Для продакшена фронт и API на разных доменах: фронт на `profiboard.uz`, API на `api.profiboard.uz` (см. п. 7).

---

## 2. Целевая схема туннеля

- **https://profiboard.uz** (и **https://www.profiboard.uz**) → `http://localhost:8080` (Vite dev или статика на 8080).
- **https://api.profiboard.uz** → `http://localhost:8000` (FastAPI).

SPA (React Router): при прямых переходах по путям типа `/products` Vite dev‑сервер отдаёт `index.html` (history fallback). Если будете отдавать статику (например, через `npx serve -s dist -l 8080`), убедитесь, что сервер настроен на fallback на `index.html` для не‑файловых путей (например, флаг `-s` у `serve` это даёт).

Postgres не участвует в туннеле — к нему подключается только приложение на этой же машине.

---

## 3. Команды для настройки cloudflared

### 3.1. Установка cloudflared

**Windows (PowerShell от администратора):**

```powershell
# Через winget (рекомендуется)
winget install Cloudflare.cloudflared

# Или скачать exe с https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
# и положить в PATH.
```

**Linux (x64):**

```bash
# Пример для Debian/Ubuntu
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

Или бинарник с [релизов Cloudflare](https://github.com/cloudflare/cloudflared/releases).

### 3.2. Вход в Cloudflare

```bash
cloudflared tunnel login
```

Откроется браузер: выберите домен (например, `profiboard.uz`). После успеха сертификат сохранится локально (нужен для создания туннелей).

### 3.3. Создание туннеля

```bash
cloudflared tunnel create profiboard
```

Будет выведен **Tunnel ID** (UUID) и путь к файлу с учётными данными, например:
`C:\Users\<User>\.cloudflared\<UUID>.json` (Windows) или `~/.cloudflared/<UUID>.json` (Linux). Этот путь понадобится для конфига.

### 3.4. Привязка DNS к туннелю

Выполнить в корне проекта (или из любой папки):

```bash
# Корень и www → туннель (фронт)
cloudflared tunnel route dns profiboard profiboard.uz
cloudflared tunnel route dns profiboard www.profiboard.uz

# Поддомен API
cloudflared tunnel route dns profiboard api.profiboard.uz
```

Имя туннеля здесь — `profiboard` (как в `tunnel create`). В зоне появятся CNAME на `<TUNNEL_ID>.cfargotunnel.com`.

---

## 4. Конфиг туннеля (config.yml)

Файл в репозитории: **`deploy/cloudflared-config.yml`**.

Перед запуском в нём нужно заменить плейсхолдеры:

1. **`<TUNNEL_ID>`** — UUID туннеля из вывода `cloudflared tunnel create profiboard`.
2. **`<PATH_TO_CREDENTIALS_JSON>`** — полный путь к файлу `*.json` из того же вывода (например `C:\Users\YourName\.cloudflared\xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json` или `~/.cloudflared/...`).

Пример готового фрагмента:

```yaml
tunnel: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
credentials-file: C:\Users\YourName\.cloudflared\xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json

ingress:
  - hostname: profiboard.uz
    service: http://localhost:8080
  - hostname: www.profiboard.uz
    service: http://localhost:8080
  - hostname: api.profiboard.uz
    service: http://localhost:8000
  - service: http_status:404
```

Последнее правило `service: http_status:404` обязательно: оно обрабатывает все остальные hostname’ы и запросы, не попавшие в правила выше.

Куда положить конфиг:
- Рекомендуется оставить в репозитории: **`deploy/cloudflared-config.yml`** (файл с секретами — `credentials-file` — в git не коммитить; в конфиге можно указать путь к нему вне репо).
- Либо скопировать в каталог cloudflared, например:
  - Windows: `%USERPROFILE%\.cloudflared\config.yml`
  - Linux: `~/.cloudflared/config.yml`  
  и запускать: `cloudflared tunnel run profiboard` (без `--config`).

---

## 5. Запуск туннеля

### 5.1. Ручной запуск (из корня проекта)

**Если конфиг в репо (с подставленными TUNNEL_ID и credentials-file):**

```bash
cloudflared tunnel --config deploy/cloudflared-config.yml run profiboard
```

**Если конфиг в `~/.cloudflared/config.yml`:**

```bash
cloudflared tunnel run profiboard
```

Туннель должен оставаться запущенным (окно/терминал не закрывать).

### 5.2. Автозапуск

**Windows (служба):**

```powershell
# Установить как службу (запуск от имени администратора)
cloudflared service install
```

Перед этим убедитесь, что конфиг по умолчанию лежит в `%USERPROFILE%\.cloudflared\config.yml` и в нём указаны правильные `tunnel` и `credentials-file`. Служба при старте системы будет поднимать туннель по этому конфигу.

**Linux (systemd):**

```bash
sudo cloudflared service install
```

Конфиг по умолчанию: `~/.cloudflared/config.yml` (для пользователя, от которого ставили службу). При необходимости скопируйте туда `deploy/cloudflared-config.yml`, подставив `tunnel` и `credentials-file`.

Проверка:

```bash
sudo systemctl status cloudflared
sudo systemctl enable cloudflared
```

---

## 6. Настройки Cloudflare (дашборд)

- **SSL/TLS** → режим: **Full** или **Full (strict)**.  
  Рекомендуется **Full (strict)** при использовании туннеля: трафик Cloudflare → cloudflared уже по TLS; для strict нужен валидный сертификат на стороне origin. У туннеля свой сертификат, обычно подходит Full (strict). Если появятся ошибки сертификата — временно можно Full.
- **Always Use HTTPS** — включить (редирект HTTP → HTTPS).
- **www → корень**: в **Rules** → **Redirect Rules** добавить правило:
  - If: hostname equals `www.profiboard.uz`
  - Then: Dynamic redirect → `https://profiboard.uz${uri.path}`, status 301.

---

## 7. CORS и переменная API для фронта

### 7.1. Backend (FastAPI)

В **`apps/api/app/main.py`** в CORS уже добавлены продакшн-домены:

- `https://profiboard.uz`
- `https://www.profiboard.uz`

Если добавите другие фронт-домены — укажите их в `allow_origins` в том же блоке `CORSMiddleware`.

### 7.2. Frontend: URL API в продакшене

Чтобы в браузере запросы уходили на **https://api.profiboard.uz**, при сборке фронта задайте переменную окружения:

В **`apps/web`** при сборке:

```powershell
# Windows (PowerShell) — сначала задать переменную, затем команда
$env:VITE_API_URL = "https://api.profiboard.uz"; npm run build
```

```bash
# Linux/macOS (bash)
VITE_API_URL=https://api.profiboard.uz npm run build
```

В PowerShell синтаксис `VITE_API_URL=значение` не работает — это синтаксис bash. Нужно использовать `$env:ИМЯ = "значение"`.

Либо в `.env.production` в `apps/web`:

```
VITE_API_URL=https://api.profiboard.uz
```

Тогда `getApiBaseUrl()` в `apps/web/src/lib/api.ts` будет возвращать `https://api.profiboard.uz` в продакшене.

При работе через **Vite dev** (порт 8080) с туннелем на profiboard.uz тоже лучше задать `VITE_API_URL=https://api.profiboard.uz` в `.env` или `.env.local`, чтобы запросы шли на поддомен API, а не через proxy на тот же хост.

---

## 8. Проверка

### 8.1. DNS

```bash
nslookup profiboard.uz
nslookup api.profiboard.uz
```

Ожидаются CNAME на `<TUNNEL_ID>.cfargotunnel.com` (или ответ через proxy Cloudflare).

### 8.2. API

```bash
curl -s https://api.profiboard.uz/health
# Ожидается: {"ok":true}

curl -s https://api.profiboard.uz/api/health
# Аналогично
```

Документация API: https://api.profiboard.uz/docs

### 8.3. Фронт и запросы к API

- Открыть https://profiboard.uz (и при необходимости https://www.profiboard.uz).
- Убедиться, что страница грузится и что запросы к API (логин, данные) идут на `https://api.profiboard.uz` и проходят без ошибок (в DevTools → Network).

---

## 9. Типовые ошибки и решения

| Симптом | Возможная причина | Что сделать |
|--------|-------------------|-------------|
| **502 Bad Gateway** | Туннель работает, но на машине не запущен сервис на указанном порту | Запустить Vite на 8080 и/или uvicorn на 8000; проверить в конфиге туннеля порты. |
| **403 / CORS** | Браузер блокирует запрос с фронта к API | Проверить в `apps/api/app/main.py` наличие `https://profiboard.uz` и `https://www.profiboard.uz` в `allow_origins`. |
| **Tunnel not found / не подключается** | Неверный Tunnel ID или credentials | Проверить `tunnel` и `credentials-file` в конфиге; пересоздать туннель при необходимости. |
| **Страница открывается, API не вызывается** | Фронт ходит не на api.profiboard.uz | Задать `VITE_API_URL=https://api.profiboard.uz` и пересобрать (или перезапустить dev с этим env). |
| **SSL ошибка (например 526)** | Режим SSL «Full (strict)» и недоверенный сертификат origin | Временно поставить SSL **Full** или проверить, что cloudflared и конфиг туннеля корректны. |
| **404 на путях типа /products** | SPA: сервер не отдаёт index.html для не-корневых путей | Для dev — Vite уже даёт history fallback. Для статики (например `serve`) использовать `-s` (single page). |

---

## 10. Краткий чеклист

1. Установить cloudflared, выполнить `cloudflared tunnel login`.
2. Создать туннель: `cloudflared tunnel create profiboard`.
3. Привязать DNS: `profiboard.uz`, `www.profiboard.uz`, `api.profiboard.uz` через `cloudflared tunnel route dns`.
4. Подставить в `deploy/cloudflared-config.yml` Tunnel ID и путь к `credentials-file`.
5. Запустить фронт (8080) и API (8000), затем туннель: `cloudflared tunnel --config deploy/cloudflared-config.yml run profiboard`.
6. В Cloudflare: SSL Full (или Full strict), Always Use HTTPS, при необходимости редирект www → корень.
7. В `apps/web`: задать `VITE_API_URL=https://api.profiboard.uz` для продакшен-сборки (и при необходимости для dev).
8. Проверить: `/health`, `/api/health`, открытие https://profiboard.uz и запросы к API.

Endpoint **`/health`** и **`/api/health`** в FastAPI уже есть (`apps/api/app/main.py`), дополнительно добавлять не нужно.
