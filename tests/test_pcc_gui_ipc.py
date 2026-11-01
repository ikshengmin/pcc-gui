"""Native byte-message replies reuse the canonical command lifecycle."""
from pathlib import Path
import sys
import struct
import zlib
from test_pcc_gui_commands import _compile_run

def test_native_ipc_copies_retries_and_consumes_once(tmp_path, pcc_py_runtime_archive):
    source=(Path(__file__).parent/'fixtures/ipc_roundtrip.py').read_text()
    output=_compile_run(tmp_path,pcc_py_runtime_archive,'ipc_roundtrip',source)
    assert 'PCC_GUI_NATIVE_IPC_OK' in output

def test_host_pcc_native_image_pointer_boundary(tmp_path, pcc_py_runtime_archive):
    """Exercise the image decoder pointer annotations through a native binary."""
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))
         +chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\xff'))+chunk(b'IEND',b''))
    stores='\n'.join(f'    store_i8(data,{i},{v})' for i,v in enumerate(png))
    source=f'''from pcc.extern import c_int32,c_int64,c_rawptr,extern
from pcc.unsafe import stack_alloc,store_i8,load_i8,load_i64,null
decode=extern("pcc_gui_png_decode",(c_rawptr,c_int64,c_rawptr,c_rawptr,c_int64),c_int32)
def main()->int:
    data=stack_alloc({len(png)})
{stores}
    header=stack_alloc(32)
    pixels=stack_alloc(4)
    if decode(data,{len(png)},header,null(),0)!=-6 or load_i64(header,24)!=4:
        return 1
    if decode(data,{len(png)},header,pixels,4)!=0:
        return 2
    if load_i64(header,0)!=1 or load_i64(header,8)!=1 or load_i64(header,16)!=4:
        return 3
    if (load_i8(pixels,0)&255)!=255 or load_i8(pixels,1)!=0 or load_i8(pixels,2)!=0 or (load_i8(pixels,3)&255)!=255:
        return 4
    print("PCC_GUI_NATIVE_IMAGE_OK")
    return 0
main()
'''
    output=_compile_run(tmp_path,pcc_py_runtime_archive,'image_host_compiled',source,
                        compiler=[sys.executable,'-m','pcc'])
    assert 'PCC_GUI_NATIVE_IMAGE_OK' in output

def test_host_pcc_builds_native_ipc_with_the_same_owned_runtime(tmp_path, pcc_py_runtime_archive):
    """Explicit host-compiler lane; this does not certify installed PCC1."""
    source=(Path(__file__).parent/'fixtures/ipc_roundtrip.py').read_text()
    output=_compile_run(tmp_path,pcc_py_runtime_archive,'ipc_host_compiled',source,
                        compiler=[sys.executable,'-m','pcc'])
    assert 'PCC_GUI_NATIVE_IPC_OK' in output
