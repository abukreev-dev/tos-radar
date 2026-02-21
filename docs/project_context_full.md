# Полный контекст проекта tos-radar

Дата фиксации: 2026-02-21

## 1) Назначение

`tos-radar` отслеживает изменения ToS-документов сервисов (HTML/PDF) по фиксированным URL:
- регулярный запуск (cron);
- извлечение текста документа;
- сравнение с baseline;
- генерация HTML-отчета с диффом и диагностикой.

## 2) Согласованные правила (актуально)

- Источники в MVP фиксированные (`.txt`).
- По ссылкам со страницы в MVP не переходим.
- Поддерживаем прямые PDF URL.
- Дубли домена в `tos_urls` не роняют запуск: обрабатывается первый URL домена.
- Baseline обновляется только на успешных результатах.
- Для `FAILED` baseline не меняется.

## 3) Технологии

- Python 3.12
- Playwright (Chromium)
- pypdf
- unittest + ruff
- Frontend v1: отдельный репозиторий `../tos-radar-frontend` (vanilla HTML/CSS/JS + node:test)

## 4) Команды

- `make init` — первичный baseline
- `make run` — основной запуск сравнения
- `make rerun-failed` — прогон только прошлых `FAILED`
- `make report-open` — открыть последний отчет tenant
- `make test`, `make lint`

CLI:
- `python -m tos_radar.cli init`
- `python -m tos_radar.cli run`
- `python -m tos_radar.cli rerun-failed`
- `python -m tos_radar.cli report-open`

## 5) Runtime-конфиг (`.env`)

- `TENANT_ID` (default: `default`)
- `TOS_URLS_FILE`
- `PROXIES_FILE`
- `CONCURRENCY`
- `TIMEOUT_SEC`
- `RETRY_PROXY_COUNT`
- `RETRY_BACKOFF_BASE_SEC`
- `RETRY_BACKOFF_MAX_SEC`
- `RETRY_JITTER_SEC`
- `MIN_TEXT_LENGTH`
- `LOG_LEVEL`

## 6) Архитектурные блоки

- `tos_radar/cli.py` — входные команды
- `tos_radar/runner.py` — orchestration
- `tos_radar/fetcher.py` — получение HTML/PDF, ретраи, anti-bot детект
- `tos_radar/normalize.py` — нормализация
- `tos_radar/diff_utils.py` — HTML diff
- `tos_radar/change_classifier.py` — `NOISE/MINOR/MAJOR`
- `tos_radar/report.py` — HTML-отчет
- `tos_radar/state_store.py` — хранение baseline
- `tos_radar/settings.py` — загрузка env
- `tos_radar/config.py` — загрузка URL/прокси

## 7) Поток обработки

1. Загрузить список сервисов и прокси.
2. Параллельно пройти URL (`CONCURRENCY`).
3. Для каждого URL:
- fetch с retry policy;
- quality gate;
- сравнение с baseline;
- выставление `NEW/CHANGED/UNCHANGED/FAILED`.
4. В режиме `run` выполнить один автоматический повтор только для `FAILED` доменов.
5. Сохранить список финальных `FAILED` URL.
6. Сформировать отчет.

## 8) Ретраи и надежность

- Попытка №1: без прокси.
- Затем до `RETRY_PROXY_COUNT` прокси.
- Между попытками: exponential backoff + jitter.
- Есть hard-timeout на попытку и на сервис целиком.
- При прерывании run идет аккуратная отмена задач.

## 9) Anti-bot и тех-страницы

- Детектируются anti-bot/blocked patterns (`BOT_DETECTED`, `TECHNICAL_PAGE`).
- Для бинарных URL (`/file/`, `/attachment`, `download`) есть fallback логика.

## 10) Quality gates

- `SHORT_CONTENT`: HTML документ короче `MIN_TEXT_LENGTH`.
- `TECHNICAL_PAGE`: тех/блок-страница по маркерам.

Эти кейсы идут в `FAILED` и не обновляют baseline.

## 11) Коды ошибок (`error_code`)

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

## 12) Классификация изменений

Для `CHANGED` вычисляются:
- `change_level`: `NOISE`, `MINOR`, `MAJOR`
- `change_ratio`: доля отличий

В отчете есть блок `Suspicious CHANGED`.

## 13) Формат и хранение данных (tenant-scoped)

- state:
  - `data/state/<tenant_id>/<domain>/current.txt`
  - `data/state/<tenant_id>/<domain>/previous.txt`
- failed list:
  - `data/<tenant_id>/last_failed_urls.txt`
- logs:
  - `logs/<tenant_id>/run-YYYYMMDD-HHMMSS.log`
- reports:
  - `reports/<tenant_id>/report-YYYYMMDD-HHMMSS.html`

## 14) Что в отчете по каждому URL

- `domain`
- `url`
- `status`
- `source`
- `duration`
- `text_length`
- `change_level` (если `CHANGED`)
- `change_ratio` (если `CHANGED`)
- `error_code`
- `error`
- `diff` (если `CHANGED`)

## 15) Тестовое покрытие

Покрыты модули:
- config
- fetcher
- normalize
- diff_utils
- change_classifier
- runner quality gates
- failed url persistence
- state_store
- cabinet_billing_service
- cabinet_api degradation flows (`4xx/5xx/network/timeout`)

## 16) Ключевые последние коммиты

- `ed7be86` — quality gates (`SHORT_CONTENT`, `TECHNICAL_PAGE`)
- `7638075` — change classification + suspicious changed
- `d79c573` — rerun-failed + авто-повтор failed
- `badd70b` — tenant-scoped state/log/report/failed storage

## 17) Известные практические кейсы

- Некоторые домены могут отдавать anti-bot challenge (`BOT_DETECTED`) в зависимости от IP/VPN.
- После изменения формата хранения текста возможен одноразовый всплеск `CHANGED`.
- Для диагностики корректности извлечения использовать `text_length` в отчете.

## 18) Следующий уровень (после MVP)

- UI/аккаунты/управление сервисами
- автопоиск ToS
- уведомления (Telegram/email/webhook)
- БД и историческая аналитика
- site-specific extraction rules

## 19) Актуальный статус реализации v1 P0 (2026-02-21)

- Backend P0: закрыты (`E7-03`, `E8-01`, `E8-02`), подтверждены тестами.
- Frontend P0: закрыты в `../tos-radar-frontend` (`E1-03`, `E1-04`, `E2-04`, `E3-01`, `E3-03`).
- Backlog синхронизирован со статусами `DONE` по указанным задачам.

## 20) Актуальные API кабинета (добавление)

- Добавлен endpoint `GET /api/v1/billing/plan`.
- Назначение: отдать `plan_code` (`FREE|PAID_30|PAID_100`) для применения UI ограничений и paywall-сценариев.
- Добавлен endpoint `POST /api/v1/email/verify/resend` (rate-limit: 60 сек, 10/сутки).
- Добавлены security notification endpoints:
  - `POST /api/v1/security/notify/password-changed`
  - `POST /api/v1/security/notify/email-changed`

## 21) Финальный статус реализации (2026-02-21)

- Backlog задач v1 синхронизирован: все `P0/P1/P2` отмечены `DONE`.
- Frontend реализован в `../tos-radar-frontend` и покрывает:
  - `Профиль -> Уведомления` (save/retry/resend verify/telegram controls);
  - `Каталог`, `Мои сервисы`, `Изменения`, `Дашборд`;
  - error states `403/404/500` (для `500` есть short error id).
