import gdb

def register_nebula_printers(obj):
    from .printers import build_nebula_printers
    gdb.printing.register_pretty_printer(obj, build_nebula_printers())
