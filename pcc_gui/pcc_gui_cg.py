"""pcc-Python owner: 64-bit macOS CoreGraphics backend (via dlopen).

The framework handle is cached for process lifetime. CoreGraphics objects are
not: context_create returns one owned CGContext that the caller releases once;
its temporary DeviceRGB color space is released after bitmap creation, on both
success and failure. CoreGraphics owns the bitmap data allocated for NULL data.
All framework calls are synchronous and borrow their argument storage.

Public geometry stays signed i64; it is converted to CGFloat (f64 on the
supported 64-bit target). Public RGBA channels are 0..255, matching the other
GUI render paths, and are normalized to CoreGraphics' 0..1 channel scale.

Owned surface (stable C ABI names):

  pcc_gui_cg_ensure, pcc_gui_cg_context_create, pcc_gui_cg_context_release,
  pcc_gui_cg_set_fill, pcc_gui_cg_fill_rect, pcc_gui_cg_stroke_line
"""

__pcc_runtime_port__ = True

from pcc.extern import c_abi_typed_export, c_ptr
from pcc.unsafe import (
    c_abi_alignof,
    c_abi_sizeof,
    call_c_abi,
    cstr,
    define_global_ptr_null,
    dynamic_library_open,
    dynamic_library_symbol,
    global_addr,
    global_load_ptr,
    load_ptr,
    null,
    ptr_add,
    ptr_is_null,
    ptr_to_int,
    stack_alloc,
    store_f64,
    store_ptr,
)


define_global_ptr_null("pcc_gui_cg_framework")


