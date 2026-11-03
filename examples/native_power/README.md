# Native power notification ownership

The `pcc_gui_power` ABI observes native resume and shutdown notifications for an
explicit application/session lease. It requests no power transition, needs no
window, and replaces no application/window delegate. Open with mask 1 (resume),
2 (shutdown), or 3 (both); poll with `pcc_gui_power_peek`, acknowledge the selected
sequence before running application callbacks, and explicitly release the lease.

Publication only copies integer events under a native lock. Release first marks
the lease inactive, then unregisters its observer tokens. In-flight native
callbacks retain storage safely and discard late notifications. Queue exhaustion
is explicit; no event or output cell is silently replaced.

The native regression uses a private notification center to test ordering,
worker publication, failed registration and retirement without suspending or
shutting down the computer. That test does not qualify OS shutdown ordering.
Harness production integration must deliver shutdown before its termination
decision through one ordered owner or an explicit deferred termination handshake.
The existing startup-only EVENT_RESUMED is not an OS wake event.

`subscribe.py` is a typed compiled consumer. Replace `__BRIDGE__` in a private
copy with the canonical native bridge path. It opens and releases a subscription
without generating notifications. Compiler/ABI acceptance is separate from native
observer tests and complete application execution.
