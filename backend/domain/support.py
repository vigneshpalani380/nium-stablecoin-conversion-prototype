"""Small shared helpers: clock, ids, asset naming, demo faults, structured logging."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("wallet")


# ---- clock -------------------------------------------------------------------------------
class SystemClock:
    """Naive UTC clock (SQLite stores naive datetimes)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)


class FrozenClock:
    """Controllable clock for tests and expiry scenarios."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, 12, 0, 0)
        self._lock = threading.Lock()

    def now(self) -> datetime:
        with self._lock:
            return self._now

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._now += timedelta(seconds=seconds)


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.isoformat(timespec="milliseconds") + "Z"


# ---- ids / naming -------------------------------------------------------------------------
def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def network_key(network: str | None) -> str:
    """Normalise the null fiat network so uniqueness constraints work."""
    return network or ""


def display_name(asset_code: str, network: str | None) -> str:
    return asset_code if not network else f"{asset_code}-{network.title()}"


# ---- demo fault injection ----------------------------------------------------------------
@dataclass
class DemoFaults:
    """Demo/test-only faults. Boolean faults are one-shot: consumed by the next conversion."""

    pause_after_reserve_seconds: float = 0.0
    fail_mid_reserve: bool = False
    fail_mid_settle: bool = False
    timeout_after_commit: bool = False
    # Uncertain settlement commit (one-shot). What actually happened in the database:
    #   "COMMITTED"   - settlement committed, then the connection was lost before the acknowledgement
    #   "ROLLED_BACK" - the connection was lost during COMMIT and the settlement rolled back
    uncertain_commit: str | None = None
    # If true, automated-recovery lookups also fail (simulated continued unavailability) -> human review.
    recovery_lookup_fails: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def take(self, name: str) -> bool:
        with self._lock:
            if getattr(self, name):
                setattr(self, name, False)
                return True
            return False

    def take_uncertain_commit(self) -> tuple[str, bool] | None:
        """Consume the uncertain-commit fault together with its recovery behaviour."""
        with self._lock:
            if self.uncertain_commit is None:
                return None
            fault = (self.uncertain_commit, self.recovery_lookup_fails)
            self.uncertain_commit = None
            self.recovery_lookup_fails = False
            return fault

    def update(self, **values: object) -> None:
        with self._lock:
            for key, value in values.items():
                if value is None or key not in self.snapshot_unlocked():
                    continue
                if key == "uncertain_commit" and value == "OFF":
                    value = None
                setattr(self, key, value)

    def snapshot_unlocked(self) -> dict:
        return {
            "pause_after_reserve_seconds": self.pause_after_reserve_seconds,
            "fail_mid_reserve": self.fail_mid_reserve,
            "fail_mid_settle": self.fail_mid_settle,
            "timeout_after_commit": self.timeout_after_commit,
            "uncertain_commit": self.uncertain_commit,
            "recovery_lookup_fails": self.recovery_lookup_fails,
        }

    def snapshot(self) -> dict:
        with self._lock:
            return self.snapshot_unlocked()

    def reset(self) -> None:
        with self._lock:
            self.pause_after_reserve_seconds = 0.0
            self.fail_mid_reserve = self.fail_mid_settle = self.timeout_after_commit = False
            self.uncertain_commit = None
            self.recovery_lookup_fails = False


# ---- logging --------------------------------------------------------------------------------
def log_event(event: str, **fields: object) -> None:
    logger.info(json.dumps({"event": event, **fields}, default=str))
