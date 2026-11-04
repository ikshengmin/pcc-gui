"""AppKit URL launches and Finder selections on a main-thread document lease."""
from pcc.extern import c_int64, c_rawptr, extern

pcc_gui_shell_open_external = extern(
    "pcc_gui_shell_open_external", (c_int64, c_rawptr, c_int64, c_int64, c_rawptr), c_int64
)
pcc_gui_shell_show_item_in_folder = extern(
    "pcc_gui_shell_show_item_in_folder", (c_int64, c_rawptr, c_int64), c_int64
)