def _cg_handle() -> c_ptr:
    handle = global_load_ptr("pcc_gui_cg_framework")
    if ptr_is_null(handle):
        handle = dynamic_library_open(
            cstr("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        )
        if not ptr_is_null(handle):
            store_ptr(global_addr("pcc_gui_cg_framework"), 0, handle)
    return handle


def _cg_symbol(name: c_ptr) -> c_ptr:
    handle = _cg_handle()
    if ptr_is_null(handle):
        return null()
    return dynamic_library_symbol(handle, name)


def _cg_abi_supported() -> bool:
    # These are the SDK layouts for the supported 64-bit CGFloat target.
    # Explicit bounds protect the literal stack reservations below.
    return (
        c_abi_sizeof("ptr") == 8
        and c_abi_alignof("ptr") == 8
        and c_abi_sizeof("{f64,f64}") == 16
        and c_abi_alignof("{f64,f64}") == 8
        and c_abi_sizeof("{{f64,f64},{f64,f64}}") == 32
        and c_abi_alignof("{{f64,f64},{f64,f64}}") == 8
    )


@c_abi_typed_export("pcc_gui_cg_ensure", "i32", ())
def pcc_gui_cg_ensure() -> int:
    if not _cg_abi_supported():
        return -4
    if ptr_is_null(_cg_handle()):
        return -1
    if ptr_is_null(_cg_symbol(cstr("CGContextSetRGBFillColor"))):
        return -2
    if ptr_is_null(_cg_symbol(cstr("CGContextFillRect"))):
        return -3
    if ptr_is_null(_cg_symbol(cstr("CGBitmapContextCreate"))):
        return -5
    if ptr_is_null(_cg_symbol(cstr("CGColorSpaceCreateDeviceRGB"))):
        return -6
    if ptr_is_null(_cg_symbol(cstr("CGColorSpaceRelease"))):
        return -7
    if ptr_is_null(_cg_symbol(cstr("CGContextRelease"))):
        return -8
    if ptr_is_null(_cg_symbol(cstr("CGContextStrokeLineSegments"))):
        return -9
    return 0


@c_abi_typed_export("pcc_gui_cg_context_create", "ptr", ("i64", "i64"))
def pcc_gui_cg_context_create(width: int, height: int) -> c_ptr:
    if not _cg_abi_supported() or width <= 0 or height <= 0:
        return null()
    # Four bytes per pixel; reject signed-size overflow before multiplication.
    if width > 2305843009213693951:
        return null()
    row_bytes = width * 4
    if height > 9223372036854775807 // row_bytes:
        return null()
    fn = _cg_symbol(cstr("CGBitmapContextCreate"))
    color_create = _cg_symbol(cstr("CGColorSpaceCreateDeviceRGB"))
    color_release = _cg_symbol(cstr("CGColorSpaceRelease"))
    context_release = _cg_symbol(cstr("CGContextRelease"))
    if (
        ptr_is_null(fn) or ptr_is_null(color_create)
        or ptr_is_null(color_release) or ptr_is_null(context_release)
    ):
        return null()
    storage = stack_alloc(16)
    result = ptr_add(storage, (-ptr_to_int(storage)) % c_abi_alignof("ptr"))
    call_c_abi(color_create, "ptr", (), (), result)
    color_space = load_ptr(result, 0)
    if ptr_is_null(color_space):
        return null()
    # kCGImageAlphaPremultipliedLast (1) | kCGBitmapByteOrder32Big (4 << 12),
    # the same RGBA8 format selected by the canonical Metal render bridge.
    call_c_abi(
        fn, "ptr", ("ptr", "u64", "u64", "u64", "u64", "ptr", "u32"),
        (null(), width, height, 8, row_bytes, color_space, 16385), result,
    )
    context = load_ptr(result, 0)
    call_c_abi(color_release, "void", ("ptr",), (color_space,), None)
    return context


@c_abi_typed_export("pcc_gui_cg_context_release", "void", ("ptr",))
def pcc_gui_cg_context_release(ctx: c_ptr) -> None:
    if ptr_is_null(ctx):
        return
    fn = _cg_symbol(cstr("CGContextRelease"))
    if not ptr_is_null(fn):
        call_c_abi(fn, "void", ("ptr",), (ctx,), None)


@c_abi_typed_export("pcc_gui_cg_set_fill", "void", ("ptr", "i64", "i64", "i64", "i64"))
def pcc_gui_cg_set_fill(ctx: c_ptr, r: int, g: int, b: int, a: int) -> None:
    if ptr_is_null(ctx):
        return
    fn = _cg_symbol(cstr("CGContextSetRGBFillColor"))
    if ptr_is_null(fn):
        return
    call_c_abi(
        fn, "void", ("ptr", "f64", "f64", "f64", "f64"),
        (ctx, r / 255.0, g / 255.0, b / 255.0, a / 255.0), None,
    )


@c_abi_typed_export("pcc_gui_cg_fill_rect", "void", ("ptr", "i64", "i64", "i64", "i64"))
def pcc_gui_cg_fill_rect(ctx: c_ptr, x: int, y: int, w: int, h: int) -> None:
    if ptr_is_null(ctx) or not _cg_abi_supported():
        return
    fn = _cg_symbol(cstr("CGContextFillRect"))
    if ptr_is_null(fn):
        return
    call_c_abi(
        fn, "void", ("ptr", "{{f64,f64},{f64,f64}}"),
        (ctx, ((x, y), (w, h))), None,
    )


@c_abi_typed_export("pcc_gui_cg_stroke_line", "void", ("ptr", "i64", "i64", "i64", "i64"))
def pcc_gui_cg_stroke_line(ctx: c_ptr, x0: int, y0: int, x1: int, y1: int) -> None:
    if ptr_is_null(ctx) or not _cg_abi_supported():
        return
    fn = _cg_symbol(cstr("CGContextStrokeLineSegments"))
    if ptr_is_null(fn):
        return
    storage = stack_alloc(40)
    points = ptr_add(storage, (-ptr_to_int(storage)) % c_abi_alignof("{f64,f64}"))
    store_f64(points, 0, x0)
    store_f64(points, 8, y0)
    store_f64(points, 16, x1)
    store_f64(points, 24, y1)
    call_c_abi(fn, "void", ("ptr", "ptr", "u64"), (ctx, points, 2), None)
