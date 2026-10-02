# Harness project instructions

Use the [repository guide](../../AGENTS.md) for framework ownership, compiler
contracts and validation. The rules here cover the Harness application only.

This project is a clean-room Python port of DeepSeek Harness and a product-scale
proof that the current self-hosted `pcc1` can replace CPython as the execution
owner of a real Python application. The production application must compile
and run through the current `pcc1` self backend with `--python-libpython off`.
Do not introduce Node.js, JavaScript, CPython fallback, a browser runtime,
Electron, or a WebView.

The canonical upstream is `https://github.com/deepseek-ai/deepseek-harness`.
`migration/upstream.json` records the upstream commit currently understood by
the port. Every migration commit must add one file under
`migration/commits/` that names the upstream commits and behavior moved by the
change, the affected PCC task ids, the verification commands, and remaining
differences.

Use PCC-owned facilities before adding project-local infrastructure:

- native declarative GUI from the `pcc_gui` package in this repository;
- `pcc.virtual_thread` for concurrency;
- `pcc_gateway` and `pcc_gateway.web` from the sibling gateway package for HTTP;
- pcc filesystem, subprocess, networking, GC, and native ABI facilities.

When the port exposes a missing Python semantic, standard-library operation,
compiler lowering, runtime primitive, GC owner, platform ABI, or reusable
facility, repair or extend PCC with a minimized regression and a realistic
Harness confirmation. Do not reduce the application design to fit an existing
PCC limitation and do not keep a project-local shadow of generally reusable
infrastructure.

`TASKS.md` is a historical pinned-upstream coverage breakdown; its `HARNESS-`
IDs remain useful migration references, not current task status. Track active
application/framework work in `allstoalls/pcc-gui` and compiler/runtime defects
in `allstoalls/pcc`. The old monorepo task board and `goal_state.py` workflow
are retired. Check ledger tools against the current checkout paths before
relying on their results; a historical validator is not current coverage proof.

Do not claim upstream or UI parity from source presence. A migrated capability
needs a behavioral comparison against the pinned upstream revision. GUI parity
additionally requires interaction traces and pixel comparisons on the same
platform and viewport.
