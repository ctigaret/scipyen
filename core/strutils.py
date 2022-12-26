"""Various string utilties
"""

from __future__ import print_function
import errno, os
import locale
import sys
import typing
import keyword
import string
import ast
import re as _re
from numbers import (Number, Real,)
import numpy as np
import quantities as pq

import inflect
InflectEngine = inflect.engine()

from PyQt5 import QtCore, QtGui

__translation_table_to_identifier = str.maketrans(dict([(c_, "_") for c_ in string.punctuation + string.whitespace]))

__translation_table_to_R_identifier = str.maketrans(dict([(c_, ".") for c_ in string.punctuation + string.whitespace]))

import errno, os
def is_sequence(s:str):
    possibleSequence = False
    if s.startswith('(') and s.endswith(')'):
        possibleSequence = True
        seqStart = '('
        seqEnd = ')'
        
    elif s.startswith('[') and s.endswith(']'):
        possibleSequence = True
        seqStart = '['
        seqEnd = ']'
        
    if possibleSequence:
        ss = s[1:-1].replace(" ", "")
        if ',' in ss:
            if len(ss.split('.')):
                return True
            
    return False
            
        
def str2sequence(s:str):
    possibleSequence = False
    
    if s.startswith('(') and s.endswith(')'):
        possibleSequence = True
        seqStart = '('
        seqEnd = ')'
        
    elif s.startswith('[') and s.endswith(']'):
        possibleSequence = True
        seqStart = '['
        seqEnd = ']'
        
    if possibleSequence:
        ss = s[1:-1].replace(" ", "")
        delim = None
        if ',' in ss:
            delim = ','
        elif ';' in ss:
            delim = ';'
        else:
            return s
        
        if delim is not None:
            if seqStart == '(' and seqEnd == ')':
                return tuple(ss.split(delim))
            else:
                return ss.split # a list
        else:
            return s
        
    return s
            
def is_path(s:str):
    return any(c in s for c in (os.sep, os.pathsep, ";", "\\"))
    
def str2range(s):
    parts = list(int(s_) for s_ in s.split(":"))
    if len(parts) <= 3:
        return range(*parts)
    else:
        return range(*parts[0:3])
    
def is_pathname_valid(pathname: str):
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    
    See:
    https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta/34102855#34102855
    '''
    # Sadly, Python fails to provide the following magic number for us.
    #Windows-specific error code indicating an invalid pathname.

    #See Also
    #----------
    #https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
        #Official listing of all such codes.
    ERROR_INVALID_NAME = 123
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)   # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError as exc:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?

def get_int_sfx(s, sep = "_"):
    """Parses an integral suffix from the string.
    
    The suffix needs to be delimited by the sep string.
    
    Returns the string base and the integer value as given by the literal suffix.
    
    If a literal suffix is absent, the value is None
    
    e.g.:
    
    get_int_sfx("some_name") -> ("some_name", None)
    
    but:
    
    get_int_sfx("some_name_0") -> ("some_name", 0)
    
    whereas:
    
    get_int_sfx("some_name_1") -> ("some_name", 1)
    
    
    """
    parts = s.split(sep)
    
    if len(parts) <= 1:
        return s, None
        #return s, 0
    
    sfx = parts[-1]
    base = sep.join(parts[0:-1])
    
    try:
        sfx = int(sfx)
    except:
        sfx = None
        #sfx = 0
        
    return base, sfx
    
def str2symbol(s):
    """Returns a string that can be used as valid Python symbol (a.k.a variable name).
    
    If argument can already be used as a symbol ('s.isidentifier() is True') 
    returns the argument unchanged.
    
    Otherwise:
    * replace any punctuation & white spaces with "_"
    
    * if s is a Python keyword or does not beign with a letter or underscore, 
        prepends "data_" and returns it
    
    """
    if not isinstance(s, str):
        raise TypeError("Expecting a str; got %s instead" % type(s).__name__)
    
    if s.isidentifier():
        return s
    
    if keyword.iskeyword(s):
        s = "data_"+s
    
    # replace any punctuation & white spaces with "_"
    #print("str2symbol: ", s)
    s = _re.sub("^(?=\d)","data_", _re.sub("\W", "_", _re.sub("\s", "_", s)))
    # s = s.translate(__translation_table_to_identifier)
    
    # do some grooming
    while ("__" in s):
        s = s.replace("__", "_")
        
    if s.endswith("_"):
        s = s[0:-1]
    
    # then check if all is digits
    
    # if len(s) and not s[0].isalpha():
    #     s = "data_"+s
        
    return s

def strcat(a,b):
    """Just a convenience function for ''.join((a,b))
    """
    return ''.join((a,b))

def str2R(s):
    if not isinstance(s, str):
        raise TypeError("Expecting a str; got %s instead" % type(s).__name__)
    
    if keyword.iskeyword(s):
        s = "data."+s
    
    s = _re.sub("^(?=\d)","data.", _re.sub("\W", ".", _re.sub("\s", ".", arg)))
    # s = s.translate(__translation_table_to_R_identifier)
    while (".." in s):
        s = s.replace("..", ".")
        
    if s.endswith("."):
        s = s[0:-1]

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
        
def numbers2str(value:typing.Optional[typing.Union[Number, np.ndarray, tuple, list]], precision:int=5, format:str="g", show_units=False):
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
        
    return txt

def str2float(s):
    if not isinstance(s, str):
        return np.nan
    
    try:
        ret = eval(s)
        
    except:
        ret = np.nan
    
    return ret

def isnumber(s):
    """Returns True if string s can be evalated to a numbers.Number
    
    Strings of the form [-/+]x.y[e][-/+]z return True.
    
    """
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    
    try:
        v = eval(s)
        if isinstance(v, Number):
            return True
        
    except:
        return False
    
    # ### BEGIN fool around, do NOT delete
#     # split the string in parts separated by the current locale decimal point,
#     # or by "e" (scientific notation)
#     
#     # in scientific notation a mantissa can have a decimal point
#     
#     ss = s.split("e")
#     
#     if len(ss) > 2:
#         return False
#     
#     ss_ = ss[0].split(locale.localeconv()["decimal_point"])
#     if len(ss_) > 2:
#         return False
#     
#     print(f"ss_: {ss_}")
#     ss_.extend(ss[1:])
#     print(f"extended ss_: {ss_}")
#     
#     if ss_[0].startswith('-') or ss_[0].startswith('+'):
#         ss_[0] = ss_[0][1:]
#     
#     if ss_[-1].startswith('-') or ss_[-1].startswith('+'):
#         ss_[-1] = ss_[-1][1:]
#         
#     if ss_[-1].endswith('j'):
#         ss_[-1] - ss_[-1][0:-1]
#      
#     print(f"ss_: {ss_} w/o signs")
#     test = "".join(ss_)
#     print(f"test: {test}")
#     
#     return test.isnumeric()
    # ### END fool around, do NOT delete

