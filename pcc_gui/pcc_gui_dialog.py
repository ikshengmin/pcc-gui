"""Native message-box configuration, async completion and explicit UI ownership.

Call from the UI thread. The app owner pumps native events and polls ready jobs;
source-language Promise and Electron option semantics belong above this ABI.
"""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_message_box_create = extern("pcc_gui_message_box_create", (c_int64, c_int64, c_int64, c_int64, c_ptr), c_int64)
pcc_gui_message_box_text = extern("pcc_gui_message_box_text", (c_int64, c_int64, c_ptr, c_int64), c_int64)
pcc_gui_message_box_button = extern("pcc_gui_message_box_button", (c_int64, c_ptr, c_int64), c_int64)
pcc_gui_message_box_begin = extern("pcc_gui_message_box_begin", (c_int64, c_ptr), c_int64)
pcc_gui_message_box_poll = extern("pcc_gui_message_box_poll", (c_int64, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_message_box_cancel = extern("pcc_gui_message_box_cancel", (c_int64,), c_int64)
pcc_gui_message_box_release = extern("pcc_gui_message_box_release", (c_int64,), c_int64)
pcc_gui_message_box_live_count = extern("pcc_gui_message_box_live_count", (c_ptr,), c_int64)
