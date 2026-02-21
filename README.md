# tos-radar

Ежедневный мониторинг изменений ToS-документов (HTML/PDF): сбор текста, сравнение с baseline, классификация изменений и HTML-отчет.

## Текущее состояние

- Стек: `Python 3.12 + Playwright + pypdf`.
- Для backend кабинета используется `MariaDB` (через `pymysql`).
- Режимы: `init`, `run`, `rerun-failed`, `report-open`.
- Входные URL: `config/tos_urls.txt` (дубли домена автоматически пропускаются, берется первый URL домена).
- Поддержка HTML и прямых PDF URL.
- Ретраи: первая попытка без прокси, затем до `RETRY_PROXY_COUNT` прокси.
- Exponential backoff + jitter между попытками.
- Жесткие таймауты:
  - на попытку fetch;
  - на сервис целиком.
- Авто-повтор упавших доменов один раз в конце `run`.
- Отдельный запуск только для прошлых падений: `rerun-failed`.
- Quality gates:
  - `SHORT_CONTENT` для слишком коротких HTML-документов;
  - `TECHNICAL_PAGE` для тех/блок-страниц.
- Anti-bot/блокировки классифицируются отдельными `error_code`.
- Классификация изменений: `NOISE`, `MINOR`, `MAJOR` + `change_ratio`.
- В отчете есть блок `Suspicious CHANGED`.

## Cabinet Backend API (MVP)

Поднять API:
```bash
make db-migrate
make api-run
```

Health-check:
- `GET /api/v1/health`

Базовые endpoint'ы кабинета:
- `GET /api/v1/notification-settings`
- `POST /api/v1/notification-settings`
- `POST /api/v1/telegram/link/start`
- `POST /api/v1/telegram/link/confirm`
- `POST /api/v1/telegram/unlink`
- `POST /api/v1/telegram/disconnected`
- `POST /api/v1/telegram/test-send`
- `POST /api/v1/security/sessions/create`
- `POST /api/v1/security/revoke-all-sessions`
- `GET /api/v1/security/active-sessions`
- `POST /api/v1/account/soft-delete/start`
- `POST /api/v1/account/soft-delete/restore`
- `GET /api/v1/account/access-state`
- `GET /api/v1/billing/plan`

Авторизация (MVP):
- Для защищенных endpoint'ов обязателен заголовок `X-Session-Id`.
- После `revoke-all-sessions` старые `session_id` становятся невалидными.
- В режиме `RECOVERY_ONLY` (soft-delete) разрешены только:
  - `GET /api/v1/account/access-state`
  - `POST /api/v1/account/soft-delete/restore`

## Multi-tenant хранение

Все артефакты разделены по `TENANT_ID`:

- state: `data/state/<tenant_id>/<domain>/current.txt` и `previous.txt`
- failed list: `data/<tenant_id>/last_failed_urls.txt`
- logs: `logs/<tenant_id>/run-YYYYMMDD-HHMMSS.log`
- reports: `reports/<tenant_id>/report-YYYYMMDD-HHMMSS.html`

По умолчанию `TENANT_ID=default`.

## Быстрый старт

1. Подготовить конфиги:
```bash
cp .env.example .env
cp config/tos_urls.txt.example config/tos_urls.txt
cp config/proxies.txt.example config/proxies.txt
```

2. Заполнить `config/tos_urls.txt` реальными URL.

3. Первый baseline:
```bash
make init
```

Для backend кабинета сначала применить миграции MariaDB:
```bash
make db-migrate
```

4. Обычный запуск:
```bash
make run
```

5. Повторить только прошлые падения:
```bash
make rerun-failed
```

6. Открыть последний отчет текущего tenant:
```bash
make report-open
```

## Форматы входных файлов

`config/tos_urls.txt`:
- один URL на строку;
- пустые строки и комментарии (`#`) игнорируются;
- при дубле домена берется первый URL, остальные пропускаются в лог.

Пример:
```text
https://example.com/terms
https://example.org/tos.pdf
```

`config/proxies.txt`:
- `host:port`
- `host:port:login:pass`

Пример:
```text
127.0.0.1:8080
127.0.0.1:8081:user:password
```

## Конфигурация `.env`

- `TENANT_ID` (по умолчанию `default`)
- `TOS_URLS_FILE` (по умолчанию `config/tos_urls.txt`)
- `PROXIES_FILE` (по умолчанию `config/proxies.txt`)
- `CONCURRENCY` (по умолчанию `20`)
- `TIMEOUT_SEC` (по умолчанию `60`)
- `RETRY_PROXY_COUNT` (по умолчанию `3`)
- `RETRY_BACKOFF_BASE_SEC` (по умолчанию `0.8`)
- `RETRY_BACKOFF_MAX_SEC` (по умолчанию `8.0`)
- `RETRY_JITTER_SEC` (по умолчанию `0.4`)
- `MIN_TEXT_LENGTH` (по умолчанию `350`, только для HTML)
- `LOG_LEVEL` (по умолчанию `INFO`)
- `API_HOST` (по умолчанию `127.0.0.1`)
- `API_PORT` (по умолчанию `8080`)
- `MARIADB_HOST` (по умолчанию `127.0.0.1`)
- `MARIADB_PORT` (по умолчанию `3306`)
- `MARIADB_DATABASE` (по умолчанию `tos_radar`)
- `MARIADB_USER` (по умолчанию `tos_radar`)
- `MARIADB_PASSWORD` (по умолчанию пусто)
- `BILLING_PLAN_DEFAULT` (по умолчанию `FREE`, допустимо: `FREE|PAID_30|PAID_100`)
- `BILLING_PLAN_OVERRIDES_JSON` (по умолчанию пусто, формат: `{"tenant:user":"PAID_30"}`)

## Поведение режимов

`make init`:
- загружает документы и записывает baseline;
- статусы в отчете обычно `NEW`/`FAILED`.

`make run`:
- сравнивает с baseline;
- пишет `CHANGED/UNCHANGED/FAILED`;
- при `CHANGED` обновляет baseline;
- в конце один раз автоматически повторяет только `FAILED` домены.

`make rerun-failed`:
- берет URL из `data/<tenant_id>/last_failed_urls.txt`;
- прогоняет только их.

## `error_code`

- `BOT_DETECTED`
- `TECHNICAL_PAGE`
- `SHORT_CONTENT`
- `TIMEOUT`
- `NETWORK`
- `PROXY`
- `BROWSER`
- `PDF_DOWNLOAD`
- `PDF_PARSE`
- `EMPTY_CONTENT`
- `PARSER`
- `UNKNOWN`

## Изменения и diff

- Сравнение идет по нормализованному тексту.
- Для `CHANGED` считаются:
  - `change_level`: `NOISE/MINOR/MAJOR`
  - `change_ratio`: доля отличий.
- В отчете есть:
  - `text_length`;
  - `change_level`, `change_ratio`;
  - отдельный блок `Suspicious CHANGED`.

## Make-команды

- `make install`
- `make install-browser`
- `make init`
- `make run`
- `make rerun-failed`
- `make test`
- `make lint`
- `make report-open`
- `make api-run`
- `make db-migrate`
- `make acceptance-smoke`
- `make acceptance-backend`

## Тесты

```bash
make test
make lint
make acceptance-smoke
```

## Контекст

- Краткий актуальный контекст: `docs/context.md`
- Полный контекст и история решений: `docs/project_context_full.md`
- Frontend-реализация кабинета: `../tos-radar-frontend`
