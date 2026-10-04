# Harness provider, Loader, Session and GUI qualification

## Current qualification (2026-10-04)

The exact pinned DeepSeek Harness source at
`47f943859bef60e4160492346772ded9b24f765a` is restored. The independent reference
receipt verifies all 7,412 Git blobs and file modes; its archive SHA-256 is
`534c9f1c9d30fea136026ecf7a23c2137e350f43558e2f1eff6218aef7b15b26`.
This pass inspected actual restored source. The upstream TypeScript application
was not executed. Source comparison, host regression, native execution and
interaction/pixel equivalence remain separate evidence.

The unchanged GUI baseline `45b84f1d1b112c4a88cc9d5a6772077a2f78bb7c`
passed all **147 Harness host cases** freshly. The repaired candidate passed
**204 host cases plus 14 subtests**, with nine integration cases explicitly
deselected. This final selection contains all **156 Harness host cases**, the
complete low-cost declarative contract, test-infrastructure, Harness shell and
owned-text suites, plus all source-only framework declaration checks. Tests
that emit, compile, link or execute native code were outside this selection;
this is not the complete default pytest suite.

The final gate used qualified CPython 3.15.0rc1 and pytest 9.0.3, an explicit
import binding to the immutable 2026-10-04 05:27:21 core capture (source identity
manifest SHA-256 `f7d16454da570550c0a9ac9ffd52ad8ca187bf32960adadf17ab13f2c236b236`),
no automatic pytest plugin loading, and disabled native provisioning. It took
1.20 seconds in pytest and 2.415 seconds under a 30-second/512-MiB process-tree
watchdog, with 69,849,088 bytes sampled peak RSS. Candidate source hashes were
unchanged during every run. The baseline run took 0.71 seconds in pytest;
all earlier test counts below are retained only as historical evidence.

### Source-grounded repairs

1. Session event publication now preserves the append commit point when a
   synchronous observer fails: diagnostics go to stderr and remaining observers
   still receive the event. Reentrant append is rejected before a second event
   can commit. Turn/step helpers check the same publication guard before changing
   their lifecycle state. A `finally` releases the guard after validation or
   publication failures. Eight added cases cover containment, later appends,
   reentrancy, all four lifecycle helpers, failed validation and observer snapshots.
   These contracts come from pinned `packages/core/session/src/index.ts`
   (`invokeContainedSessionObservers`, `Session.append`) and its
   `tests/session.spec.ts` containment and reentrant-observer cases.
2. The Harness bridge invokes `pcc_gui_metal_run_loop_pump(void)` using the
   existing typed `call_c_abi` contract with `i64` return and zero arguments.
   Both initialization and ongoing pumping previously passed a dummy pointer
   through the one-pointer intrinsic, contrary to the native C declaration.
   The new host ABI regression inspects that declaration and asserts both real
   bridge paths call it with no arguments. Native lowering and execution of
   this candidate remain unqualified.

Three controls using the old implementation failed for the intended reasons:
escaped observer exception, extra reentrant event and the extra pump argument.
The repairs and tests are isolated from the baseline until coordinator
integration. No compiler/runtime build, local Mac action, network provider
request, commit or push was performed in this pass.

### Fresh pinned-source contract comparison and remaining gaps

- **Loader:** `vendor/loader/src/config/entry.ts` and `group.ts` use stable ids,
  per-entry update/rollback, asynchronous group settlement and nested owning
  fibers. The PCC host tests exercise keyed retention, static dependency restart,
  disposal and rollback for its synchronous subset. Upstream can update a
  config on a live fiber; PCC currently replaces a changed record. Upstream
  retains group fibers when disabled; PCC filters disabled group records and
  their descendants. Plugin-owned nested entry trees and full asynchronous
  transaction semantics remain open.
- **HMR:** pinned `vendor/hmr/src/index.ts` watches module dependencies and exact
  config paths, serializes dirty refreshes and awaits watcher/task teardown.
  PCC catalog-generation replacement is explicit synchronous reconciliation;
  it does not implement the upstream automatic watcher/module reload contract.
