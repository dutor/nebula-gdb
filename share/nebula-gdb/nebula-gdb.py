import os

# Apply basic GDB settings
basics = [
    'set print demangle on',
    'set print asm-demangle on',
    'set print pretty on',
    'set listsize 40',
    'set confirm off',
    'set pagination off',
    'set verbose off',
    'set python print-stack full',
    'set history save on',
    'set history filename ' + os.environ['HOME'] + '/.gdb_history',
]

for cmd in basics:
    gdb.execute(cmd)

# Add to Python module path
module_dir = os.path.dirname(os.path.realpath(__file__)) + '/python'
if not module_dir in sys.path:
    sys.path.insert(0, module_dir)

# Install hook on object loading
def new_objfile_handler(ev):
    try:
        if gdb.lookup_type('nebula') == None:
            return

        if not 'libstdcxx.v6' in sys.modules:
            from libstdcxx.v6 import register_libstdcxx_printers
            register_libstdcxx_printers(gdb.current_progspace())

        if not 'nebula.v3' in sys.modules:
            from nebula.v3 import register_nebula_printers
            register_nebula_printers(gdb.current_progspace())
    except:
        pass

gdb.events.new_objfile.connect(new_objfile_handler)

import rsp
import rsp.cmd
import rsp.mem as mem
