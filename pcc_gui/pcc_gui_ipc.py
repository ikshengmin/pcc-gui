"""Byte-message adapter for the canonical native GUI command resolver.

This is an in-process renderer/host boundary, not an OS process transport.
The UI owner registers routes and drives asynchronous completions through
``pcc_gui_commands``. Request bytes are copied by that owner. ``take`` copies
a terminal reply into caller storage before retiring its resolver exactly once.
No Python/JavaScript object, callback closure or application response is invented.
The existing v1 command payload bound (256 bytes) remains explicit.
"""

__pcc_runtime_port__ = True

from pcc.extern import c_abi_typed_export, c_int32, c_int64, c_ptr, extern
from pcc.unsafe import (
    load_i64, load_ptr, memcpy, null, ptr_is_null, stack_alloc,
    store_i32, store_i64, store_ptr,
)

_invoke = extern("pcc_gui_commands_invoke", (c_ptr,), c_int32)
_completion = extern("pcc_gui_commands_completion", (c_int64, c_ptr), c_int32)
_release = extern("pcc_gui_commands_release_completion", (c_int64,), c_int32)


@c_abi_typed_export(
    "pcc_gui_ipc_submit", "i32",
    ("i64", "i32", "i64", "i64", "i64", "ptr", "i64", "ptr"),
)
def pcc_gui_ipc_submit(
    request_id: int, route: int, target_id: int, context_id: int,
    resolver_id: int, payload, payload_length: int, error_out,
) -> int:
    """Submit on the UI owner thread; the canonical owner copies the payload."""
    packet = stack_alloc(64)
    store_i64(packet, 0, request_id)
    store_i32(packet, 8, route)
    store_i32(packet, 12, 1)  # INVOKE_ASYNC; synchronous completion is also valid.
    store_i64(packet, 16, target_id)
    store_ptr(packet, 24, payload)
    store_i64(packet, 32, payload_length)
    store_i64(packet, 40, context_id)
    store_i64(packet, 48, resolver_id)
    store_ptr(packet, 56, error_out)
    return _invoke(packet)


@c_abi_typed_export(
    "pcc_gui_ipc_take", "i32", ("i64", "ptr", "i64", "ptr"),
)
def pcc_gui_ipc_take(resolver_id: int, payload_out, capacity: int, completion_out) -> int:
    """Return 1 pending, 0 copied/consumed, or a canonical negative error.

    Failed/pending reads preserve caller output and keep a terminal reply for
    retry. ``completion_out`` is a writable, independent 48-byte
    PccGuiCompletionV1 record. Its payload points into caller storage after a
    successful take. Static error messages keep their canonical lifetime.
    """
    if capacity < 0 or ptr_is_null(completion_out):
        return -105  # ERR_OWNERSHIP
    reply = stack_alloc(48)
    status = _completion(resolver_id, reply)
    if status == -103:  # Canonical completion reports only pending this way.
        return 1
    if status != 0:
        return status
    length = load_i64(reply, 24)
    if length > capacity:
        return -101  # ERR_CAPACITY; do not consume the terminal reply.
    if length > 0 and ptr_is_null(payload_out):
        return -105
    if length > 0:
        memcpy(payload_out, load_ptr(reply, 16), length)
    memcpy(completion_out, reply, 48)
    store_ptr(completion_out, 16, payload_out if length > 0 else null())
    return _release(resolver_id)
