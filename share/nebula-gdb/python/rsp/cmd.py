import re
import gdb
import rsp
from rsp import *

class ReloadCommand(gdb.Command):
    '''Reload the rsp package'''
    def __init__(self):
        super(ReloadCommand, self).__init__('rsp-reload', gdb.COMMAND_USER)

    def invoke(self, args, is_tty):
        rsp.reload(rsp)

ReloadCommand()

def active(invoke):
    def wrapper(*args, **kwargs):
        if not is_active():
            print('No active inferior to debug')
            return
        invoke(*args, **kwargs)

    return wrapper

def catch(invoke):
    def wrapper(*args, **kwargs):
        try:
            invoke(*args, **kwargs)
        except Exception as e:
            print(e)

    return wrapper

class ShowStackCommand(gdb.Command):
    '''Show various info about the current stack'''
    def __init__(self):
        super(ShowStackCommand, self).__init__("show-stack-info", gdb.COMMAND_USER)

    @active
    @catch
    def invoke(self, args, is_tty):
        start, end = stack_range()
        if is_x64():
            top = reg('rsp')
        elif is_arm64():
            top = reg('sp')
        print(f"bottom: {end:#x}, top: {top:#x}, size: {end-start}, usage: {end-top}")

ShowStackCommand()


class ExamineRangeCommand(gdb.Command):
    '''Examine contents in a range of memory area'''
    def __init__(self):
        super(ExamineRangeCommand, self).__init__('xrange', gdb.COMMAND_USER)

    @active
    @catch
    def invoke(self, args, is_tty):
        args = args.split()
        if len(args) != 2:
            print('xrange <start> <end>')
            return
        try:
            start = int(gdb.parse_and_eval(args[0]))
        except:
            print(f"'{args[0]}': cannot be evaluated to a valid address")
            return

        try:
            end = int(gdb.parse_and_eval(args[1]))
        except:
            print(f"'{args[1]}': cannot be evaluated to a valid address")
            return

        start, end = (start & ~0x7), (end & ~0x7)
        if start >= end:
            start, end = end, start
        if end - start < 8:
            return

        if not is_valid_addr(start):
            print('Memory cannot be accessed at 0x%x' % start)
            return

        if not is_valid_addr(end - 1):
            print('Memory cannot be accessed at 0x%x' % (end - 1))
            return

        addrs = x(start, 'Q', (end - start) / 8)
        addrs = [addr for addr in addrs if is_valid_addr(addr)]
        addrs.reverse()
        for addr in addrs:
            out = gdb.execute('info symbol 0x%x' % addr, to_string = True)
            out = out[:-1]
            ok, n = is_str_at_addr(addr)
            if ok:
                tail = ''
                if n > 64:
                    n = 64
                    tail = '...'
                print('0x%x: "%s"' % (addr, ''.join(c.decode() for c in x(addr, 'c', n)) + tail))
            if not 'No symbol' in out:
                try:
                    if not hasattr(gdb, 'symbol_line_pattern'):
                        gdb.symbol_line_pattern = re.compile(r'^([^+]+) \+?( \d+ )?in section .* of (.*)$')
                    pattern = gdb.symbol_line_pattern
                    match = pattern.match(out)
                    func = match.group(1)
                    offset = match.group(2)
                    objfile = match.group(3)
                    if offset is None:
                        print('0x%x: <%s>' % (addr, func))
                    else:
                        print('0x%x: <%s+%d>' % (addr, func, int(offset)))
                except:
                    raise

ExamineRangeCommand()


class ExamineStackCommand(gdb.Command):
    '''Examine contents in the current stack'''
    def __init__(self):
        super(ExamineStackCommand, self).__init__('xstack', gdb.COMMAND_USER)

    @active
    @catch
    def invoke(self, args, is_tty):
        start, end = stack_range()
        if is_x64():
            top = reg('rsp')
        elif is_arm64():
            top = reg('sp')
        bottom = end
        gdb.execute('xrange %d %d' % (top, bottom))

ExamineStackCommand()