- **Session:** the repaired synchronous publication subset now matches the
  inspected containment/reentrancy contract. Upstream also snapshots/freezes
  JSON events and headers, uses a different full event envelope, contains
  rejected promises and supports scoped store publication/detachment and awaited
  flush. PCC's scalar event codec, mutable event objects and synchronous
  callbacks do not establish those capabilities or upstream wire compatibility.
- **Native UI bridge:** host lifetime tests execute actual Python bridge logic
  with explicitly fake pointers and native functions. The typed pump repair
  corrects a source-visible signature mismatch. Actual C/Objective-C ABI calls,
  callback ownership under GC0–4 and AppKit/Metal rendering remain unexecuted.
- **UI behavior and pixels:** all five source anchors in
  `examples/harness/gui/upstream-baseline.json` were inspected at the exact pin.
  The reference has responsive columns, resizing/collapse, theme tokens and a
  shared hero/active composer. PCC still uses a fixed 1280×800 first shell and
  restricted controls. There are no matched viewport/input traces or image
  comparisons from this pass. A declaration, fake-ABI interaction or source
  color match cannot establish visual equivalence.

The sealed off-tree evidence is identified by
`pcc-gui-qualification-20261004T0532Z`: it contains the baseline/candidate
file identities, test selection and exact launches, JUnit/log/resource receipts,
old-source controls, inspected-reference hashes, and an integration delta.
Only this maintained qualification document is updated; the upstream pin and
existing migration ledger identities remain unchanged. A future migration
commit must reconcile its ordered record with the existing pending slice.

## Historical recovery qualification (2026-10-03)

The following records describe recovery work before the fresh source comparison
and repaired-candidate gate above. At that time the full pinned reference had
not been restored or re-executed.

Selective reconciliation preserves unchanged entry identities across edits,
reordering, insertion and removal. Changed groups and static dependency chains
restart their owned mounts; dynamic service consumers keep their kernel fiber.
Rollback attempts independent old mounts and reports candidate-cleanup errors.
Disposal unlinks retired scopes, registrations and effects, drains disposer
captures, preserves in-flight callback snapshots, and retains committed service
values until dependent cleanup releases them, including reentrant withdrawal.

Before the reset, the combined full Harness host suite passed 147 cases,
including 23 Loader, 24 plugin and 21 GUI-state/lifetime cases. The expanded
native workload ran only as a host oracle. A separate runtime test observed
old agents and sessions becoming unreachable through 20 session replacements.
The historical run used a shared lock and a 30-second/512-MiB process-tree
watchdog: 0.47 seconds in pytest, 0.804 seconds total, 48,066,560 bytes sampled
peak RSS. Old-source controls failed the intended identity/retirement assertions.
Those results remain historical and separate from the recovery qualification.

A fresh post-reset run on 2026-10-03 collected and passed all 147 Harness host
cases in 0.84 seconds. The qualified CPython 3.15 interpreter used an explicit
current-core pytest pythonpath override and disabled native provisioning. The
shared-lock, 30-second/512-MiB process-tree watchdog observed 1.808 seconds total
and 54,566,912 bytes peak RSS; all 32 prepared source hashes remained unchanged.
This requalifies the reconstructed source's host behavior only. Native emission,
GC0–4 execution, live transport, reference execution and GUI pixel acceptance
were not run by this gate.

The prepared native gate is
`tests/test_harness_loader_native.py::test_current_pcc1_keyed_loader_all_gc`.
It compiles the actual Loader/kernel fixture once using self/no-libpython and
owned object/link owners, then selects runtime GC0–4 with no executable PATH.
It has never run natively. New emission, whole-Harness native execution,
HTTP/TLS composition, async Loader/HMR, and Darwin interaction/pixel acceptance
remain open. The pre-reset evidence in the following sections does not close
any of these gates for the reconstructed source.

## Implemented source paths

The model adapter now keeps the provider's tool-call index while assembling
interleaved deltas. It rejects conflicting index/id mappings, ambiguous
unindexed continuations and incomplete successful-call identities. Legacy
single-call unindexed fixtures remain supported; they cannot silently merge
multiple pending calls. Assistant history encodes grouped `tool_calls` with
exact argument strings and corresponding tool-result ids. Text and reasoning
from tool-call responses are reconstructed from the logged chunks on replay.

