"""Reviewed VISTA helpers: coordinate mapping, frame comparison, windows, evidence audit.

Windows routines adapt the Win32 window enumeration/focus concepts in
t1m0nch1k/computer-use-windows (MIT); see ../references/sources.md and licenses/.
Other routines are original VISTA implementations of documented workflow concepts.
No capture deletion, background service, installer, or second MCP server is included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


def map_point(x: float, y: float, image_width: int, image_height: int,
              source_width: int, source_height: int, region: dict | None = None) -> dict:
    if min(image_width, image_height, source_width, source_height) < 1:
        raise ValueError("Image dimensions must be positive")
    if not math.isfinite(x) or not math.isfinite(y) or not (0 <= x < image_width and 0 <= y < image_height):
        raise ValueError("Point must be within the displayed image")
    region = region or {"x": 0, "y": 0, "width": source_width, "height": source_height}
    left, top, width, height = (region[k] for k in ("x", "y", "width", "height"))
    if (min(left, top) < 0 or min(width, height) < 1 or left + width > source_width
            or top + height > source_height):
        raise ValueError("Crop must be within the original source image")
    return {"x": min(left + width - 1, math.floor(left + x * width / image_width + 0.5)),
            "y": min(top + height - 1, math.floor(top + y * height / image_height + 0.5)),
            "coordinate_space": "original primary-monitor physical pixels"}


def compare_frames(before: Path, after: Path, region: dict | None = None, tolerance: int = 0) -> dict:
    """Report pixel changes; missing evidence is an error, never implicit success."""
    from PIL import Image, ImageChops
    if not 0 <= tolerance <= 255:
        raise ValueError("tolerance must be 0-255")
    with Image.open(before) as a, Image.open(after) as b:
        if a.size != b.size:
            raise ValueError("Frame dimensions changed; reacquire coordinates before comparing")
        width, height = a.size
        region = region or {"x": 0, "y": 0, "width": width, "height": height}
        left, top, rw, rh = (region[k] for k in ("x", "y", "width", "height"))
        if min(left, top) < 0 or min(rw, rh) < 1 or left + rw > width or top + rh > height:
            raise ValueError("Region lies outside the frame")
        box = (left, top, left + rw, top + rh)
        diff = ImageChops.difference(a.convert("RGB").crop(box), b.convert("RGB").crop(box))
        red, green, blue = diff.split()
        maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        mask = maximum.point([255 if n > tolerance else 0 for n in range(256)])
        changed = mask.histogram()[255]
        bbox = mask.getbbox()
        return {"identical": changed == 0, "changed_pixels": changed,
                "changed_fraction": changed / (rw * rh), "tolerance": tolerance,
                "region": region, "source_size": {"width": width, "height": height},
                "changed_bounds": [bbox[0] + left, bbox[1] + top, bbox[2] + left, bbox[3] + top] if bbox else None,
                "meaning": "Pixel comparison only; unchanged pixels do not establish task success or target identity"}


def _window_api():
    if sys.platform != "win32":
        raise RuntimeError("Window helpers require Windows")
    import ctypes
    import win32con
    import win32gui
    import win32process
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    return win32gui, win32process, win32con


def window_info(hwnd: int) -> dict:
    gui, process, _ = _window_api()
    if not gui.IsWindow(hwnd):
        raise ValueError("Window no longer exists; enumerate again")
    _, pid = process.GetWindowThreadProcessId(hwnd)
    left, top, right, bottom = gui.GetWindowRect(hwnd)
    return {"hwnd": hwnd, "pid": pid, "title": gui.GetWindowText(hwnd),
            "bounds": {"x": left, "y": top, "width": right - left, "height": bottom - top},
            "minimized": bool(gui.IsIconic(hwnd)), "active": hwnd == gui.GetForegroundWindow(),
            "coordinate_space": "physical screen pixels; secondary-monitor bounds may be negative"}


def list_windows() -> list[dict]:
    gui, _, _ = _window_api()
    windows = []

    def collect(hwnd, _):
        if gui.IsWindowVisible(hwnd) and gui.GetWindowText(hwnd).strip():
            try:
                windows.append(window_info(hwnd))
            except Exception:
                pass  # A window may close between enumeration and inspection.
        return True

    gui.EnumWindows(collect, None)
    return windows


def active_window() -> dict | None:
    gui, _, _ = _window_api()
    hwnd = gui.GetForegroundWindow()
    return window_info(hwnd) if hwnd else None


def focus_window(hwnd: int, expected_pid: int) -> dict:
    gui, _, constants = _window_api()
    current = window_info(hwnd)
    if current["pid"] != expected_pid:
        raise ValueError("Window process changed; enumerate again before focusing")
    if current["minimized"]:
        gui.ShowWindow(hwnd, constants.SW_RESTORE)
    error = None
    try:
        gui.SetForegroundWindow(hwnd)
    except Exception as exc:
        error = str(exc)
    result = window_info(hwnd)
    if not result["active"]:
        raise RuntimeError("Windows did not grant foreground focus; observe before retrying" + (f": {error}" if error else ""))
    return result


def audit_session(session_dir: Path) -> dict:
    """Read-only integrity audit of recorded image references, including moved archives."""
    root = session_dir.resolve(strict=True)
    checks = []
    for name in ("history.jsonl", "memories.jsonl"):
        source = root / name
        if not source.exists():
            continue
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            try:
                entry = json.loads(line)
                evidence = entry["evidence"] if name == "memories.jsonl" else [entry]
                for frame in evidence:
                    relative = frame.get("relative_path")
                    if not isinstance(relative, str) or Path(relative).is_absolute():
                        raise ValueError("Missing/invalid relative_path (legacy archive needs manual review)")
                    image = (root / relative).resolve()
                    if not image.is_relative_to(root):
                        raise ValueError("Image reference leaves session directory")
                    expected = frame.get("sha256")
                    actual = hashlib.sha256(image.read_bytes()).hexdigest()
                    checks.append({"source": name, "line": number, "turn": frame.get("turn"),
                                   "relative_path": relative, "ok": bool(expected) and actual == expected})
            except (ValueError, TypeError, KeyError, OSError) as exc:
                checks.append({"source": name, "line": number, "ok": False, "error": str(exc)})
    return {"session_dir": str(root), "ok": bool(checks) and all(c["ok"] for c in checks),
            "checked_references": len(checks), "failures": [c for c in checks if not c["ok"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    point = sub.add_parser("map-point")
    point.add_argument("--point", type=float, nargs=2, required=True, metavar=("X", "Y"))
    point.add_argument("--image-size", type=int, nargs=2, required=True)
    point.add_argument("--source-size", type=int, nargs=2, required=True)
    point.add_argument("--region", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    compare = sub.add_parser("compare")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--region", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    compare.add_argument("--tolerance", type=int, default=0)
    audit = sub.add_parser("audit")
    audit.add_argument("session_dir", type=Path)
    windows = sub.add_parser("windows")
    windows.add_argument("action", choices=["list", "active"])
    args = parser.parse_args()
    region = dict(zip(("x", "y", "width", "height"), args.region)) if getattr(args, "region", None) else None
    try:
        if args.command == "map-point":
            result = map_point(*args.point, *args.image_size, *args.source_size, region)
        elif args.command == "compare":
            result = compare_frames(args.before, args.after, region, args.tolerance)
        elif args.command == "audit":
            result = audit_session(args.session_dir)
        else:
            result = list_windows() if args.action == "list" else active_window()
        print(json.dumps(result, ensure_ascii=True))
        return 1 if args.command == "audit" and not result["ok"] else 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
