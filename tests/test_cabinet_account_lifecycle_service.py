from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tos_radar.cabinet_account_lifecycle_service import (
    AccountLifecycleError,
    get_access_state,
    restore_account,
    start_soft_delete,
)
from tos_radar.cabinet_models import AccountLifecycleState, AccountStatus


class CabinetAccountLifecycleServiceTests(unittest.TestCase):
    def test_start_soft_delete_sets_recovery_window(self) -> None:
        with patch("tos_radar.cabinet_account_lifecycle_service.write_account_lifecycle_state") as mocked:
            now = datetime(2026, 2, 21, 15, 0, 0, tzinfo=UTC)
            state = start_soft_delete("t1", "u1", now=now, ttl_days=30)
        self.assertEqual(state.status, AccountStatus.SOFT_DELETED)
        self.assertEqual(state.soft_deleted_at, now.isoformat())
        self.assertEqual(state.purge_at, (now + timedelta(days=30)).isoformat())
        mocked.assert_called_once()

    def test_restore_account_from_soft_deleted(self) -> None:
        current = AccountLifecycleState(
            status=AccountStatus.SOFT_DELETED,
            soft_deleted_at="2026-02-20T10:00:00+00:00",
            purge_at="2026-03-22T10:00:00+00:00",
        )
        with patch(
            "tos_radar.cabinet_account_lifecycle_service.read_account_lifecycle_state",
            return_value=current,
        ), patch("tos_radar.cabinet_account_lifecycle_service.write_account_lifecycle_state") as mocked:
            state = restore_account(
                "t1",
                "u1",
                now=datetime(2026, 2, 21, 15, 0, 0, tzinfo=UTC),
            )
        self.assertEqual(state.status, AccountStatus.ACTIVE)
        mocked.assert_called_once()

    def test_restore_fails_when_not_soft_deleted(self) -> None:
        with patch(
            "tos_radar.cabinet_account_lifecycle_service.read_account_lifecycle_state",
            return_value=AccountLifecycleState(status=AccountStatus.ACTIVE),
        ):
            with self.assertRaises(AccountLifecycleError) as ctx:
                restore_account("t1", "u1", now=datetime(2026, 2, 21, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(ctx.exception.code, "ACCOUNT_NOT_SOFT_DELETED")

    def test_access_state_recovery_only(self) -> None:
        current = AccountLifecycleState(
            status=AccountStatus.SOFT_DELETED,
            soft_deleted_at="2026-02-20T10:00:00+00:00",
            purge_at="2026-03-22T10:00:00+00:00",
        )
        with patch(
            "tos_radar.cabinet_account_lifecycle_service.read_account_lifecycle_state",
            return_value=current,
        ):
            access = get_access_state(
                "t1",
                "u1",
                now=datetime(2026, 2, 21, 15, 0, 0, tzinfo=UTC),
            )
        self.assertEqual(access.mode, "RECOVERY_ONLY")


if __name__ == "__main__":
    unittest.main()
