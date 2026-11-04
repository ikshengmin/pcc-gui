"""Typed declarations for the native document request queue.

Owners are document/session generations. Native producers copy opaque bytes;
the UI owner claims requests, takes terminal replies, and retires the lease.
No source callback, URL policy or HTTP implementation is installed here.
"""
from pcc.extern import c_int64, c_rawptr, extern

pcc_gui_protocol_open = extern("pcc_gui_protocol_open", (c_rawptr,), c_int64)
pcc_gui_protocol_submit = extern(
    "pcc_gui_protocol_submit", (c_int64, c_rawptr, c_int64, c_rawptr, c_int64, c_rawptr), c_int64
)
pcc_gui_protocol_request_peek = extern(
    "pcc_gui_protocol_request_peek", (c_int64, c_rawptr, c_rawptr, c_rawptr, c_rawptr), c_int64
)
pcc_gui_protocol_request_copy = extern(
    "pcc_gui_protocol_request_copy", (c_int64, c_int64, c_int64, c_rawptr, c_int64), c_int64
)
pcc_gui_protocol_request_claim = extern("pcc_gui_protocol_request_claim", (c_int64, c_int64), c_int64)
pcc_gui_protocol_reply = extern(
    "pcc_gui_protocol_reply", (c_int64, c_int64, c_rawptr, c_int64, c_rawptr, c_int64), c_int64
)
pcc_gui_protocol_fail = extern("pcc_gui_protocol_fail", (c_int64, c_int64, c_int64), c_int64)
pcc_gui_protocol_cancel = extern("pcc_gui_protocol_cancel", (c_int64, c_int64), c_int64)
pcc_gui_protocol_response_peek = extern(
    "pcc_gui_protocol_response_peek",
    (c_int64, c_int64, c_rawptr, c_rawptr, c_rawptr, c_rawptr, c_rawptr), c_int64,
)
pcc_gui_protocol_response_take = extern(
    "pcc_gui_protocol_response_take",
    (c_int64, c_int64, c_rawptr, c_int64, c_rawptr, c_int64, c_rawptr, c_rawptr), c_int64,
)
pcc_gui_protocol_retire = extern("pcc_gui_protocol_retire", (c_int64,), c_int64)
pcc_gui_protocol_live_counts = extern(
    "pcc_gui_protocol_live_counts", (c_rawptr, c_rawptr, c_rawptr), c_int64
)