class ShowAssemblyTipsCommand(gdb.Command):
    '''Show brief assembly tips of arm or x86'''
    def __init__(self):
        super(ShowAssemblyTipsCommand, self).__init__('show-asm-tips', gdb.COMMAND_USER)

    @catch
    def invoke(self, args, is_tty):
        if args == 'arm':
            self.show_arm_tips()
        elif args == 'x86':
            self.show_x86_tips()

        if is_x64():
            self.show_x86_tips()
        elif is_arm64():
            self.show_arm_tips()

    def show_arm_tips(self):
        tips = '''
REGISTERS                                                   BASIC INSTRUCTIONS
    sp:         stack pointer                                   mov   x0, x1                x0 = x1
    x0-x7:      function arguments                              add   x0, x1, x2            x0 = x1 + x2
    x0:         return value                                    add   x0, x1, #123          x0 = x1 + 123
    x8-x18:     caller-saved                                    add   x0, x1, x2 lsl #3     x0 = x1 + (x2 << 3)
    x8:         return value of non-scalar type                 add   x0, x1, x2 lsl #3     x0 = x1 + (x2 << 3)
    x19-x29:    callee-saved                                    mul   x0, x1, x2            x0 = x1 * x2
    x29:        stack frame pointer                             sdiv  x0, x1, x2            x0 = x1 / x2
    x30:        link register to save return address            udiv  x0, x1, x2            x0 = x1 / x2
    NOTE: w0 is the lower 32 bits of x0                         cmp   x0, x1                x0 - x1
                                                                tst   x0, x1                x0 & x1

MEMORY ACCESS
    ldr   x0, [x1]                  x0 = *x1
    ldr   x0, [x1, x2]              x0 = *(x1 + x2)
    ldr   x0, [x1, #8]              x0 = *(x1 + 8)
    ldr   x0, [x1, x2, lsl #3]      x0 = *(x1 + (x2 << 3))
    ldrb  w0, [x1]                  w0 = *(char*)x1
    str   x0, [x1]                 *x1 = x0
    strb  w0, [x1]                 *(char*)x1 = x0
    stp   x29, x30, [sp, #-16]!    *(sp-16) = x29, *(sp-8) = x30, sp -= 16
    ldp   x29, x30, [sp], #16       x29 = *sp, x30 = *(sp + 8), sp += 16

BRANCH INSTRUCTIONS
    Given `cmp x0, x1'
    bl:                             branch and save return address to x30
    b.eq:                           if x0 == x1
    b.ne:                           if x0 != x1
    b.lt:                           if x0 < x1
    b.le:                           if x0 <= x1
    b.gt:                           if x0 > x1
    b.ge:                           if x0 >= x1
    b.hi:                           if x0 > x1, for unsigned
    b.lo:                           if x0 < x1, for unsigned
    blr x0:                         branch to address in x0
    cbz x0:                         branch if x0 == 0
    cbnz x0:                        branch if x0 != 0

DEMO
class Base {
public:
    Base() {}
    virtual ~Base() {}
    virtual Result get(Parameter param) = 0;
};

class Derived : public Base {
public:
    Derived() {}
    ~Derived() override {}
    Result get(Parameter param) override {
        Result result;
        return result;
    }
};

Result foo() noexcept {
    Base *bptr = new Derived();
    Parameter param;
    auto result = bptr->get(param);
    return result;
}

Dump of assembler code for function foo():
   0x0000aaaaaaaaab7c <+0>:     stp     x29, x30, [sp, #-64]!       // allocate stack space
   0x0000aaaaaaaaab80 <+4>:     mov     x29, sp
   0x0000aaaaaaaaab84 <+8>:     stp     x19, x20, [sp, #16]         // save called-saved registers
   0x0000aaaaaaaaab88 <+12>:    mov     x19, x8         // store address of return value to x19
   0x0000aaaaaaaaab8c <+16>:    mov     x0, #0x8                    // #8 allocate a 8B space for Derived object
   0x0000aaaaaaaaab90 <+20>:    bl      0xaaaaaaaaa9f0 <operator new(unsigned long)@plt>
   0x0000aaaaaaaaab94 <+24>:    mov     x20, x0         // store address of the Derived object to x20
   0x0000aaaaaaaaab98 <+28>:    mov     x0, x20
   0x0000aaaaaaaaab9c <+32>:    bl      0xaaaaaaaaad8c <Derived::Derived()> // default construct
   0x0000aaaaaaaaaba0 <+36>:    str     x20, [sp, #56]  // store address of the Derived object to `bptr'
   0x0000aaaaaaaaaba4 <+40>:    add     x0, sp, #0x28   // default construct `param'
   0x0000aaaaaaaaaba8 <+44>:    bl      0xaaaaaaaaacdc <Parameter::Parameter()>
   0x0000aaaaaaaaabac <+48>:    ldr     x0, [sp, #56]   // load `bptr' to x0
   0x0000aaaaaaaaabb0 <+52>:    ldr     x0, [x0]        // load vptr to x0
   0x0000aaaaaaaaabb4 <+56>:    add     x0, x0, #0x10   // locate entry for virtual method `get' inside the vtbl
   0x0000aaaaaaaaabb8 <+60>:    ldr     x20, [x0]       // load address of `get' to x20
   0x0000aaaaaaaaabbc <+64>:    add     x1, sp, #0x28   // load address of `param' to x1
   0x0000aaaaaaaaabc0 <+68>:    add     x0, sp, #0x30   // load address of `param' of `get' to x0
   0x0000aaaaaaaaabc4 <+72>:    bl      0xaaaaaaaaad04 <Parameter::Parameter(Parameter const&)> // copy construct
   0x0000aaaaaaaaabc8 <+76>:    add     x0, sp, #0x30   // load address of the temporary Parameter to x0
   0x0000aaaaaaaaabcc <+80>:    mov     x8, x19         // use the same address of return value as `get'
   0x0000aaaaaaaaabd0 <+84>:    mov     x1, x0          // load address of the  temporary Parameter to x1
   0x0000aaaaaaaaabd4 <+88>:    ldr     x0, [sp, #56]   // use `bptr' as this
   0x0000aaaaaaaaabd8 <+92>:    blr     x20             // invoke `get'
   0x0000aaaaaaaaabdc <+96>:    add     x0, sp, #0x30   // destruct the temporary Parameter
   0x0000aaaaaaaaabe0 <+100>:   bl      0xaaaaaaaaacf0 <Parameter::~Parameter()>
   0x0000aaaaaaaaabe4 <+104>:   nop
   0x0000aaaaaaaaabe8 <+108>:   add     x0, sp, #0x28   // destruct `param'
   0x0000aaaaaaaaabec <+112>:   bl      0xaaaaaaaaacf0 <Parameter::~Parameter()>
   0x0000aaaaaaaaabf0 <+116>:   nop
   0x0000aaaaaaaaabf4 <+120>:   mov     x0, x19         // load address of return value to x0
   0x0000aaaaaaaaabf8 <+124>:   ldp     x19, x20, [sp, #16]
   0x0000aaaaaaaaabfc <+128>:   ldp     x29, x30, [sp], #64
   0x0000aaaaaaaaac00 <+132>:   ret
Dump of assembler code for function Derived::get(Parameter):
   0x0000aaaaaaaaae14 <+0>:     stp     x29, x30, [sp, #-48]!
   0x0000aaaaaaaaae18 <+4>:     mov     x29, sp
   0x0000aaaaaaaaae1c <+8>:     str     x19, [sp, #16]
   0x0000aaaaaaaaae20 <+12>:    mov     x19, x8
   0x0000aaaaaaaaae24 <+16>:    str     x0, [sp, #40]
   0x0000aaaaaaaaae28 <+20>:    str     x1, [sp, #32]
   0x0000aaaaaaaaae2c <+24>:    mov     x0, x19
   0x0000aaaaaaaaae30 <+28>:    bl      0xaaaaaaaaacb4 <Result::Result()>
   0x0000aaaaaaaaae34 <+32>:    nop
   0x0000aaaaaaaaae38 <+36>:    mov     x0, x19
   0x0000aaaaaaaaae3c <+40>:    ldr     x19, [sp, #16]
   0x0000aaaaaaaaae40 <+44>:    ldp     x29, x30, [sp], #48
   0x0000aaaaaaaaae44 <+48>:    ret
        '''
        print(tips.strip())

    def show_x86_tips(self):
        tips = '''
REGISTERS
    rdi,rsi,rdx,rcx,r8,r9:          function arguments; temporary
    rax:                            return value; temporary
    rdi:                            `this'
    rsp:                            stack pointer
    rbx,rbp,r12-15:                 callee-saved
    xmm0-1:                         pass and return floating function arguments; temporary
    xmm2-7:                         pass floating function arguments; temporary
    xmm8-15:                        temporary
    mmx0-7:                         temporary
    fs:                             thread local storage, referred to as `$fs_base' in GDB
        '''
        print(tips.strip())

