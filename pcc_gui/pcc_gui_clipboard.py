"""Typed declarations for the native AppKit text clipboard lease API.

All calls require the UI thread. Text uses explicit UTF-8 lengths, including
embedded NUL; snapshots survive clipboard mutation and board-lease close.
Callers release snapshot keys and close board keys explicitly. These declarations
do not select a clipboard or implement Electron/Promise behavior.
"""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_clipboard_open_general = extern("pcc_gui_clipboard_open_general", (c_ptr,), c_int64)
pcc_gui_clipboard_open_named = extern("pcc_gui_clipboard_open_named", (c_ptr, c_int64, c_ptr), c_int64)
pcc_gui_clipboard_close = extern("pcc_gui_clipboard_close", (c_int64,), c_int64)
pcc_gui_clipboard_write_utf8 = extern("pcc_gui_clipboard_write_utf8", (c_int64, c_ptr, c_int64), c_int64)
pcc_gui_clipboard_clear = extern("pcc_gui_clipboard_clear", (c_int64,), c_int64)
pcc_gui_clipboard_snapshot = extern("pcc_gui_clipboard_snapshot", (c_int64, c_ptr, c_ptr), c_int64)
pcc_gui_clipboard_snapshot_copy = extern("pcc_gui_clipboard_snapshot_copy", (c_int64, c_ptr, c_int64), c_int64)
pcc_gui_clipboard_snapshot_release = extern("pcc_gui_clipboard_snapshot_release", (c_int64,), c_int64)
pcc_gui_clipboard_live_counts = extern("pcc_gui_clipboard_live_counts", (c_ptr, c_ptr), c_int64)
