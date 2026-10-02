# AGENTS.md

## Project intent

Build a declarative native desktop GUI for pcc: components and state updates,
keyed render/commit, layout/style, events/commands and application lifecycle.
A capability must work through component -> render -> event -> state -> re-render.
Keep one canonical framework implementation in `pcc_gui`; examples demonstrate
and validate it. Absorb useful UI concepts without requiring React, a browser,
Electron, a WebView or a host Python fallback as the native execution owner.

[Core Intent](../pcc/docs/project-intent.md) and
[compiler contracts](../pcc/docs/compiler-contract.md) define the shared target:
host pcc uses CPython plus its standard library; native pcc1 requires no external
LLVM/llvmlite, cc/toolchain, host Python or libpython, including C and runtime
construction. Named OS frameworks are platform ABI dependencies, not proof of
compiler independence. Existing external bridge-build routes remain migration work.

## Work from source and fix the right owner

- Read current implementation, callers, tests and `git status --short` first.
  Design notes and old receipts are historical context; verify source/artifact
  identity before reusing implementation claims. Do not preload core's history.
- GUI semantics, rendering/window bridges and public framework APIs belong here.
  Python semantics, lowering, ABI/codegen, allocation/GC, compiler packaging and
  reusable platform primitives belong in `../pcc`; follow its
  [AGENTS.md](../pcc/AGENTS.md), add a small core regression, then rerun the GUI case.
  Do not simplify application behavior or duplicate a kernel to conceal a compiler bug.
- Preserve the component/style/kernel/command boundaries. Reuse the canonical
  implementation; compatibility modules may forward to it, not fork its state.
  ABI changes must update declarations, consumers and focused tests together;
  inspect `pcc_gui/gui_declarative_contract_v1.json` against code, not copied offsets.
- Track work in `allstoalls/pcc-gui` or `allstoalls/pcc` by ownership. Preserve
  other edits and unfinished scope; no destructive resets, unrelated release
  edits or unrequested commit/push. Read nested AGENTS.md when entering an example.

## Correctness and user-visible behavior

- Preserve keyed component identity, ordered state updates, effect/cleanup phases,
  paint/hit-test order, clipping, focus/event routing and stable error behavior.
  A redraw optimization must preserve the rendered result and interaction trace.
- Respect the platform UI-thread boundary. Background work must not block or
  re-enter event/render ownership unexpectedly; use the existing scheduler and
  lifecycle mechanisms. Keep UI interaction responsive during background work.
- Check mount/unmount, failed commits, callback payload lifetime, stale handles,
  repeated window open/close and exactly-once release. Runtime/ownership changes
  need relevant GC0–4 validation in core, not only a successful screenshot.
- Headless structure tests, native compiled execution and real window/render
  behavior are separate evidence. UI changes need real interactions and visual
  inspection on the affected platform; use fixed viewport/input for comparisons.
  Hardware-unavailable tests must be reported as unavailable, never as a GUI pass.

## Development and validation

- `pyproject.toml` selects the adjacent `../pcc` checkout. Use
  `env -u LC_ALL uv run ...` and keep `.python-version` aligned with core
  (3.15.0rc1). Development tools do not establish native execution ownership.
- Resolve the shared qualified `pcc1` through PATH, normally `~/.local/bin/pcc1`.
  `tests/gui_compiler.py` accepts `PCC1` and the older `PCC_CURRENT_PCC1` override.
  Missing compilers are installation errors: GUI tests must not bootstrap core
  or silently pick a binary from `build/bootstrap`. Keep candidates isolated.
- Use focused pytest nodes with `-x -vv --tb=short` and a timeout (`-n0` while
  diagnosing). The default suite excludes `integration`, but some selected tests
  still compile programs and may rebuild the shared runtime; inspect fixtures.
- `tests/test_pcc_gui_current_pcc1.py` checks native kernel/component execution;
  Darwin window/bridge tests explicitly use `-m integration`. Inspect their
  required compiler, runtime, OS and hardware before running them. A focused
  event-ABI declaration check is:

```bash
gtimeout 60s env -u LC_ALL uv run pytest tests/test_pcc_gui_events.py::test_event_owner_freezes_callback_abis_and_component_hooks -x -n0 -vv --tb=short
```

- Follow core's source-freezing, process-tree watchdog/RSS and performance-lock
  rules for heavy builds/timing. Keep long-run logs and stop at the first failure.
  A GUI run built with an external clang bridge is not an entirely pcc1-owned
  build; record the actual owners and fix general compilation capability in core.
- New public features need a minimal example plus behavioral regression. Profile
  frame/update work before optimizing; record input latency/frame time, CPU and
  memory on a fixed workload without dropping effects, events or rendered work.

## Source routing

| Work | Source/tests to inspect |
|---|---|
| Components/state/effects | `pcc_gui/pcc_gui_components.py`, `pcc_gui_scheduler.py`, `tests/test_pcc_gui_components.py` |
| Layout/style/render tree | `pcc_gui/pcc_gui_kit.py`, `pcc_gui_layout.py`, `pcc_gui_style.py`, `pcc_gui_cg.py`; matching tests |
| Events/commands/lifecycle | `pcc_gui/pcc_gui_events.py`, `pcc_gui_commands.py`, `pcc_gui_app_lifecycle.py`; matching tests |
| Native window/Metal | `pcc_gui/native/`, `pcc_gui/pcc_gui_window.py`, `tests/test_pcc_gui_*_darwin.py` |
| End-to-end examples | `examples/closure_probe/`, `examples/mac_diff_app/`, `examples/harness/` |

Keep README concise, with runnable examples and artifact-scoped results. Keep
experiment history out of this startup guide; consult design/reference documents
only for the mechanism being changed.
