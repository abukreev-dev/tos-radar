# Backend Acceptance Pass (E8-01)

Дата: 2026-02-21  
Область: backend API и доменная логика кабинета в текущем репозитории

## Цель

Зафиксировать воспроизводимый acceptance-прогон для backend-части v1 и связать его с критериями из `docs/v1_scope_checklist_2026-02-21.md`.

## Команда прогона

```bash
make acceptance-backend
```

## Покрытие acceptance-критериев backend

1. Настройки уведомлений (`Профиль -> Уведомления`)
- Ограничение verify email для email digest: `tests/test_cabinet_service.py`
- API чтения/сохранения настроек: `tests/test_cabinet_api.py`
- Деградационные сценарии save (`4xx/5xx/network/timeout`): `tests/test_cabinet_api_degradation.py`

2. Telegram flow
- Link/confirm/unlink/disconnected: `tests/test_cabinet_telegram_service.py`, `tests/test_cabinet_api.py`
- Test-send rate limits (`1/60 sec`, `20/day`): `tests/test_cabinet_telegram_test_service.py`, `tests/test_cabinet_api.py`

3. Безопасность и lifecycle
- Revoke всех сессий при security-сценариях: `tests/test_cabinet_security_service.py`, `tests/test_cabinet_api.py`
- Soft-delete/recovery-only/restore: `tests/test_cabinet_account_lifecycle_service.py`, `tests/test_cabinet_api.py`, `tests/test_acceptance_smoke_backend.py`

4. Интеграционный smoke сценарий
- Сквозной backend smoke: `tests/test_acceptance_smoke_backend.py`

## Результат прогона

- Статус: PASS
- Блокирующие P0/P1 дефекты backend: не обнаружены по результатам тестового набора.
