# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Various string utilties"""

from __future__ import print_function
import errno, os, io
import locale
import sys
import typing
import keyword
import string
import itertools
import subprocess
import ast
import re as _re
import numbers
import numpy as np
import quantities as pq
import sympy
from sympy import abc as symabc
import PIL
from PIL.Image import Image as PILImage
import drawsvg as dw

import matplotlib.pyplot as plt
from IPython.core.latex_symbols import (latex_symbols, reverse_latex_symbol)
from IPython.display import Image as IPImage
from IPython.core.interactiveshell import is_integer_string

import inflect
# import PIL # to convert latex strings to PIL Image

InflectEngine = inflect.engine()

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True
    

# import qtpy
# qtpy.API = os.environ["QT_API"]
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import QtCore, QtGui
# else:
#     from qtpy import QtCore, QtGui

SUPERSCRIPT_UNICODE = {"-":"⁻",
                    "+":"⁺",
                    "0":"⁰",
                    "1":"¹",
                    "2":"²",
                    "3":"³",
                    "4":"⁴",
                    "5":"⁵",
                    "6":"⁶",
                    "7":"⁷",
                    "8":"⁸",
                    "9":"⁹",
                    "a":"ᵃ", 
                    "b":"ᵇ",
                    "c":"ᶜ",
                    "d":"ᵈ",
                    "e":"ᵉ",
                    "f":"ᶠ",
                    "g":"ᵍ",
                    "h":"ʰ",
                    "i":"ⁱ",
                    "j":"ʲ",
                    "k":"ᵏ",
                    "l":"ˡ",
                    "m":"ᵐ",
                    "n":"ⁿ",
                    "o":"ᵒ",
                    "p":"ᵖ",
                    "r":"ʳ",
                    "s":"ˢ",
                    "t":"ᵗ",
                    "u":"ᵘ",
                    "v":"ᵛ",
                    "w":"ʷ",
                    "x":"ˣ",
                    "y":"ʸ",
                    "z":"ᶻ"}


REGEXP_METACHARACTERS = (
    ".",
    "^",
    "$",
    "*",
    "+",
    "?",
    "{",
    "}",
    "[",
    "]",
    "\\",
    "|",
    "(",
    ")",
)

__translation_table_to_identifier = str.maketrans(
    dict([(c_, "_") for c_ in string.punctuation + string.whitespace])
)

__translation_table_to_R_identifier = str.maketrans(
    dict([(c_, ".") for c_ in string.punctuation + string.whitespace])
)

__output_cache_regexp__ = _re.compile(r"^(_o)|(_+)(h|\d*)$")

__input_cache_regexp__ = _re.compile(r"^_i+(h|\d*)$")

import errno, os

def superscript(s:str)->str:
    if len(s)==1:
        return SUPERSCRIPT_UNICODE.get(s, s)
    
    return "".join(list(map(lambda c: SUPERSCRIPT_UNICODE.get(c,c), s)))
        


def is_sequence(s: str) -> bool:
    r"""Return True if the s is a string representation of a tuple or list"""
    if not isinstance(s, str) or len(s.strip())==0:
        return False

    possibleSequence = False
    if s.startswith("(") and s.endswith(")"):
        possibleSequence = True
        seqStart = "("
        seqEnd = ")"

    elif s.startswith("[") and s.endswith("]"):
        possibleSequence = True
        seqStart = "["
        seqEnd = "]"

    if possibleSequence:
        ss = s[1:-1].replace(" ", "")
        if "," in ss:
            if len(ss.split(".")):
                return True

    return False


def is_cached_output_varname(s: str) -> bool:
    r"""Returns True if s is an IPython cached output variable"""
    return isinstance(s, str) and len(s.strip()) and __output_cache_regexp__.match(s) is not None


def is_cached_input_varname(s: str) -> bool:
    r"""Returns True if s is an IPython cached input variable"""
    return isinstance(s, str) and len(s.strip()) and __input_cache_regexp__.match(s) is not None


def is_glob(s: str) -> bool:
    r"""Returns True if s is a string containing the '*' character"""
    return isinstance(s, str) and len(s.strip()) and any(c in s for c in ("*", "?"))


