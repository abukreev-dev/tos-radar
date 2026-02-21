from __future__ import annotations

import unittest
from unittest.mock import patch

from tos_radar.cabinet_billing_service import get_billing_plan


class CabinetBillingServiceTests(unittest.TestCase):
    def test_default_plan_is_free(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(get_billing_plan("t1", "u1"), "FREE")

    def test_default_plan_from_env(self) -> None:
        with patch.dict("os.environ", {"BILLING_PLAN_DEFAULT": "PAID_30"}, clear=True):
            self.assertEqual(get_billing_plan("t1", "u1"), "PAID_30")

    def test_override_has_priority(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "BILLING_PLAN_DEFAULT": "FREE",
                "BILLING_PLAN_OVERRIDES_JSON": '{"t1:u1":"PAID_100","t1:u2":"PAID_30"}',
            },
            clear=True,
        ):
            self.assertEqual(get_billing_plan("t1", "u1"), "PAID_100")
            self.assertEqual(get_billing_plan("t1", "u2"), "PAID_30")
            self.assertEqual(get_billing_plan("t1", "u3"), "FREE")

    def test_invalid_values_fallback_to_free(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "BILLING_PLAN_DEFAULT": "UNKNOWN",
                "BILLING_PLAN_OVERRIDES_JSON": '{"t1:u1":"ENTERPRISE"}',
            },
            clear=True,
        ):
            self.assertEqual(get_billing_plan("t1", "u1"), "FREE")


if __name__ == "__main__":
    unittest.main()
