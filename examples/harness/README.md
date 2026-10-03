# PCC DeepSeek Harness

This directory is the pcc-native Python port of
[`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness).
It is not a Python wrapper around the Node runtime. It is a product-scale proof
that self-hosted `pcc1` can replace CPython as the execution owner of a real,
long-running Python application. The production target is a native `pcc1`
self-backend executable with no libpython, Node.js, browser, Electron, or
WebView dependency.

## Current runnable slice

The first tracer bullet implements one complete deterministic agent turn:

```text
input -> durable-style event log -> prompt/tool assembly -> model decision
      -> optional tool call -> assistant response -> transcript projection
```

Build and run it from the pcc-gui repository root:

```bash
uv run examples/harness/harness
uv run examples/harness/harness "hello"                 # explicit CLI turn
uv run examples/harness/harness "/tool echo native pcc" # explicit CLI tool turn
uv run examples/harness/harness --self-check
uv run examples/harness/harness --gui-self-check
```

`harness` rebuilds `build/harness-core` when the application, framework or
native bridge source changes, then executes that native artifact. Builds use
`pcc1` from PATH by default; set `PCC1=/absolute/path/to/pcc1` to select a
specific compiler. The shared compiler installation is owned by `~/my/pcc`;
this launcher never selects private bootstrap artifacts or builds a compiler.
The Metal/AppKit bridge is the framework-owned source under `pcc_gui/native/`.
The new compiler must support the application's required native facilities;
a compiler failure is reported directly, without a CPython execution fallback.

With no arguments, `harness` opens the native PCC AppKit/Metal GUI. The first
shell mirrors the upstream light-theme column geometry and exposes the
sidebar, session navigation, Chat/Trajectory views, composer, status and
settings regions. Clicking the composer send control submits the deterministic
sample through PCC's typed GUI command registry into the same logged agent
core; **New Session** clears it. This is the first parity shell, not a claim of
complete Web UI parity yet.

The runtime now also includes a reactive Cordis-style Fiber graph with pending
Consumers, scoped service realms, Provider-identity reload, committed teardown
bindings, dependency diagnostics, five event dispatch modes and reversible
effects. Disposal unlinks retired scopes and registrations, drains cleanup
captures, and retains committed service values through dependent teardown.
Session state uses atomic JSONL persistence; settings are revisioned
and atomically persisted; credential references stay secret-safe; anonymous
identity, whole-list `todo_write`, and logged plan mode are assembled into the
same runtime. Declarative Loader updates snapshot configuration, preserve
unchanged keyed mounts across edits/reordering, and support explicit catalog hot
replacement with rollback to the previous implementation. Group ownership and
static dependencies determine which additional mounts must restart;
service-driven consumers remain owned by the reactive kernel.
The DeepSeek adapter preserves indexed tool calls, reasoning and tool-result
history, publishes live deltas into the session log, and propagates cancellation
through its streaming transport contract. These paths have deterministic host
regressions; current native acceptance is a separate gate.

The executable still selects a deterministic local model by default. Async
Loader/effect parity, a verified native PCC HTTP/TLS client, complete capability
composition and native GUI pixel parity remain open. See the
[provider/Loader qualification](../../docs/verification/harness-provider-loader-2026-10-02.md)
for the exact executed scope and transport boundary; the runnable slice is not
a full-port claim.

## Target architecture

The port preserves the upstream domain split while using PCC-native owners:

| Upstream domain | PCC port owner |
|---|---|
| session event log and projections | Python core, then PCC persistence |
| system prompt, todo/plan and tool registry | Python core |
| agent loop and live events | `pcc.virtual_thread`-driven Python runtime |
| LLM streaming | PCC HTTP client and virtual-thread I/O |
| web host | `pcc.gateway` / `pcc.web` where a server surface is needed |
| Web React client | PCC declarative native GUI; no browser compatibility layer |
| filesystem, shell, terminal and LSP | PCC capability providers |
| settings, credentials and identity | validated Python providers over PCC filesystem primitives |
| profile/bundle composition | Python reactive Fiber/realm/effect runtime, then declarative Loader |

The final `uv run examples/harness/harness` command will open the PCC native GUI. Its
layout, visible state, interactions, streaming trajectory, approvals,
settings, session navigation, and error states must match the upstream Web UI.
Implementation technology is intentionally different; observable behavior and
pixels are the parity target.

Harness requirements are allowed to drive general PCC development. Missing
Python semantics, stdlib modules, compiler lowerings, runtime/GC behavior,
virtual-thread facilities, networking, persistence, GUI primitives and native
ABI support belong in PCC with focused compiler/runtime tests. The port will
not simplify product behavior merely to stay inside PCC's current subset.

## Task tracking

Active application/framework work is tracked in
[pcc-gui issues](https://github.com/allstoalls/pcc-gui/issues); reusable
compiler/runtime work belongs in [pcc issues](https://github.com/allstoalls/pcc/issues).
[`TASKS.md`](TASKS.md) is the historical coverage index for the pinned upstream
commit, including native GUI parity, capabilities/protocols, release closure
and upstream discovery. Its `HARNESS-` references remain migration identifiers;
the retired monorepo task board is not a current completion record.

## Upstream tracking

[`migration/upstream.json`](migration/upstream.json) pins the official remote,
branch, and last audited commit. [`migration/README.md`](migration/README.md)
defines the commit-to-commit migration ledger. A later task adds automated
upstream discovery and task generation; until that lands, update the pin only
after an audited comparison.
