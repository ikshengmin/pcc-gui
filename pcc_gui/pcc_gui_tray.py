"""Owned native image/status-item capabilities; source scheduling is caller-owned."""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_tray_create = extern("pcc_gui_tray_create", (c_int64, c_ptr), c_int64)
pcc_gui_tray_set_image = extern("pcc_gui_tray_set_image", (c_int64, c_int64), c_int64)
pcc_gui_tray_tooltip = extern("pcc_gui_tray_tooltip", (c_int64, c_ptr, c_int64), c_int64)
pcc_gui_tray_menu = extern("pcc_gui_tray_menu", (c_int64, c_int64), c_int64)
pcc_gui_tray_popup = extern("pcc_gui_tray_popup", (c_int64,), c_int64)
pcc_gui_tray_event_peek = extern("pcc_gui_tray_event_peek", (c_int64, c_ptr, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_tray_event_ack = extern("pcc_gui_tray_event_ack", (c_int64, c_int64), c_int64)
pcc_gui_tray_release = extern("pcc_gui_tray_release", (c_int64,), c_int64)
pcc_gui_tray_live_count = extern("pcc_gui_tray_live_count", (c_ptr,), c_int64)
