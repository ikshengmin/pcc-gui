"""Owner-polled AppKit fullscreen transitions on a live Metal window handle."""
from pcc.extern import c_int64, c_rawptr, extern

pcc_gui_fullscreen_acquire = extern("pcc_gui_fullscreen_acquire", (c_rawptr, c_rawptr), c_int64)
pcc_gui_fullscreen_state = extern("pcc_gui_fullscreen_state", (c_int64, c_rawptr, c_rawptr), c_int64)
pcc_gui_fullscreen_set = extern("pcc_gui_fullscreen_set", (c_int64, c_int64), c_int64)
pcc_gui_fullscreen_take = extern("pcc_gui_fullscreen_take", (c_int64, c_rawptr), c_int64)
pcc_gui_fullscreen_release = extern("pcc_gui_fullscreen_release", (c_int64,), c_int64)
pcc_gui_fullscreen_live_count = extern("pcc_gui_fullscreen_live_count", (c_rawptr,), c_int64)
