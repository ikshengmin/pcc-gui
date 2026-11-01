# Native GUI byte-message boundary

`pcc_gui_ipc_submit` builds the existing PccGuiInvokeV1 packet with asynchronous
completion permitted. Route registration, request copying, target/context policy,
pending state and teardown remain owned by `pcc_gui_commands`. There is no second
resolver table. Calls run on the existing UI owner thread; this adapter does not
create an OS process channel or execute callbacks on worker threads.

`pcc_gui_ipc_take(resolver, payload_out, capacity, completion_out)` returns 1 while
pending, 0 after copying and consuming a terminal reply, or a canonical negative
error. The caller supplies independent writable payload and 48-byte completion
buffers. Insufficient capacity and invalid/pending reads preserve output and do
not consume the reply. Successful output rewrites the payload pointer to caller
storage before releasing the resolver. Static error messages remain owned by the
canonical command module. Target teardown produces its existing cancellation.

The v1 payload limit remains 256 bytes. Larger messages, external process
transport, translated source serialization/handler registration and complete
Electron IPC are separate work. No application channel or response is built in.
Run `tests/test_pcc_gui_ipc.py` with the installed matching PCC1 and an explicitly
staged runtime archive; the fixture checks native copies, sender policy, pending
reads, capacity retry, one-time retirement and target cancellation.
