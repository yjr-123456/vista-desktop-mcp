"""Actual stdio MCP handshake, screenshots and optional isolated GUI input test."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent


def probe_window(directory):
    import ctypes
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    import tkinter as tk
    window = tk.Tk()
    window.title("VISTA isolated input verification")
    window.geometry("500x180+200+200")
    window.attributes("-topmost", True)
    tk.Label(window, text="Temporary VISTA input test; closes automatically").pack(pady=10)
    entry = tk.Entry(window, font=("Arial", 16))
    entry.pack(fill="x", padx=20, pady=10)
    window.update()
    directory.joinpath("ready.json").write_text(json.dumps({
        "x": entry.winfo_rootx() + 30, "y": entry.winfo_rooty() + 10,
    }))

    def poll():
        directory.joinpath("value.json").write_text(json.dumps(entry.get(), ensure_ascii=False), encoding="utf-8")
        directory.joinpath("focused.json").write_text(json.dumps(window.focus_get() is entry))
        window.after(100, poll)

    poll()
    window.after(45000, window.destroy)
    window.mainloop()


async def run(gui_test):
    with tempfile.TemporaryDirectory(prefix="vista-smoke-") as temp:
        directory = Path(temp)
        params = StdioServerParameters(command=sys.executable,
            args=[str(HERE / "server.py")], cwd=str(directory))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {t.name for t in (await client.list_tools()).tools}
                assert names == {"configure_session", "observe", "play", "inspect", "read_pixels", "history", "sessions", "memory_notes", "remember", "recall", "windows", "compare_frames"}, names

                async def call(name, arguments):
                    result = await client.call_tool(name, arguments)
                    assert not result.isError, (name, result)
                    return result

                assert (await client.call_tool("observe", {})).isError
                assert (await client.call_tool("play", {"action": "wait"})).isError
                assert not directory.joinpath(".agents").exists()
                await call("configure_session", {"workspace": str(directory), "session_id": "smoke"})
                frame = await call("observe", {})
                assert any(c.type == "image" for c in frame.content), frame
                metadata = json.loads(next(c.text for c in frame.content if c.type == "text"))
                assert metadata["width"] > 0
                session_dir = directory / ".agents" / "vista-desktop" / "sessions" / "smoke"
                assert Path(metadata["session_dir"]) == session_dir
                assert Path(metadata["path"]).is_file()
                await call("windows", {"action": "active"})
                same = await call("compare_frames", {"before_turn": 0, "after_turn": 0})
                assert json.loads(next(c.text for c in same.content if c.type == "text"))["identical"]
                assert (await client.call_tool("windows", {"action": "focus", "hwnd": 0})).isError
                assert (session_dir / metadata["relative_path"]).is_file()
                await call("remember", {"summary": "Verified primary monitor screenshot", "turns": [0], "tags": ["smoke"]})
                recalled = await call("recall", {"query": "smoke"})
                payload = json.loads(next(c.text for c in recalled.content if c.type == "text"))
                assert payload["memories"][0]["evidence"][0]["turn"] == 0
                assert session_dir.joinpath("MEMORY.md").is_file()
                zoom = await call("inspect", {"question": "top left", "views": [
                    {"label": "corner", "turn": 0, "region": {"x": 0, "y": 0, "width": 100, "height": 100}}]})
                assert any(c.type == "image" for c in zoom.content)
                await call("read_pixels", {"turn": 0, "rows": 2, "columns": 2})
                await call("memory_notes", {"name": "WORKING", "content": "smoke test turn 0"})
                await call("history", {})
                await call("sessions", {})
                invalid = await client.call_tool("play", {"action": "click", "x": -1, "y": -1})
                assert invalid.isError
                waited = await call("play", {"action": "wait", "seconds": 0})
                wait_metadata = json.loads(next(c.text for c in waited.content if c.type == "text"))
                assert wait_metadata["turn"] == 1
                assert Path(wait_metadata["path"]).parent == session_dir / "frames"
                print("PASS: MCP handshake, 12 tools, workspace binding, .agents archive, memories, screenshot, crop, pixels, notes, history, window query, frame comparison, invalid input")
                print(f"Primary desktop: {metadata['width']}x{metadata['height']}")
                if gui_test:
                    probe = subprocess.Popen([sys.executable, str(__file__), "--probe", temp],
                                             creationflags=subprocess.CREATE_NO_WINDOW)
                    try:
                        for _ in range(100):
                            if directory.joinpath("ready.json").exists():
                                break
                            if probe.poll() is not None:
                                raise RuntimeError("GUI probe exited")
                            await asyncio.sleep(0.1)
                        point = json.loads(directory.joinpath("ready.json").read_text())
                        listed = await call("windows", {"action": "list", "title_contains": "VISTA isolated input verification"})
                        targets = json.loads(next(c.text for c in listed.content if c.type == "text"))["windows"]
                        assert len(targets) == 1, "Expected exactly one isolated test window"
                        await call("windows", {"action": "focus", "hwnd": targets[0]["hwnd"], "expected_pid": targets[0]["pid"]})
                        await call("play", {"action": "click", **point})
                        await asyncio.sleep(0.2)
                        assert json.loads(directory.joinpath("focused.json").read_text()), "Test entry did not receive focus"
                        await call("play", {"action": "type", "text": "VISTA 中文输入 123"})
                        await asyncio.sleep(0.3)
                        value = json.loads(directory.joinpath("value.json").read_text(encoding="utf-8"))
                        assert value == "VISTA 中文输入 123", repr(value)
                        await call("play", {"action": "hotkey", "keys": ["ctrl", "a"]})
                        await call("play", {"action": "press", "keys": ["backspace"]})
                        await asyncio.sleep(0.3)
                        assert json.loads(directory.joinpath("value.json").read_text(encoding="utf-8")) == ""
                        print("PASS: window discovery/focus, real GUI click, Unicode Chinese input, Ctrl+A, Backspace, screenshots after actions")
                    finally:
                        probe.terminate()
                        probe.wait(timeout=10)
                assert next(c for c in frame.content if c.type == "image").mimeType == "image/jpeg"
                crop_region = {"x": 10, "y": 20, "width": 120, "height": 80}
                cropped = await call("observe", {"preview_region": crop_region, "preview_format": "png"})
                cm = json.loads(next(c.text for c in cropped.content if c.type == "text"))
                assert cm["preview_region"] == crop_region
                assert (cm["preview_width"], cm["preview_height"]) == (120, 80)
                assert next(c for c in cropped.content if c.type == "image").mimeType == "image/png"
                assert all(v >= 0 for v in cm["timings_ms"].values())
                from PIL import Image
                with Image.open(cm["path"]) as original:
                    assert original.size == (metadata["width"], metadata["height"])
                bad = await client.call_tool("play", {"action": "wait", "seconds": 0, "preview_region": {"x": metadata["width"], "y": 0, "width": 1, "height": 1}})
                assert bad.isError
                print("PASS: JPEG/PNG preview, crop offsets, full archive, timings, invalid region")
                initialized = await call("configure_session", {"workspace": str(directory), "session_id": "second", "initial_observe": True})
                assert any(c.type == "image" for c in initialized.content)
                initial_meta = json.loads(initialized.content[1].text)
                assert "active_window" in initial_meta
                assert initial_meta["action"] == "initial_observe"
                old = await call("recall", {"query": "smoke", "session_id": "smoke"})
                assert json.loads(next(c.text for c in old.content if c.type == "text"))["memories"]
                await call("inspect", {"question": "historical evidence", "views": [{"label": "previous", "turn": 0}], "session_id": "smoke"})
                rejected = await client.call_tool("memory_notes", {"name": "WORKING", "content": "overwrite", "session_id": "smoke"})
                assert rejected.isError
                await call("configure_session", {"workspace": str(directory), "session_id": "smoke", "resume": True})
                assert session_dir.joinpath("WORKING.md").read_text(encoding="utf-8") == "smoke test turn 0"
                print("PASS: post-action archive, historical retrieval, read-only old notes and explicit resume")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    if args.probe:
        probe_window(args.probe)
    else:
        asyncio.run(run(args.gui))
