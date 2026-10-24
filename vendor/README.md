# Vendored VISTA visual-memory implementation

`vista_session.py` is an unmodified copy of `src/vista/core/session.py`
from VISTA commit `c97c354f0a8948256545a3e8850a1848f8e5b8c1`.
It is distributed under the MIT license in `VISTA-LICENSE`.

The desktop adapter uses SessionController inspection, crop validation,
frame lookup, pixel sampling, and atomic note writing. The original module
is retained intact to make upstream comparison and updates straightforward.
Only Pillow and the Python standard library are required by this module.

The adapter imports this local copy and has no runtime dependency on a
sibling VISTA directory. See the main README for desktop-specific behavior.
