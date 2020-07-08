# -*- coding: utf-8 -*-
'''
Decorators, context managers, and helper functions & classes for programming
'''

#print("{}: {}".format(__file__, __name__))

import traceback, re, io, sys, enum, itertools, time, typing, types, warnings, inspect
from functools import singledispatch, update_wrapper, wraps
from contextlib import contextmanager

#### BEGIN Decorators

#NOTE: 2017-11-22 22:00:40 FIXME TODO
# for pyqtSlots, place this AFTER the @pyqtSlot decorator
def safeWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
            traceback.print_exc()
            
    return wrapper

def safeGUIWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Critical)
            msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            
    return wrapper

def timefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        r = func(*args, **kwargs)
        end = time.perf_counter()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

def processtimefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.process_time()
        r = func(*args, **kwargs)
        end = time.process_time()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

def strfy(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if inspect.isfunction(f) or inspect.isbuiltin(f):
            # function, builtin function, method
            fname = f.__name__
            
            if fname == "<lambda>":
                fname="lambda"
            
        elif inspect.ismethod(f):
            if inspect.isclass(f.__self__):
                # this is a class method - OK
                fname = "{}.{}".format(f.__self.__name, f.__name__)
                
            else:
                raise TypeError("Instance methods are not supported")
            
        elif inspect.isclass(f) and hasattr(f, "__call__"):
            # callable class (not object) - may also be a builtin, such as 'type', 'str'
            if hasattr(f, "__name__"):
                fname = f.__name__
                
            else:
                fname = f.__class__.__name__
                
        else:
            raise TypeError("Expecting a function, classmethod, or callable class; got %s instead" % type(f).__name__)
        
        sig = inspect.signature(f)
        
        return "".join([fname, str(sig)])
        
    return wrapper

#### END Decorators

#### BEGIN Context managers

@contextmanager
def timeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print("{} : {}".format(label, end-start))

@contextmanager
def processtimeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.process_time()
    try:
        yield
    finally:
        end = time.process_time()
        print("{} : {}".format(label, end-start))

#### END Context managers

def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
    log = file if hasattr(file, "write") else sys.stderr
    traceback.print_stack(file=log)
    log.write(warnings.formatwarning(message, category, filename, lineno, line))
    
#"def" instanceMethodSingleDispatch(func):
    #"""
        #NOTE: 2017-08-11 08:56:01
        #a little trick to use singledispatch as an instancemethod decorator
        #I picked up from below:
        #https://stackoverflow.com/questions/24601722/how-can-i-use-functools-singledispatch-with-instance-methods
    #"""
    #dispatcher = singledispatch(func)
    #def wrapper(*args, **kw):
        #return dispatcher.dispatch(args[1].__class__)(*args, **kw)
    #wrapper.register = dispatcher.register
    ## update_wrapper(wrapper, func)
    ## or better, for the full interface of singledispatch:
    #update_wrapper(wrapper, dispatcher)
    #return wrapper

class Timer(object):
    """Recipe 13.13 "Making a Stopwatch Timer" in Python Cookbook 3rd Ed. 2013
    """
    def __init__(self, func = time.perf_counter):
        self.elapsed = 0.0
        self._func = func
        self._start = None
        
    def start(self):
        if self._start is not None:
            raise RuntimeError("Already started")
        
        self._start = self._func()
        
    def stop(self):
        if self._start is None:
            raise RuntimeError("Not started")
        
        end = self._func()
        
        self.elapsed += end - self._start
        self._start = None
        
    def reset(self):
        self.elapsed = 0.0
        
    @property
    def running(self):
        return self._start is not None
    
    def __enter__(self):
        # for use as context manager
        self.start()
        return self
    
    def __exit__(self):
        # for use as context manager
        self.stop()