def is_regexp(s: str) -> bool:
    r"""Returns True if s is a string containing regexp metacharacters.

    The regexp metacharacters are:

    ".", "^", "$", "*", "+", "?", "{", "}", "[", "]", "\\", "|", "(", ")"

    """
    return isinstance(s, str) and len(s.strip()) and any(c in s for c in REGEXP_METACHARACTERS)


def ordinalToLetters(x: int, upperCase: bool = True) -> str:
    r"""Returns a string given an integer ordinal `x`.

    The string is the element with index `x` from the complete ascii sequence¹
    extended with its own cartesian product i.e.:
    'A', 'B', … 'B', 'AA', 'AB', … 'ZZ'


    E.g., 0 → 'A', 30 → 'AE', etc … up to 701 → 'ZZ'

    Returns '?' if x < 0 or x >= 702

    ¹⁾ Either upper (default) or lower case, depending on the value of the
    `upperCase` parameter.

    """
    assert(isinstance(x, int)), f"Expecting an int; got {type(x.__name__)} instead."
    if x < 0:
        return "?"

    l = list(string.ascii_uppercase if upperCase else string.ascii_lowercase)

    ll = list(itertools.product(l, l))

    l.extend(ll)

    if x >= len(l):
        return "?"

    return "".join(list(l[x]))


ordinal2letters = ordinalToLetters


def lettersToOrdinal(x: str) -> int:
    r"""The inverse of ordinalToLetters.
    Case-insensitive.

    Returns -1 if `x` is not of the form '𝒙' or '𝒙𝒚' where 𝒙 and 𝒚 are characters
    in the complete ascii set (upper or lower case), or `x` is not a string.
    """
    if not isinstance(x, str) or len(x.strip()) == 0:
        return -1
    
    x = "".join(tuple(x.lower()))

    l = list(string.ascii_lowercase)

    ll = list(map(lambda k: "".join(k), itertools.product(l, l)))

    l.extend(ll)

    if x not in l:
        return -1

    return l.index(x)


letters2ordinal = lettersToOrdinal


def str2sequence(s: str) -> typing.List[str]:
    r"""Parses the string representation of a sequence into a sequence of strings"""
    if not isinstance(s, str) or len(s.strip()) == 0:
        return list()
    
    possibleSequence = False

    if s.startswith("(") and s.endswith(")"):
        possibleSequence = True
        seqStart = "("
        seqEnd = ")"

    elif s.startswith("[") and s.endswith("]"):
        possibleSequence = True
        seqStart = "["
        seqEnd = "]"

    if possibleSequence:
        ss = s[1:-1].replace(" ", "")
        delim = None
        if "," in ss:
            delim = ","
        elif ";" in ss:
            delim = ";"
        else:
            return s

        if delim is not None:
            if seqStart == "(" and seqEnd == ")":
                return tuple(ss.split(delim))
            else:
                return ss.split  # a list
        else:
            return s

    return s


def is_path(s: str) -> bool:
    r"""Returns True if s is a string representation of a file system path."""
    import pydoc
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    return pydoc.ispath(s)
    # return isinstance(x, str) and x.find(os.sep) >= 0


def str2range(s: str) -> range:
    r"""Parses the string representation of a range into a range object"""
    if not isinstance(s, str) or len(s.strip()) == 0:
        return range(0,0)
    
    parts = list(int(s_) for s_ in s.split(":"))
    if len(parts) <= 3:
        return range(*parts)
    else:
        return range(*parts[0:3])


def is_pathname_valid(pathname: str) -> bool:
    """
    `True` if 'pathname' is a valid pathname regardless of the current OS;
    `False` otherwise.

    See:
    https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta/34102855#34102855
    """
    # Sadly, Python fails to provide the following magic number for us.
    # Windows-specific error code indicating an invalid pathname.

    # See Also
    # ----------
    # https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
    # Official listing of all such codes.
    ERROR_INVALID_NAME = 123
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not (isinstance(pathname, str) and len(pathname.strip) > 0) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = (
            os.environ.get("HOMEDRIVE", "C:")
            if sys.platform.startswith("win32")
            else os.path.sep
        )
        assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

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
                if hasattr(exc, "winerror"):
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


