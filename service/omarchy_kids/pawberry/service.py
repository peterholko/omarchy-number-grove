"""Per-account daily practice quotas, committed before a pet is awarded.

The game owns its presentation. This service issues problems, verifies every
intermediate step and owns limits and completion counters. One
outstanding problem per account prevents concurrent windows spending a slot.
"""
from datetime import datetime
import copy
import pwd
import secrets
from ..core import paths, storage
from .rewards import Rewards, DEFAULTS, valid_patch
from . import work

OPERATIONS = ("add", "subtract", "multiply", "divide")
LIMITED = ("add", "subtract", "multiply")


def answer_for(problem):
    operation, a, b = (problem.get(key) for key in ("operation", "a", "b"))
    if type(a) is not int or type(b) is not int or operation not in OPERATIONS:
        raise ValueError("invalid problem")
    if operation == "divide":
        if not (10 <= a <= 99 and 2 <= b <= 9 and a % b == 0 and a // b <= 9):
            raise ValueError("use exact two-digit / one-digit table facts")
        return a // b
    small = operation == "multiply" and 1 <= a <= 9 and 1 <= b <= 9
    if not small and not (10 <= a <= 999 and 10 <= b <= 999):
        raise ValueError("invalid operands")
    if operation == "subtract" and a < b:
        raise ValueError("negative subtraction")
    return a + b if operation == "add" else a - b if operation == "subtract" else a * b


class Service:
    def __init__(self, host):
        self.host = host
        self.path = host.layout.config_path.with_name("pawberry.json")
        self.state_dir = host.layout.state_dir / "pawberry"
        self.config = storage.read_json(self.path, {"users": {}})
        self.accounts = {}
        self.rewards = Rewards(host)

    def managed_uids(self):
        result = []
        for name in self.config["users"]:
            try:
                result.append(pwd.getpwnam(name).pw_uid)
            except KeyError:
                pass
        return result

    def account(self, uid):
        if uid not in self.accounts:
            paths.private_dir(self.state_dir, scrub=False)
            self.accounts[uid] = storage.read_json(self.state_dir / (str(uid) + ".json"),
                {"day": "", "counts": {}, "pending": None, "receipt": None})
        state = self.accounts[uid]
        state.setdefault("receipts", {})
        if state.get("receipt"):
            state["receipts"].setdefault(state["receipt"]["id"], state["receipt"])
        today = datetime.fromtimestamp(self.host.clock.now()).date().isoformat()
        # Never reset backwards after a clock or timezone change.
        if today > state["day"]:
            state["day"], state["counts"] = today, {}
            self.persist(uid, state)
        return state

    def persist(self, uid, state):
        storage.write_json(self.state_dir / (str(uid) + ".json"), state)
        self.accounts[uid] = state

    def status(self, uid):
        self.settle_reward(uid)
        state = self.account(uid)
        name = pwd.getpwuid(uid).pw_name
        limits = {op: self.config["users"].get(name, {}).get(op) for op in LIMITED}
        counts = {op: state["counts"].get(op, 0) for op in OPERATIONS}
        return {"ok": True, "user": name, "day": state["day"], "limits": limits,
                "reward_receipts": [{"id": r["id"], "reward_seconds": r.get("reward_seconds")} for r in state["receipts"].values()],
                "screen_time": self.rewards.status(uid, self.reward_settings(name)),
                "completed": counts, "remaining": {op: None if limits.get(op) is None
                    else max(0, limits[op] - counts[op]) for op in OPERATIONS}}

    def reward_settings(self, name):
        return {**DEFAULTS, **self.config["users"].get(name, {}).get("screen_time", {})}

    def settle_reward(self, uid):
        state = self.account(uid)
        state = copy.deepcopy(state)
        changed = False
        for receipt in state["receipts"].values():
            if ("requested_seconds" in receipt or receipt.get("backend") == "platform") and receipt.get("reward_seconds") is None:
                result = self.rewards.settle(uid, receipt, self.reward_settings(pwd.getpwuid(uid).pw_name))
                if result is not None:
                    receipt["reward_seconds"] = result; changed = True
        if changed:
            if state.get("receipt"):
                state["receipt"] = state["receipts"][state["receipt"]["id"]]
            self.persist(uid, state)

    def dispatch(self, peer, message):
        command = message.get("cmd")
        uid = self.host.resolve_uid(peer, message)
        if uid == 0:
            return {"ok": False, "error": "choose_child_user"}
        try:
            name = pwd.getpwuid(uid).pw_name
        except KeyError:
            return {"ok": False, "error": "unknown_user"}
        if command == "users.set":
            if peer != 0 or type(message.get("enabled")) is not bool:
                return {"ok": False, "error": "not_authorized"}
            with self.host.lock:
                config = copy.deepcopy(self.config)
                if message["enabled"]:
                    config["users"].setdefault(name, {"screen_time": {**DEFAULTS, "backend": "platform"}})
                # Removing integration does not erase a child's practice limits.
                else:
                    config["users"].setdefault(name, {}).setdefault("screen_time", {})["enabled"] = False
                storage.write_json(self.path, config); self.config = config
                return {"ok": True}
        if command in ("limits.set", "settings.set"):
            patch = message.get("limits", {})
            reward_patch = message.get("screen_time", {}) if command == "settings.set" else {}
            if not isinstance(patch, dict) or (not patch and not reward_patch) or set(patch) - set(LIMITED) or any(
                    value is not None and (type(value) is not int or not 0 <= value <= 10000)
                    for value in patch.values()):
                return {"ok": False, "error": "invalid_limits"}
            if not valid_patch(reward_patch):
                return {"ok": False, "error": "invalid_rewards"}
            denied = self.host.auth.check(peer, message)
            if denied:
                return denied
            with self.host.lock:
                config = copy.deepcopy(self.config)
                config["users"].setdefault(name, {}).update(patch)
                if reward_patch:
                    settings = {**self.reward_settings(name), **reward_patch}
                    if settings["enabled"] and not self.rewards.status(uid, settings)["available"]:
                        return {"ok": False, "error": "screen_time_not_managed"}
                    config["users"][name]["screen_time"] = settings
                storage.write_json(self.path, config)
                self.config = config
                return self.status(uid)
        with self.host.lock:
            if command == "status":
                return self.status(uid)
            if command not in ("begin", "complete"):
                return {"ok": False, "error": "unknown_command"}
            self.settle_reward(uid)
            state = copy.deepcopy(self.account(uid))
            if command == "begin":
                problem = message.get("problem")
                try:
                    answer_for(problem if isinstance(problem, dict) else {})
                except ValueError:
                    return {"ok": False, "error": "invalid_problem"}
                operation = problem["operation"]
                status = self.status(uid)
                state = copy.deepcopy(self.account(uid))
                if status["remaining"][operation] == 0:
                    return {**status, "ok": False, "error": "daily_limit", "operation": operation}
                settings = self.reward_settings(name)
                modern = message.get("protocol") == 2
                if settings["enabled"] and settings["backend"] == "platform" and not modern:
                    return {"ok": False, "error": "update_game_required"}
                state["pending"] = work.generate(problem) if modern else {key: problem[key] for key in ("a", "b", "operation")}
                state["pending"]["id"] = secrets.token_hex(16)
                state["pending"].update(protocol=2 if modern else 1, issued_at=self.host.clock.now(), reward_backend=settings["backend"])
                self.persist(uid, state)
                return {**status, "id": state["pending"]["id"], "problem": {key: state["pending"][key] for key in ("a", "b", "operation")}}
            identifier = message.get("id")
            if isinstance(identifier, str) and identifier in state["receipts"]:
                return {**self.status(uid), "id": identifier, "already_completed": True,
                    "reward_seconds": self.account(uid)["receipts"][identifier].get("reward_seconds", 0)}
            pending = state.get("pending")
            if not pending or identifier != pending["id"]:
                return {"ok": False, "error": "stale_problem"}
            given = message.get("answer")
            if type(given) is not int or given != answer_for(pending):
                return {"ok": False, "error": "incorrect_answer"}
            if pending.get("protocol") == 2:
                if not work.verified(pending, message.get("steps")):
                    return {"ok": False, "error": "incomplete_work"}
                elapsed = self.host.clock.now() - pending["issued_at"]
                if elapsed > 3600 or elapsed < 0:
                    return {"ok": False, "error": "stale_problem"}
                if elapsed < max(1.5, len(message["steps"]) * 0.15):
                    return {"ok": False, "error": "too_fast"}
            status = self.status(uid)
            state = copy.deepcopy(self.account(uid))
            operation = pending["operation"]
            if status["remaining"][operation] == 0:
                return {**status, "ok": False, "error": "daily_limit", "operation": operation}
            state["counts"][operation] = state["counts"].get(operation, 0) + 1
            reward = status["screen_time"]
            symbols = {"add": "+", "subtract": "−", "multiply": "×", "divide": "÷"}
            state["receipt"] = {"id": identifier, "reward_seconds": 0}
            if reward["active"] and pending.get("reward_backend", "legacy") == reward.get("backend", "legacy"):
                state["receipt"].update(reward_seconds=None, reward_day=state["day"],
                    backend=reward.get("backend", "legacy"),
                    requested_seconds=reward["minutes_per_problem"] * 60,
                    daily_cap_minutes=reward["daily_cap_minutes"],
                    label=f'{pending["a"]} {symbols[operation]} {pending["b"]}')
            state["pending"] = None
            # Retain unacknowledged receipts across later problems and crashes.
            while len(state["receipts"]) >= 256:
                obsolete = next((key for key, value in state["receipts"].items() if value.get("reward_seconds") is not None), None)
                if obsolete is None:
                    state["receipt"]["reward_seconds"] = 0
                    break
                state["receipts"].pop(obsolete)
            state["receipts"][identifier] = state["receipt"]
            self.persist(uid, state)
            result = self.status(uid)
            return {**result, "id": identifier, "already_completed": False,
                "reward_seconds": self.account(uid)["receipt"]["reward_seconds"]}

    def tick(self, now, elapsed):
        for uid in set(self.accounts) | set(self.managed_uids()):
            self.settle_reward(uid)

    def save(self):
        # Every setting and completion is synchronously committed before reply.
        pass
