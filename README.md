# tos-radar

Ежедневный мониторинг изменений ToS-документов (HTML/PDF) с сохранением baseline, сравнением текста и генерацией общего HTML-отчета.

## Что уже реализовано

- `Python 3.12 + Playwright`.
- Режимы `init` и `run`.
- Источник URL из файла (`1 домен = 1 URL`, дубликаты домена блокируются).
- Поддержка PDF по прямой ссылке.
- Ретраи: сначала без прокси, потом до `N` прокси из списка.
- Нормализация текста для сравнения: lowercase, схлопывание пробелов, удаление пунктуации.
- Статусы: `NEW`, `CHANGED`, `UNCHANGED`, `FAILED`.
- Хранение двух последних версий на диск: `current.txt` и `previous.txt`.
- Единый HTML-отчет за запуск с подсвеченным diff для `CHANGED`.
- Логирование в консоль и в файл.

## Архитектура

- `tos_radar/cli.py`: входная точка (`init`, `run`, `report-open`).
- `tos_radar/runner.py`: оркестрация параллельной обработки.
- `tos_radar/fetcher.py`: получение HTML/PDF, таймауты, прокси-ретраи.
- `tos_radar/normalize.py`: нормализация текста.
- `tos_radar/diff_utils.py`: сравнение и HTML diff.
- `tos_radar/state_store.py`: файловое состояние (`current/previous`).
- `tos_radar/report.py`: общий HTML-отчет.
- `tos_radar/config.py`: загрузка URL и прокси из файлов.
- `tos_radar/settings.py`: загрузка параметров из `.env`.

## Требования

- `Python 3.12+`.
- `chromium` для Playwright (устанавливается через `make init` или `make run`).
- Linux/macOS (для `make report-open` на Linux нужен `xdg-open`, на macOS используется `open`).

## Быстрый старт

1. Подготовить конфиги:
```bash
cp .env.example .env
cp config/tos_urls.txt.example config/tos_urls.txt
cp config/proxies.txt.example config/proxies.txt
```
2. Заполнить `config/tos_urls.txt` реальными URL ToS.
3. При необходимости заполнить `config/proxies.txt`.
4. Инициализировать baseline:
```bash
make init
```
5. Выполнить проверку изменений:
```bash
make run
```
6. Открыть последний отчет:
```bash
make report-open
```

## Формат входных файлов

`config/tos_urls.txt`:

- Один URL на строку.
- В MVP допускается только один URL на домен.
- Пустые строки и строки, начинающиеся с `#`, игнорируются.

Пример:
```text
https://example.com/terms
https://example.org/tos.pdf
```

`config/proxies.txt`:

- Один прокси на строку.
- Поддерживаемый формат: `host:port`.
- Поддерживаемый формат: `host:port:login:pass`.

Пример:
```text
127.0.0.1:8080
127.0.0.1:8081:user:password
```

## Конфигурация через `.env`

- `TOS_URLS_FILE` (по умолчанию `config/tos_urls.txt`)
- `PROXIES_FILE` (по умолчанию `config/proxies.txt`)
- `CONCURRENCY` (по умолчанию `20`)
- `TIMEOUT_SEC` (по умолчанию `60`)
- `RETRY_PROXY_COUNT` (по умолчанию `3`)
- `RETRY_BACKOFF_BASE_SEC` (по умолчанию `0.8`)
- `RETRY_BACKOFF_MAX_SEC` (по умолчанию `8.0`)
- `RETRY_JITTER_SEC` (по умолчанию `0.4`)
- `LOG_LEVEL` (по умолчанию `INFO`)

## Поведение `init` и `run`

`make init`:

- Загружает документы и сохраняет baseline.
- Помечает элементы как `NEW`.
- Формирует общий отчет в `reports/`.

`make run`:

- Сравнивает свежую версию с `current.txt`.
- Если есть изменение, статус `CHANGED`, создается diff, baseline обновляется.
- Если изменений нет, статус `UNCHANGED`.
- Если документ получить не удалось, статус `FAILED`, baseline не меняется.
- Для `FAILED` в отчете фиксируются `error_code` и текст ошибки.
- Если baseline отсутствует для домена, запись получает `NEW`.

## Ретраи и прокси

- Попытка 1: без прокси.
- Дальше: до `RETRY_PROXY_COUNT` прокси из `config/proxies.txt`.
- На каждую попытку действует `TIMEOUT_SEC`.
- Между попытками используется exponential backoff с jitter.
- При успешной последней попытке именно она считается финальным результатом URL.

## Что считается изменением

- Сравнение делается по нормализованному тексту.
- Игнорируются различия в регистре, пунктуации и пробелах.
- Изменения дат вида `Last updated` считаются реальным изменением (если поменялся текст даты).

## Данные и артефакты

- Состояние `current`: `data/state/<domain>/current.txt`.
- Состояние `previous`: `data/state/<domain>/previous.txt`.
- Логи запуска: `logs/run-YYYYMMDD-HHMMSS.log`.
- HTML-отчеты: `reports/report-YYYYMMDD-HHMMSS.html`.

## Make-команды

- `make install`: создать venv и поставить зависимости Python.
- `make install-browser`: установить Chromium для Playwright.
- `make init`: первичный сбор baseline.
- `make run`: регулярный запуск сравнения.
- `make test`: unit-тесты.
- `make lint`: `ruff`.
- `make report-open`: открыть последний отчет.

## Cron (ежедневный запуск)

Пример запуска каждый день в `03:30`:

```cron
30 3 * * * cd /path/to/tos-radar && make run >> /path/to/tos-radar/logs/cron.log 2>&1
```

Если используется отдельный пользователь/окружение, проверьте путь к `python3.12` и доступность `playwright`-браузера в этом окружении.

## Тесты

- `tests/test_config.py`: парсинг URL/прокси и валидация доменов.
- `tests/test_normalize.py`: нормализация текста.
- `tests/test_diff_utils.py`: сравнение и генерация diff.
- `tests/test_fetcher.py`: порядок попыток без/с прокси.
- `tests/test_state_store.py`: ротация `current -> previous`.

Запуск:
```bash
make test
make lint
```

## Ограничения MVP

- Нет UI и аккаунтов пользователей.
- Нет автопоиска ToS по сайту.
- Нет перехода по ссылкам со страницы на документ.
- Нет уведомлений в Telegram/email/webhook.
- Нет БД и длинной истории версий.
- Эвристическая очистка HTML без site-specific правил.

## Roadmap

### MVP

- Ежедневный запуск по cron.
- Мониторинг фиксированного списка URL.
- HTML/PDF обработка и diff-отчет.
- Ретраи с прокси после попытки без прокси.
- Файловое хранение двух последних версий.

### Полный релиз

- UI с аккаунтами и настройками источников.
- Пользовательские списки сервисов.
- Автопоиск актуальной ToS/договора на сайте.
- Многоканальные уведомления.
- БД и аналитика истории изменений.
- Гибкие правила очистки для конкретных доменов.

## Контекст решений

Подробно зафиксированный контекст обсуждения: `docs/context.md`.
