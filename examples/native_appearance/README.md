# App-owned appearance

The canonical bridge owns one explicit application appearance lease. Source modes
are system (0, nil), Aqua (1) and DarkAqua (2). It changes NSApp.appearance only;
system preferences and explicit window/view overrides remain separate owners.
Snapshot flags report independently sampled dark, contrast, inversion, reduced
transparency, differentiation and reduced motion. Requested source and actual
observations remain distinct, especially after a foreign replacement.

Native callbacks invalidate state and coalesce sampling on the UI thread. Queued
samples retain their original source/flags and sequence; peek does not consume.
Acknowledge before source callbacks. Mode writes and immediate reads are separate
from queued notification and renderer media publication. Dynamic color queries
resolve under effective app appearance without changing current drawing context.

All source callbacks stay outside native KVO/notification code. Retirement marks
the lease inactive before exact observer removal, then restores its prior raw
appearance only if the last installed value is still present. Foreign replacements
survive. Indistinguishable same-value assignments cannot prove ownership intent.
A native setter failure may have applied its value; the lease keeps ownership so
inspection and explicit release remain possible. Nested writes/releases return
busy during the setter, including its callback-capable preflight.

`lease.py` is a typed ABI consumer. Replace __BRIDGE__ in a private copy with the
canonical bridge path. Host IR emission, external clang/AppKit execution and
installed PCC1 execution are independent gates. This API does not establish
Chromium/Electron notification counts or complete Harness/native-theme wiring.
