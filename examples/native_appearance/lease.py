"""Read app-owned appearance through the canonical bridge."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol,
    load_i64, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    count = dynamic_library_symbol(library, cstr("pcc_gui_appearance_live_count"))
    if ptr_is_null(count):
        return 2
    result = stack_alloc(8)
    output = stack_alloc(8)
    call_c_abi(count, "i64", ("ptr",), (output,), result)
    return load_i64(result, 0)


main()
