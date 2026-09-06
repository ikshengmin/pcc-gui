# mac_diff_app — dual-pane file compare on the pcc GUI path

A native macOS desktop app authored in pcc-Python, compiled with `pcc1`
(self backend, `--python-libpython off`), rendered through a Metal
`CAMetalLayer` surface with real text via `CATextLayer`.

## What it does (technical)

- Opens two real files (paths supplied as command-line arguments), splits them
  into lines, hashes each line (64-bit rolling hash), runs a line-level LCS
  diff core (`diff_core.py`, pure pcc-Python).
- Renders toolbar, dual panes/rows, overview and status as five bounded
  declarative components.  Keyed commit owns node mutation; the application
  does not rewrite committed nodes in a frame loop.
- The same source drives queued cross-lane reducer work, targeted listeners,
  phased effects, compiled style candidates, typed commands/state and the
  cancellable/exactly-once application exit lifecycle.
- `declarative_headless.py` is the deterministic host/current-pcc1 GC0..4
  canary; `app.py` is the canonical native bridge entrypoint.

## Layout

| file | role |
|---|---|
| `app.py` | canonical native entrypoint |
| `declarative_app.py` | shared file/diff model + complete declarative canary |
| `declarative_headless.py` | deterministic no-window acceptance entrypoint |
| `diff_core.py` | line-level LCS diff core (pure pcc-Python) |
| `pcc_gui_high.py` | GUI class API (window/menu/theme/rect/button/click/present) |
| `build.sh` | build: Metal bridge dylib + pcc1-compiled binary |
| `samples/` | two sample files to compare |

The Metal/AppKit bridge is maintained in this repository at
`pcc_gui/native/pcc_gui_metal_render_bridge.m`. `build.sh` compiles that same
source into `libpcc_gui_metal.dylib`; it does not generate GUI code from core.

## Build

The installed v84 baseline does not recognize the current `c_rawptr` argv ABI.
Full application qualification requires the newer core compiler; use `PCC1`
only for an explicitly selected candidate. The current host compiler has passed
both native window cases and the headless canary, with self backend and
libpython off; that is separate from installed-pcc1 GC0..4 acceptance.


```bash
# from the pcc-gui checkout root, after uv sync --locked
uv run examples/mac_diff_app/build.sh
./examples/mac_diff_app/mac_diff_app    # opens the window
```

## Runtime surface

- AppKit: `NSWindow`, menu bar, Dock activation, window close detection.
- Metal: `CAMetalLayer` drawable, RGBA/BGRA pipeline, solid-color rects.
- Text: `CATextLayer` per slot (512 slots), top-left coordinates.
- Bridge addresses and buffers use explicit integer address types across
  module calls, matching PCC application-module unsafe semantics.
- Text descriptors opt into signed 16-bit positions through property flag 0x2;
  component props carry each panel's origin, and both panes display file lines.
- Scene rendering owns text slots 0..511, clears retired labels and reports
  capacity or bridge failures through `render_ack()`.
- The Metal library is loaded beside the executable via `@executable_path`,
  so the launch working directory does not choose the bridge
  ([Apple loading rules](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html)).
- Events: targeted component listeners plus typed application run events;
  native AppKit lifecycle reachability is covered by its dedicated bridge gate.

## Known limits (tracked)

- Text glyph layout is CATextLayer-based; `pcc_gui_text.py` measure is a
  byte metric (monospace ASCII works; proportional/wide glyphs need real
  CoreText metrics).
- The native entry renders one acknowledged frame; continuous interaction and
  permission-gated pixel capture remain separately labeled hardware work.
- The bounded canary renders at most thirteen diff rows per pane.  Larger-file
  virtualization is not claimed by this slice.
