import gdb

class NebulaPrinter:
    def get_from_unique_ptr(self, ptr):
        return ptr['_M_t']['_M_t']['_M_head_impl']
    def deref_from_unique_ptr(self, ptr):
        pointer = self.get_from_unique_ptr(ptr)
        return pointer.dereference()

class StatusPrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        base_ptr = self.get_from_unique_ptr(self.value['state_'])
        if base_ptr == 0:
            return "OK"
        size_ptr = base_ptr.cast(gdb.lookup_type('uint16_t').pointer())
        code_ptr = (base_ptr + 2).cast(gdb.lookup_type('nebula::Status::Code').pointer())
        msg_ptr = (base_ptr + 4).cast(gdb.lookup_type('char').pointer())
        result = "Status = {\n  code = %s,\n  msg  = \"%s\"\n}" % (str(code_ptr.dereference()), msg_ptr.string(length = size_ptr.dereference()))
        return result;

class StatusOrPrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        state = self.value['state_']
        if state == 0:
            return "void"
        if state == 1:
            return str(self.value['variant_']['status_'])
        if state == 2:
            return str(self.value['variant_']['value_'])

class NullPrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        if self.value == 0:
            return "kNullValue"
        if self.value == 1:
            return "kNullNaN"
        if self.value == 2:
            return "kNullBadData"
        if self.value == 3:
            return "kNullBadType"
        if self.value == 4:
            return "kNullOverflow"
        if self.value == 5:
            return "kNullUnknownProp"
        if self.value == 6:
            return "kNullDivByZero"
        if self.value == 7:
            return "kNullOutOfRange"
        return "unknown"

class DatePrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        v = self.value
        return "%04d-%02d-%02d" % (v['year'], v['month'], v['day'])

class TimePrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        v = self.value
        return "%02d:%02d:%02d.%06d" % (v['hour'], v['minute'], v['sec'], v['microsec'])

class DateTimePrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        v = self.value
        return "%04d-%02d-%02d %02d:%02d:%02d.%06d" % (v['year'], v['month'], v['day'], v['hour'], v['minute'], v['sec'], v['microsec'])

class ValuePrinter(NebulaPrinter):
    def __init__(self, value):
        self.value = value

    def to_string(self):
        type = self.value['type_']
        if type == 1:
            return "kEmpty"
        if type == (1<<1):
            return str(self.value['value_']['bVal'])
        if type == (1<<2):
            return str(self.value['value_']['iVal'])
        if type == (1<<3):
            return str(self.value['value_']['fVal'])
        if type == (1<<4):
            return str(self.deref_from_unique_ptr(self.value['value_']['sVal']))
        if type == (1<<5):
            return str(self.value['value_']['dVal'])
        if type == (1<<6):
            return str(self.value['value_']['tVal'])
        if type == (1<<7):
            return str(self.value['value_']['dtVal'])
        if type == (1<<8):
            return str(self.deref_from_unique_ptr(self.value['value_']['vVal']))
        if type == (1<<9):
            return str(self.deref_from_unique_ptr(self.value['value_']['eVal']))
        if type == (1<<10):
            return str(self.deref_from_unique_ptr(self.value['value_']['pVal']))
        if type == (1<<11):
            return str(self.deref_from_unique_ptr(self.value['value_']['lVal']))
        if type == (1<<12):
            return str(self.deref_from_unique_ptr(self.value['value_']['mVal']))
        if type == (1<<13):
            return str(self.deref_from_unique_ptr(self.value['value_']['uVal']))
        if type == (1<<14):
            return str(self.deref_from_unique_ptr(self.value['value_']['gVal']))
        if type == (1<<15):
            return str(self.deref_from_unique_ptr(self.value['value_']['ggVal']))
        if type == (1<<16):
            return str(self.deref_from_unique_ptr(self.value['value_']['duVal']))
        if type == (1<<63):
            return str(self.value['value_']['nVal'])

def build_nebula_printers():
    pp = gdb.printing.RegexpCollectionPrettyPrinter("nebula-printers")
    pp.add_printer("Status", "^nebula::Status$", StatusPrinter)
    pp.add_printer("StatusOr", "^nebula::StatusOr<.*>$", StatusOrPrinter)
    pp.add_printer("Value", "^nebula::Value$", ValuePrinter)
    pp.add_printer("Null", "^nebula::NullType$", NullPrinter)
    pp.add_printer("Date", "^nebula::Date$", DatePrinter)
    pp.add_printer("Time", "^nebula::Time$", TimePrinter)
    pp.add_printer("DateTime", "^nebula::DateTime$", DateTimePrinter)
    return pp
