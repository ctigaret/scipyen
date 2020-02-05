"""Various string utilties
"""

from __future__ import print_function

import sys
import keyword
import string
import quantities as pq
import numpy as np

from PyQt5 import QtCore, QtGui

__translation_table_to_identifier = str.maketrans(dict([(c_, "_") for c_ in string.punctuation + string.whitespace]))

__translation_table_to_R_identifier = str.maketrans(dict([(c_, ".") for c_ in string.punctuation + string.whitespace]))

def string_to_valid_identifier(s):
    if not isinstance(s, str):
        raise TypeError("Expecting a str; got %s instead" % type(s).__name__)
    
    if s.isidentifier():
        return s
    
    if keyword.iskeyword(s):
        return "data_" + s
    
    # replace any punctuation & white spaces with "_"
    #print("string_to_valid_identifier: ", s)
    
    s = s.translate(__translation_table_to_identifier)
    
    # then check if all is digits
    
    if len(s) and not s[0].isalpha():
        s = "data_"+s
        
    return s

def strcat(a,b):
    return ''.join((a,b))

def string_to_R_identifier(s):
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
        return string_to_valid_identifier(value)
            

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
        return string_to_R_identifier(value)
        
def print_scalar_quantity(x, precision = 2):
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("Expecting a python Quantity or UnitQuantity; got %s instead" % type(x).__name__)
    
    if x.magnitude.flatten().size != 1:
        raise TypeError("Expecting a scalar quantity; got a quantity of size %d instead" % x.magnitude.flatten().size)
    
    if not isinstance(precision, int):
        raise TypeError("precision expected to be an int; got %s instead" % type(precision).__name__)
    
    if precision <= 0:
        raise ValueError("precision must be strictly positive; got %d instead" % precision)
    
    #s = "%s" % x
    
    #mag_str, unit_str = s.split()
    
    mag_format = "%d" % precision
    
    fmt = "%." + mag_format + "f"
    
    #print(fmt % eval(mag_str))
    
    return " ".join([fmt % x.magnitude, x.units.dimensionality.string])
    
    
def string_to_float(s):
    if not isinstance(s, str):
        return np.nan
    
    try:
        ret = eval(s)
        
    except:
        ret = np.nan
    
    return ret

