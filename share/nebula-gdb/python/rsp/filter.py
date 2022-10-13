import re
import gdb
from gdb.FrameDecorator import FrameDecorator
import itertools
import rsp
from rsp import *

patterns = []

class PrettyTemplateFilter():
    def __init__(self):
        self.name = 'PrettyTemplate'
        self.enabled = True
        self.priority = 100
        gdb.frame_filters[self.name] = self
        if len(patterns) != 0:
            return
        l = []
        l.append((r'std::__cxx11::basic_string.+?std::allocator<char> >', 'std::string'))
        l.append((r', std::allocator<[^<]+? >', ''))
        for p,s in l:
            patterns.append((re.compile(p), s))


    def filter(self, fi):
        fi = map(PrettyTemplateDecorator, fi)
        return fi

class PrettyTemplateDecorator(FrameDecorator):
    def __init__(self, frame):
        super(PrettyTemplateDecorator, self).__init__(frame)

    def function(self):
        frame = self.inferior_frame()
        name = str(frame.name())
        if name == 'None':
            name = '??'
        for p,s in patterns:
            name = re.sub(p, s, name)
        if frame == gdb.selected_frame():
            name = '\001\033[1m\002' + name + '\001\033[0m\002'
        if frame.type() == gdb.INLINE_FRAME:
            name = name + ' [inlined]'
        return name

PrettyTemplateFilter()
