# CoreGraphics raw ABI boundary

`pcc_gui/pcc_gui_cg.py` owns the synchronous CoreGraphics adapter. Its public
`pcc_gui_cg_*` C exports keep their existing pointer/i64 signatures; the adapter
uses the reusable `pcc.unsafe.call_c_abi` API for the platform calls. It neither
embeds a foreign runtime nor supplies a GUI-local compiler bridge.

## Data and ownership

- The supported target is 64-bit macOS: CGFloat is f64, CGPoint is two f64
  fields (16 bytes, alignment 8), and CGRect contains origin and size pairs
  (32 bytes, alignment 8). `c_abi_sizeof` and `c_abi_alignof` check the selected
  target layout before bounded stack storage is used
- RGBA inputs remain integer 0..255 channels, matching the other GUI render
  paths. Each channel is divided by 255 before calling SetRGBFillColor
- FillRect passes the nested CGRect aggregate by value. StrokeLineSegments
  borrows an aligned, caller-owned two-point array during its synchronous call
- Bitmap creation rejects non-positive dimensions and signed stride/area
  overflow. It selects 8-bit RGBA, premultiplied alpha last, and 32-bit big byte
  order, matching the native Metal bridge. The selected SDK flag value is
  16385; the real-SDK oracle checks the declaration and enumerators
- A temporary DeviceRGB color space is released once after bitmap creation,
  including a null context result. Missing release symbols prevent allocation
- Passing NULL bitmap data asks Quartz to allocate its own backing memory.
  A successful context is returned owned; the caller releases it exactly once
  with `pcc_gui_cg_context_release`. Null contexts are no-ops. A released non-null
  pointer must never be reused or released twice
- The dynamic framework handle is cached for process lifetime. Contexts and
  temporary color spaces are not cached. No callback or borrowed stack pointer
  escapes a platform call

Apple references: [CGFloat](https://developer.apple.com/documentation/CoreFoundation/CGFloat-swift.struct?changes=__8_6),
[bitmap contexts and ownership](https://developer.apple.com/library/archive/documentation/GraphicsImaging/Conceptual/drawingwithquartz2d/dq_context/dq_context.html),
[FillRect](https://developer.apple.com/documentation/coregraphics/cgcontext/fill%28_%3A%29-7a0rk?language=objc),
and [line segments](https://developer.apple.com/library/archive/documentation/GraphicsImaging/Conceptual/drawingwithquartz2d/dq_paths/dq_paths.html).

## Availability and errors

`pcc_gui_cg_ensure` checks the actual symbols used by the adapter. It returns
0 only when the target layout, framework and all required functions resolve:

- -1: framework unavailable
- -2: SetRGBFillColor unavailable
- -3: FillRect unavailable
- -4: unsupported scalar/aggregate layout
- -5: bitmap creation unavailable
- -6: DeviceRGB creation unavailable
- -7: color-space release unavailable
- -8: context release unavailable
- -9: StrokeLineSegments unavailable

Context creation returns null on invalid dimensions, missing required symbols
or allocation failure. Drawing entrypoints preserve their void ABI and return
without calling an unavailable platform function.

## Separate verification gates

`tests/test_pcc_gui_cg_abi.py` and `tests/test_pcc_gui_cg_runtime.py` inspect the
actual production module's IR and owned Linux/Darwin objects. This is compiler
and ABI evidence, not execution of CoreGraphics.

`tests/test_pcc_gui_cg_provider.py -m integration` has two distinct boundaries:

- Linux x86-64: production module plus a provenance-matched, explicitly staged
  core runtime, called against independent SysV assembly platform providers.
  It checks scalar/aggregate values, null/error paths and release counts; the
  providers do not draw anything or replace core runtime behavior
- Darwin: an explicitly labeled Apple-Clang/SDK declaration oracle checks
  real headers, field offsets, enum values and function signatures. This
  external reference is not proof of compiler independence

Both gates must actually run against the final artifacts before their behavior
is qualified. Real bitmap pixels, AppKit/Metal rendering, native callbacks,
window interactions and GC0–4 ownership are additional acceptance boundaries.
