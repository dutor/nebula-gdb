import gdb
import struct

def x(addr, fmt, n = 1):
    inferior = gdb.selected_inferior()
    mview = inferior.read_memory(addr, struct.calcsize(fmt) * n)
    return mview.cast(fmt).tolist()
