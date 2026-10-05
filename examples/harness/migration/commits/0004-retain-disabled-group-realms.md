# Retain disabled Loader group owners and service realms

- Schema: pcc.harness.migration.v1
- Sequence: 0004
- PCC change: pending:retain-disabled-group-realms
- Upstream commit: 47f943859bef60e4160492346772ded9b24f765a
- Changed domains: examples/harness/loader
- Tasks: HARNESS-P1-PLUGIN-EFFECT-KERNEL
- GUI impact: none; this slice changes Loader ownership

## Behavior migrated

Pinned `vendor/loader/src/config/entry.ts` keeps group fibers alive while
disabling plugin descendants through ancestor options. `config/isolate.ts`
retains the entry-owned private realm. The port now preserves group owners and
realms across disable/re-enable, including nested groups, so existing joined
consumers resume against the same realm after provider hot replacement.
Actual group removal still disposes owners, services and listeners.

Retained declarations publish only after all candidate mounts succeed. Failed
enable or disable updates restore the old declaration and active descendants,
matching the rollback ownership in `config/group.ts`. The corresponding
upstream scenario is in
`packages/boot/app-boot/tests/config-reload.spec.ts`, “stops and restores
descendants when an ancestor group is disabled and re-enabled”.

## PCC facilities

The existing PluginKernel owns consumer suspension, service bindings and
effect cleanup. No compiler/runtime primitive is added.

## Verification

- PASS | Python 3.15.0rc1, `pytest -x -vv --tb=short -p no:cacheprovider examples/harness/tests` | 160 host tests, including the complete Loader file, four new group lifecycle cases, and the extended native workload executed as a host oracle.
- PASS | unchanged-source control | the original Loader leaves the same joined consumer PENDING after disable/re-enable; repaired behavior returns it to ACTIVE without replacing the consumer fiber.
- PASS | `git apply --check integration.patch` | patch applies to the preserved GUI baseline.
- NOT-RUN | current pcc1, GC0–4 and upstream TypeScript execution | host results and source comparison are separate evidence.

The gate disabled automatic native provisioning and pytest plugin loading,
bound imports to the explicit core checkout, and ran under a 30-second,
512-MiB process-tree limit. Full commands, source hashes, original upstream
files and receipts are in Library `libfile_45f62b905b008191b0cfdea91f6d6211`.

## Remaining boundaries

Asynchronous Loader settlement, live-fiber config updates, plugin-owned nested
entry trees and automatic module-watcher HMR remain open. This repair does not
establish native execution, native GUI interaction or pixel equivalence.