def get_int_sfx(s: str, sep: str = "_", use_re: bool = False) -> typing.Tuple[str, int]:
    r"""Parses an integral suffix from the string.

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
    if not isinstance(s, str) or len(s.strip()) == 0:
        return ("", 0)
    
    if not isinstance(sep, str) or len(sep) == 0 or use_re:
        # regexp = _re.compile(r"^(\D+)*(\d*)$")
        regexp = _re.compile(r"(.*?)??(\d*)$")
        re_match = regexp.match(s)
        if re_match is not None and len(re_match.groups()) > 1:
            try:
                base, sfx = re_match.group(1, 2)
            except:
                base, sfx = s, 0
                # base, sfx = s, None

        else:
            base, sfx = s, 0
            # base, sfx = s, None

    else:
        parts = s.split(sep)

        # if len(parts) <= 1:
        if len(parts) < 2:
            return s, 0
            # return s, None

        sfx = parts[-1]
        base = sep.join(parts[:-1])

    try:
        sfx = int(sfx)
    except:
        # sfx = None
        sfx = 0

    return base, sfx

def counter_suffix(x:str, strings:typing.List[str], sep:str="_", start:int=0, ret:bool=False):
    r"""Appends a counter suffix to x:str if x is found in the list of strings
    
    Parameters:
    ==========
    
    x = str: string to check for existence
    
    strings = sequence of str to check for existence of x
    
    sep: str, default is "_"; suffix separator
    
    start: 
    
    """
    # TODO:
    
    #base = "AboveTheSky"
    #p = re.compile("^%s_{0,1}\d*$" % base)
    #p = re.compile("^%s_{0,1}\d*$" % base)
    #items = list(filter(lambda x: p.match(x), standardQtGradientPresets.keys()))
    #items
    #names = list(standardQtGradientPresets.keys())
    #names.append("AboveTheSky_1")
    #items = list(filter(lambda x: p.match(x), names))
    #items

    if not isinstance(strings, (tuple, list)) and not hasattr(strings, "__iter__"):
        raise TypeError("Second positional parameter was expected to be an iterable; got %s instead" % type(strings).__name__)
    
    if not all ([isinstance(s, str) for s in strings]):
        raise TypeError("Second positional parameter was expected to contain str elements only")
    
    if not isinstance(sep, str):
        raise TypeError("Separator must be a str; got %s instead" % type(sep).__name__)
    
    # if len(sep.strip()) == 0:
    #     raise ValueError("Separator cannot be an empty string")
    
    if not isinstance(start, int):
        raise TypeError(f"'start' expected to be an int; got {type(start).__name__} instead")
    
    if start < 0:
        raise ValueError(f"'start' expected to be a positive int (>= 0); instead, got {start}")
    
    # print(f"counter_suffix: x = {x}, strings = {strings}, start = {start}")
    # print(f"counter_suffix: x = {x}, start = {start}, ret = {ret}")
    
    if len(strings):
        base, cc = get_int_sfx(x, sep=sep)#, bracketed=bracketed)
        
        # print(f"counter_suffix: base = {base}, cc = {cc}")
        
        #p = re.compile(base)
        # if bracketed:
        #     p = re.compile(r"^%s%s{0,1}\(\d*\)$" % (base, sep))
        # else:
        #     p = re.compile(r"^%s%s{0,1}\d*$" % (base, sep))
        p = re.compile(r"^%s%s{0,1}\d*$" % (base, sep))
        
        items = sorted(list(filter(lambda x: p.match(x), strings)))
        
        # print(f"counter_suffix items = {items}")
        newsfx = None
        if len(items):
            full_ndx = list(range(start, len(items)))
            currentsfx = list(x[1] for x in sorted(list(filter(lambda x: isinstance(x[1], int), (map(lambda x: get_int_sfx(x, sep=sep), items)))), key=lambda x: x[1]))
            # currentsfx = list(x[1] for x in sorted(list(filter(lambda x: isinstance(x[1], int), (map(lambda x: get_int_sfx(x, sep=sep, bracketed=bracketed), items)))), key=lambda x: x[1]))
            if len(currentsfx):
                min_current = min(currentsfx)
                max_current = max(currentsfx)
                if  len(full_ndx) == 0:
                    newsfx = 0
                else:
                    if min_current > min(full_ndx):
                        newsfx = min(full_ndx)
                    else:
                        # find out missing indices
                        if len(currentsfx) > 1:
                            dsfx = np.ediff1d(currentsfx)
                            locs = np.where(dsfx > 1)[0]
                            if len(locs):
                                newsfx = locs[0] + 1
                            else:
                                newsfx = currentsfx[-1] + 1
                        else:
                            newsfx = currentsfx[-1] + 1
                        
                    # newsfx = full_ndx[-1]
                    
            else:
                newsfx = start   
                
            # if bracketed:
            #     result = sep.join([base, "(%d)" % newsfx])
            # else:
            #     result = sep.join([base, "%d" % newsfx])
            result = sep.join([base, "%d" % newsfx])
            
            if ret:
                return result, newsfx
            
            return result
        
        else:
            result = x
            if ret:
                return x, None
            return x
        
    if ret:
        return x, None
    return x
                
def similar_strings(a:str, b:str) -> bool:
    r"""Similarity between two strings using difflib.SequenceMatcher./
