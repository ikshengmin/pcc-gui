"""Create and retire an empty image lease through the canonical native ABI."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol,
    load_i64, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create = dynamic_library_symbol(library, cstr("pcc_gui_native_image_empty"))
    release = dynamic_library_symbol(library, cstr("pcc_gui_native_image_release"))
    if ptr_is_null(create) or ptr_is_null(release):
        return 2
    result = stack_alloc(8)
    key_out = stack_alloc(8)
    call_c_abi(create, "i64", ("ptr",), (key_out,), result)
    status = load_i64(result, 0)
    if status != 0:
        return status
    key = load_i64(key_out, 0)
    call_c_abi(release, "i64", ("i64",), (key,), result)
    return load_i64(result, 0)


main()
