"""Workspace-local multimodal evidence and session binding."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone
from uuid import uuid4

from PIL import Image as PILImage
from vendor.vista_session import SessionController


class VisualMemory(SessionController):
    """Original lossless PNG frames; upstream VISTA inspection and sampling."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.frames_dir = self.directory / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.observation_mode = "vision"
        self.display_size = 1600
        self._size = (1, 1)
        self.log = self.directory / "history.jsonl"
        self.turn = max(
            (int(p.name.split("_")[1]) for p in self.frames_dir.glob("turn_*_frame_*.png")),
            default=-1,
        )

    def visual_size(self):
        return self._size

    def archive(self, image: PILImage.Image, event: dict) -> dict:
        self.turn += 1
        path = self.frames_dir / f"turn_{self.turn:03d}_frame_000.png"
        encoded = io.BytesIO()
        image.convert("RGB").save(encoded, format="PNG")
        payload = encoded.getvalue()
        path.write_bytes(payload)
        metadata = {
            "turn": self.turn, "time": datetime.now(timezone.utc).isoformat(),
            "width": image.width, "height": image.height,
            "path": str(path), "relative_path": path.relative_to(self.directory).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(), **event,
        }
        with self.log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        return metadata

    def remember(self, summary: str, turns: list[int], tags: list[str]) -> dict:
        if not summary.strip() or len(summary) > 8000:
            raise ValueError("summary must contain 1-8000 characters")
        if not 1 <= len(turns) <= 16 or any(type(t) is not int or t < 0 for t in turns):
            raise ValueError("Supply 1-16 nonnegative turn IDs as visual evidence")
        if len(tags) > 16 or any(not t.strip() or len(t) > 64 for t in tags):
            raise ValueError("Use at most 16 nonempty tags, each at most 64 characters")
        evidence = []
        for turn in dict.fromkeys(turns):
            paths = self._turn_frame_paths(turn)
            if not paths:
                raise ValueError(f"No frame for evidence turn {turn}")
            frame = paths[-1]
            with PILImage.open(frame) as image:
                width, height = image.size
            evidence.append({"turn": turn, "relative_path": frame.relative_to(self.directory).as_posix(),
                             "sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
                             "width": width, "height": height})
        entry = {"id": uuid4().hex, "time": datetime.now(timezone.utc).isoformat(),
                 "summary": summary, "tags": tags, "evidence": evidence,
                 "provenance": "agent-authored observation; not an instruction"}
        with (self.directory / "memories.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Human-readable companion with relative image links; JSONL is authoritative.
        entries = self.recall("", 100000)
        lines = ["# Visual memory", "", "Agent-authored observations linked to archived evidence.", ""]
        for item in entries:
            lines.extend([f"## {item['id']}", "", item["summary"], "",
                          "Tags: " + ", ".join(item["tags"]), ""])
            lines.extend(f"[Turn {e['turn']}]({e['relative_path']})" for e in item["evidence"])
            lines.append("")
        self._atomic_write_text(self.directory / "MEMORY.md", "\n".join(lines), mode=0o600)
        return entry

    def recall(self, query: str, limit: int) -> list[dict]:
        source = self.directory / "memories.jsonl"
        if not source.exists():
            return []
        words = query.casefold().split()
        entries = []
        for line in source.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            haystack = (entry["summary"] + " " + " ".join(entry["tags"])).casefold()
            if all(word in haystack for word in words):
                entries.append(entry)
        return entries[-limit:]

    def select(self, turn: int):
        paths = self._turn_frame_paths(turn)
        if not paths:
            raise ValueError(f"No archived frame for turn {turn}")
        with PILImage.open(paths[-1]) as image:
            self._size = image.size

    def _inspection_view(self, selection, index):
        self.select(selection["turn"])
        # Prevent upstream integer resize from producing a zero-width strip.
        region = selection.get("region")
        if region:
            w, h = region["width"], region["height"]
            if min(w, h) * self.display_size < max(w, h):
                raise ValueError("Region is too thin; choose a wider region")
        return super()._inspection_view(selection, index)

    def pixels(self, turn: int, region: dict | None, rows: int, columns: int):
        self.select(turn)
        metadata, samples = self._pixel_readout_view(
            {"label": "desktop", "turn": turn, "region": region,
             "rows": rows, "columns": columns}, 1,
        )
        # Desktop gradients exceed the game's 64-color palette. Preserve RGB.
        return {**metadata, "sampling": "equal-bin-centers", "rgb": samples}


def validate_session_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) or value.upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10)),
    }:
        raise ValueError("Session ID must be 1-100 letters/digits/hyphens/underscores, not a reserved name")
    return value


