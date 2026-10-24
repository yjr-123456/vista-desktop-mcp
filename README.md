# VISTA Desktop MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Built on [VISTA: A Visual Harness for Reasoning in an Interactive World](https://github.com/joshhhhhan/VISTA)
by Qiushi Han, Keya Hu, Linlu Qiu, Cathy Wu, and Kaiming He (2026).
See the [paper](https://arxiv.org/abs/2610.02200) and
[project website](https://vista-research.github.io/).

This local stdio MCP adapter adds desktop tools to normal Codex sessions. It
reuses a vendored copy of VISTA’s `SessionController` for archived-frame inspection,
cropping, and pixel sampling. It does not launch the Linux/Docker game harness,
change the model, or require an ARC/API key. This is a local adaptation, not an
upstream VISTA Windows desktop feature.

## Install

This project is standalone; it does not need the original VISTA checkout.
Requires an interactive Windows desktop, Python 3.12, and uv. Clone and install:

```powershell
git clone https://github.com/yjr-123456/vista-desktop-mcp.git
cd vista-desktop-mcp
```

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt
.venv/Scripts/python.exe -m unittest discover -v
.venv/Scripts/python.exe smoke_test.py
.venv/Scripts/python.exe install_codex.py --with-skill
```

The installer backs up `~/.codex/config.toml` (or `$env:CODEX_HOME/config.toml`)
and adds only `[mcp_servers.vista_desktop]`. Existing differing entries are not
overwritten. Keep this checkout and `.venv` at their configured paths.
Restart Codex after installation; already-running sessions may not discover it.
`--with-skill` also installs `vista-computer-use` under the Codex skills directory.
An existing differing skill is backed up before updating its bundled files.

For a real input test, run `smoke_test.py --gui`. It briefly opens its own test
window, checks entry focus, types Chinese text, tests Ctrl+A/Backspace, then
closes the window. It uses a temporary archive that is removed on exit.

## Usage

Ask Codex, for example:

> 使用 vista_desktop 查看当前桌面，放大检查目标窗口，再按我的要求操作。

The MCP server supplies usage instructions automatically. The companion
[`vista-computer-use`](skills/vista-computer-use/SKILL.md) skill explains workspace
binding, coordinate conversion, outcome verification and evidence-based recovery.
The [compatibility notes](skills/vista-computer-use/references/compatibility.md)
compare GitHub/ClawHub skills and document tool mappings and unsupported features.
Its twelve tools are:

| Tool | Function |
| --- | --- |
| `configure_session` | Bind the current task workspace; create or resume a memory session |
| `observe` | Capture primary monitor, archive original PNG, return preview and native dimensions |
| `play` | Click, double-click, move, drag, scroll, press, hotkey, Unicode typing, wait; then capture |
| `inspect` | Revisit one or more archived turns or regions using VISTA |
| `read_pixels` | Sample exact RGB values; desktop colors are not limited to VISTA's game palette |
| `history` | Read action/frame history, with pagination |
| `sessions` | Discover old archives across server restarts |
| `memory_notes` | Read/write current-session GUIDE.md and WORKING.md; read older notes |
| `remember` | Save a verified observation linked to archived frame IDs and hashes |
| `recall` | Search saved observations by text/tags, returning image references |
| `windows` | Enumerate windows, inspect foreground, focus exact HWND/PID and archive the result |
| `compare_frames` | Compare archived frame regions and report pixel differences |

The skill includes reviewed workflow guidance and
[`desktop_helpers.py`](skills/vista-computer-use/scripts/desktop_helpers.py) for
coordinate mapping, window diagnosis, archived-image comparison and image-hash
verification. Window focus and frame comparison are also exposed directly by the
MCP. Sources, versions, adaptation details and retained MIT licenses are documented
in the skill's [source notes](skills/vista-computer-use/references/sources.md).
No additional third-party computer-use skill or runtime is installed.

Bind the actual conversation workspace first with `configure_session`, then
observe. All input and crop coordinates are **original physical
pixels**, not scaled preview pixels. An inspect response gives both the source
region and rendered image dimensions. For a crop, map rendered `(u,v)` back as
`x = region.x + u * region.width / image_size.width`, and similarly for y.
Act once, inspect the result, then proceed. After an action error, observe before
retrying because input may have been delivered before capture failed.

## Workspace-local multimodal memory

Global MCP processes cannot be assumed to inherit the current conversation's
working directory. The default server creates no archive until the agent calls:

```json
{"workspace":"E:/Code_Space/MyProject"}
```

Use the real task directory with `configure_session`, not the MCP installation
directory. The server requires an existing absolute workspace and returns the
canonical `session_dir`. No user prompt is needed when the directory is already
known from the conversation environment.

```text
<workspace>/
  .agents/
    vista-desktop/
      .gitignore
      sessions/
        <session-id>/
          session.json       # schema, provenance, coordinate convention
          frames/
            turn_000_frame_000.png
          history.jsonl      # action metadata, native size, relative path, hash
          memories.jsonl     # agent observations linked to visual evidence
          MEMORY.md          # readable observations with relative frame links
          GUIDE.md           # reusable verified knowledge
          WORKING.md         # objective, current state, next step
          .writer.lock       # OS-managed exclusive writer lease
```

`memories.jsonl`/`MEMORY.md` appear on the first `remember` call. Frames stay
lossless; previews may be scaled. Relative frame paths and SHA-256 hashes keep
evidence traceable if the workspace moves. Absolute paths in old history and the
creation-time workspace in `session.json` are provenance; use `session_dir` plus
`relative_path` after a move. Only the memory subtree is ignored by Git, not the
entire `.agents` directory or project skills.

The generated ID identifies a **VISTA memory session**, not a Codex thread ID.
Repeated binding to the same workspace in the same process retains the current
session unless a new ID is supplied. After restart, use `sessions` to find the
old ID and `configure_session(workspace=..., session_id=..., resume=true)` to
continue it. A concurrent writer is rejected. Historical read tools accept
`session_id` within the bound workspace. A different workspace has a separate
archive namespace.

Use `remember(summary, turns, tags)` at meaningful verified milestones, then
`recall(query)` and `inspect` for retrieval. Recall is text/tag matching, not
embedding search. Summaries and GUIDE/WORKING notes are agent-authored; they are
not inferred automatically or silently injected after compaction. The skill
directs the agent to recover and check them, then observe the current desktop.

Frames are retained until their archive is explicitly removed. Typed text is
omitted from action metadata but can be visible in screenshots. No third-party
memory service is added; images returned to Codex still participate in normal
model/tool processing.

### Explicit launch options and old archives

`server.py --workspace <absolute-path>` prebinds a known workspace. Avoid pinning
this in global Codex config if the server is used across projects. `--session`
and `--resume` can select an existing session for either launch option.

The old `%LOCALAPPDATA%/VISTA/desktop/` archives are left intact: their originating
workspace cannot be reliably inferred. To read/resume them explicitly, launch
`server.py --data-dir <old-root> --session <old-id> --resume`. `--data-dir` is also
an explicit override for users with another storage convention; it cannot be
combined with `--workspace`. New default sessions no longer write there.

## Scope and controls

- Windows interactive **primary monitor** only; tested at 3840x2160. Secondary
  monitors, UAC secure desktop, and locked/remote-disconnected sessions are not supported.
- Uses screenshot reasoning and keyboard/mouse input, without adding OCR/UIA.
- Unicode input does not replace the clipboard. Some games and elevated apps
  may reject injected input; this adapter does not elevate privileges.
- Moving the mouse to a primary-screen corner triggers the PyAutoGUI fail-safe
  for input actions. `observe` remains available.
- Avoid simultaneous desktop actions from multiple Codex sessions or manual
  input while an action is running; the lock serializes only one server process.
- Disable by setting `enabled = false` in `[mcp_servers.vista_desktop]`, then
  restart Codex. Remove that table to uninstall registration. A dated configuration
  backup is kept beside `config.toml`; avoid restoring it wholesale after other edits.

Codex MCP configuration reference:
https://developers.openai.com/learn/docs-mcp

## Acknowledgments and citation

The visual-memory foundation comes from **VISTA**, including archived-frame
inspection, crop validation, pixel sampling, and persistent working-memory
conventions. This project adds a Windows desktop MCP adapter and a companion
Codex skill. It is an independent adaptation, not an official VISTA release.

The vendored `SessionController` comes from upstream commit
[`c97c354`](https://github.com/joshhhhhan/VISTA/tree/c97c354f0a8948256545a3e8850a1848f8e5b8c1).
See [vendor/README.md](vendor/README.md) for implementation provenance and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for redistribution notices.
If you use the VISTA work in research, please cite the original authors using
the citation supplied in the upstream README:

```bibtex
@misc{han2026vista,
  title         = {{VISTA}: A Visual Harness for Reasoning in an Interactive World},
  author        = {Han, Qiushi and Hu, Keya and Qiu, Linlu and Wu, Cathy and He, Kaiming},
  year          = {2026},
  eprint        = {2610.02200},
  archivePrefix = {arXiv},
  url           = {https://arxiv.org/abs/2610.02200}
}
```

## License

This project is licensed under the [MIT License](LICENSE).
The vendored VISTA code retains its original copyright notice and
[MIT license](vendor/VISTA-LICENSE). Other adapted material retains its
respective attribution and MIT notices in the skill's
[source notes](skills/vista-computer-use/references/sources.md) and
[license directory](skills/vista-computer-use/references/licenses/).

## Performance

Default response previews use JPEG quality 90 (4:4:4); original evidence remains full-resolution lossless PNG with SHA-256. observe/play accept preview_format="png" and optional preview_region={x,y,width,height}. Map coordinates through the returned region offset and preview dimensions. Archives remain full-screen. Reuse action-result images instead of redundant observations.

Returned timings_ms separates capture/window-context/archive/preview processing, excluding action waits, MCP transport, model inference and hooks. Move/drag use seconds once as movement duration. Archive hashing reuses encoded bytes without rereading disk.

Run .venv/Scripts/python benchmark_preview.py for seven encoding samples of one live frame, without input or saved screenshots. On 2026-10-25: PNG 32.36 ms / 569326 bytes; JPEG 4.20 ms / 280864 bytes. Screen content affects results; these are not end-to-end timings.

Client hooks and shell startup can dominate end-to-end latency. If calls stall while
server timings remain low, diagnose the client launch/hook path separately.

Reconnect/restart the MCP after updating to load the implementation.

### Focus recovery and guarded input

windows(focus) returns focused=false, status=focus_denied and a fresh full-screen
preview when Windows refuses activation. Inspect that evidence before choosing a
recovery action; no automatic click or keyboard fallback occurs. Stale HWND/PID
validation remains an error.

play optionally accepts expected_hwnd and expected_pid together. A foreground
mismatch returns status=not_applied, reason=foreground_changed and a full-screen
preview without sending input. This checks top-level window identity immediately
before dispatch; it does not establish field focus or eliminate concurrent races.
The skill uses these responses directly, avoiding a redundant observe round trip.

### Shared observation context

configure_session(initial_observe=true) optionally returns binding metadata and
the first screenshot in one call; the default remains metadata-only. Every new
screenshot includes best-effort active_window metadata sampled just after capture.
Reuse its HWND/PID for guarded input instead of a separate foreground query.
A window-query failure returns active_window=null plus window_context_error and
preserves the screenshot. This metadata is not atomic with capture and does not
prove field focus. These capabilities apply to desktop applications generally.
