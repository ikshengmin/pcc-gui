"""Exchange opaque bytes; substitute the built bridge path in a private copy."""
from pcc.unsafe import (
    call_c_abi, cstr, dynamic_library_open, dynamic_library_symbol, load_i8,
    load_i64, null, ptr_is_null, stack_alloc,
)


def main() -> int:
    library = dynamic_library_open(cstr("__BRIDGE__"))
    if ptr_is_null(library):
        return 1
    create = dynamic_library_symbol(library, cstr("pcc_gui_protocol_open"))
    submit = dynamic_library_symbol(library, cstr("pcc_gui_protocol_submit"))
    claim = dynamic_library_symbol(library, cstr("pcc_gui_protocol_request_claim"))
    reply = dynamic_library_symbol(library, cstr("pcc_gui_protocol_reply"))
    take = dynamic_library_symbol(library, cstr("pcc_gui_protocol_response_take"))
    retire = dynamic_library_symbol(library, cstr("pcc_gui_protocol_retire"))
    if (ptr_is_null(create) or ptr_is_null(submit) or ptr_is_null(claim)
            or ptr_is_null(reply) or ptr_is_null(take) or ptr_is_null(retire)):
        return 2
    result = stack_alloc(8)
    owner_out = stack_alloc(8)
    request_out = stack_alloc(8)
    call_c_abi(create, "i64", ("ptr",), (owner_out,), result)
    if load_i64(result, 0) != 0:
        return 3
    owner = load_i64(owner_out, 0)
    call_c_abi(submit, "i64", ("i64", "ptr", "i64", "ptr", "i64", "ptr"),
               (owner, cstr("resource"), 8, null(), 0, request_out), result)
    status = load_i64(result, 0)
    if status == 0:
        request = load_i64(request_out, 0)
        call_c_abi(claim, "i64", ("i64", "i64"), (owner, request), result)
        status = load_i64(result, 0)
        if status == 0:
            call_c_abi(reply, "i64", ("i64", "i64", "ptr", "i64", "ptr", "i64"),
                       (owner, request, null(), 0, cstr("OK"), 2), result)
            status = load_i64(result, 0)
        if status == 0:
            body = stack_alloc(2)
            kind = stack_alloc(8)
            code = stack_alloc(8)
            call_c_abi(take, "i64", ("i64", "i64", "ptr", "i64", "ptr", "i64", "ptr", "ptr"),
                       (owner, request, null(), 0, body, 2, kind, code), result)
            status = load_i64(result, 0)
            if status == 0 and (load_i64(kind, 0) != 1 or load_i64(code, 0) != 0
                                or load_i8(body, 0) != 79 or load_i8(body, 1) != 75):
                status = 7
    call_c_abi(retire, "i64", ("i64",), (owner,), result)
    if load_i64(result, 0) != 0:
        return 8
    return status


main()
