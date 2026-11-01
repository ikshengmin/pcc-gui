import pcc_gui
from pcc.extern import c_abi_typed_export, c_int32, c_int64, c_ptr, c_rawptr, extern
from pcc.unsafe import function_addr, load_i32, load_i64, load_i8, load_ptr, null, stack_alloc, store_i8, store_i64

init = extern("pcc_gui_commands_init", (c_int64,c_int64,c_int64,c_int64), c_int32)
register = extern("pcc_gui_commands_register", (c_int32,c_rawptr,c_int32,c_int32,c_int64,c_int64), c_int32)
submit = extern("pcc_gui_ipc_submit", (c_int64,c_int32,c_int64,c_int64,c_int64,c_rawptr,c_int64,c_rawptr), c_int32)
take = extern("pcc_gui_ipc_take", (c_int64,c_rawptr,c_int64,c_rawptr), c_int32)
request = extern("pcc_gui_commands_request_payload", (c_int64,c_rawptr), c_int32)
resolve = extern("pcc_gui_commands_resolve_result", (c_int64,c_rawptr,c_int64), c_int32)
teardown = extern("pcc_gui_commands_target_teardown", (c_int64,), c_int32)
shutdown = extern("pcc_gui_commands_shutdown", (), c_int64)

@c_abi_typed_export("ipc_deferred", "i32", ("ptr","i64"))
def ipc_deferred(packet: c_ptr, resolver: int) -> int:
    return 1

def main() -> int:
    if init(2,2,2,4) != 0:
        return 1
    if register(7,function_addr("ipc_deferred"),1,1,11,29) != 0:
        return 2
    value=stack_alloc(8)
    store_i8(value,0,65)
    if submit(1,7,11,30,1,value,1,null()) != -111:
        return 3
    if submit(1,7,11,29,1,value,1,null()) != 1:
        return 4
    store_i8(value,0,90)
    reply=stack_alloc(48)
    out=stack_alloc(8)
    store_i64(reply,0,99)
    if take(1,out,8,reply) != 1 or load_i64(reply,0) != 99:
        return 5
    borrowed=stack_alloc(16)
    if request(1,borrowed) != 0 or load_i8(load_ptr(borrowed,0),0) != 65:
        return 6
    if resolve(1,load_ptr(borrowed,0),1) != 0:
        return 7
    if take(1,out,0,reply) != -101 or load_i64(reply,0) != 99:
        return 8
    if take(1,out,8,reply) != 0 or load_i8(out,0) != 65 or load_i32(reply,8) != 1:
        return 9
    if take(1,out,8,reply) != -108:
        return 10
    if submit(2,7,11,29,2,value,1,null()) != 1 or teardown(11) != 0:
        return 11
    if take(2,out,8,reply) != 0 or load_i32(reply,8) != 3:
        return 12
    shutdown()
    print("PCC_GUI_NATIVE_IPC_OK")
    return 0

main()
