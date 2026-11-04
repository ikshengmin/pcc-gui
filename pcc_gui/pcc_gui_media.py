"""Main-thread microphone status and explicit async requests on protocol leases.

The protocol queue owns native completion bytes. Source permission policy,
Promises, callbacks, and the decision to request access belong to its caller.
"""
from pcc.extern import c_int64, c_rawptr, extern

pcc_gui_media_microphone_status = extern("pcc_gui_media_microphone_status", (c_rawptr,), c_int64)
pcc_gui_media_microphone_ask = extern("pcc_gui_media_microphone_ask", (c_int64, c_rawptr), c_int64)
