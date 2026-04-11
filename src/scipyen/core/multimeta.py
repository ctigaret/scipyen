# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2013 David Deazley and The Authors, Python Cookbook 3rd Edition, O'Reilly <http://oreilly.com/catalog/errata.csp?isbn=9781449340377>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Python Cookbook Chapter 9.20 Implementing Multiple Dispatch with Function Annotations

This file taken from:
https://github.com/dabeaz/python-cookbook/tree/master/src/9/multiple_dispatch_with_function_annotations/example1.py

NOTE: 2025-02-11 22:28:54
as a workaround metaclass conflicts for PyQt5 classes, see

https://www.pythonfixing.com/2022/07/fixed-multiple-inheritance-metaclass.html

and

http://www.phyast.pitt.edu/~micheles/python/metatype.html

See commented-out example in the code file of this module.

"""
# NOTE: 2025-02-11 22:46:31
# ### BEGIN example workaround metaclass conflict in PyQt5/6 (and possibly PySide6?)
# from PyQt5.QtGui import QStandardItem
# from configparser import ConfigParser
# 
# class FinalMeta(type(QStandardItem), type(ConfigParser)):
#     pass
# 
# class FinalClass(ConfigParser, QStandardItem, metaclass=FinalMeta):
#     def __init__(self, param):
#         ConfigParser.__init__(self)
#         QStandardItem.__init__(self)
# ### END   example workaround metaclass conflict in PyQt5/6 (and possibly PySide6?)


import inspect
import types

class MultiMethod:
    '''
    Represents a single multimethod.
    '''
    def __init__(self, name):
        self._methods = {}
        self.__name__ = name

    def register(self, meth):
        '''
        Register a new method as a multimethod
        '''
        sig = inspect.signature(meth)

        # Build a type-signature from the method's annotations
        types = []
        for name, parm in sig.parameters.items():
            if name == 'self': 
                continue
            if parm.annotation is inspect.Parameter.empty:
                raise TypeError(
                    'Argument {} must be annotated with a type'.format(name)
                    )
            if not isinstance(parm.annotation, type):
                raise TypeError(
                    'Argument {} annotation must be a type'.format(name)
                    )
            if parm.default is not inspect.Parameter.empty:
                self._methods[tuple(types)] = meth
            types.append(parm.annotation)

        self._methods[tuple(types)] = meth

    def __call__(self, *args):
        '''
        Call a method based on type signature of the arguments
        '''
        types = tuple(type(arg) for arg in args[1:])
        meth = self._methods.get(types, None)
        if meth:
            return meth(*args)
        else:
            raise TypeError('No matching method for types {}'.format(types))
        
    def __get__(self, instance, cls):
        '''
        Descriptor method needed to make calls work in a class
        '''
        if instance is not None:
            return types.MethodType(self, instance)
        else:
            return self
    
class MultiDict(dict):
    '''
    Special dictionary to build multimethods in a metaclass
    '''
    def __setitem__(self, key, value):
        if key in self:
            # If key already exists, it must be a multimethod or callable
            current_value = self[key]
            if isinstance(current_value, MultiMethod):
                current_value.register(value)
            else:
                mvalue = MultiMethod(key)
                mvalue.register(current_value)
                mvalue.register(value)
                super().__setitem__(key, mvalue)
        else:
            super().__setitem__(key, value)

class MultipleMeta(type):
    '''
    Metaclass that allows multiple dispatch of methods
    BUG: 2025-01-08 13:06:59 FIXME
    Currently does not work well with property getter/setter decorators
    '''
    def __new__(cls, clsname, bases, clsdict):
        return type.__new__(cls, clsname, bases, dict(clsdict))

    @classmethod
    def __prepare__(cls, clsname, bases):
        return MultiDict()
    

class MultipleMetaAdapter(type):
    # NOTE: 2025-02-12 21:37:20
    # not used yet - worth a try
    metadic = {}
    
    @staticmethod
    def _generatemetaclass(bases,metas,priority):
        trivial=lambda m: sum([issubclass(M,m) for M in metas], m is type)
        # hackish!! m is trivial if it is 'type' or, in the case explicit
        # metaclasses are given, if it is a superclass of at least one of them
        metabs=tuple([mb for mb in map(type,bases) if not trivial(mb)])
        metabases=(metabs+metas, metas+metabs)[priority]
        if metabases in metadic: # already generated metaclass
            return metadic[metabases]
        elif not metabases: # trivial metabase
            meta=type 
        elif len(metabases)==1: # single metabase
            meta=metabases[0]
        else: # multiple metabases
            metaname="_"+''.join([m.__name__ for m in metabases])
            meta=makecls()(metaname,metabases,{})
        return metadic.setdefault(metabases,meta)

    @staticmethod
    def makecls(*metas,**options):
        """Class factory avoiding metatype conflicts. The invocation syntax is
        makecls(M1,M2,..,priority=1)(name,bases,dic). If the base classes have 
        metaclasses conflicting within themselves or with the given metaclasses, 
        it automatically generates a compatible metaclass and instantiate it. 
        If priority is True, the given metaclasses have priority over the 
        bases' metaclasses"""

        priority=options.get('priority',False) # default, no priority
        return lambda n,b,d: _generatemetaclass(b,metas,priority)(n,b,d)
    

# ### BEGIN multiple dispatch examples - ATTENTION Do NOT delete
# # Some example classes that use multiple dispatch
# class Spam(metaclass=MultipleMeta):
#     def bar(self, x:int, y:int):
#         print('Bar 1:', x, y)
#     def bar(self, s:str, n:int = 0):
#         print('Bar 2:', s, n)
# 
# # Example: overloaded __init__
# import time
# class Date(metaclass=MultipleMeta):
#     def __init__(self, year: int, month:int, day:int):
#         self.year = year
#         self.month = month
#         self.day = day
# 
#     def __init__(self):
#         t = time.localtime()
#         self.__init__(t.tm_year, t.tm_mon, t.tm_mday)
# 
# if __name__ == '__main__':
#     s = Spam()
#     s.bar(2, 3)
#     s.bar('hello')
#     s.bar('hello', 5)
#     try:
#         s.bar(2, 'hello')
#     except TypeError as e:
#         print(e)
# 
#     # Overloaded __init__
#     d = Date(2012, 12, 21)
#     print(d.year, d.month, d.day)
#     # Get today's date
#     e = Date()
#     print(e.year, e.month, e.day)
#
# ### END   multiple dispatch examples - ATTENTION Do NOT delete
