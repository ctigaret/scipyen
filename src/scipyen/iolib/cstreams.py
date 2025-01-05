# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Original "gist" by cizixs 
https://gist.github.com/cizixs/6211652
"""
import io, os, struct, sys, typing

class IOManipulator(object):
    def __init__(self, function=None):
        self.function = function
    def do(self, output):
        self.function(output)

def do_endl(stream):
    if isinstance(stream.output, io.TextIOBase):
        stream.output.write('\n')
    else:
        stream.output.write(struct.pack("=x"))
    stream.output.flush()

endl = IOManipulator(do_endl)

class OStream(object):
    def __init__(self, output=None):
        if output is None:
            import sys
            output = sys.stdout
            self.output = output
            self.format = '%s'
        else:
            self.output=output
            if isinstance(output, io.TextIOBase):
                self.format="%s"
            else:
                self.format = None

    def __lshift__(self, thing):
        '''Python will call this function when you use << with left operator being OStream
        '''
        if isinstance(thing, IOManipulator):
            thing.do(self)
        else:
            if isinstance(self.output, io.TextIOBase):
                self.output.write(self.format % thing)
                # self.format = '%s'
            else:
                if isinstance(thing, bytes):
                    self.output.write(thing)
                else:
                    raise TypeError(f"Invalid thing type: {type(thing).__name__}")
        return self
    
def example_main():
    cout = OStream()
    cout << "The average of " << 1 << " and " << 3 << " is " << (1+3)/2 << endl

if __name__ == '__main__':
    example_main()
    
__all__ = ["endl", "OStream"]
