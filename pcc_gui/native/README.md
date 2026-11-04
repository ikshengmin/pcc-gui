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
published before qualification. The 2026-11-02 native run passed 32 cycles and
64 immutable snapshots, with independent AppKit text checks, NUL/Unicode/empty
text, write-failure preservation, short-buffer guards, stale handles and all
nine worker-thread rejections. No general clipboard content was read or written.
This clang/AppKit pass does not qualify installed PCC1, translated Electron
services or a complete Harness GUI.

### Native message-box ownership

`pcc_gui_dialog.h` exposes main-thread message-box leases. Configure UTF8 text
(including NUL), style and buttons before begin. Begin selects an existing owned
NSWindow by pointer identity in NSApp's window inventory, or NULL for an
application-modal session. Only one owned message box may be active; busy returns
5 without starting another. No interpreter graph or callback is stored natively.

The app owner continues its native event pump and polls the key. Polling advances
one application-modal turn; sheets complete through their native callback. Ready
results retain response index and suppression-checkbox state until explicit
release. Pending outputs preserve response/checked sentinels. Cancellation is
idempotent after completion; pending release refuses. Parent close cancels the
owned sheet without replacing window delegates. Keys never alias recycled objects.
A foreign active modal session is never stopped by this API.

Styles 0/1/2 are AppKit informational/warning/critical. Default ID -1 disables a
return-key default; cancel ID must name an actual button. Empty button lists add
OK. Text is bounded to 1 MiB and button count to 32. Custom icons, file panels,
multiple concurrent modal owners, source Electron normalization and production
translation/native event wiring remain separate. Native clang/AppKit tests and
installed PCC1 qualification are separate evidence.

The parent pointer follows the existing live-owned-window handle contract;
message-box keys have independent stale-key protection. The integration fixture
captures only its own window through the host-provided capture symbol because
view-cache snapshots omit system-composited alert controls on the tested macOS.
This capture path is test-only and does not establish general screen capture.

### Document request ownership

`pcc_gui_protocol.h` supplies a bounded native FIFO for a caller-owned document
generation. Native producers copy opaque metadata/body bytes and never invoke
source callbacks. The UI owner claims each head, copies and consumes terminal
replies, and retires the lease on document replacement. See the [consumer and
contract](../../examples/native_protocol/README.md) for bounds, threading,
cancellation and the separate source/production wiring boundary.

### Microphone authorization

`pcc_gui_media.h` adds the main-thread AVFoundation microphone status query and
an explicit async request. The latter completes through an existing document
request lease. See the [consumer and authorization contract](../../examples/native_media/README.md)
for terminal payloads, bundle prerequisites, cancellation and fixture scope.

`pcc_gui_shell.h` supplies main-thread AppKit URL opening with terminal
results on an existing document lease, and synchronous Finder selection.
The [native shell consumer](../../examples/native_shell/README.md) describes
the URL and path contracts.

### Fullscreen transitions

`pcc_gui_fullscreen.h` exposes owner-polled fullscreen and close notifications
for existing Metal window handles. It observes AppKit state without replacing
window delegates. The finite native contract and controlled hidden-window
qualification are in `examples/native_fullscreen/README.md`.
