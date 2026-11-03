"""Owned native image/status-item capabilities; source scheduling is caller-owned."""
from pcc.extern import c_int64, c_ptr, extern

pcc_gui_native_image_empty = extern("pcc_gui_native_image_empty", (c_ptr,), c_int64)
pcc_gui_native_image_rgba = extern("pcc_gui_native_image_rgba", (c_ptr, c_int64, c_int64, c_int64, c_int64, c_int64, c_ptr), c_int64)
pcc_gui_native_image_path = extern("pcc_gui_native_image_path", (c_ptr, c_int64, c_ptr), c_int64)
pcc_gui_native_image_info = extern("pcc_gui_native_image_info", (c_int64, c_ptr, c_ptr, c_ptr, c_ptr), c_int64)
pcc_gui_native_image_template = extern("pcc_gui_native_image_template", (c_int64, c_int64), c_int64)
pcc_gui_native_image_release = extern("pcc_gui_native_image_release", (c_int64,), c_int64)
pcc_gui_native_image_live_count = extern("pcc_gui_native_image_live_count", (c_ptr,), c_int64)
