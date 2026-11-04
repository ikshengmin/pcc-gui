"""Consume an invalid URL result without launching an application."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol, load_i64,
    null, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create = dynamic_library_symbol(library, cstr("pcc_gui_protocol_open"))
    start = dynamic_library_symbol(library, cstr("pcc_gui_shell_open_external"))
    take = dynamic_library_symbol(library, cstr("pcc_gui_protocol_response_take"))
    retire = dynamic_library_symbol(library, cstr("pcc_gui_protocol_retire"))
    if ptr_is_null(create) or ptr_is_null(start) or ptr_is_null(take) or ptr_is_null(retire):
        return 2
    result = stack_alloc(8)
    owner_out = stack_alloc(8)
    key_out = stack_alloc(8)
    kind = stack_alloc(8)
    error = stack_alloc(8)
    call_c_abi(create, "i64", ("ptr",), (owner_out,), result)
    if load_i64(result, 0) != 0:
        return 3
    owner = load_i64(owner_out, 0)
    call_c_abi(start, "i64", ("i64", "ptr", "i64", "i64", "ptr"),
               (owner, null(), 0, 0, key_out), result)
    status = load_i64(result, 0)
    if status == 0:
        key = load_i64(key_out, 0)
        call_c_abi(take, "i64", ("i64", "i64", "ptr", "i64", "ptr", "i64", "ptr", "ptr"),
                   (owner, key, null(), 0, null(), 0, kind, error), result)
        status = load_i64(result, 0)
        if status == 0 and (load_i64(kind, 0) != 2 or load_i64(error, 0) != 10):
            status = 4
    call_c_abi(retire, "i64", ("i64",), (owner,), result)
    if status != 0 or load_i64(result, 0) != 0:
        return 5
    print("invalid URL")
    return 0


main()
