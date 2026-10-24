# Compatibility with other computer-use skills

Research checked on 2026-10-25. These are workflow references, not installed
backends or delegated authority. This skill was written specifically for
`vista_desktop`. The three selected sources have now been consolidated into
the workflow reference and adapted helper scripts; see [sources.md](sources.md)
for code provenance and retained licenses. No separate skill/runtime is installed.

| Source | Relevant behavior | Integration decision |
| --- | --- | --- |
| [cenglin123/computer-use-mcp](https://github.com/cenglin123/computer-use-mcp/blob/master/skills/computer-use/SKILL.md) | Task-scoped visual work, inline previews, original PNG evidence, browser-tool routing | Closest workflow fit. Map task/screenshot/crop concepts to configure_session/observe/inspect. Its UIA and batch tools need its own backend. |
| [t1m0nch1k/computer-use-windows](https://github.com/t1m0nch1k/computer-use-windows/blob/main/SKILL.md) | Persistent observe/act/verify loop, window control and physical coordinates | Window list/active/focus are adapted into VISTA. Screenshot disposal and overlay are omitted. |
| [itziktdk/openclaw-computer-use](https://github.com/itziktdk/openclaw-computer-use/blob/main/SKILL.md) | Cross-platform screenshot/mouse/keyboard scripts, including PyAutoGUI on Windows | Basic actions map well. Use existing MCP calls instead of invoking its separate scripts. |
| [ClawHub: wimi321/computer-use-windows](https://clawhub.ai/wimi321/skills/computer-use-windows) | Bundled standalone runtime/MCP built with npm, bootstrapped Python | It supplies an alternative backend, not a drop-in instruction layer for VISTA. Installing it would add another runtime. |
| [ClawHub: lexylent/desktop-control-win](https://clawhub.ai/lexylent/skills/desktop-control-win) | PowerShell window/process/clipboard tools and focus-before-input workflow | Window management could complement VISTA if separately installed and tested. Its OpenClaw-specific script paths are not usable as-is in Codex. |
| [ClawHub: ram-raghav-s/computer-use](https://clawhub.ai/ram-raghav-s/skills/computer-use) | Headless Linux Xvfb/XFCE/xdotool | Not a backend for this interactive Windows desktop. |

ClawHub was queried via `/api/v1/search`; candidate SKILL.md files were read via
`/api/v1/skills/<slug>/file?path=SKILL.md&owner=<owner>`. Owner names matter because
multiple publishers use the same slug. No candidate installer/runtime was run.

## Concrete mappings

| External workflow concept | vista_desktop call |
| --- | --- |
| Start task/session | configure_session(workspace, optional session_id) |
| Screenshot | observe() |
| Click/double click/drag/type/key/wheel | play(action, matching arguments) |
| Post-action screenshot | Already returned by play; inspect it |
| Crop/review earlier screen | inspect(question, views, optional session_id) |
| Enumerate/check/focus a window | windows(action, hwnd, expected_pid) |
| Compare archived pixels | compare_frames(before_turn, after_turn, optional region) |
| Visual checkpoint with explanation | remember(summary, turns, tags) |
| Recover task state | sessions, memory_notes, recall, history, then inspect |

Do not translate UIA selectors, OCR text targets, accessibility element IDs,
multi-monitor origins, background-window input, or arbitrary action batches into
guessed pixel coordinates. These capabilities are not present in this MCP.
When another available tool supplies them, use its actual contract and capture
fresh VISTA evidence after the state change. Avoid interleaving input from two
backends. Continue using VISTA's session path and persistent frame lifecycle.