class SessionStore:
    """Explicit workspace binding prevents global MCP cwd from misplacing images."""

    def __init__(self):
        self.root = None
        self.workspace = None
        self.memory = None
        self._lease = None

    def require(self) -> VisualMemory:
        if self.memory is None:
            raise ValueError("Call configure_session(workspace=<absolute current task directory>) first")
        return self.memory

    def info(self) -> dict:
        memory = self.require()
        return {"session_id": memory.directory.name, "workspace": str(self.workspace) if self.workspace else None,
                "data_root": str(self.root), "session_dir": str(memory.directory),
                "next_turn": memory.turn + 1, "storage_version": 1}

    @staticmethod
    def _acquire(directory: Path):
        lease = (directory / ".writer.lock").open("a+b")
        try:
            lease.seek(0, 2)
            if lease.tell() == 0:
                lease.write(b"0")
                lease.flush()
            lease.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            lease.close()
            raise ValueError("Session is being written by another MCP process; use a new session") from exc
        return lease

    def close(self):
        if self._lease is not None:
            self._lease.close()
            self._lease = None
        self.memory = None

    def bind(self, workspace: str | Path | None = None, session_id: str | None = None,
             resume: bool = False, *, data_root: Path | None = None) -> dict:
        if workspace is not None and data_root is not None:
            raise ValueError("Specify workspace or explicit data_root, not both")
        workspace_path = None
        if data_root is None:
            if workspace is None:
                raise ValueError("An absolute existing workspace directory is required")
            workspace_path = Path(workspace).expanduser()
            if not workspace_path.is_absolute() or not workspace_path.is_dir():
                raise ValueError("workspace must be an absolute existing directory")
            workspace_path = workspace_path.resolve()
            root = (workspace_path / ".agents" / "vista-desktop" / "sessions").resolve()
            if not root.is_relative_to(workspace_path):
                raise ValueError(".agents storage must remain inside the workspace (check links/junctions)")
        else:
            root = data_root.resolve()
        if resume and session_id is None:
            raise ValueError("resume requires a session_id returned by sessions")
        if session_id is None and self.memory is not None and self.root == root:
            return self.info()
        session_id = validate_session_id(session_id if session_id is not None else datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
        directory = root / session_id
        if directory.resolve().parent != root:
            raise ValueError("Session directory escapes storage root")
        if self.memory is not None and self.memory.directory == directory:
            return self.info()
        if resume:
            if not directory.is_dir() or not (directory / "frames").is_dir():
                raise ValueError("Cannot resume an unknown session")
        elif directory.exists():
            raise ValueError("Session already exists; use resume=True or a new session ID")
        root.mkdir(parents=True, exist_ok=True)
        directory.mkdir(exist_ok=resume)
        lease = self._acquire(directory)
        try:
            memory = VisualMemory(directory)
            manifest = directory / "session.json"
            if not manifest.exists():
                memory._atomic_write_text(manifest, json.dumps({
                    "storage_version": 1, "session_id": session_id,
                    "workspace": str(workspace_path) if workspace_path else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "coordinate_space": "original primary-monitor physical pixels",
                    "frame_pattern": "frames/turn_NNN_frame_000.png",
                }, ensure_ascii=False, indent=2), mode=0o600)
            for name in ("GUIDE", "WORKING"):
                note = directory / f"{name}.md"
                if not note.exists():
                    memory._atomic_write_text(note, f"# {name}\n\n", mode=0o600)
            # Ignore just this memory subtree, leaving .agents/skills trackable.
            ignore = root.parent / ".gitignore"
            if workspace_path is not None and not ignore.exists():
                with ignore.open("x", encoding="utf-8") as handle:
                    handle.write("*\n!.gitignore\n")
        except Exception:
            lease.close()
            raise
        self.close()
        self.root, self.workspace, self.memory, self._lease = root, workspace_path, memory, lease
        return self.info()

    def get(self, session_id: str | None = None) -> VisualMemory:
        current = self.require()
        if session_id is None or session_id == current.directory.name:
            return current
        directory = self.root / validate_session_id(session_id)
        if directory.resolve().parent != self.root:
            raise ValueError("Session directory escapes storage root")
        if not directory.is_dir() or not (directory / "frames").is_dir():
            raise ValueError("Unknown session")
        return VisualMemory(directory)

    def list_sessions(self, limit: int):
        self.require()
        paths = sorted((p for p in self.root.iterdir() if p.is_dir() and (p / "frames").is_dir()),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        return {**self.info(), "current_session": self.memory.directory.name,
                "sessions": [p.name for p in paths[:limit]]}
