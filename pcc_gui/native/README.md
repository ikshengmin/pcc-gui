# Native GUI bridge

`pcc_gui_metal_render_bridge.m` is the canonical Metal/AppKit bridge for
pcc-gui applications and tests. It was extracted from
`allstoalls/pcc@77cdf411`, `pcc/kernel_ir/metal_render_surface.py`, and is now
maintained here. Compiler intrinsics and the reusable PCC runtime remain in
core; GUI paint, window and event behavior belong to this framework.

The public window handle transfers one retained NSWindow reference to the
caller. Creation disables `releasedWhenClosed`; `pcc_gui_metal_window_close`
closes the window and releases that reference exactly once. Clients must not
reuse a closed handle. Native ownership and delegate integration are tested
with `tests/test_pcc_gui_app_lifecycle_darwin.py` through the default pcc1.

Both example build scripts compile this file with clang. There is no
build-time dependency on core's older GUI source generator. Python package
builds include this source asset alongside the pcc-Python framework.

`pcc_gui_metal_window_focus_state(void *window, int32_t *key,
int32_t *application_active)` snapshots the actual AppKit key-window and
application-activation flags on the main thread. Status 0 writes both flags;
status 2 rejects null arguments or a worker-thread call without changing outputs.
The caller must retain a live window handle and stop using it after close. The
query creates no owner, pumps no events and changes no focus. Logical node focus
and a translated document's focusability remain separate owner responsibilities.

`tests/fixtures/native_window_focus.m` is a minimal native consumer covering two
windows, activation transfer, hiding, repeated close/reopen and wrong-thread
rejection. `tests/test_pcc_gui_window_focus_darwin.py` builds it with clang as an
AppKit ABI oracle. Passing it does not qualify native PCC1 or translated Harness.

The 2026-11-01 native run passed three cycles with six real windows, focus
transfer and hide behavior, worker-thread rejection, preserved error outputs and
weak release checks after bounded native close processing. Each observer must
have its own Objective-C `__weak` declaration. The test supplies no PCC runtime
archive and does not build or replace the shared compiler.

## Clipboard text leases

The canonical bridge includes `pcc_gui_clipboard.inc`; consumers use
`pcc_gui_clipboard.h` or the typed declarations in `pcc_gui_clipboard.py`.
All operations require the UI thread. Positive opaque keys identify board leases
and immutable UTF-8 snapshots. Snapshot copy/release is independent of subsequent
clipboard mutations or board close; stale and duplicate releases are rejected.
Text uses explicit lengths, preserving embedded NUL. Invalid UTF-8 is rejected
before modifying the board. Named boards reject the system-reserved board names;
the general board has its own explicit open operation. Closing a board lease does
not erase its OS contents. Named-board disposal remains its creator's decision.

Status 0 is success; 2 rejects arguments, stale keys or a wrong-thread call;
3 rejects UTF-8 conversion; 4 reports native failure; 5 means insufficient copy
space; 6 reports the size/identity bound. Text is bounded to 64 MiB and names to
4096 bytes. Output arguments are unchanged on error, and snapshot output slots
must be distinct. Native write failure after clearing the board is not rolled
back. Snapshots/leases never contain Python/T2 objects or callbacks.

`tests/fixtures/native_clipboard.m` is the minimal native consumer. Its integration
test uses only unique private named pasteboards, checks native data independently,
and exercises NUL/Unicode/empty text, immutable snapshots, stale keys, short
buffers, worker-thread rejection and repeated release. The implementation is
published before qualification; a clang/AppKit pass does not qualify installed
PCC1, translated Electron services or a complete Harness GUI.
