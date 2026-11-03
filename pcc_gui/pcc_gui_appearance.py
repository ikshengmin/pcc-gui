"""App-local appearance ownership; native snapshots do not run source callbacks."""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_appearance_open = extern("pcc_gui_appearance_open", (c_ptr,), c_int64)
pcc_gui_appearance_set_source = extern("pcc_gui_appearance_set_source", (c_int64, c_int64), c_int64)
pcc_gui_appearance_snapshot = extern("pcc_gui_appearance_snapshot", (c_int64, c_ptr, c_ptr), c_int64)
pcc_gui_appearance_event_peek = extern("pcc_gui_appearance_event_peek", (c_int64, c_ptr, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_appearance_event_ack = extern("pcc_gui_appearance_event_ack", (c_int64, c_int64), c_int64)
pcc_gui_appearance_color = extern("pcc_gui_appearance_color", (c_int64, c_int64, c_ptr, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_appearance_release = extern("pcc_gui_appearance_release", (c_int64,), c_int64)
pcc_gui_appearance_live_count = extern("pcc_gui_appearance_live_count", (c_ptr,), c_int64)
