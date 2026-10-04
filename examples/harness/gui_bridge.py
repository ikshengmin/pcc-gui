"""Narrow native window bridge over the verified PCC AppKit/Metal surface."""

from pcc.extern import (
    c_int64,
    extern,
)
from pcc.unsafe import (
    call_c_abi,
    call_i64_ptr1,
    call_i64_ptr2,
    call_i64_ptr3,
    call_i64_ptr3_i64_i64_i64,
    call_ptr_i64_i64,
    cstr,
    define_global_i64_array,
    dynamic_library_open,
    dynamic_library_symbol,
    global_addr,
    int_to_ptr,
    load_i64,
    load_ptr,
    null,
    ptr_is_null,
    ptr_to_int,
    stack_alloc,
    store_i64,
)


pcc_platform_sleep_ns = extern("pcc_platform_sleep_ns", (c_int64,), c_int64)

# Byte offsets into the bridge-owned raw state array.
WINDOW_SLOT = 0
RENDER_SLOT = 8
SHOW_SLOT = 16
CLOSE_SLOT = 24
PUMP_SLOT = 32
CLOSED_SLOT = 40
CLICK_SLOT = 48
TEXT_SLOT = 56
CAPTURE_SLOT = 64
WIDTH_SLOT = 72
HEIGHT_SLOT = 80
RENDER_ACK_SLOT = 88
TEXT_COUNT_SLOT = 96

# Existing kit render-record ABI, consumed without retaining borrowed pointers.
TEXT_RECORD_BYTES = 48
TEXT_X_OFFSET = 0
TEXT_Y_OFFSET = 8
TEXT_LENGTH_OFFSET = 16
TEXT_FONT_OFFSET = 24
TEXT_COLOR_OFFSET = 32
TEXT_POINTER_OFFSET = 40
TEXT_CALL_BYTES = 48
TEXT_CALL_SLOT_OFFSET = 0
TEXT_CALL_X_OFFSET = 8
TEXT_CALL_Y_OFFSET = 16
TEXT_CALL_RESERVED_X_OFFSET = 24
TEXT_CALL_RESERVED_Y_OFFSET = 32
NATIVE_TEXT_CAPACITY = 512

define_global_i64_array(
    "harness_gui_bridge_state", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0
)


def _g(offset: int) -> int:
    return load_i64(global_addr("harness_gui_bridge_state"), offset)


def _setg(offset: int, value: int) -> None:
    store_i64(global_addr("harness_gui_bridge_state"), offset, value)


def _gp(offset: int):
    return int_to_ptr(_g(offset))


def init(title, width: int, height: int, dylib_path) -> int:
    if _g(WINDOW_SLOT) != 0:
        return -4
    handle = dynamic_library_open(dylib_path)
    if ptr_is_null(handle):
        return -1
    create = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_create"))
    render = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_render"))
    show = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_show"))
    close = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_close"))
    pump = dynamic_library_symbol(handle, cstr("pcc_gui_metal_run_loop_pump"))
    closed = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_is_closed"))
    click = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_poll_click"))
    text = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_text"))
    capture = dynamic_library_symbol(handle, cstr("pcc_gui_metal_window_capture"))
    if (
        ptr_is_null(create)
        or ptr_is_null(render)
        or ptr_is_null(show)
        or ptr_is_null(close)
        or ptr_is_null(pump)
        or ptr_is_null(closed)
        or ptr_is_null(click)
        or ptr_is_null(text)
    ):
        return -2
    window = call_ptr_i64_i64(create, title, width, height)
    if ptr_is_null(window):
        return -3
    _setg(WINDOW_SLOT, ptr_to_int(window))
    _setg(RENDER_SLOT, ptr_to_int(render))
    _setg(SHOW_SLOT, ptr_to_int(show))
    _setg(CLOSE_SLOT, ptr_to_int(close))
    _setg(PUMP_SLOT, ptr_to_int(pump))
    _setg(CLOSED_SLOT, ptr_to_int(closed))
    _setg(CLICK_SLOT, ptr_to_int(click))
    _setg(TEXT_SLOT, ptr_to_int(text))
    _setg(CAPTURE_SLOT, ptr_to_int(capture))
    _setg(WIDTH_SLOT, width)
    _setg(HEIGHT_SLOT, height)
    _setg(RENDER_ACK_SLOT, -1)
    _setg(TEXT_COUNT_SLOT, 0)
    call_i64_ptr1(show, window)
    _pump()
    return 0


