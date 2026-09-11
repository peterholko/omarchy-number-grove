"""Optional API v1 adapter. Only verified, durable game receipts reach it.

The worker never holds the host's accounting lock while invoking another
service. A lost reply is retried with the same receipt, including after reboot.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import threading
import time

PLUGIN = "peterholko.screen-time"
PROVIDERS = {"pawberry": ("peterholko.pawberry", "Pawberry Pet Hotel", "completed problem"),
    "grove": ("peterholko.number-grove", "Number Grove", "completed challenge"),
    "typing": ("peterholko.paw-post", "Paw Post Typing", "completed delivery")}


def submit(user, provider, receipt, day):
    try:
        completed = subprocess.run(["/usr/bin/omarchy-peterholko-screen-time-credit", "--user", user,
            "--provider", provider, "--receipt", receipt, "--day", day], capture_output=True, text=True, timeout=15)
        result = json.loads(completed.stdout)
        if isinstance(result, dict) and type(result.get("ok")) is bool:
            return result
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return {"ok": False, "error": "unavailable"}


class Platform:
    def __init__(self, runtime=Path("/run/peterholko-screen-time"), transport=submit, clock=time.time, trusted_owner=0):
        self.runtime, self.transport, self.clock = Path(runtime), transport, clock
        self.trusted_owner = trusted_owner
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="game-credit")
        self.jobs, self.retry_at = {}, {}
        self.lock = threading.Lock()

    def status(self, uid, provider):
        unavailable = {"backend": "platform", "available": False, "active": False, "enabled": False,
            "reason": "platform_unavailable", "earned_today_seconds": 0, "remaining_today_seconds": 0,
            "seconds_per_event": 0, "minutes_per_problem": 0, "daily_cap_minutes": 0, "balance_seconds": 0}
        path = self.runtime / str(uid) / "status.json"
        try:
            if path.is_symlink() or path.stat().st_uid != self.trusted_owner or not -5 <= self.clock() - path.stat().st_mtime <= 30:
                return unavailable
            data = json.loads(path.read_text())
            if data.get("plugin_id") != PLUGIN or data.get("api_version") != 1 or not data.get("ok"):
                return unavailable
            credits = data.get("credits", {})
            policy = credits.get("providers", {}).get(provider, {})
            enabled = credits.get("enabled") is True and policy.get("enabled") is True
            earned = int(policy.get("credited_today_seconds", 0))
            cap = int(policy.get("daily_cap_minutes", 0))
            room = max(0, min(int(credits.get("room_seconds", 0)), cap * 60 - earned))
            reason = "" if enabled else "credits_disabled"
            if enabled and (data.get("philosophy") != "limits" or data.get("phase") in ("paused", "bedtime", "idle") or data.get("locked")):
                reason = "policy_blocked"
            if not reason and room == 0:
                reason = "daily_cap_reached"
            seconds = int(policy.get("seconds_per_event", 0))
            return {**unavailable, "available": True, "enabled": enabled, "active": not reason, "reason": reason,
                "seconds_per_event": seconds, "minutes_per_problem": seconds / 60, "daily_cap_minutes": cap,
                "earned_today_seconds": earned, "remaining_today_seconds": room, "balance_seconds": int(data.get("remaining_seconds", 0))}
        except (OSError, ValueError, TypeError, AttributeError):
            return unavailable

    def settle(self, user, provider, receipt):
        key = (user, provider, receipt["id"], receipt["reward_day"])
        with self.lock:
            future = self.jobs.get(key)
            if future is None:
                if len(self.jobs) >= 32 or time.monotonic() < self.retry_at.get(key, 0):
                    return None
                self.jobs[key] = self.pool.submit(self.transport, *key)
                return None
            if not future.done():
                return None
            self.jobs.pop(key)
            try:
                result = future.result()
            except Exception:
                result = {"ok": False, "error": "unavailable"}
            if not isinstance(result, dict):
                result = {"ok": False, "error": "unavailable"}
            if result.get("ok") is True:
                seconds = result.get("credited_seconds")
                if type(seconds) is int and 0 <= seconds <= 3600:
                    self.retry_at.pop(key, None)
                    return seconds
            elif result.get("error") in {"wrong_day", "not_managed", "unregistered_provider", "receipt_capacity_reached", "invalid_receipt"}:
                self.retry_at.pop(key, None)
                return 0
            self.retry_at[key] = time.monotonic() + 5
            # Bound diagnostic retry bookkeeping; durable receipts live in
            # the game state, so eviction here cannot duplicate a credit.
            if len(self.retry_at) > 512:
                self.retry_at.pop(next(iter(self.retry_at)))
            return None

    def close(self):
        self.pool.shutdown(wait=True)