`post_sse(url, headers, body, cancellation)` returns an iterable of decoded
text chunks. The adapter reads lazily, stops at `[DONE]`, closes a closeable
response on success/error/cancellation, and rejects truncated, malformed and
empty responses. Accepted deltas reach the session event log before the next
transport read. Finish reasons and trailing usage are retained; a truncated
or non-tool-call finish does not authorize tool execution.

One cancellation token is shared across the agent, model transport and tools.
Session replacement and runtime disposal cancel the prior agent before
withdrawing services, preventing late results from executing tools. Disposal
continues root/kernel cleanup after a Loader cleanup error and preserves the
first failure. The native entrypoint now propagates `main`'s exit status.

The synchronous Loader snapshots nested configuration and catalog identity.
Explicit `PluginCatalog.replace` changes the implementation generation even
when the declarative entry is unchanged. Old registration disposers cannot
remove replacements. Failed candidate setup remounts the captured prior
implementation/configuration rather than resolving the failed catalog entry
again. Failed old cleanup retires the actual unmounted suffix records before
propagating its error, so later reconciliation can remount the original desired
tree instead of mistaking missing resources for a committed prefix. This is
not asynchronous setup or automatic module-watcher reload.

## Source comparison

The upstream pin remains `47f943859bef60e4160492346772ded9b24f765a`.
The [pinned translator](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/llm/llm-deepseek/src/translate.ts)
and [serializer](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/llm/llm-deepseek/src/serialize.ts)
were inspected for indexed calls, response termination and grouped assistant
history. The [official wire schema](https://api-docs.deepseek.com/api/create-chat-completion/)
defines streamed indices and `[DONE]`; the
[tool-call guide](https://api-docs.deepseek.com/guides/tool_calls/)
shows assistant/tool history pairing. These source comparisons informed the
fixtures; the upstream TypeScript implementation was not executed, so this
is not full upstream or live-provider parity.

## Executed evidence

The final host-only `examples/harness/tests` selection passed **100 tests** on
2026-10-02, using qualified CPython 3.15 development tooling with native
provisioning disabled. Relative to the prior 70 Harness checks, the 30 added
cases comprise 21 provider-protocol cases, four agent tool/stream/replay/
cancellation cases, four synchronous Loader replacement/recovery cases and one
cleanup-error continuation case. Parameterized cases are counted separately;
the interleaved-call case also checks every two-piece transport split.

The same final run included **three** emission cases, compiling the actual
`model_runtime.py`, `agent_runtime.py` and `loader_runtime.py` unchanged to
Linux IR and PCC-owned ELF objects. All **103 cases** completed in 10.21
seconds. The 120-second, 1-GiB process-tree watchdog observed 187,109,376 bytes
peak RSS. Harness and core Python source hashes matched before and after the
run; source identities, IR and objects were retained. This checks the current
development compiler's lowering/emission path and host behavior. It does not
link or execute a native Harness program or qualify an installed self-hosted
compiler. No HTTP request, credential use, local Mac operation or upstream
execution was part of this gate.

## Native and transport boundaries

`tests/test_harness_gui.py::test_current_pcc1_native_harness_headless` is a new
opt-in integration gate. It compiles the actual `examples/harness/app.py`,
runs its runtime self-check plus assistant/tool CLI turns, and checks failure
exit status. It does not invoke `build.sh`, build a bridge/archive or rewrite
the application. It remains pending the qualified compiler/runtime freeze.

A real streaming HTTP/TLS client is still missing from the selected native
owners. Gateway supplies nonblocking socket/DNS primitives and an HTTP/1
upstream response codec, but its current TLS provider is server/listener-only
(`SSL_set_accept_state`). Outbound TLS requires client mode, emitted SNI,
certificate-chain and hostname verification, and cancellation/deadline/close
ownership. The relay-specific `ProxyExchange` is not an application-client
API. Buffered system-libcurl/host HTTP is not substituted for PCC virtual-thread
streaming. The adapter's tested injected stream is deliberately not claimed as
a live network transport.

Asynchronous Loader/effect completion, automatic module-watcher HMR, the
remaining capability families, and real AppKit/Metal interactions/pixels
remain separate acceptance work. No migration commit or upstream-pin change
was made; the imported ledger's existing pending identity is preserved.
