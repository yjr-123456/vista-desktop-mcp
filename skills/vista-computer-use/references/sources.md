# Source review and integration decisions

Reviewed 2026-10-25. Exact fetched-source hashes and GitHub revisions are in
[source-manifest.json](source-manifest.json). The third-party skills are not
installed. This directory is the only skill entrypoint for these capabilities.

## cenglin123/computer-use-mcp — MIT

Reviewed its skill's `workflows.md` and `context-budget.md`. Integrated task
ownership, browser routing, focused observations, avoiding duplicate image reads,
and evidence-based recovery into our own workflow instructions. The read-only
archive audit implements trace verification for VISTA's own JSONL format.
Its repository scripts are project maintenance/curation utilities, not portable
desktop control helpers; copying those would not help this runtime. UIA, batching,
model-context quota claims and its separate MCP protocol are not imported.

Source: https://github.com/cenglin123/computer-use-mcp
License: [computer-use-mcp-MIT.txt](licenses/computer-use-mcp-MIT.txt).

## t1m0nch1k/computer-use-windows — MIT

Reviewed `scripts/window.py` and `scripts/screen.py`. Adapted window enumeration,
foreground inspection and focus workflow into `desktop_helpers.py`, using the
existing pywin32 dependency for pointer-safe API calls. Added exact handle/PID
matching and verification of actual foreground state; removed fuzzy first-match
selection, thread-input attachment and unrelated window mutations. Coordinate
mapping is implemented for VISTA's preview/crop metadata.

Screenshot deletion/expiry, overlay processes, separate capture store and a
second keyboard/mouse implementation are not included. VISTA retains original
frames in the user's `.agents` memory tree.

Source: https://github.com/t1m0nch1k/computer-use-windows
License: [computer-use-windows-MIT.txt](licenses/computer-use-windows-MIT.txt).

## ClawHub wimi321/computer-use-windows — version 0.1.1

Reviewed the version's file manifest and `pixelCompare.ts`/`imageResize.ts`.
The registry labels the package MIT-0 but its bundled vendor files have additional
provenance; no original runtime/vendor code is redistributed here. The reviewed
version also reports a suspicious scan verdict, which is a registry signal,
not a determination that every file is malicious. No installer was executed.

Implemented an original Pillow frame-region comparison and explicit coordinate
conversion. Unlike its live click guard, ours compares named archived frames,
supports a stated tolerance and raises on missing/invalid evidence. No
fail-open click behavior or model-specific image-token constants are imported.
The TypeScript/Python bootstrap, second MCP server and app/shortcut policy lists
are not copied. This keeps one runtime and the user's existing task scope.

Source: https://clawhub.ai/wimi321/skills/computer-use-windows