See also jaccard
"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

def pluralize(s: str, n: int = 1) -> str:
    if not isinstance(s.str):
        return ""
    return InflectEngine.plural(s, n)

def simplify(s: str) -> str:
    r"""Strips spaces at ends and converts inner double spaces to single spaces"""
    if not isinstance(s.str):
        return ""
    s = s.strip()
    while "  " in s:
        s = s.replace("  ", " ")

    return s


def str2symbol(s: str) -> str:
    r"""Returns a string that can be used as valid Python symbol (a.k.a variable name).

    If argument can already be used as a symbol ('s.isidentifier() is True')
    returns the argument unchanged.

    Otherwise:
    * replace any punctuation & white spaces with "_"

    * if s is a Python keyword or does not beign with a letter or underscore,
        prepends "data_" and returns it

    """
    if not isinstance(s, str) or len(s.strip()) == 0:
        return ""
        # raise TypeError("Expecting a str; got %s instead" % type(s).__name__)

    if s.isidentifier():
        return s

    if keyword.iskeyword(s):
        s = "data_" + s

    # replace any punctuation & white spaces with "_"
    # print("str2symbol: ", s)
    s = _re.sub(r"^(?=\d)", "data_", _re.sub(r"\W", "_", _re.sub(r"\s", "_", s)))
    # s = s.translate(__translation_table_to_identifier)

    # do some grooming
    while "__" in s:
        s = s.replace("__", "_")

    if s.endswith("_"):
        s = s[0:-1]

    # then check if all is digits

    # if len(s) and not s[0].isalpha():
    #     s = "data_"+s

    return s

def str2identifier(s: str) -> str:
    r"""Alias to str2symbol"""
    return str2symbol(s)

def strcat(a: str, b: str) -> str:
    r"""Just a convenience function for ''.join((a,b))"""
    if not all([isinstance(s, str) for s in (a,b)]):
        return ""
    
    return "".join((a, b))


def str2R(s: str) -> str:
    r"""Converts the string s into a form usable in R.
    The non-alpha-numeric characters are replaced with dots ('.')
    """
    if not isinstance(s, str) or len(s.strip()) == 0:
        return "data"
        # raise TypeError("Expecting a str; got %s instead" % type(s).__name__)

    if keyword.iskeyword(s):
        s = "data." + s

    s = _re.sub(r"^(?=\d)", "data.", _re.sub(r"\W", ".", _re.sub(r"\s", ".", arg)))
    # s = s.translate(__translation_table_to_R_identifier)
    while ".." in s:
        s = s.replace("..", ".")

    if s.endswith("."):
        s = s[0:-1]

    return s


class QNameValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def validate(self, value: str, pos: int) -> QtGui.QValidator.State:
        if len(value.strip()) == 0:
            return QtGui.QValidator.Intermediate

        if keyword.iskeyword(value[0:pos]):
            return QtGui.QValidator.Intermediate

        elif value[0:pos].isidentifier():
            return QtGui.QValidator.Acceptable

        else:
            return QtGui.QValidator.Intermediate

    def fixup(self, value: str) -> str:
        return str2symbol(value)


class QRNameValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def validate(self, value: str, pos: int) -> QtGui.QValidator.State:
        if len(value.strip()) == 0:
            return QtGui.QValidator.Intermediate

        if not value[0].isalpha():
            return QtGui.QValidator.Intermediate

        else:
            if any([c in string.punctuation + string.whitespace for c in value[0:pos]]):
                return QtGui.QValidator.Intermediate

            else:
                return QtGui.QValidator.Acceptable

    def fixup(self, value: str) -> str:
        return str2R(value)


