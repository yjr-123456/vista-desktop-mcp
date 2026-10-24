# Consolidated desktop workflows

## Choose the narrowest usable tool

For webpage content, use an available browser tool attached to the needed user
session. Native dialogs and desktop applications use VISTA. If a separate,
already-available UIA tool exposes an unambiguous control, it may be used for
that control; VISTA does not invent UIA handles or pretend to provide OCR.

Orient once with `observe`. When the active application is uncertain, use
`windows(action="list", title_contains="...")`, select an exact `hwnd`/`pid`,
then `windows(action="focus", hwnd=..., expected_pid=...)`. Focus is checked
against the real foreground window. Windows may refuse it; a focus_denied response
includes focused=false and a fresh full-screen image. Use that image directly
for recovery instead of another observe call. Choose a safe visible area of the
intended window to click, or select an occluded window through the visible
taskbar/switcher. Verify the resulting image before keyboard input. Stale
handles/PIDs remain errors; enumerate again rather than repeating the old call. A focus response already
contains its archived screenshot. Listing a secondary-monitor window does not
extend VISTA's primary-monitor input scope.

## Keep visual context purposeful

Use the inline preview once; do not also read the same original PNG by default.
Zoom an ambiguous control through `inspect` on that archived turn. Every `play`
already captures and returns its result. Obtain another frame only when state
may have changed or a delayed transition still needs checking. Avoid printing
base64 or complete history logs into text context.

Keep image retention separate from model context: archived PNGs stay on disk
for memory, while only relevant frames/crops need to be returned to the model.
VISTA currently returns a preview after every action; it does not inherit another
server's inline-image quota, model-specific resize/token formula, or batch API.

## State changes, stale coordinates and comparisons

After scrolling, resizing, focusing, opening a dialog, or user interaction,
re-establish the target from current evidence. Use `compare_frames` to quantify
changes between archived turns, optionally within one native-pixel region.
Zero changed pixels is not proof of task completion; changed pixels can be a
cursor blink or animation. Different resolutions invalidate the comparison.

For a delayed result, observe again and check the actual expected UI state.
If repeating the same action produces no relevant change, stop that attempt,
inspect focus/layout/current state, and select a justified next step. Never
auto-replay a failed input call: the input may have been delivered before the
response or screenshot failed.

## Recovery and reusable knowledge

Before context loss, save the objective, last verified state, session ID,
important turn IDs, pending action, and uncertainty in WORKING. Record verified
milestones through `remember`, attaching the actual frames. On recovery, read
notes and `recall`, inspect the cited evidence, and observe the current desktop
before acting. Prior success is applicable only if the preconditions still hold.

Report completion with the achieved result and evidence turn IDs. An attempted
action, an unchanged screenshot, a timeout, and a verified outcome are different
states. Keep errors and incomplete work explicit in notes rather than writing a
success-shaped memory. Use the read-only `audit` helper if an image is missing,
an archive moved, or the stored evidence appears inconsistent.

These workflows consolidate the sources listed in [sources.md](sources.md),
with tool names and screenshot lifetime adapted to this user's VISTA setup.

## Guard keyboard input

Once a window is identified, pass expected_hwnd and expected_pid together to play.
A foreground mismatch returns status=not_applied and a full-screen recovery image;
no input is sent. Do not record it as a completed action. The check covers window
identity immediately before dispatch, not field focus or concurrent user input.
For clicks intended to change windows, omit the old-window guard when it would
contradict the intended transition.
