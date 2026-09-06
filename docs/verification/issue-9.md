# Issue #9: complete declarative diff canary (native compiler gate pending)

The app now uses the raw-address argv ABI and correct file-descriptor widths,
propagates missing-input errors, and preserves stack-slot lifetime until
mount copies the state, assigns distinct callback IDs, and uses the canonical
accent/spacing token IDs. Component props carry panel origins; an additive
text-origin property positions labels and real file lines without per-frame
node mutation. The record remains 72 bytes and legacy text origins stay zero.
The lifecycle owner encodes valid kit node zero as a nonzero resource handle.

Scene rendering uses all 512 text slots, clears retired labels, and propagates
text/capacity failures through the bridge receipt. The bridge is discovered
beside the executable with dyld's `@executable_path` mechanism. Entry points
propagate failed application status instead of silently returning success.

## Verified on 2026-09-06

- Host compiler, self backend, libpython off: full headless canary passes with
  13/12 lines, 13 operations, 7 equal, 1 deleted, 0 inserted and 5 changed.
- The same host compiler passes both native window cases, including real file
  labels and an explicit successful render/present/text receipt.
- Installed pcc1: the component regression passes signed text coordinates and
  stable keyed reuse (2 tests); the scene-slot regression passes allocation,
  retirement and propagated bridge/capacity failures (1 test).
- Contract, reference-provenance, CoreGraphics IR and canonical entry guards:
  17 tests passed.

## Remaining boundary

The installed v84 compiler fails the first full native application gate because
it lacks `pcc.extern.c_rawptr`. The corrected argv declaration intentionally
uses the core's explicit raw-address type; a raw pointer is not a managed
Python object. No host fallback is used for the production app.

Re-run `tests/test_mac_diff_app_declarative.py` and `tests/test_mac_diff_app.py`
with `-m integration` through the default PATH pcc1 after the compiler-side
raw-address support is available in that installation. Compiler fixes belong
in ~/my/pcc; no host compiler result substitutes for this native gate. GC0..4 acceptance checks the
backend actually reported by each executable. The remaining GC matrix and
current-core bootstrap/fixed-point gates have not been represented as passing.
Native delegate ownership now passes using the framework-owned bridge (#8). No pixel/UI
parity claim is made by these bridge and event receipts.