def make_ordinal(n:int) -> str:
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'

    (Florian Brucker, StackOverflow:
    https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement,

    modifed by me to use superscript unicode characters)
    """
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = "ᵗʰ"
        # suffix = 'th'
    else:
        suffix = ["ᵗʰ", "ˢᵗ", "ⁿᵈ", "ʳᵈ", "ᵗʰ"][min(n % 10, 4)]
        # suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def numbers2str(
    value: typing.Optional[typing.Union[numbers.Number, np.ndarray, tuple, list]],
    precision: int = 5,
    format: str = "g",
    show_units=False,
) -> str:
    r"""Generates a string representation of numeric data in base 10.
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

    from core.scipyen_quantities import quantity2str

    if value is None:
        return ""
    # TODO 2020-12-28 11:41:33
    # convert for new formatting specs (using str.format() and format string syntax)
    if isinstance(value, np.ndarray):
        val = value.flatten()

    elif isinstance(value, numbers.Number):
        val = np.array([value]).flatten()

    elif isinstance(value, (tuple, list)) and all(
        [isinstance(v, numbers.Number) for v in value]
    ):
        val = value

    else:
        raise TypeError(
            "Expecting a scalar, a sequence (tuple, list) of scalars or a numpy array"
        )

    mag_format = "%d" % precision

    fmt = "%." + mag_format + format

    if show_units and all([isinstance(v, pq.Quantity) for v in val]):
        txt = ", ".join(
            [quantity2str(i, precision=precision, format=format) for i in val]
        )
    else:
        txt = ", ".join([fmt % i for i in val])

    return txt


def str2float(s: str) -> float:
    r"""Parse the string s into a float value"""
    if not isinstance(s, str) or len(s.strip()) == 0:
        return np.nan

    try:
        ret = eval(s)

    except:
        ret = np.nan

    return ret

def isnumber(s: str) -> bool:
    r"""Returns True if string s can be evalated to a numbers.Number

    Strings of the form [-/+]x.y[e][-/+]z return True.

    """
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False

    try:
        v = eval(s)
        if isinstance(v, numbers.Number):
            return True

    except:
        return False
    
def is_svg(s:str) -> bool:
    from lxml import etree
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    
    ret = False
    try:
        root = etree.fromstring(s)
        if root.tag == '{http://www.w3.org/2000/svg}svg':
            ret = True
    except:
        ret = False
    if not ret:
        pattern = r'<svg[^>]*>(.*?)<\/svg>'
        matches = _re.findall(pattern, s, _re.DOTALL)
        ret = len(matches)>0 and len(matches[0])>0
        
    return ret
    
def is_html(s:str) -> bool:
    from lxml import html
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    try:
        test = html.fromstring(s)
        return True
    except:
        return False
    # return all(v in s for v in ("<html>", "</html>"))
    
def is_xml(s:str) -> bool:
    from lxml import etree
    try:
        test = etree.fromstring(s)
        return True
    except:
        return False
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    return "<xml" in s
    
def is_latex(s:str) -> bool:
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    pattern = r'(\$\$([^$]*)\$\$|\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}|(\$[^\$]*\$|\\[a-zA-Z]+(?:\{[^\}]*\})?))'
    matches = _re.findall(pattern, s, _re.DOTALL)
    return len(matches)>0 and len(matches[0])>0

def is_ReST(s:str) -> bool:
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    pattern = r"(^[=]+$|^[-]+$|^~+$|^`[^`]+`_|\s*:\w+:\s+.*|^\s*[\*\+\-]\s+.*|^\s*\d+\.\s+.*|^\s*.. .*)"
    matches = _re.findall(pattern, s, _re.MULTILINE)# | _re.DOTALL)
    return len(matches)>0 and len(matches[0])>0
    
def is_markdown(s:str) -> bool:
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    pattern = r"(^#{1,6}\s.*|^\s*[*+-] .*$|^\s*\d+\.\s.*$|!\[.*\]\(.*\)|\[[^\]]+\]\(.*\)|\*\*.*?\*\*|__.*?__|`[^`]+`|~{2}.*?~{2})"
    matches = _re.findall(pattern, s, _re.MULTILINE)# | _re.DOTALL)
    return len(matches)>0 and len(matches[0])>0

