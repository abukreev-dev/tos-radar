# Полный контекст проекта tos-radar

Дата фиксации контекста: 2026-02-21

## 1) Цель проекта

Сервис мониторинга изменений ToS-документов:
- запуск раз в сутки (cron);
- получение документа по фиксированному URL;
- сравнение с предыдущей версией;
- если есть изменения, показать diff в HTML-отчете.

## 2) Согласованные продуктовые решения

- Источники в MVP фиксированные (список URL в `.txt`), автопоиска пока нет.
- В MVP: 1 домен = 1 URL, дубль домена в конфиге считается ошибкой.
- Сравнение только по тексту документа, а не по HTML-разметке.
- Изменение даты (например, `Last updated`) считается валидным изменением.
- По ссылкам со страницы в MVP не переходим.
- PDF поддерживается при прямом URL на документ.
- Если URL не удалось получить: `FAILED`, пайплайн продолжается.
- Baseline обновляется только на успешном результате, для `FAILED` не трогаем.
- Храним только две версии: `current` и `previous`.
- Выход MVP: общий HTML-отчет + логи.

## 3) Нефункциональные требования и рантайм

- Целевой объем: 300–500 документов в час.
- Согласованный дефолт по параллелизму: `CONCURRENCY=20`.
- Таймаут: `TIMEOUT_SEC=60`.
- Ретраи: 1 попытка без прокси + до 3 попыток с прокси.
- Прокси: пользовательский список, формат `host:port` или `host:port:login:pass`.
- Таймзона логов/отчетов: локальная серверная.

## 4) Текущая реализация (что уже сделано)

### 4.1 Стек

- Python 3.12
- Playwright (Chromium)
- pypdf
- unittest + ruff

### 4.2 CLI и make-цели

- `make init` -> `python -m tos_radar.cli init`
- `make run` -> `python -m tos_radar.cli run`
- `make report-open` -> открыть последний report
- `make test` -> unit-тесты
- `make lint` -> ruff

### 4.3 Поведение `init`

- Загружает все URL.
- Сохраняет baseline (`current.txt`, ротация в `previous.txt` при повторном init).
- В отчете помечает как `NEW`.

### 4.4 Поведение `run`

- Загружает текущий документ.
- Сравнивает с `data/state/<domain>/current.txt`.
- Статусы:
- `CHANGED`: есть изменение, строится HTML diff, baseline обновляется.
- `UNCHANGED`: изменений нет.
- `FAILED`: получить документ не удалось, baseline не меняется.
- `NEW`: baseline отсутствовал.

### 4.5 Получение документа

- Если URL оканчивается на `.pdf`, сразу PDF-пайплайн.
- Для HTML:
- загрузка через Playwright;
- удаление шумных узлов (script/style/nav/footer/banner/cookie/a и т.д.);
- выбор наиболее содержательного блока;
- эвристическая фильтрация коротких/навигационных строк.
- Для PDF:
- скачивание (с учетом прокси);
- извлечение текста через `pypdf`.

### 4.6 Ретраи и устойчивость

- Порядок попыток: `None` (без прокси) -> первые `N` прокси из списка.
- Между попытками: exponential backoff + jitter.
- Настройки:
- `RETRY_BACKOFF_BASE_SEC=0.8`
- `RETRY_BACKOFF_MAX_SEC=8.0`
- `RETRY_JITTER_SEC=0.4`

### 4.7 Коды ошибок FAILED

Поддерживаются:
- `TIMEOUT`
- `NETWORK`
- `PROXY`
- `BROWSER`
- `PDF_DOWNLOAD`
- `PDF_PARSE`
- `EMPTY_CONTENT`
- `PARSER`
- `UNKNOWN`

`error_code` и `error` выводятся в HTML-отчете.

### 4.8 Хранилище и артефакты

- Состояние:
- `data/state/<domain>/current.txt`
- `data/state/<domain>/previous.txt`
- Логи:
- `logs/run-YYYYMMDD-HHMMSS.log`
- Отчеты:
- `reports/report-YYYYMMDD-HHMMSS.html`

## 5) Конфигурация

### 5.1 `.env`

- `TOS_URLS_FILE=config/tos_urls.txt`
- `PROXIES_FILE=config/proxies.txt`
- `CONCURRENCY=20`
- `TIMEOUT_SEC=60`
- `RETRY_PROXY_COUNT=3`
- `RETRY_BACKOFF_BASE_SEC=0.8`
- `RETRY_BACKOFF_MAX_SEC=8.0`
- `RETRY_JITTER_SEC=0.4`
- `LOG_LEVEL=INFO`

### 5.2 Входные файлы

- `config/tos_urls.txt` — URL по одному на строку.
- `config/proxies.txt` — прокси по одному на строку.

## 6) Тесты

Покрыты unit-тестами:
- парсинг конфигов и валидация доменов;
- нормализация;
- сравнение + генерация diff;
- формирование retry-цепочки;
- backoff/ошибки;
- ротация state.

## 7) Безопасность и git-практика

- В `.gitignore` добавлено:
- `config/*.txt` (боевые URL/прокси не коммитим),
- `*.swp`,
- `.env`, `data/`, `logs/`, `reports/`, `.venv/` и служебные кэши.

## 8) История ключевых коммитов

- `32a22b2` — bootstrap проекта.
- `c066e21` — ядро scan/diff/report + тесты.
- `1423a9e` — quickstart и make-targets в docs.
- `6b8f5f3` — полноценный README.
- `0c98990` — backoff + error codes + extractor hardening.
- `5a68d74` — docs под backoff/error codes.

## 9) Что отложено на полный релиз

- UI и аккаунты пользователей.
- Выбор/добавление сервисов из интерфейса.
- Автопоиск ToS по сайту.
- Переход со страницы-агрегатора к актуальному документу.
- Уведомления (Telegram/email/webhook).
- БД и длинная история.
- Site-specific правила очистки контента.
- Интеграционные тесты с реальными сайтами.

## 10) Рекомендуемые следующие шаги

- Добавить в отчет сводку `FAILED by error_code`.
- Добавить health-check скрипт по последнему запуску.
- Прогнать `init/run` на пилотном списке 10–20 доменов и откалибровать extractor.
