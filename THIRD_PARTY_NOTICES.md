# Third-party notices

This is an independent adaptation. It is not an official VISTA release and does
not imply endorsement by the VISTA authors. MIT licensing of this adapter does
not replace the copyright notices of upstream components.

## VISTA

- Upstream: https://github.com/joshhhhhan/VISTA
- Revision: c97c354f0a8948256545a3e8850a1848f8e5b8c1
- Original file: src/vista/core/session.py
- Distributed file: vendor/vista_session.py (unmodified)
- Copyright (c) 2026 VISTA contributors
- License: MIT; complete original notice in [vendor/VISTA-LICENSE](vendor/VISTA-LICENSE).

The Windows adapter subclasses this implementation in memory_store.py. Desktop
input, MCP integration, workspace binding and additional evidence handling live
outside the unmodified upstream module. The README credits the original authors
and reproduces their research citation.

## computer-use-windows

Window-handling concepts/code were adapted from
https://github.com/t1m0nch1k/computer-use-windows into
skills/vista-computer-use/scripts/desktop_helpers.py. The original MIT notice is
retained in [computer-use-windows-MIT.txt](skills/vista-computer-use/references/licenses/computer-use-windows-MIT.txt).
Adaptations include exact HWND/PID targeting and foreground verification.

## computer-use-mcp

Workflow guidance draws on https://github.com/cenglin123/computer-use-mcp.
The original MIT notice is retained in
[computer-use-mcp-MIT.txt](skills/vista-computer-use/references/licenses/computer-use-mcp-MIT.txt).
No second MCP runtime is distributed.

## Reviewed but not redistributed

The ClawHub computer-use-windows package was reviewed for comparison; its
runtime and vendor files are not included. See the skill's
[source notes](skills/vista-computer-use/references/sources.md) and
[source manifest](skills/vista-computer-use/references/source-manifest.json)
for reviewed versions and adaptation details.

## Runtime dependencies

Dependencies are installed separately from requirements-lock.txt; their source,
binaries and virtual environments are not bundled in this repository. They retain
their respective licenses.
