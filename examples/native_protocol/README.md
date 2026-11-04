# Document request queue

`queue.py` is a compiled Python consumer of `pcc_gui_protocol.h`. Build the
canonical native bridge and replace `__BRIDGE__` in a private copy with its
absolute path. The example opens a document lease, submits opaque bytes,
claims the FIFO head, publishes and takes a reply, then retires the lease.

Open a fresh lease for each document generation. Native producers may submit
requests, reply, report failure or cancel from any thread. The UI owner peeks,
copies and claims requests before invoking source code. Only a claimed request
accepts a reply or failure. Cancellation can also remove a queued request
without changing the order of the others. The first terminal result wins.

Pending response peeks write only `ready=0`. A pending or short response take
preserves every output. A successful take copies the complete metadata and body
and consumes the key once. Retiring the owner invalidates its requests and
releases all snapshots without invoking callbacks. Public keys do not alias
recycled storage. Limits are 64 owners, 256 outstanding requests per owner,
64 KiB metadata, 8 MiB body and 64 MiB total live payload bytes.

This is a polling, in-process native capability. It needs no window and makes
no network request. Source protocol registration, Fetch/Request/Response,
streaming, document navigation/policy, wake integration, and production
Harness wiring are separate. Existing `pcc_gui_ipc_submit/take` retain their
256-byte command ABI; no application handler is registered with this queue.
Clang/Foundation fixture execution and installed PCC1 qualification are distinct.
