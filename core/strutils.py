"""Various string utilties
"""

from __future__ import print_function

import sys
import typing
import keyword
import string
from numbers import (Number, Real,)
import numpy as np
import quantities as pq

from PyQt5 import QtCore, QtGui

__translation_table_to_identifier = str.maketrans(dict([(c_, "_") for c_ in string.punctuation + string.whitespace]))

__translation_table_to_R_identifier = str.maketrans(dict([(c_, ".") for c_ in string.punctuation + string.whitespace]))

def str2symbol(s):
    """Returns a string that can be used as valid Python source code symbol.
    
    If argument can already be sued as a symbol ('s.isidentifier() is True') 
    returns the argument unchanged.
    
    Otherwise:
    * replace any punctuation & white spaces with "_"
    
    * if s is a Python keyword or does not beign with a letter or underscore, 
        prepends "data_" and returns it
    
    """
    if not isinstance(s, str):
        raise TypeError("Expecting a str; got %s instead" % type(s).__name__)
    
    if keyword.iskeyword(s):
        s = "data_"+s
    
    if s.isidentifier():
        return s
    
    # replace any punctuation & white spaces with "_"
    #print("str2symbol: ", s)
    
    s = s.translate(__translation_table_to_identifier)
    
    # then check if all is digits
    
    if len(s) and not s[0].isalpha():
        s = "data_"+s
        
    return s

def strcat(a,b):
    """Just a convenience function for ''.join((a,b))
    """
    return ''.join((a,b))

def str2R(s):
    if not isinstance(s, str):
        raise TypeError("Expecting a str; got %s instead" % type(s).__name__)
    
    s = s.translate(__translation_table_to_R_identifier)

    return s
    
class QNameValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
    def validate(self, value, pos):
        if len(value.strip()) == 0:
            return QtGui.QValidator.Intermediate
            
        if keyword.iskeyword(value[0:pos]):
            return QtGui.QValidator.Intermediate
        
        elif value[0:pos].isidentifier():
            return QtGui.QValidator.Acceptable
        
        else:
            return QtGui.QValidator.Intermediate
        
    def fixup(self, value):
        return str2symbol(value)
            

class QRNameValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
    def validate(self, value, pos):
        if len(value.strip()) == 0:
            return QtGui.QValidator.Intermediate
            
        if not value[0].isalpha():
            return QtGui.QValidator.Intermediate
        
        else:
            if any([c in string.punctuation + string.whitespace for c in value[0:pos]]):
                return QtGui.QValidator.Intermediate
            
            else:
                return QtGui.QValidator.Acceptable
        
        
    def fixup(self, value):
        return str2R(value)
        
def quantity2str(x, precision = 2, format="f"):
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("Expecting a python Quantity or UnitQuantity; got %s instead" % type(x).__name__)
    
    if x.magnitude.flatten().size != 1:
        raise TypeError("Expecting a scalar quantity; got a quantity of size %d instead" % x.magnitude.flatten().size)
    
    if not isinstance(precision, int):
        raise TypeError("precision expected to be an int; got %s instead" % type(precision).__name__)
    
    if precision <= 0:
        raise ValueError("precision must be strictly positive; got %d instead" % precision)
    
    mag_format = "%d" % precision
    
    fmt = "%." + mag_format + format
    
    return " ".join([fmt % x.magnitude, x.units.dimensionality.string])

def numbers2str(value:typing.Optional[typing.Union[Number, np.ndarray, tuple, list]], 
                precision:int=5, format:str="g", show_units=False) -> str:
    """Generates a string representation of numeric data in base 10.
    Parameters:
    ----------
    value: numpy array, scalar, or sequence of scalars = base 10 numeric data
    precision:int; optional (default is 5); the precision (number of decimals)
    format:str (optional default is '%f') printf-style format string, for example:
        %d = integer data (ignores precision)
        %f = floating point (takes precision into account)
        
        For details see https://docs.python.org/3/library/stdtypes.html#old-string-formatting
        
    show_units:bool (optional default is False)
        If True, include units in the text representation of python quantity
        values.
    
    """
    if value is None:
        return ""
    # TODO 2020-12-28 11:41:33
    # convert for new formatting specs (using str.format() and format string syntax)
    if isinstance(value, np.ndarray):
        val = value.flatten()
        
    elif isinstance(value, Number):
        val = np.array([value]).flatten()
        
    elif isinstance(value, (tuple, list)) and all([isinstance(v, Number) for v in value]):
        val = value
        
    else:
        raise TypeError("Expecting a scalar, a sequence (tuple, list) of scalars or a numpy array")
        
    mag_format = "%d" % precision
    
    fmt = "%." + mag_format + format
    
    if show_units and all([isinstance(v, pq.Quantity) for v in val]):
        txt = ", ".join([quantity2str(i, precision=precision, format=format) for i in val])
    else:
        txt = ", ".join([fmt % i for i in val])
        
    #if len(val) == 1:
        #if show_units and isinstance(val, pq.Quantity):
            #txt = quantity2str(val[0], precision=precision, format=format)
        #else:
            #txt = fmt % val[0]
        
    #elif len(val) > 1:
        #if show_units and all([isinstance(v, pq.Quantity) for v in val]):
            #txt = ", ".join([quantity2str(i, precision=precision, format=format) for i in val])
        #else:
            #txt = ", ".join([fmt % i for i in val])
        
    #else:
        #txt = ""
        
    return txt
    
def str2float(s):
    if not isinstance(s, str):
        return np.nan
    
    try:
        ret = eval(s)
        
    except:
        ret = np.nan
    
    return ret

