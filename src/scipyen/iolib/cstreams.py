# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Original "gist" by cizixs 
https://gist.github.com/cizixs/6211652
"""
import ctypes, io, os, struct, sys, typing
import functools
from functools import singledispatch
import qtpy
qtpy.API = os.environ["QT_API"]
if os.environ["QT_API"] == "pyside6":
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    from PySide6.QtCore import Signal, Slot, Property
else:
    from qtpy import QtCore, QtGui, QtWidgets, QtSvg
    from qtpy.QtCore import Signal, Slot, Property


class IOManipulator(object):
    def __init__(self, function=None):
        self.function = function
    def do(self, output):
        self.function(output)

def do_endl(stream):
    if isinstance(stream.output, io.TextIOBase):
        stream.output.write('\n')
        stream.output.flush()
    elif isinstance(stream.output, QtCore.QDataStream):
        ss = struct.pack("=x")
        stream.output.writeBytes(ss, len(ss))
    elif isinstance(stream.output, io.IOBase):
        stream.output.write(struct.pack("=x"))
        stream.output.flush()
    else:
        raise TypeError(f"Invalid output stream type: {type(stream.output).__name__}")

endl = IOManipulator(do_endl)

@singledispatch
def pack(obj, format:typing.Optional[str]=None):
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@pack.register(int)
def _(obj:int, format:typing.Optional[str]=None):
    if format is None:
        format = "=i"
    return struct.pack(format, obj)
    
@pack.register(float)
def _(obj:float, format:typing.Optional[str]=None):
    if format is None:
        format = "=f"
    return struct.pack(format, obj)

@pack.register(str)
def _(obj:str, format:typing.Optional[str]=None):
    bb = bytes(obj, "utf-8")
    if format is None:
        format = f"={len(bb)}s"
    return struct.pack(format, bb)

class OStream(object):
    def __init__(self, output:typing.Optional[typing.Union[io.IOBase, QtCore.QDataStream]]=None):
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
            elif isinstance(self.output, QtCore.QDataStream):
                # NOTE: 2025-01-05 14:52:34
                # QtCore.QDataStream supports the ">>" and "<<" operators straight away
                # but only with QtCore.QByteArray data
                # WARNING: this NOT exhaustive !!!
                if isinstance(thing, bytes):
                    self.output << thing
                else:
                    if isinstance(thing, bool):
                        f = self.output.writeBool
                    elif isinstance(thing, int):
                        f = self.output.writeInt
                    elif isinstance(thing, str):
                        f = self.output.writeQString
                    elif isinstance(thing, bytes):
                        f = self.output.writeBytes
                    elif isinstance(thing, float):
                        f = self.output.writeFloat
                    elif isinstance(thing, typing.Iterable):
                        if isinstance(thing, typing.Sequence):
                            if all(isinstance(v, str) for v in thing):
                                f = self.output.writeQStringList
                            else:
                                f = self.output.writeQVariantList

                        elif isinstance(thing, typing.Mapping):
                            if all(isinstance(k, str) for k in thing.keys):
                                f = self.output.writeQVariantMap
                            else:
                                f = self.output.writeQVariantHash
                        else:
                            f = self.output.writeQVariant
                    else:
                        f = self.output.writeQVariant

                    f(thing)

            else:
                if isinstance(thing, bytes):
                    self.output.write(thing)
                else:
                    bthing = pack(thing)
                    self.output.write(bthing)

        return self
    
def example_main():
    cout = OStream()
    cout << "The average of " << 1 << " and " << 3 << " is " << (1+3)/2 << endl

if __name__ == '__main__':
    example_main()
    
__all__ = ["endl", "OStream"]
