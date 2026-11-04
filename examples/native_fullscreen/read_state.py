"""Small PCC consumer of an already-acquired fullscreen lease."""
from pcc.extern import c_int64
from pcc_gui.pcc_gui_fullscreen import pcc_gui_fullscreen_live_count
from pcc.unsafe import addr_of


def main() -> int:
    live: c_int64 = 0
    return pcc_gui_fullscreen_live_count(addr_of(live))
