# Lifecycle interruption and cleanup qualification

## Source changes

The event queue keeps callback-borrowed records and payloads stable even when
callbacks enqueue enough work to wrap the ring. Delivery copies the bounded
48-byte event and up to 256 payload bytes into caller-owned stack storage
before retiring the queue slot. Posting remains allowed during a callback;
recursive drain or synchronous native delivery returns `INVALID_TRANSITION`.
The processing guard is cleared after both successful and failed delivery.

Accepted exit visits all teardown owners and delivers one terminal `Exit`,
even when an owner reports failure. The first teardown error retains its
subject/phase and takes precedence over an error from the terminal callback.
Event shutdown attempts the remaining queued passive cleanups after a failed
callback, preserves the first diagnostic, and retires listener/effect records.

The AppKit adapter now cancels termination on negative sink results, detaches
its owned delegate/sink when closing the installed window, and ignores stale
notifications from other windows. Closing the current rendered window clears
its retained text/pane/layer caches so sequential windows can reuse the same
slots. This does not add a multiple-simultaneous-window rendering contract.
Native window handles still transfer one ownership reference and must not be
used or released again after the caller closes them.

## Executed on Linux x86-64

The explicit host-only selection passed **109 tests** on 2026-10-02:
105 pre-existing Harness/source-contract checks and four production-module
object-emission checks. The added checks lower the actual app-lifecycle and
event owners and emit Linux x86-64 and Darwin ARM64 objects through PCC's
owned object writer. They do not link or execute those objects.

The process-tree watchdog limited the run to 120 seconds and 1 GiB. The tests
completed in 4.82 seconds; observed peak tree RSS was 106,000,384 bytes.
The interpreter was the qualified CPython 3.15 development environment, with
native provisioning and implicit compiler bootstrap disabled. Core source
was under active development, so this is source-scoped emission evidence,
not qualification of an installed native compiler.

## Prepared, not executed

The following native tests use the actual `pcc_gui` package and require an
explicitly staged provenance-matched runtime archive and compiler:

- `tests/test_pcc_gui_app_lifecycle.py::test_callback_payload_survives_ring_wrap_and_recursive_delivery_is_rejected`
- `tests/test_pcc_gui_app_lifecycle.py::test_teardown_failure_still_delivers_one_terminal_exit`
- `tests/test_pcc_gui_events.py::test_shutdown_attempts_later_passive_cleanup_after_callback_failure`

The strengthened Darwin lifetime oracle additionally creates text and pane
controls on three successive windows, checks that reused slots belong to the
new tree, checks weak references after close, and exercises negative/cancel/
accepted termination responses plus stale delegate delivery. It is selected
by `tests/test_pcc_gui_app_lifecycle_darwin.py::test_native_window_handle_is_released_once`
with `-m integration`. It was not run on Linux, and no Apple SDK compilation,
real AppKit interaction, Metal presentation, bitmap/pixel comparison, or
GC0–4 native result is implied by the object-emission checks above.

Current-pcc1 component/event/state re-render, keyed lifecycle, command
cancellation and native ownership acceptance must be rerun against the final
compiler/runtime artifacts. Historical September receipts do not qualify
these October changes. Harness's documented full-product parity work remains
separate from this bounded framework repair.
