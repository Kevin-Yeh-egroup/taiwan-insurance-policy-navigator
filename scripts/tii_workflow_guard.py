#!/usr/bin/env python3
"""Concurrency guards and atomic writers for the local TII workflow."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


INTEGRATION_LOCK_TOKEN_ENV = "TII_INTEGRATION_LOCK_TOKEN"


class WorkflowLockError(RuntimeError):
    """Raised when another worker owns a workflow lock."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _temporary_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{uuid4().hex}.pending")


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write one file completely before replacing the visible destination."""

    path.parent.mkdir(parents=True, exist_ok=True)
    pending = _temporary_sibling(path)
    try:
        with pending.open("x", encoding=encoding, newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Stream JSONL to a sibling file and expose it only when complete."""

    path.parent.mkdir(parents=True, exist_ok=True)
    pending = _temporary_sibling(path)
    count = 0
    try:
        with pending.open("x", encoding="utf-8", newline="") as handle:
            for row in rows:
                handle.write(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)
    return count


def read_lock_payload(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


class ExclusiveFileLock:
    """Small cross-process lock based on exclusive file creation."""

    def __init__(
        self,
        path: Path,
        *,
        purpose: str,
        owner: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.path = path
        self.purpose = purpose
        self.owner = owner
        self.extra = extra or {}
        self.token = uuid4().hex
        self.acquired = False

    def acquire(self) -> "ExclusiveFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "token": self.token,
            "pid": os.getpid(),
            "created_at": now_iso(),
            "purpose": self.purpose,
            "owner": self.owner,
            **self.extra,
        }
        try:
            with self.path.open("x", encoding="utf-8", newline="") as handle:
                handle.write(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as error:
            current = read_lock_payload(self.path)
            raise WorkflowLockError(
                f"workflow lock is already held: {self.path}; "
                f"owner={current.get('owner') or 'unknown'}; "
                f"purpose={current.get('purpose') or 'unknown'}; "
                f"created_at={current.get('created_at') or 'unknown'}"
            ) from error
        self.acquired = True
        return self

    def release(self) -> None:
        if not self.acquired:
            return
        current = read_lock_payload(self.path)
        if current.get("token") != self.token:
            raise WorkflowLockError(
                f"workflow lock ownership changed before release: {self.path}"
            )
        self.path.unlink(missing_ok=True)
        self.acquired = False

    def __enter__(self) -> "ExclusiveFileLock":
        return self.acquire()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.release()


class IntegrationLock(ExclusiveFileLock):
    """A re-entrant canonical-writer lock inherited by child processes."""

    def __init__(
        self,
        path: Path,
        *,
        purpose: str,
        owner: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(path, purpose=purpose, owner=owner, extra=extra)
        self.inherited = False
        self.previous_environment_token: str | None = None

    def acquire(self) -> "IntegrationLock":
        inherited_token = os.environ.get(INTEGRATION_LOCK_TOKEN_ENV, "")
        if inherited_token:
            current = read_lock_payload(self.path)
            if current.get("token") != inherited_token:
                raise WorkflowLockError(
                    "integration lock token does not match the visible lock: "
                    f"{self.path}"
                )
            self.token = inherited_token
            self.inherited = True
            self.acquired = True
            return self

        self.previous_environment_token = os.environ.get(
            INTEGRATION_LOCK_TOKEN_ENV
        )
        super().acquire()
        os.environ[INTEGRATION_LOCK_TOKEN_ENV] = self.token
        return self

    def release(self) -> None:
        if not self.acquired:
            return
        if self.inherited:
            self.acquired = False
            return
        super().release()
        if self.previous_environment_token is None:
            os.environ.pop(INTEGRATION_LOCK_TOKEN_ENV, None)
        else:
            os.environ[INTEGRATION_LOCK_TOKEN_ENV] = (
                self.previous_environment_token
            )


def canonical_integration_lock(root: Path) -> Path:
    return (
        root
        / "work"
        / "tii-workflow-locks"
        / "canonical-integration.lock"
    )
