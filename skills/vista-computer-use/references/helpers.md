# Bundled helper scripts

Resolve `scripts/desktop_helpers.py` relative to this skill, not a fixed username.
Use the Python interpreter configured for `mcp_servers.vista_desktop` when Pillow
or pywin32 is needed. The current project uses its `.venv/Scripts/python.exe`.
These dependencies are already installed there; do not bootstrap another runtime.

Use MCP `windows` and `compare_frames` during ordinary GUI work. The CLI is for
offline calculations, archive diagnostics, or read-only window diagnosis. It
does not capture screenshots, send keyboard/mouse input, or expose CLI focus.
Focus mutations go through MCP so the resulting evidence is archived.

## Coordinate mapping

For a point at `(800,450)` in a 1600x900 preview of a 3840x2160 original:

```text
python <SKILL_DIR>/scripts/desktop_helpers.py map-point --point 800 450 --image-size 1600 900 --source-size 3840 2160
```

The result is `(1920,1080)` in original physical pixels. Supply
`--region X Y WIDTH HEIGHT` for an inspect crop, using its returned native region
and rendered image dimensions. Coordinates outside the preview/source are errors.

## Frame comparison

```text
python <SKILL_DIR>/scripts/desktop_helpers.py compare <before.png> <after.png> --region 100 200 300 100 --tolerance 0
```

Returns the changed pixel count/fraction and change bounds. Tolerance is the
maximum per-channel difference allowed before a pixel counts as changed.
Missing files, invalid crops and resolution mismatch fail instead of treating
the evidence as unchanged. This is an offline comparison, not an automatic live
click guard or a guarantee that a control has the same identity.

## Archive integrity

```text
python <SKILL_DIR>/scripts/desktop_helpers.py audit <session_dir>
```

Checks history and memory image references against their SHA-256 hashes, using
portable relative paths. Paths escaping the session directory are rejected.
It emits compact JSON and exits nonzero for failures or no recorded evidence.
Legacy archives without relative paths/hashes need manual review. No repairs,
deletions, new screenshots or notes are written by this command.

## Window diagnosis

```text
python <SKILL_DIR>/scripts/desktop_helpers.py windows list
python <SKILL_DIR>/scripts/desktop_helpers.py windows active
```

These return window handles, process IDs, bounds and active/minimized state.
For actual focusing use MCP `windows(action="focus", hwnd=..., expected_pid=...)`.
It verifies process identity and foreground state, and returns an archived image.
There is no fuzzy-title focus, forced process kill, privilege elevation, or
automatic input retry in this helper.
