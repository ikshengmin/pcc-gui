"""Read an ordinary hidden Metal window's fullscreen state through its lease."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol, load_i64,
    load_ptr, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_create"))
    close = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_close"))
    acquire = dynamic_library_symbol(library, cstr("pcc_gui_fullscreen_acquire"))
    state = dynamic_library_symbol(library, cstr("pcc_gui_fullscreen_state"))
    release = dynamic_library_symbol(library, cstr("pcc_gui_fullscreen_release"))
    if ptr_is_null(create) or ptr_is_null(close) or ptr_is_null(acquire) or ptr_is_null(state) or ptr_is_null(release):
        return 2
    result = stack_alloc(8)
    slot = stack_alloc(8)
    closed = stack_alloc(8)
    full = stack_alloc(8)
    call_c_abi(create, "ptr", ("ptr", "i64", "i64"), (cstr("PCC hidden"), 160, 120), result)
    window = load_ptr(result, 0)
    if ptr_is_null(window):
        return 3
    call_c_abi(acquire, "i64", ("ptr", "ptr"), (window, slot), result)
    status = load_i64(result, 0)
    if status == 0:
        key = load_i64(slot, 0)
        call_c_abi(state, "i64", ("i64", "ptr", "ptr"), (key, closed, full), result)
        status = load_i64(result, 0)
        if status == 0 and (load_i64(closed, 0) != 0 or load_i64(full, 0) != 0):
            status = 4
        call_c_abi(release, "i64", ("i64",), (key,), result)
        if load_i64(result, 0) != 0:
            status = 5
    call_c_abi(close, "i64", ("ptr",), (window,), result)
    if status or load_i64(result, 0):
        return 6
    print("windowed")
    return 0


main()
