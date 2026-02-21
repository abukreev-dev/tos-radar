# V1 Sprint Execution Plan

Дата: 2026-02-21  
Основа: `docs/v1_scope_checklist_2026-02-21.md`

## 1) Принципы исполнения

- Работаем только в рамках утвержденного v1 scope.
- Любые новые идеи и расширения сразу в `post-v1`.
- Закрываем задачи вертикальными срезами: backend + frontend + проверка.

## 2) Критический путь

- `Профиль -> Уведомления` (ядро ценности).
- Тарифные ограничения + paywall-паттерны.
- Ошибочные состояния UI (`403`, `404`, `500`).
- Жизненный цикл аккаунта (verify, reset, soft-delete).

## 3) План на 10 рабочих дней

## День 1

- Подготовка бэклога из scope по блокам FE/BE/QA.
- Декомпозиция API-контрактов для `Профиль -> Уведомления`.
- Подготовка тест-кейсов для verify/email/telegram.

## День 2

- Backend: модель настроек каналов, валидации, лимиты.
- Backend: ограничения `email digest only if verified`.
- Backend unit tests по валидации.

## День 3

- Backend: Telegram link/unlink flow + test-send rate-limit.
- Backend: обработка `telegram disconnected` и автосброс тумблеров.
- Интеграционные тесты по Telegram.

## День 4

- Frontend: экран `Профиль -> Уведомления` (базовый).
- Frontend: кнопки `Сохранить`, `Отправить тест`, resend verify.
- Frontend: состояния ошибок/успеха сохранения.

## День 5

- Frontend: `Дашборд` KPI + CTA `Включить уведомления`.
- Frontend: onboarding-чеклист (скрываемый).
- Frontend: paywall inline-паттерн для ограничений.

## День 6

- Frontend: `Мои сервисы` (поиск, сортировка по дате подключения, карточка).
- Frontend: confirm-модалка удаления сервиса.
- Frontend: empty-state и переходы.

## День 7

- Frontend: `Изменения` (карточки, фильтры период+сервис, empty-state).
- Frontend: страницы ошибок `403`, `404`, `500` (+ short error id).
- UX-полировка mobile/desktop.

## День 8

- Backend: логика дайджеста `09:00 timezone profile`.
- Backend: timezone fallback `Europe/Moscow`.
- Backend: сценарии hard-bounce/switch email.

## День 9

- QA: полный регресс по чеклисту acceptance.
- Исправление найденных P0/P1 дефектов.
- Повторный прогон ключевых сценариев.

## День 10

- Stabilization freeze.
- Финальный staging sign-off.
- Подготовка release candidate.

## 4) Минимальный список эпиков

- E1: Notification Settings Core (`Профиль -> Уведомления`).
- E2: Telegram Integration v1.
- E3: Billing Limits + Paywall UX.
- E4: Dashboard and My Services UX.
- E5: Changes Feed v1.
- E6: Auth/Security Lifecycle.
- E7: Error States and Reliability.
- E8: QA, Stabilization, Release.

## 5) Definition of Ready для задачи

- Есть четкий scope и non-scope.
- Описан API-контракт (если нужен).
- Есть критерии приемки.
- Понятны зависимости от других задач.

## 6) Definition of Done для спринта

- Все критические блоки из раздела `2` закрыты.
- Acceptance checklist пройден на staging.
- Открытых P0/P1 нет.
- Все незакрытые идеи явно зафиксированы как `post-v1`.
