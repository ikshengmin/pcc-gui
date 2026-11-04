"""Read the calling process's microphone status. Run with a built bridge path."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol,
    load_i64, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    query = dynamic_library_symbol(library, cstr("pcc_gui_media_microphone_status"))
    if ptr_is_null(query):
        return 2
    observed = stack_alloc(8)
    result = stack_alloc(8)
    call_c_abi(query, "i64", ("ptr",), (observed,), result)
    if load_i64(result, 0) != 0:
        return 3
    value = load_i64(observed, 0)
    if value < 0 or value > 4:
        return 4
    print(value)
    return 0


main()
