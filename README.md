# pcc-gui

A declarative desktop GUI framework written in pcc-Python and compiled to native
code by [pcc](https://github.com/allstoalls/pcc): a retained element/control
tree, a Tailwind-like bounded style grammar, layout, theme animation,
CoreGraphics/Metal drawing and an AppKit window bridge, with no libpython at run
time.

It is an ordinary pcc package. An application does `import pcc_gui`, and
`pcc1` compiles the framework into the program together with the application
code. Nothing is prebuilt and nothing is linked from outside the compiler.

## Layout

- `pcc_gui/` – the framework package (17 modules: `pcc_gui_kit`,
  `pcc_gui_layout`, `pcc_gui_style`, `pcc_gui_theme_anim`, `pcc_gui_cg`,
  `pcc_gui_window`, `pcc_gui_app`, ...). `import pcc_gui` imports all of them.
  Applications call the framework through its C ABI (`pcc_kit_*`,
  `pcc_gui_*`) declared with `pcc.extern`.
- `examples/closure_probe/probe.py` – the smallest complete program.
- `examples/mac_diff_app/` – a Beyond-Compare-style diff viewer (Metal render
  bridge, declarative and headless variants).
- `examples/harness/` – the agent harness application: GUI front end plus its
  runtime modules and tests.
- `tests/` – framework unit tests and pcc1 canaries.
- `docs/gui-declarative-absorption.md` – design note.

## Setup

Use the shared, verified **`~/.local/bin/pcc1`** through PATH, also used by
`pcc-gateway`. Versioned installations live under
`~/.local/share/pcc/toolchains/`; validate a candidate before atomically
switching the entry, and retain the previous version for rollback. Core
`build/bootstrap/` outputs are development artifacts, not the shared compiler.
See [the core installation contract](https://github.com/allstoalls/pcc#one-installed-compiler-for-multiple-projects).
The initial shared installation is the v84 Stage1/Stage2 baseline with an
installed execution canary. The newer 0.1.8 candidate remains under qualification;
new application features may require it.

Install [uv](https://docs.astral.sh/uv/) and keep the compiler checkout next to
this one, as in `pcc-gateway`:

```bash
# from this checkout, if the compiler is not already present
git clone https://github.com/allstoalls/pcc ../pcc
```

Run all commands below from the `pcc-gui` checkout root:

```bash
uv sync --locked
command -v pcc1  # normally ~/.local/bin/pcc1, installed by the core checkout
export PCC_PACKAGE_SITE="$PWD"
pcc1 examples/closure_probe/probe.py -o examples/closure_probe/probe
./examples/closure_probe/probe
```

uv installs the pinned development Python and dependencies, including the
editable `../pcc` development tools. The native compiler has a separate stable
installation at `~/.local/bin/pcc1`; keep `~/.local/bin` on PATH. `uv sync` does
not build or install that executable. Applications compile through `pcc1` and
do not link libpython.
Native windows require macOS on Apple silicon and Xcode command line tools.

## Install the framework package

Once the shared compiler is installed, use its package installer, the same
entry used by pcc-gateway and NumPy:

```bash
pcc1 env info --json
pcc1 -m pip install /path/to/pcc-gui
```

Without `VIRTUAL_ENV`, packages go to
`~/.local/share/pcc/environments/<compatibility-tag>/site-packages`. With an
active virtual environment, all packages use that environment's pcc overlay.
Use the same environment when installing and compiling; `env info` reports
its actual site. The `PCC_PACKAGE_SITE` export in development examples is an
explicit checkout override. It is not needed for a successfully installed
package in the selected environment. Source-install and native GUI execution
have separate 0.1.8 qualification gates.
The next qualified compiler defaults to Python 3.15 and records it as
compatibility metadata. Native package paths use pcc's ABI and platform rather
than the Python version. Existing `py311` sites remain untouched; use the same
install command to populate the selected compiler's new default environment.

For the clone-to-compiler installation command, see the
[core README](https://github.com/allstoalls/pcc#first-native-installation-after-cloning-macos-arm64).

## Use it

Import the framework to include its implementation in your application:

```python
# app.py
from pcc.extern import c_int32, c_int64, extern

import pcc_gui  # pcc1 compiles the framework into this program

_kit_init = extern("pcc_kit_init", (c_int64,), c_int32)
_kit_create = extern("pcc_kit_create", (c_int64,), c_int64)
_live_nodes = extern("pcc_kit_live_nodes", (), c_int64)

_kit_init(64)
root = _kit_create(-1)
print("nodes", _live_nodes())
```

```bash
pcc1 app.py -o app
./app
```

`pcc1` defaults to the self backend, libpython off and IR lowering on, so
ordinary commands do not repeat those options. Builds resolve `pcc1` through
PATH; set `PCC1=/absolute/path/to/pcc1` for an explicit build-script/test override.
This repository does not bootstrap a compiler or search core build directories.

The `PCC_PACKAGE_SITE` export above makes the framework available even to
example sources in subdirectories. Set it once per shell; it accepts a
colon-separated list when adding multiple packages.

## Examples

```bash
# headless diff viewer
pcc1 examples/mac_diff_app/declarative_headless.py -o examples/mac_diff_app/declarative_headless
./examples/mac_diff_app/declarative_headless examples/mac_diff_app/samples/left.txt examples/mac_diff_app/samples/right.txt

# windowed diff viewer; generates and builds the Metal bridge too
uv run examples/mac_diff_app/build.sh
./examples/mac_diff_app/mac_diff_app examples/mac_diff_app/samples/left.txt examples/mac_diff_app/samples/right.txt
```

Set `PCC1=/absolute/path/to/candidate/pcc1` only to test an isolated compiler
candidate. The Metal bridge is maintained under `pcc_gui/native/` and
compiled with the Xcode toolchain; this GUI build is not a no-clang or zero-libc claim.
See [Harness](examples/harness/README.md) for the agent application's separate
build and current migration status.

## Tests

Tests run directly from this checkout. Native archive fixtures require
`PCC_RUNTIME_ARCHIVE` to name an explicitly staged `libpy_runtime_pcc_py.a`
whose provenance matches the adjacent core checkout. Verification stays owned
by core; archive fixtures never build missing archives, and compiler lookup
never bootstraps core.
Hardware integration tests are excluded by default and can be selected
explicitly with `-m integration`.

The following selection needs neither a native compiler nor a runtime archive;
it exercises host-Python Harness behavior and declarative contract checks only:

```bash
gtimeout 120s env -u LC_ALL uv run pytest examples/harness/tests tests/test_gui_declarative_design.py tests/test_gui_test_infrastructure.py -x -n0 -vv --tb=short
```

For native checks, stage and qualify the compiler and archive in the core
checkout first, then select their exact paths:

```bash
export PCC1=/absolute/path/to/qualified/pcc1
export PCC_RUNTIME_ARCHIVE=/absolute/path/to/qualified/libpy_runtime_pcc_py.a
gtimeout 900s env -u LC_ALL uv run pytest -vv -x
gtimeout 120s env -u LC_ALL uv run pytest -q -x tests/test_pcc_gui_kit.py
gtimeout 900s env -u LC_ALL uv run pytest -vv -x examples/harness/tests
gtimeout 180s env -u LC_ALL uv run pytest -vv -x -m integration tests/test_pcc_gui_kit_darwin.py
```

`tests/test_pcc_gui_current_pcc1.py` checks the installed self-hosted compiler.
A missing compiler produces an installation error; it never starts a core build.
The older `PCC_CURRENT_PCC1` test override is also accepted.
Open migration work and remaining acceptance gates are tracked in
[GitHub issues](https://github.com/allstoalls/pcc-gui/issues).

## Provenance

Extracted from `allstoalls/pcc` at commit `2574f585` (2026-09-06). The core no
longer ships these modules in its runtime archive; the framework modules carry
the `__pcc_runtime_port__ = True` directive because they build objects out of
raw memory exactly like the runtime ports they came from.
