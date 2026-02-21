from __future__ import annotations

import json
import os


def get_billing_plan(tenant_id: str, user_id: str) -> str:
    """Return normalized billing plan code for a user.

    Supported values: FREE, PAID_30, PAID_100.
    Source of truth is env-driven for MVP wiring:
    - BILLING_PLAN_OVERRIDES_JSON: {"tenant:user": "PAID_30"}
    - BILLING_PLAN_DEFAULT: FREE|PAID_30|PAID_100
    """
    overrides_raw = os.getenv("BILLING_PLAN_OVERRIDES_JSON", "").strip()
    key = f"{tenant_id}:{user_id}"

    if overrides_raw:
        try:
            parsed = json.loads(overrides_raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            value = parsed.get(key)
            normalized = _normalize_plan(value)
            if normalized is not None:
                return normalized

    default_plan = _normalize_plan(os.getenv("BILLING_PLAN_DEFAULT", "FREE"))
    return default_plan or "FREE"


def _normalize_plan(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().upper()
    if raw in {"FREE", "PAID_30", "PAID_100"}:
        return raw
    return None
