"""Owned native menu graphs and a non-consuming event queue.

All operations run on the UI thread. Popup performs synchronous AppKit tracking;
events contain only lease/command integers and are drained by the caller after
tracking. This is separate from source-language asynchronous scheduling.
"""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_menu_create = extern("pcc_gui_menu_create", (c_ptr,), c_int64)
pcc_gui_menu_insert = extern("pcc_gui_menu_insert", (c_int64, c_int64, c_int64, c_int64, c_ptr, c_int64, c_ptr), c_int64)
pcc_gui_menu_remove = extern("pcc_gui_menu_remove", (c_int64, c_int64), c_int64)
pcc_gui_menu_item_text = extern("pcc_gui_menu_item_text", (c_int64, c_int64, c_ptr, c_int64), c_int64)
pcc_gui_menu_item_state = extern("pcc_gui_menu_item_state", (c_int64, c_int64, c_int64, c_ptr, c_int64), c_int64)
pcc_gui_menu_item_submenu = extern("pcc_gui_menu_item_submenu", (c_int64, c_int64), c_int64)
pcc_gui_menu_count = extern("pcc_gui_menu_count", (c_int64, c_ptr), c_int64)
pcc_gui_menu_set_application = extern("pcc_gui_menu_set_application", (c_int64,), c_int64)
pcc_gui_menu_popup = extern("pcc_gui_menu_popup", (c_int64, c_ptr, c_int64, c_int64, c_int64), c_int64)
pcc_gui_menu_cancel = extern("pcc_gui_menu_cancel", (c_int64,), c_int64)
pcc_gui_menu_event_peek = extern("pcc_gui_menu_event_peek", (c_int64, c_ptr, c_ptr, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_menu_event_ack = extern("pcc_gui_menu_event_ack", (c_int64, c_int64), c_int64)
pcc_gui_menu_release = extern("pcc_gui_menu_release", (c_int64,), c_int64)
pcc_gui_menu_live_count = extern("pcc_gui_menu_live_count", (c_ptr, c_ptr), c_int64)
