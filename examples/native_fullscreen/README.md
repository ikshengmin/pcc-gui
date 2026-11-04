# AppKit fullscreen window lease

`pcc_gui_fullscreen_acquire` accepts a live window handle produced by the Metal
window bridge. It grants one UI-thread lease for that window. A second window has
its own state and event queue. Closing the window publishes a terminal close
event; the owner can still drain the queue and then releases its lease. Raw
handles retain their existing Metal-window ownership. A lease ID is never
reused.

The supported Darwin profile reads the actual NSWindowStyleMaskFullScreen bit.
Setting the same state or requesting a change on a window without
NSWindowCollectionBehaviorFullScreenPrimary is a no-op. Hidden windows call
the native toggle directly. Visible windows defer the toggle past the current
main turn. A retired lease or an externally started transition invalidates the
deferred request. An equivalent in-flight request coalesces; status 5 exposes
an overlapping opposite transition. Electron's wider pending transition FIFO,
simple fullscreen and maximize/resize/deferred-close policies have independent
behavior. Native toggle exceptions return status 4, and source timeouts remain
caller-owned when AppKit does not publish a completion.

Use `pcc_gui_fullscreen_take` to poll a copied native notification. Values are
0 empty, 1 entered, 2 left and 3 closed. An empty poll never dispatches a source
callback. NSNotificationCenter observers do not replace the app or window
delegate. Up to 256 leases and 256 pending notices per lease are admitted.
A queue overflow returns status 6 until explicit retirement.

The Darwin integration fixture creates an ordinary hidden Metal window and
copies its actual close notification. Additional hidden subclass windows
intercept fullscreen toggles at construction. The tests cover native style
observations, deferred requests, nested requests, foreign windows, stale
events, retirement and worker rejection. No physical Space switch is needed
for this profile. Run the focused pytest with `tests/test_pcc_gui_fullscreen_darwin.py
-m integration`. The PCC sample `read_state.py` consumes an already built
native bridge at the path supplied in place of `__BRIDGE__`.
