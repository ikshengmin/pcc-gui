"""Minimal compiled consumer; replace __BRIDGE__ in a private build copy."""
from pcc.unsafe import (
    call_c_abi, call_ptr_i64_i64, call_i64_ptr1, cstr,
    dynamic_library_open, dynamic_library_symbol, load_i64, ptr_is_null,
    stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create_window = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_create"))
    close_window = dynamic_library_symbol(library, cstr("pcc_gui_metal_window_close"))
    window = call_ptr_i64_i64(create_window, cstr("PCC owned menu"), 600, 400)
    if ptr_is_null(window):
        return 2
    result = stack_alloc(8)
    menu_out = stack_alloc(8)
    item_out = stack_alloc(8)
    create = dynamic_library_symbol(library, cstr("pcc_gui_menu_create"))
    insert = dynamic_library_symbol(library, cstr("pcc_gui_menu_insert"))
    popup = dynamic_library_symbol(library, cstr("pcc_gui_menu_popup"))
    release = dynamic_library_symbol(library, cstr("pcc_gui_menu_release"))
    call_c_abi(create, "i64", ("ptr",), (menu_out,), result)
    if load_i64(result, 0) != 0:
        call_i64_ptr1(close_window, window)
        return 3
    menu = load_i64(menu_out, 0)
    call_c_abi(insert, "i64", ("i64", "i64", "i64", "i64", "ptr", "i64", "ptr"), (menu, 0, 0, 42, cstr("Open project"), 12, item_out), result)
    if load_i64(result, 0) != 0:
        call_c_abi(release, "i64", ("i64",), (menu,), result)
        call_i64_ptr1(close_window, window)
        return 4
    call_c_abi(popup, "i64", ("i64", "ptr", "i64", "i64", "i64"), (menu, window, 40, 40, -1), result)
    status = load_i64(result, 0)
    call_c_abi(release, "i64", ("i64",), (menu,), result)
    call_i64_ptr1(close_window, window)
    return status


main()