def str2svg(s:str, width:int, height:int, /, 
            font_size:int=10, x:int=0, y:int=0, 
            stroke_width:typing.Optional[int]=None,
            stroke:typing.Optional[str]="auto", 
            fill:typing.Optional[str]="auto",
            *args, **kwargs) -> dw.Drawing | None:
    r"""Draws a string as SVG using the ``drawsvg 2.x`` package.
    Returns:
    ========
    A drawsvg.Drawing object.
    
    The SVG string is obtained by calling
    
    ::
        d.as_svg()

    .. note::
    This is NOT to be used to render LaTeX strings as SVG. For this purpose, pass
    a LaTeX expression string to ``render_latex`` with ``out="svg"``.
"""
    from gui.guiutils import isDarkGui
    from gui.scipyen_colormaps import is_color
    from functools import partial
    
    if not isinstance(s, str) or len(s.strip()) == 0:
        return
    # if not isinstance(s, str):
    #     raise TypeError(f"Expecting a string; isnetad got a {type(s).__name))}") 
    # if len(s.strip()) == 0:
    #     return
    
    if not is_color(fill):
        if fill == "auto":
            fill = "#ffffff" if isDarkGui() else "#000000"
        else:
            fill = None
        
    if not is_color(stroke):
        if stroke == "auto":
            stroke = "#ffffff" if isDarkGui() else "#000000"
        else:
            stroke = None
        
    d = dw.Drawing(width, height)
    DrawText = partial(dw.Text, font_size=font_size, x=x, y=y, stroke_width=stroke_width, stroke=stroke, fill = fill, *args, **kwargs)
        
    d.append(DrawText(s))
    
    return d
    
