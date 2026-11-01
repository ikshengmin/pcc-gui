"""pcc-Python owner: PNG decode for the GUI image resource path.

Decodes a PNG (8-bit, color types 0/2/4/6, non-interlaced) into RGBA8
pixels.  Chunk parsing, IHDR, IDAT concatenation, per-scanline unfiltering
(Sub/Up/Average/Paeth) and gray/RGB->RGBA expansion are pure pcc-Python
logic; the DEFLATE decompression is delegated to the system zlib
(uncompress via dlopen — zlib is a host substrate, not a pcc-Python owner).

Owned surface:

  pcc_gui_png_decode(data, data_len, out_header, out_pixels, out_cap) -> i32
      header: width@0, height@8, channels@16 (i64 slots)
      out_pixels: width*height*4 bytes RGBA
      0 = ok, <0 = error code.

Error codes: -1 bad signature, -2 missing IHDR, -3 unsupported format
(bit depth != 8, interlace, palette), -4 missing/invalid IDAT,
-5 zlib inflate failed, -6 output buffer too small, -7 bad scanline data,
-8 scratch allocation failed. Slot 24 reports the required RGBA output size.
CRC verification and palette/interlaced PNGs are outside this decoder contract.
"""

__pcc_runtime_port__ = True

from pcc.extern import c_abi_typed_export, c_int64, c_ptr, c_void, extern
from pcc.unsafe import (
    calloc,
    free,
    stack_alloc,
    define_global_i64,
    global_addr,
    int_to_ptr,
    ptr_to_int,
    cstr,
    dynamic_library_open,
    dynamic_library_symbol,
    load_i64,
    null,
    ptr_add,
    ptr_is_null,
    store_i64,
    store_i8,
    load_i8,
    call_i64_ptr_ptr_ptr_i64,
)

define_global_i64("pcc_gui_zlib_handle", 0)
define_global_i64("pcc_gui_zlib_uncompress", 0)


def _zlib_uncompress() -> int:
    """Resolve one process-lifetime zlib handle without making it a GC owner."""
    if load_i64(global_addr("pcc_gui_zlib_uncompress"), 0) != 0:
        return 0
    handle = dynamic_library_open(cstr("/usr/lib/libz.1.dylib"))
    if ptr_is_null(handle):
        handle = dynamic_library_open(cstr("libz.so.1"))
    if ptr_is_null(handle):
        return -1
    fn = dynamic_library_symbol(handle, cstr("uncompress"))
    if ptr_is_null(fn):
        return -1
    store_i64(global_addr("pcc_gui_zlib_handle"), 0, ptr_to_int(handle))
    store_i64(global_addr("pcc_gui_zlib_uncompress"), 0, ptr_to_int(fn))
    return 0


def _u8(data: c_ptr, offset: int) -> int:
    return load_i8(data, offset) & 255


def _u32(data: c_ptr, offset: int) -> int:
    return (
        (_u8(data, offset) << 24)
        | (_u8(data, offset + 1) << 16)
        | (_u8(data, offset + 2) << 8)
        | _u8(data, offset + 3)
    )


