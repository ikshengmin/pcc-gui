# Contain Session observers and match the native pump ABI

- Schema: pcc.harness.migration.v1
- Sequence: 0003
- PCC change: pending:contain-session-observers-and-match-pump-abi
- Upstream commit: 47f943859bef60e4160492346772ded9b24f765a
- Changed domains: examples/harness/session, examples/harness/gui-bridge
- Tasks: HARNESS-P1-SESSION-EVENT-COMPAT, HARNESS-P0-NATIVE-GUI-SHELL
- GUI impact: native bridge signature corrected; rendering unchanged

## Behavior migrated

Pinned `packages/core/session/src/index.ts` contains observer failures after
append commits and rejects reentrant publication. The synchronous port now
preserves that commit point, continues remaining observers, and checks reentry
before turn/step state changes. The bridge also uses the declared zero-argument
`pcc_gui_metal_run_loop_pump(void)` ABI through the existing typed FFI.

## Verification

- PASS | qualified CPython 3.15.0rc1 pytest with `-x -vv --tb=short`, the complete Harness host directory, and the maintained low-cost GUI selection | 204 tests and 14 subtests passed; nine integration cases deselected.
- PASS | three unchanged-source controls | observer escape, reentrant publication and the extra native pump argument each reproduce before repair.
- NOT-RUN | current pcc1, GC0–4, native AppKit/Metal calls, matched interactions and pixels | no native or visual equivalence is claimed.

Exact commands, source identities and receipts are preserved in Library
`libfile_a839998f72a481918cf262e6de32634b`. The maintained qualification document
records the complete selection and remaining Loader/HMR, asynchronous observer,
Session envelope/immutability, native lifetime and visual boundaries. The
upstream pin remains unchanged.