def render_latex(l:str, backend:str="auto", out:str="ipython", 
                darkmode:typing.Optional[bool]=None, wrap:bool=False,
                **kwargs) -> typing.Optional[typing.Union[PIL.Image, QtGui.QPixmap, QtGui.QImage, IPImage, dict]]:
    r"""Graphic rendering of a LaTeX string.

    Positional parameters:
    =======================
    
    :l: The LaTeX string to be rendered. Must contain a math LaTeX environment,
        and assumes the use of the 'amsmath' LaTeX package. The string is NOT
        verified for compliance with LaTeX.
    
    :backend: The backend used to render the LaTeX string 'l'. 
        One of "auto" (default), "dvipng", "matplotlib".
        The "dvipng" backend uses the 'dvipng' utility, which requires a LaTeX
        distribution installed locally.
        The "matplotlib" backend uses the renderer supplied by the 'matplotlib'
        package, which *may* use the 'dvipng' utility from a local LaTeX 
        distribution (if available) or the 'matplotlib.mathtext' module as fallback.
        Both "dvipng" and "matplotlib" backends are involed indirectly, via 
        ``IPython.lib.latextools.latex_to_png(…)`` function.
        The "auto" backend tries "dvipng" first, then "matplotlib", before failing.
    
        .. note::
            This parameter is *ignored* if ``out`` is "svg" (see below)
        
    :out: The kind of output generated. One of "ipython" (default), "bytes", 
        "img", "pix", or "pil".
        * "ipython" generates an IPython Image object that is readily displayed
            by suitable IPython frontends (e.g. qtconsole)
        * "bytes" generates a bytes image data object (PNG)
        * "pix" generates a QtGui.QPixmap object
        * "img" generates a QtGui.QImage object
        * "pil" generates a PIL.Image.Image object
        * "svg" generates an SVG string and *ignores* the ``backend`` parameter; returns a mapping where the SVG output is found under the key ``svg``
    
        .. note::
            The "svg" output requires the package latex2png from https://github.com/Moonbase59/latex2svg.git#
    
    :darkmode: Optional flag indicating if the generated graphic is suitable for a dark 
        (True) or bright (False) background. Except for the "pil" output and the
        "matplotlib" backend, the graphic data has transparent background. This
        flag simply determines the foregreound color (white for ``darkmode=True``,
        black for ``darkmode=False``)   
    
        .. note::
            By default, this is None, in which case the use of dark mode style will be detected
    
    :wrap: Flag passed on to IPython's ``latex_to_png(…)`` function
    
    Var-keyword parameters:
    =======================
    
    :kwargs: passed directly to ``IPython.lib.latextools.latex_to_png(…)`` 
    function
    
    Returns:
    ========
    
    An object of the type determined by the value of the 'out' parameter:
    
    * "ipython" ↦ ``IPython.core.display.Image``
    * "bytes"   ↦ ``bytes`` (PNG data)
    * "pix"     ↦ ``QtGui.QPixmap``
    * "img"     ↦ ``QtGui.QImage``
    * "pil"     ↦ ``PIL.Image.Image``
        
"""
    from io import BytesIO
    from base64 import b64encode
    from IPython.lib import latextools
    from core.prog import scipywarn
    from gui.guiutils import isDarkGui
    
    hasLatex2SVG = False
    
    if not isinstance(l, str) or len(l.strip()) == 0:
        return
    
    try:
        import latex2svg
        hasLatex2SVG = True
    except:
        pass
    
    if not isinstance(darkmode, bool):
        darkmode = isDarkGui()

    if not isinstance(backend, str) or backend.lower() not in ("auto", "dvipng", "matplotlib"):
        backend = "auto"
    else:
        backend = backend.lower()
        
    if out.lower() == "svg":
        if not hasLatex2SVG:
            scipywarn("The Python package latex2svg is required. Please install it.")
            return
        
        # NOTE: 2026-01-16 00:13:14 
        # special case of SVG output requested
        # syscheck = subprocess.run("dvisvgm", capture_output=True)
        # if syscheck.returncode != 0:
        #     scipywarn("The 'dvisvgm' utility is not available. Is LaTeX installed?")
        #     return
        
        params = latex2svg.default_params.copy()
        params["optimizer"] = None
        
        if darkmode:
            try:
                syscheck = subprocess.run(["kpsewhich", "xcolor.sty"], capture_output=True)
                if syscheck.returncode==0:
                    cpackage = "xcolor"
                else:
                    syscheck = subprocess.run(["kpsewhich", "color.sty"], capture_output=True)
                    if syscheck.returncode==0:
                        cpackage = "color"
                    else:
                        scipywarn("Neither latex packages 'xcolor' or 'color' are available. Cannot adapt to dark background")
            except FileNotFoundError:
                scipywarn("LaTeX 'kpsewhich' utility do not appear to be installed. bailing out")
                return
                
            pparts = params["preamble"].strip().split("\n")
            pparts.append("\\usepackage{xcolor}")
            params["preamble"] = "\n".join([""] + pparts + [""])
            
            # print("strutils.render_latex: 'l' contains single backslashes : ", "\\" in l)
            
            # NOTE: 2026-01-18 11:47:19
            # below, avoid splitting by "$" or "$$" as these characters may be encountered
            # WITHIN the actual expression
            if l.startswith("$$") and l.endswith("$$"):
                # lparts = l.split("$$")
                # lparts = [l[:2], l[2:-2], l[-2:]]
                lparts = [l[2:-2]]
                lparts.insert(0,"$$\\begingroup\\color{white}")
                lparts.append("\\endgroup$$")
                l = "".join(lparts)
                
            elif l.startswith("$") and l.endswith("$"):
                # lparts = l.split("$")
                lparts = [l[1:-1]]
                lparts.insert(0, "$\\begingroup\\color{white} ")
                lparts.append(" \\endgroup$")
                l = "".join(lparts)
                
        return latex2svg.latex2svg(l, params)
        
    color = "#FFFFFF" if darkmode else "#000000"

    encode = kwargs.get("encode", False)

    if encode is True:
        out = "base64"

    # print(f"strutils.render_latex: darkmode = {darkmode}, color={color}, backend={backend}, encode={encode}, out={out}")
        
    if backend == "auto":
        data = latextools.latex_to_png(l, backend="dvipng", wrap=wrap, color=color, **kwargs)
        if not isinstance(data, bytes):
            # scipywarn("The 'dvipng' backend failed; trying 'matplotlib'")
            data = latextools.latex_to_png(l, backend="matplotlib", wrap=wrap, color=color, **kwargs)
            if not isinstance(data, bytes):
                scipywarn("All available backends have failed; check the parameters to this function call")
                return
                
    elif backend in ("dvipng", "matplotlib"):
        data = latextools.latex_to_png(l, backend=backend, wrap=wrap, color=color)
        # data = latextools.latex_to_png(sympy.latex(expr, mode=mode, itex=itex, **kwargs), backend="dvipng", wrap=False, color=color)
        if not isinstance(data, bytes):
            scipywarn(f"The backend {backend} failed; check the parameters to this function call")
            return
    else:
        raise ValueError(f"Unknown/unsupported backend {backend}")
    
    if out.lower() not in ("bytes", "img", "pix", "pil", "ipython", "base64"):
        raise ValueError(f"I do not understand 'out' parameter ({out}); expecting one of 'bytes', 'img', 'pix', 'pil', 'ipython' (case-insensitive)")
    elif out.lower() == "ipython":
        return IPImage(data)
    elif out.lower() == "base64": # not sure I need this
        return b64encode(data)
    elif out.lower() == "bytes":
        return data
    elif out.lower() == "pil":
        return PIL.Image.open(BytesIO(data))
    else:
        ret = QtGui.QPixmap()
        ok = ret.loadFromData(QtCore.QByteArray(data))
        if not ok:
            scipywarn("Cannot convert data to a pixmap")
            return
        if out.lower()=="img":
            return ret.toImage()
        else:
            return ret

