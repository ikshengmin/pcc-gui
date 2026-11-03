"""Open and retire an owned subscription; never request a power transition."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol,
    load_i64, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    open_subscription = dynamic_library_symbol(library, cstr("pcc_gui_power_open"))
    release_subscription = dynamic_library_symbol(library, cstr("pcc_gui_power_release"))
    result = stack_alloc(8)
    key_out = stack_alloc(8)
    call_c_abi(open_subscription, "i64", ("i64", "ptr"), (3, key_out), result)
    status = load_i64(result, 0)
    if status != 0:
        return status
    key = load_i64(key_out, 0)
    call_c_abi(release_subscription, "i64", ("i64",), (key,), result)
    return load_i64(result, 0)


main()