ShowAssemblyTipsCommand()


class PrintStdStringCommand(gdb.Command):
    '''Print fields of std::string, useful if no debuginfo'''
    def __init__(self):
        super(PrintStdStringCommand, self).__init__('pstr', gdb.COMMAND_USER)

    @catch
    def invoke(self, args, is_tty):
        args = args.split()
        if len(args) != 1:
            print('pstr <addr>')
            return
        value = gdb.parse_and_eval(args[0])
        tcode = value.type.code
        if tcode == gdb.TYPE_CODE_PTR or tcode == gdb.TYPE_CODE_INT:
            addr = int(value)
        else:
            addr = int(value.address)
        buf, size, cap = x(addr, 'Q', 3)
        sso = buf == addr + 16
        if sso:
            cap = 15
        print(f'cap: {cap}, size: {size}, buf: {buf:#x}, sso: {sso}')

PrintStdStringCommand()


class PrintStdVectorCommand(gdb.Command):
    '''Print fields of std::vector, useful if no debuginfo'''
    def __init__(self):
        super(PrintStdVectorCommand, self).__init__('pvec', gdb.COMMAND_USER)

    @catch
    def invoke(self, args, is_tty):
        args = args.split()
        if len(args) != 1:
            print('pvec <addr>')
            return
        value = gdb.parse_and_eval(args[0])
        tcode = value.type.code
        if tcode == gdb.TYPE_CODE_PTR or tcode == gdb.TYPE_CODE_INT:
            addr = int(value)
        else:
            addr = int(value.address)
        s, e, f = x(addr, 'Q', 3)
        print(f'start: {s:#x}, size: +{e-s}, cap: +{f-s}')