@c_abi_typed_export("pcc_gui_png_decode", "i32", ("ptr", "i64", "ptr", "ptr", "i64"))
def pcc_gui_png_decode(
    data: c_ptr, data_len: int, out_header: c_ptr, out_pixels: c_ptr, out_cap: int
) -> int:
    if ptr_is_null(data) or data_len < 8:
        return -1
    if _u32(data, 0) != 0x89504E47 or _u32(data, 4) != 0x0D0A1A0A:
        return -1
    if ptr_is_null(out_header):
        return -6
    pos: int = 8
    width: int = 0
    height: int = 0
    channels: int = 0
    idat_len: int = 0
    saw_end: int = 0
    while pos + 12 <= data_len:
        length: int = _u32(data, pos)
        if length > data_len - pos - 12:
            return -4
        kind: int = _u32(data, pos + 4)
        start: int = pos + 8
        if kind == 0x49484452:
            if pos != 8 or length != 13:
                return -2
            width = _u32(data, start)
            height = _u32(data, start + 4)
            color_type: int = _u8(data, start + 9)
            if (
                _u8(data, start + 8) != 8
                or _u8(data, start + 10) != 0
                or _u8(data, start + 11) != 0
                or _u8(data, start + 12) != 0
            ):
                return -3
            if color_type == 0:
                channels = 1
            elif color_type == 2:
                channels = 3
            elif color_type == 4:
                channels = 2
            elif color_type == 6:
                channels = 4
            else:
                return -3
        elif kind == 0x49444154:
            if channels == 0:
                return -2
            idat_len += length
        elif kind == 0x49454E44:
            if length != 0:
                return -4
            saw_end = 1
            break
        pos += length + 12
    if width <= 0 or height <= 0 or width > 0x7FFFFFFF or height > 0x7FFFFFFF:
        return -2
    if idat_len == 0 or saw_end == 0:
        return -4
    # Compute sizes only after checking that signed 64-bit products fit.
    if width > 0x7FFFFFFFFFFFFFFF // 4 // height:
        return -6
    pixels_len: int = width * height * 4
    store_i64(out_header, 24, pixels_len)
    if ptr_is_null(out_pixels) or out_cap < pixels_len:
        return -6
    stride: int = width * channels
    if stride + 1 > 0x7FFFFFFFFFFFFFFF // height:
        return -6
    raw_len: int = (stride + 1) * height
    compressed = calloc(idat_len, 1)
    if ptr_is_null(compressed):
        return -8
    raw = calloc(raw_len, 1)
    if ptr_is_null(raw):
        free(compressed)
        return -8
    # IDAT chunks contain one zlib stream, separated by chunk headers/CRCs.
    pos = 8
    copied: int = 0
    while pos + 12 <= data_len:
        length = _u32(data, pos)
        kind = _u32(data, pos + 4)
        if kind == 0x49444154:
            i: int = 0
            while i < length:
                store_i8(compressed, copied + i, _u8(data, pos + 8 + i))
                i += 1
            copied += length
        elif kind == 0x49454E44:
            break
        pos += length + 12
    if _zlib_uncompress() != 0:
        free(raw)
        free(compressed)
        return -5
    dest_len = stack_alloc(8)
    store_i64(dest_len, 0, raw_len)
    rc: int = call_i64_ptr_ptr_ptr_i64(
        int_to_ptr(load_i64(global_addr("pcc_gui_zlib_uncompress"), 0)),
        raw,
        dest_len,
        compressed,
        idat_len,
    )
    free(compressed)
    if rc != 0:
        free(raw)
        return -5
    if load_i64(dest_len, 0) != raw_len:
        free(raw)
        return -7
    row: int = 0
    while row < height:
        base: int = row * (stride + 1)
        filter_type: int = _u8(raw, base)
        if filter_type > 4:
            free(raw)
            return -7
        x: int = 0
        while x < stride:
            value: int = _u8(raw, base + 1 + x)
            left: int = 0
            above: int = 0
            upper_left: int = 0
            if x >= channels:
                left = _u8(raw, base + 1 + x - channels)
            if row > 0:
                above = _u8(raw, base - stride + x)
                if x >= channels:
                    upper_left = _u8(raw, base - stride + x - channels)
            if filter_type == 1:
                value += left
            elif filter_type == 2:
                value += above
            elif filter_type == 3:
                value += (left + above) // 2
            elif filter_type == 4:
                predict: int = left + above - upper_left
                pa: int = predict - left
                pb: int = predict - above
                pc: int = predict - upper_left
                if pa < 0:
                    pa = -pa
                if pb < 0:
                    pb = -pb
                if pc < 0:
                    pc = -pc
                chosen: int = left
                best: int = pa
                if pb < best:
                    chosen = above
                    best = pb
                if pc < best:
                    chosen = upper_left
                value += chosen
            store_i8(raw, base + 1 + x, value & 255)
            x += 1
        x = 0
        while x < width:
            start = base + 1 + x * channels
            red: int = _u8(raw, start)
            green: int = red
            blue: int = red
            alpha: int = 255
            if channels == 2:
                alpha = _u8(raw, start + 1)
            elif channels >= 3:
                green = _u8(raw, start + 1)
                blue = _u8(raw, start + 2)
                if channels == 4:
                    alpha = _u8(raw, start + 3)
            dest: int = (row * width + x) * 4
            store_i8(out_pixels, dest, red)
            store_i8(out_pixels, dest + 1, green)
            store_i8(out_pixels, dest + 2, blue)
            store_i8(out_pixels, dest + 3, alpha)
            x += 1
        row += 1
    free(raw)
    store_i64(out_header, 0, width)
    store_i64(out_header, 8, height)
    store_i64(out_header, 16, 4)
    return 0
