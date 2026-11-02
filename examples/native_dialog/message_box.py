"""Compiled-Python consumer of the canonical dialog ABI; no CPython fallback.

Replace __BRIDGE__ in a private copy with the built canonical bridge path.
The app owner initializes AppKit through a hidden window, then polls the dialog.
This example presents a real user choice; tests use the separate native fixture.
"""
from pcc.unsafe import (
    call_c_abi, call_ptr_i64_i64, call_i64_ptr1, cstr,
    dynamic_library_open, dynamic_library_symbol, load_i64, null,
    ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create_window = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_create"))
    close_window = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_close"))
    window = call_ptr_i64_i64(create_window, cstr("PCC dialog owner"), 600, 400)
    if ptr_is_null(window):
        return 2
    result = stack_alloc(8)
    key_out = stack_alloc(8)
    create = dynamic_library_symbol(library, cstr("pcc_gui_message_box_create"))
    text = dynamic_library_symbol(library, cstr("pcc_gui_message_box_text"))
    begin = dynamic_library_symbol(library, cstr("pcc_gui_message_box_begin"))
    poll = dynamic_library_symbol(library, cstr("pcc_gui_message_box_poll"))
    release = dynamic_library_symbol(library, cstr("pcc_gui_message_box_release"))
    sleep = dynamic_library_symbol(library, cstr("usleep"))
    call_c_abi(create, "i64", ("i64", "i64", "i64", "i64", "ptr"), (0, 0, 0, 0, key_out), result)
    if load_i64(result, 0) != 0:
        call_i64_ptr1(close_window, window)
        return 3
    key = load_i64(key_out, 0)
    call_c_abi(text, "i64", ("i64", "i64", "ptr", "i64"), (key, 1, cstr("Native PCC message box"), 22), result)
    if load_i64(result, 0) != 0:
        call_c_abi(release, "i64", ("i64",), (key,), result)
        call_i64_ptr1(close_window, window)
        return 4
    call_c_abi(begin, "i64", ("i64", "ptr"), (key, null()), result)
    if load_i64(result, 0) != 0:
        call_c_abi(release, "i64", ("i64",), (key,), result)
        call_i64_ptr1(close_window, window)
        return 5
    ready = stack_alloc(8)
    response = stack_alloc(8)
    checked = stack_alloc(8)
    while True:
        call_c_abi(poll, "i64", ("i64", "ptr", "ptr", "ptr"), (key, ready, response, checked), result)
        if load_i64(result, 0) != 0:
            return 6
        if load_i64(ready, 0) != 0:
            break
        call_c_abi(sleep, "i32", ("u32",), (16000,), result)
    selected = load_i64(response, 0)
    call_c_abi(release, "i64", ("i64",), (key,), result)
    call_i64_ptr1(close_window, window)
    return selected


main()