PrintStdVectorCommand()


class PrintStdHashtableCommand(gdb.Command):
    '''Print fields of std::unordered_map/set, useful if no debuginfo'''
    def __init__(self):
        super(PrintStdHashtableCommand, self).__init__('phash-table', gdb.COMMAND_USER)

    @catch
    def invoke(self, args, is_tty):
        args = args.split()
        if len(args) != 1:
            print('phashtable <addr>')
            return
        value = gdb.parse_and_eval(args[0])
        tcode = value.type.code
        if tcode == gdb.TYPE_CODE_PTR or tcode == gdb.TYPE_CODE_INT:
            addr = int(value)
        else:
            addr = int(value.address)
        buckets, nbuckets, _, size = x(addr, 'Q', 4)
        load_factor = x(addr + 32, 'f', 1)[0]
        print(f'buckets: {buckets:#x}, bucket count: {nbuckets}, size: {size}, load factor: {load_factor}')

PrintStdHashtableCommand()


class PrintStdSharedPtrcommand(gdb.Command):
    '''Print fields of std::shared_ptr, useful if no debuginfo'''
    def __init__(self):
        super(PrintStdSharedPtrcommand, self).__init__('pshared-ptr', gdb.COMMAND_USER)

    @catch
    def invoke(self, args, is_tty):
        args = args.split()
        if len(args) != 1:
            print('pshared-ptr <addr>')
            return

        value = gdb.parse_and_eval(args[0])
        tcode = value.type.code
        if tcode == gdb.TYPE_CODE_PTR or tcode == gdb.TYPE_CODE_INT:
            addr = int(value)
        else:
            addr = int(value.address)
        ptr, refptr = x(addr, 'Q', 2)
        use, weak = x(refptr + 8, 'I', 2)
        print(f'get(): {ptr:#x}, use count: {use}, weak count: {weak}')

PrintStdSharedPtrcommand()
