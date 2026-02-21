from __future__ import annotations


def send_email(*, to_email: str, subject: str, body: str) -> None:
    """Placeholder email transport for MVP.

    Real SMTP/provider integration is intentionally deferred.
    """
    _ = (to_email, subject, body)
