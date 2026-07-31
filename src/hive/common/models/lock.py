"""Pydantic model for resource locks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Lock(BaseModel):
    """Resource lock for a single device operation.

    A lock has an owner, a session id, an operation name, and a TTL.
    Expired locks are ignored by acquire(); an explicit sweeper
    removes them from the store (H1+).
    """

    model_config = ConfigDict(extra="forbid")

    device_id: str
    owner: str
    session_id: str
    operation: str
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def new(
        cls,
        device_id: str,
        owner: str,
        session_id: str | None = None,
        operation: str = "unspecified",
        ttl_seconds: int = 900,
        metadata: dict[str, Any] | None = None,
    ) -> Lock:
        now = datetime.now(UTC)
        return cls(
            device_id=device_id,
            owner=owner,
            session_id=session_id or f"sess-{uuid4()}",
            operation=operation,
            acquired_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            metadata=metadata or {},
        )

    def is_expired(self, at: datetime | None = None) -> bool:
        ts = at or datetime.now(UTC)
        return ts >= self.expires_at

    def renew(self, ttl_seconds: int) -> None:
        """Extend TTL from now (or from current expiry, whichever is later).

        Ensures monotonic non-decreasing expiry on repeated renews.
        """
        now = datetime.now(UTC)
        base = max(now, self.expires_at)
        self.expires_at = base + timedelta(seconds=ttl_seconds)
