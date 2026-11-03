"""App-owned native resume/shutdown notifications; no power transitions.

Native callbacks only publish bounded integer events. The source event owner
consumes them on its own thread. Production shutdown-before-termination ordering
requires a shared dispatcher or a deferred termination handshake.
"""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_power_open = extern("pcc_gui_power_open", (c_int64, c_ptr), c_int64)
pcc_gui_power_peek = extern("pcc_gui_power_peek", (c_int64, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_power_ack = extern("pcc_gui_power_ack", (c_int64, c_int64), c_int64)
pcc_gui_power_release = extern("pcc_gui_power_release", (c_int64,), c_int64)
pcc_gui_power_live_count = extern("pcc_gui_power_live_count", (c_ptr,), c_int64)