def render_scene(rects, colors, rect_count: int, texts, text_count: int) -> None:
    if _g(WINDOW_SLOT) == 0:
        return
    if text_count < 0 or text_count > NATIVE_TEXT_CAPACITY:
        raise ValueError("Harness text count exceeds the native slot capacity")
    _setg(
        RENDER_ACK_SLOT,
        call_i64_ptr3_i64_i64_i64(
            _gp(RENDER_SLOT),
            _gp(WINDOW_SLOT),
            rects,
            colors,
            rect_count,
            _g(WIDTH_SLOT),
            _g(HEIGHT_SLOT),
        ),
    )
    i = 0
    while i < text_count:
        record = texts
        params = stack_alloc(TEXT_CALL_BYTES)
        store_i64(params, TEXT_CALL_SLOT_OFFSET, i)
        store_i64(params, TEXT_CALL_X_OFFSET, load_i64(record, i * TEXT_RECORD_BYTES + TEXT_X_OFFSET))
        store_i64(params, TEXT_CALL_Y_OFFSET, load_i64(record, i * TEXT_RECORD_BYTES + TEXT_Y_OFFSET))
        store_i64(params, TEXT_CALL_RESERVED_X_OFFSET, 0)
        store_i64(params, TEXT_CALL_RESERVED_Y_OFFSET, 0)
        call_i64_ptr3_i64_i64_i64(
            _gp(TEXT_SLOT),
            _gp(WINDOW_SLOT),
            load_ptr(record, i * TEXT_RECORD_BYTES + TEXT_POINTER_OFFSET),
            params,
            load_i64(record, i * TEXT_RECORD_BYTES + TEXT_LENGTH_OFFSET),
            load_i64(record, i * TEXT_RECORD_BYTES + TEXT_FONT_OFFSET),
            load_i64(record, i * TEXT_RECORD_BYTES + TEXT_COLOR_OFFSET),
        )
        i += 1
    # Clear every previously published slot, including transcripts above the
    # old fixed 64-slot clearing range, when a new session has fewer rows.
    while i < _g(TEXT_COUNT_SLOT):
        params = stack_alloc(TEXT_CALL_BYTES)
        store_i64(params, TEXT_CALL_SLOT_OFFSET, i)
        call_i64_ptr3_i64_i64_i64(
            _gp(TEXT_SLOT), _gp(WINDOW_SLOT), null(), params, 0, 12, 0
        )
        i += 1
    _setg(TEXT_COUNT_SLOT, text_count)


def render_ack() -> int:
    return _g(RENDER_ACK_SLOT)


def poll_click(x_out, y_out) -> int:
    if _g(WINDOW_SLOT) == 0:
        return 0
    return call_i64_ptr3(_gp(CLICK_SLOT), _gp(WINDOW_SLOT), x_out, y_out)


def _pump() -> None:
    # The native bridge declares int64_t pump(void), with no dummy argument.
    result = stack_alloc(8)
    call_c_abi(_gp(PUMP_SLOT), "i64", (), (), result)


def running() -> int:
    if _g(WINDOW_SLOT) == 0:
        return 0
    _pump()
    return 0 if call_i64_ptr1(_gp(CLOSED_SLOT), _gp(WINDOW_SLOT)) != 0 else 1


def sleep(milliseconds: int) -> None:
    pcc_platform_sleep_ns(milliseconds * 1000000)


def capture(path) -> int:
    if _g(WINDOW_SLOT) == 0 or ptr_is_null(_gp(CAPTURE_SLOT)):
        return -1
    return call_i64_ptr2(_gp(CAPTURE_SLOT), _gp(WINDOW_SLOT), path)


def close() -> None:
    if _g(WINDOW_SLOT) == 0:
        return
    window = _gp(WINDOW_SLOT)
    close_function = _gp(CLOSE_SLOT)
    # Revoke the handle before the platform callback, even if it fails.
    offset = 0
    while offset <= TEXT_COUNT_SLOT:
        _setg(offset, 0)
        offset += 8
    _setg(RENDER_ACK_SLOT, -1)
    call_i64_ptr1(close_function, window)