def findlatex(s:str) -> list:
    
    # GTP-4o mini
    # Explanation of the Pattern:
    # 
    # \$[^\$]*\$: Matches inline LaTeX surrounded by dollar signs (e.g., $E = mc^2$).
    # |: Acts as an OR operator.
    # \\(begin|end)\{[^\}]*\}: Matches LaTeX environments, like \begin{equation} and \end{equation}.
    # |\\[a-zA-Z]+(?:\{[^\}]*\})?: Matches LaTeX commands (e.g., \frac{a}{b}), where the command may have optional braces for arguments.
    # 
    # Usage
    # 
    # This pattern allows you to extract LaTeX content from your strings, which is particularly useful for processing documents that contain mathematical notation or formatting commands.
    # 
    # You can adjust the pattern according to your needs, adding more LaTeX commands or structures as necessary.
    
    import re

    if not isinstance(s, str) or len(s.strip()) == 0:
        return list()

    # Sample string with LaTeX
    # text = "Here is some LaTeX: $E = mc^2$ and \\begin{equation} x = y + z \\end{equation}."

    # Regular expression to capture LaTeX commands
    # latex_pattern = r'(\$[^\$]*\$|\\(begin|end)\{[^\}]*\}|\\[a-zA-Z]+(?:\{[^\}]*\})?)'
    latex_pattern = r'(\$\$([^$]*)\$\$|\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}|(\$[^\$]*\$|\\[a-zA-Z]+(?:\{[^\}]*\})?))'

    matches = re.findall(latex_pattern, s)

    # # Display matches
    # for match in matches:
    #     print(match[0])  # match[0] contains the full matched LaTeX
        
    return list(map(lambda m: m[0].replace("\\\\", "\\"), matches))
    

def latexunicode2sympy(c:str, asSymbol:bool=True) -> typing.Optional[str | sympy.Symbol]:
    from core.prog import scipywarn

    if not isinstance(s, str) or len(s.strip()) == 0:
        return

    if c in reverse_latex_symbol:
        c_rep = reverse_latex_symbol[c].replace("\\", "")
        if asSymbol:
            if c_rep in symabc.__dict__:
                return symabc.__dict__[c_rep]
            else:
                return sympy.Symbol(c_rep)
        else:
            return c_rep
    else:
        scipywarn(f"No appropriate symbol found for {c}")
        
def parse_version_string(s: str) -> list:
    if not isinstance(s, str) or len(s.strip()) == 0:
        return list()
    parts = s.split(".")
    
def jaccard(s1, s2) -> float:
    if not all([isinstance(s, str) and len(s.strip()) for s in (s1,s2)]):
        return 0.
    r"""Calculates Jaccard similarity between two strings 's1' and 's2'.
See also similar_strings, which uses difflib.SequenceMatcher
"""
    set1 = set(s1)
    set2 = set(s2)
    
    return len(set1 & set2) / len(set1 | set2)

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
