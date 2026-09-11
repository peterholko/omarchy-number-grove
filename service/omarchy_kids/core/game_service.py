"""Shared lifecycle for optional game-owned challenge verifiers."""
import copy
from datetime import datetime
import pwd
import secrets
from . import paths, storage
from .game_platform import PROVIDERS


class GameService:
    module = ""

    def __init__(self, host):
        self.host = host
        self.provider = PROVIDERS[self.module][0]
        self.path = host.layout.config_path.with_name(self.module + ".json")
        self.state_dir = host.layout.state_dir / self.module
        self.config = storage.read_json(self.path, {"users": {}})
        self.accounts = {}

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
            self.accounts[uid] = storage.read_json(self.state_dir / (str(uid) + ".json"), {"pending": None, "receipts": {}})
        return self.accounts[uid]

    def persist(self, uid, state):
        storage.write_json(self.state_dir / (str(uid) + ".json"), state)
        self.accounts[uid] = state

    def settle(self, uid):
        state = copy.deepcopy(self.account(uid))
        changed = False
        for receipt in state["receipts"].values():
            if receipt.get("reward_seconds") is None:
                seconds = self.host.platform.settle(pwd.getpwuid(uid).pw_name, self.provider, receipt)
                if seconds is not None:
                    receipt["reward_seconds"] = seconds; changed = True
        if changed:
            self.persist(uid, state)

    def status(self, uid):
        self.settle(uid)
        state = self.account(uid)
        return {"ok": True, **self.host.platform.status(uid, self.provider),
            "receipts": [{"id": r["id"], "reward_seconds": r.get("reward_seconds")}
                for r in list(state["receipts"].values())[-256:]]}

    def dispatch(self, peer, message):
        uid = self.host.resolve_uid(peer, message)
        try:
            name = pwd.getpwuid(uid).pw_name
        except KeyError:
            return {"ok": False, "error": "unknown_user"}
        if uid == 0:
            return {"ok": False, "error": "choose_child_user"}
        command = message.get("cmd")
        with self.host.lock:
            if command == "users.set":
                if peer != 0 or type(message.get("enabled")) is not bool:
                    return {"ok": False, "error": "not_authorized"}
                config = copy.deepcopy(self.config)
                if message["enabled"]:
                    config["users"].setdefault(name, {})
                else:
                    config["users"].pop(name, None)
                storage.write_json(self.path, config); self.config = config
                return {"ok": True}
            if name not in self.config["users"]:
                return {"ok": False, "error": "not_managed"}
            if command == "status":
                return self.status(uid)
            if command not in ("begin", "complete"):
                return {"ok": False, "error": "unknown_command"}
            status = self.status(uid)
            state = copy.deepcopy(self.account(uid))
            now = self.host.clock.now()
            if command == "begin":
                if not status["active"]:
                    return {"ok": False, "error": status["reason"]}
                try:
                    challenge = self.challenge(message)
                except ValueError:
                    return {"ok": False, "error": "invalid_challenge"}
                state["pending"] = {**challenge, "id": secrets.token_hex(16), "issued_at": now,
                    "day": datetime.fromtimestamp(now).date().isoformat()}
                self.persist(uid, state)
                return {"ok": True, **self.public_challenge(state["pending"])}
            identifier = message.get("id")
            if isinstance(identifier, str) and identifier in state["receipts"]:
                receipt = state["receipts"][identifier]
                return {"ok": True, "id": identifier, **receipt["verdict"], "reward_seconds": receipt.get("reward_seconds"),
                    "reward_pending": receipt.get("reward_seconds") is None, "already_completed": True}
            pending = state.get("pending")
            if not pending or identifier != pending["id"]:
                return {"ok": False, "error": "stale_challenge"}
            elapsed = now - pending["issued_at"]
            if elapsed > 1800 or elapsed < 0 or pending["day"] != datetime.fromtimestamp(now).date().isoformat():
                return {"ok": False, "error": "expired"}
            if elapsed < 1.5:
                return {"ok": False, "error": "too_fast"}
            verdict = self.verify(pending, message, elapsed)
            if not verdict.get("ok"):
                return verdict
            receipts = state["receipts"]
            # Keep unresolved requests; completed receipts may be trimmed
            # because the consumed challenge can no longer be resubmitted.
            while len(receipts) >= 256:
                obsolete = next((k for k, r in receipts.items() if r.get("reward_seconds") is not None), None)
                if obsolete is None:
                    break
                receipts.pop(obsolete)
            credit = verdict.get("correct", True) and len(receipts) < 256
            receipt = {"id": identifier, "backend": "platform", "reward_day": pending["day"],
                "reward_seconds": None if credit else 0, "verdict": verdict}
            state["pending"] = None
            # Retain the latest verdict too, so a lost game acknowledgement
            # can be replayed even while the credit queue is full.
            receipts[identifier] = receipt
            self.persist(uid, state)
            self.settle(uid)
            saved = self.account(uid)["receipts"].get(identifier, receipt)
            return {**verdict, "id": identifier, "reward_seconds": saved.get("reward_seconds"),
                "reward_pending": saved.get("reward_seconds") is None, "already_completed": False}

    def tick(self, now, elapsed):
        # Load enrolled state after a restart so lost acknowledgements settle
        # even if the game window is no longer open.
        for uid in self.managed_uids():
            self.settle(uid)

    def save(self):
        pass
