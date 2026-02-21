# Актуальный контекст (кратко)

Дата обновления: 2026-02-21

## Сессия UI клиента (доп. контекст)

- Подробный лог решений по клиентскому веб-интерфейсу: `docs/client_ui_context_2026-02-21.md`
- Итоговый scope + чеклист реализации v1: `docs/v1_scope_checklist_2026-02-21.md`
- Исполнительный спринт-план v1: `docs/v1_sprint_execution_plan_2026-02-21.md`
- Issue-ready бэклог задач v1: `docs/v1_issue_backlog_2026-02-21.md`
- Интервью по UI закрыто (Q/A closed). Новые вопросы не задаем.
- Для незакрытых деталей действует правило: `deferred post-v1`.

## Backend кабинета (статус на 2026-02-21)

- Хранилище кабинета переведено на `MariaDB` (`pymysql`).
- Добавлены SQL-миграции (`migrations/001_init_cabinet.sql`) и запуск `make db-migrate`.
- Поднят минимальный HTTP API (`make api-run`) с health-check `GET /api/v1/health`.
- Реализованы backend-потоки первой волны:
  - settings + verify-email restriction;
  - Telegram link/unlink/disconnected/test-send (rate-limit + transport call);
  - session revoke при смене пароля;
  - soft-delete lifecycle (start/restore/access-state).
- На защищенных endpoint'ах включена проверка `X-Session-Id`.
- В режиме `RECOVERY_ONLY` разрешены только `access-state` и `restore`.
- Backend acceptance smoke автоматизирован (`make acceptance-smoke`).

## Цель

Автоматически мониторить изменения ToS-документов по фиксированным URL, сравнивать с baseline и формировать HTML-отчет.

## Текущий рабочий контур

- Запуски: `init`, `run`, `rerun-failed`, `report-open`.
- Основной режим: `make run`.
- После `run` автоматически выполняется один повтор для доменов со статусом `FAILED`.
- Для ручного догоняющего прогона есть `make rerun-failed`.

## Источники и ограничения

- Вход: `config/tos_urls.txt`.
- Дубли доменов не роняют запуск: берется первый URL, остальные пропускаются.
- Поддерживаются HTML и прямые PDF URL.
- По ссылкам со страницы в MVP не переходим.

## Качество извлечения

- Quality gates:
  - `SHORT_CONTENT` (слишком короткий HTML);
  - `TECHNICAL_PAGE` (тех/блок-страницы).
- В отчете выводится `text_length` для быстрой визуальной валидации документа.

## Классификация изменений

- `change_level`: `NOISE`, `MINOR`, `MAJOR`.
- `change_ratio`: доля изменений.
- Отдельный раздел отчета: `Suspicious CHANGED`.

## Ретраи и таймауты

- 1 попытка без прокси + до `RETRY_PROXY_COUNT` прокси.
- Exponential backoff + jitter.
- Жесткий timeout на попытку и на сервис целиком.

## Multi-tenant

Все данные разделены по `TENANT_ID`:

- `data/state/<tenant_id>/<domain>/...`
- `data/<tenant_id>/last_failed_urls.txt`
- `logs/<tenant_id>/...`
- `reports/<tenant_id>/...`

## Что считать нормальным после релизов

- При смене формата хранения текста возможен одноразовый всплеск `CHANGED`.
- После стабилизации второй/третий прогон должен возвращаться к реальным изменениям.
