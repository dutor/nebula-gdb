import os
import sys
import gdb
import struct
import resource

if sys.version_info[0] < 3:
    pass
elif sys.version_info[0] == 3 and sys.version_info[1] <= 4:
    from imp import reload
else:
    from importlib import reload


gdb.mmaps = []

# gdb a.out
def has_prog():
    return gdb.selected_inferior().progspace.filename != None

# gdb a.out and run
# gdb a.out core.PID
def is_active():
    return gdb.selected_inferior().pid != 0

# gdb a.out core.PID
def is_exited():
    if not is_active():
        return False

    sig = gdb.parse_and_eval('$_exitsignal')
    if sig.type.code == gdb.TYPE_CODE_INT:
        return True

    return False

# gdb a.out and run
def is_running():
    return is_active() and not is_exited()

def x(addr, fmt, n = 1):
    try:
        inferior = gdb.selected_inferior()
        mview = inferior.read_memory(addr, struct.calcsize(fmt) * n)
        return mview.cast(fmt).tolist()
    except:
        raise ValueError("Failed to read %d elements from 0x%x in '%s' format" % (n, addr, fmt))

def reg(regname):
    try:
        v = gdb.selected_frame().read_register(regname)
        return int(v)
    except:
        raise ValueError(f'Failed to read register ${regname}')

def tid():
    if is_x64():
        return x(reg('fs_base') + 720, 'I')[0]
    elif is_arm64() and is_running():
        return x(int(gdb.parse_and_eval('pthread_self()')) + 208, 'I')[0]
    else:
        raise ValueError('Cannot retrieve thread id')

def pid():
    return gdb.selected_inferior().pid

def is_main_thread():
    return tid() == pid()

def is_x64():
    return 'x86-64' in gdb.selected_inferior().architecture().name()

def is_arm64():
    return 'aarch64' in gdb.selected_inferior().architecture().name()

def arch():
    if is_x64():
        return 'x86_64'
    elif is_arm64():
        return 'aarch64'
    else:
        return 'unknown'

def stack_range():
    if not is_main_thread():
        try:
            if is_x64():
                base, size, guard_size = x(reg('fs_base') + 1680, 'Q', 3)
                bottom = base + size
                base = base + guard_size
                return base, bottom
            elif is_arm64():
                base, size, guard_size = x(int(gdb.parse_and_eval('pthread_self()')) + 1168, 'Q', 3)
                bottom = base + size
                base = base + guard_size
                return base, bottom
            else:
                raise ValueError('Cannot retrieve stack range')
        except:
            raise ValueError('Cannot retrieve stack range')

    try:
        sym = gdb.lookup_global_symbol('__libc_stack_end')
        bottom = int(sym.value())
        bottom = (bottom + 0x1000) & ~0xfff
        base = bottom - resource.getrlimit(resource.RLIMIT_STACK)[0]
        return base, bottom
    except:
        raise ValueError('Cannot retrieve stack range')


def __load_from_core():
    lines = gdb.execute('maintenance info sections', to_string = True).splitlines()
    skip = True
    skip_header = 2
    for line in lines:
        if 'Core file:' in line:
            skip_header = 1
            continue
        if skip_header == 1:
            skip_header = 0
            skip = False
            continue
        if skip:
            continue
        if not 'LOAD' in line:
            continue
        fields = line.strip().split()
        b, e = fields[1].split('->')
        b, e = int(b, 16), int(e, 16)
        gdb.mmaps.append((b, e))


def __load_from_proc():
    pid = gdb.selected_inferior().pid
    lines = os.popen('cat /proc/%d/maps' % pid).read().splitlines()
    lines = [ line.strip().split(None, 5) for line in lines ]
    for records in lines:
        b, e = records[0].split('-')
        b, e = int(b, 16), int(e, 16)
        gdb.mmaps.append((b, e))

def load_memory_space():
    if len(gdb.mmaps) != 0:
        return

    if is_running():
        __load_from_proc()
    else:
        __load_from_core()


def is_valid_addr(addr):
    if len(gdb.mmaps) == 0:
        load_memory_space()
    for b, e in gdb.mmaps:
        if addr >=b and addr < e:
            return True
    return False

def is_str_at_addr(addr):
    s = addr
    n = 0
    while True:
        if not is_valid_addr(s):
            break
        c = x(s, 'c')[0]
        if ord(c) < 0x21 or ord(c) > 0x7e:
            break
        n = n + 1
        s = s + 1
    return n > 3, n


if 'rsp.cmd' in sys.modules:
    reload(rsp.cmd)
else:
    import rsp.cmd
