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
from tribool import Tribool

# import matplotlib.pyplot as plt
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


from core.regexps import *


# import qtpy
# qtpy.API = os.environ["QT_API"]
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import QtCore, QtGui
# else:
#     from qtpy import QtCore, QtGui

SUPERSCRIPT_UNICODE = {"-":"⁻",
                    "+":"⁺",
                    "=":"⁼",
                    "(":"⁽",
                    ")":"⁾",
                    "!":"ꜝ",
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
                    "α":"ᵅ",
                    "b":"ᵇ",
                    "β":"ᵝ",
                    "c":"ᶜ",
                    "d":"ᵈ",
                    "δ":"ᵟ",
                    "e":"ᵉ",
                    "ϵ":"ᵋ",
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
                    "θ":"ᶿ",
                    "u":"ᵘ",
                    "v":"ᵛ",
                    "w":"ʷ",
                    "x":"ˣ",
                    "y":"ʸ",
                    "z":"ᶻ",
                    "γ":"ᵞ",
                        }

SUBSCRIPT_UNICODE = {"-":"₋",
                    "+":"₊",
                    "=":"₌",
                    "(":"₍",
                    ")":"₎",
                    "0":"₀",
                    "1":"₁",
                    "2":"₂",
                    "3":"₃",
                    "4":"₄",
                    "5":"₅",
                    "6":"₆",
                    "7":"₇",
                    "8":"₈",
                    "9":"₉",
                    "a":"ₐ",
                    "β":"ᵦ",
                    "χ":"ᵪ",
                    "e":"ₑ",
                    "γ":"ᵧ",
                    "h":"ₕ",
                    "i":"ᵢ",
                    "j":"ⱼ",
                    "k":"ₖ",
                    "l":"ₗ",
                    "m":"ₘ",
                    "n":"ₙ",
                    "o":"ₒ",
                    "p":"ₚ",
                    "ϕ":"ᵩ",
                    "r":"ᵣ",
                    "ρ":"ᵨ",
                    "s":"ₛ",
                    "ə":"ₔ",
                    "t":"ₜ",
                    "u":"ᵤ",
                    "v":"ᵥ",
                    "x":"ₓ"}


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

def subscript(s:str)->str:
    if len(s)==1:
        return SUBSCRIPT_UNICODE.get(s, s)

    return "".join(list(map(lambda c: SUBSCRIPT_UNICODE.get(c,c), s)))

def is_sequence(s: str, matches: bool = False, delimiters: bool = False,
                spans: bool = False) -> bool | dict:
    r"""Test if ``s`` is a string representation of a tuple or list.

.. |nbsp| unicode:: 0xA0
   :trim:

.. note::
    Enclosing brackets are NOT necessary, here.

Parameters:
===========
:s: string to test

:matches: When ``True``, also return a list of the matched (sub)strings

:delimiters: When ``True``, and ``matches`` is also ``True``, then also return |nbsp|
    the delimiter characters, in addition to the match object and the matched string

.. note::

    When there is no match, returns None for the match, an empty string for the |nbsp|
    matched string, and an empty list for the delimiter characters.

Returns:
========

A ``bool`` indicating if ``s`` is a sequence-like string.

When matches is True, also returns the regexp match and the matched string. |nbsp|
The latter is needed because in toder to recognise sequence strings in "naked" form |nbsp|
e.g. '0.2 s, 0.3 s', the function internally encloses the string in parentheses.

When delimiters is True, also returns a list of delimiter characters, sorted.

"""
    # import re
    from core.regexps import (DELIMITERS, BRACKETED_SEQUENCE,
                              BRACKETED_NUMERIC_SEQUENCE)
    from core.utilities import unique

    # decorated = False
    match = None
    string = None
    groups = list()
    delims = list()
    sequences = list()

    if not isinstance(s, str) or len(s.strip())==0:
        ret = False

    else:
        # find delimiters
        delims = unique(sorted(DELIMITERS.findall(s)))
        # check if this is a sequence and also for nested sequences
        sequences = detect_nested_sequences(s)

        match = BRACKETED_SEQUENCE.match(s)
        # match is needed because it incorporates the brackets
        # groups contain the matched BETWEEN (and excluding) the brackets
        # because of this, contents of a group MAY be a syntactically incorrect sequence string
        # i.e. with missing end bracket
        # so, might just call:  groups = list(match.groups()) instead
        # groups = BRACKETED_SEQUENCE.findall(s) # same as match.groups()

        if match is not None and len(sequences):
            ret = True
            string = match.string
            groups = list(match.groups())


            # string = match.group(1)
        else:
            # NOTE: 2026-03-20 15:59:32
            # try and see is decorating with '(' and ')' turns it into a sequence string
            ss = "(" + s + ")"
            return is_sequence(ss, matches = matches,
                               delimiters = delimiters, spans = spans)

    # print(f"matches = {matches}, delimiters = {delimiters}, spans = {spans} ")
    if any ((matches, delimiters, spans)):
        # print(f"returning a dict")
        result = {"result": ret}
        if matches:
            result["string"] = string
        if delimiters:
            result["delimiters"] = delims
        if spans:
            result["sequences"] = sequences

        return result

    else:
        return ret

def parse_sci_string(x: str) -> tuple:
    r"""Retrieve mantissa, exponent, and number of digits in the mantissa, within a string containing scientific number format"""
    if not isnumber(x):
        return (None, None, 0)

    ee = SCIENTIFIC_NUMBER_FORMAT_MATCH.findall(x)
    if len(ee):
        ms, e, e_ = ee[0] # mantissa string, exponent string, exponent char ('e' or 'E')
        _, es = e.split(e_)
        # the exponent:
        if len(es):
            p = int(es) # exponent power
        else:
            p = 0 # exponent power

        m = float(ms) # mantissa

        if "." in ms:
            i, dec = ms.split(".")
            d = len(dec) # number of decimals
        else:
            d = 0 # number of decimals

    else:
        p = 0
        if "." in x:
            parts = x.split(".")

            if len(parts) > 2:
                return (None, None, None)  # shouldn't really get here as this is not a numeric string hence it would have been rejected above

            m = float(parts[0])
            if len(parts) == 2:
                d = len(parts[1])
            else:
                d = 0
        else:
            m = float(x)
            d = 0

    return (m, p, d)

def get_decimals(x:str) -> int:
    if not isnumber(x):
        return 0

    m, p, d = parse_sci_string(x)

    return 0 if d is None else d

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

def str2sequence_2(s: str):
    from core.regexps import BRACKETED_SEQUENCE, DELIMITERS

    DELIMITERS

def detect_nested_sequences(s: str,
                            pairs: typing.Dict[str, str] = None
                            ) -> typing.List[typing.Tuple[int,int,int,str,str]]:
    r"""Detects nested sequences (balanced and properly nested delimiters) in a string.

.. |nbsp| unicode:: 0xA0
   :trim:

The function supports any opening/closing pairs supplied |nbsp|
(default: (), [], {}).

Returns:
=======
List of spans, nesting depth (1 is the outermost), and open & close characters:

    (open_index, close_index, depth, open_character, close_character)

::

    # Example

    if __name__ == "__main__":
        s = "a(b[c]{d(e)})f"
        spans = detect_nested_sequences(s)
        for open_i, close_i, depth, o, c in spans:
            print(f"{o}@{open_i} ... {c}@{close_i}  depth={depth}  substring='{s[open_i:close_i+1]}'")


.. note::
    GPT-5 mini, via Duck.ai, in answer to the query "stack-based python code for detecting nested sequences in a string"
"""
    # NOTE: 2026-03-24 10:41:25 Stack-based function.

    if pairs is None:
        pairs = {'(': ')', '[': ']', '{': '}'}

    open_to_close: dict = pairs
    close_to_open: dict = {c: o for o, c in open_to_close.items()}
    stack: typing.List[typing.Tuple[str,int,int]] = []  # (open_char, index, depth)
    results: typing.List[typing.Tuple[int,int,int,str,str]] = []
    max_depth: int = 0

    for i, ch in enumerate(s):
        if ch in open_to_close:
            depth = len(stack) + 1
            stack.append((ch, i, depth))
            if depth > max_depth:
                max_depth = depth

        elif ch in close_to_open:
            if not stack:
                # unmatched closing; skip or handle as needed
                continue

            open_ch, open_i, open_depth = stack.pop()

            expected_open = close_to_open[ch]

            if open_ch != expected_open:
                # mismatched pair: discard or try to recover (here we skip)
                # If needed, you can implement error handling/recovery here.
                continue

            results.append((open_i, i, open_depth, open_ch, ch))

    # results currently in order of encountering closes; sort by open index if desired
    results.sort(key=lambda x: x[0]) # <- sorted by open index

    return results

def parse_sequence(s: str, check: bool = False) -> typing.Optional[typing.Union[typing.Sequence, np.ndarray, Tribool]]:
    r"""Parses a string into a sequence of scalars, a plain numpy array or Quantity array.

.. |nbsp| unicode:: 0xA0
   :trim:

The scalars can be plain numbers or Quantity scalars.

Works OK for 1D arrays

Returns Tribool(False) when s is invalid, Tribool(None) when s is "intermediate"

"""
    import quantities as pq
    from core import scipyen_quantities as scq
    from core.utilities import unique

    seqdepth = lambda x: x[2]
    openchar = lambda x: x[3]
    closechar = lambda x: x[4]
    seqstring = lambda x,y: y[x[0]+1: x[1]] # string between brackets
    bseqstring = lambda x,y: y[x[0]: x[1]+1]# as the above but WITH enclosing brackets

    # as bseqstring but also return the part of 'y' NOT in bseqstring,
    # effectively splits the original string into the sequence and everything else
    bseqstringsplit = lambda x,y: (y[x[0]: x[1]+1], y[:x[0]] + y[x[1]+1:])

    seqs = detect_nested_sequences(s)

    # print(f"{len(seqs)} sequences detected")

    if len(seqs) == 1:
        # one sequence = case of strings like [x y z] and optional units symbol
        ochar = openchar(seqs[0])
        ss = bseqstringsplit(seqs[0], s)
        # print(f"ss = {ss}")
        # first element is ALWAYS the bracketed sequence string, and is guaranteed
        # by the detection function
        # here we get the un-bracketed version straight on
        s_ = ss[0][1:-1]  # un-bracketed version
        # figure out if the sequence is delimited by spaces or commas
        # if spaces => this came from a numpy array
        # if commas => this came from a python list, in which case it should NOT
        # be followed by a unit-like string; for example, a string like '[x,y] pA'
        # is syntactically wrong
        delims = unique(sorted(DELIMITERS.findall(s_)))
        # print(f"delims = {delims}")

        val = None

        if len(delims) == 0 or len(delims) > 2:
            return Tribool(False) # flag as Invalid so validator may attempt fixup

        elif len(delims) == 2:
            # bring down to one delimiter only, one of " " (space) "," (comma) or ", " (comma-space)
            if delims[0] == " " and "," in delims[1]:
                delims = delims[-1:] # so that delims remains a list
            else:
                return Tribool(False)

        if delims[0] == " ":
            if ochar == "{":
                # set case
                ss_ = s_.split(delims[0])
                v_ = list()
                try:
                    for p in ss_:
                        if NUMBER_MATCH.match(p):
                            v_.append(eval(p))

                    val = set(v_)
                except:
                    return Tribool(False)

            else:
                # numpy array case
                try:
                    val = np.fromstring(s_, sep = delims[0])
                except:
                    return Tribool(False)

        elif "," in delims[0]:
            # print("comma seq: ")
            # case of python list or tuple
            fn = None # list | tuple | set


            if ochar == "[":
                fn = list
                # -> list (deque is represented as lists, so
                # it is up to the user to figure this out)

            elif ochar == "(":
                # -> tuple
                fn = tuple

            elif ochar == "{":
                # -> set; NOTE: dict NOT supported here
                fn = set

            else:
                return Tribool(False)
                # raise SyntaxError(f"Cannot parse substring {ss} into a sequence or set")

            ss_ = s_.split(delims[0])

            # print(f"sub-parts ss_ = {ss_}")

            if any(p in (".", " ", "") for p in ss_):
                return Tribool() # incomplete sequence, flag as intermediate


            # check for any units symbols in the elements
            val = list()

            for p in ss_:
                m = NUMBER_MATCH.match(p)
                if m:
                    v = eval(p[slice(*m.span())])

                    d = DIMENSIONALITY_STRING.search(p)

                    if d:
                        dim = p[slice(*d.span())]
                        v *= scq.unitQuantityFromNameOrSymbol(dim)

                    val.append(v)

                else:
                    return Tribool(False)

            if len(val) == 0:
                return Tribool()

            if fn:
                val = fn(val)

            # raise SyntaxError(f"Cannot parse substring {ss[0]} into a sequence or set")

            # print(f"value from {ss[0]} -> {val}")

        if len(ss) == 2:
            # print(f"last bit: '{ss[1]}'")
            if len(ss[1].strip()):
                u = None
                if DIMENSIONALITY_STRING.match(ss[1].strip()):
                    u = scq.unitQuantityFromNameOrSymbol(ss[1])

                # print(f"from '{ss[1]}' -> {u}")

                if isinstance(val, set):
                    return Tribool(False)

                elif isinstance(val, (tuple, list)):
                    if all(isinstance(v, pq.Quantity) for v in val):
                        return Tribool(False)

                    val = np.array(val)

                elif not isinstance(val, np.ndarray):
                    return Tribool(False)

                if isinstance(u, pq.UnitQuantity):
                    val = val * u
                else:
                    return Tribool(False)

        return val

    elif len(seqs) > 1:
        depths = unique(list(map(seqdepth, seqs)))
        # print(f"depths = {depths}")
        if len(depths) > 1 or any(d>1 for d in depths):
            return Tribool(False)
            # raise SyntaxError(f"Strings with nested sequences are NOT supported: {s}")

    elif len(seqs) == 0:
        # no sequence detected by searching for brackets
        # maybe this is a non-bracketed sequence;
        # HOWEVER:
        # the forms below are acceptable and should resolve to array([0.1 0.2 0.3]) * pA:
        #   0.1 0.2 0.3 pA
        #   0.1,0.2,0.3,pA
        #   0.1, 0.2, 0.3, pA
        # and the next forms w/o units symbol at the end are ALL acceptable and should resolve to array([0.1 0.2 0.3])
        #   0.1, 0.2, 0.3
        #   0.1 0.2 0.3
        # whereas the next forms are ambiguous and therefore invalid
        #   0.1, 0.2, 0.3 pA
        #   0.1,0.2,0.3pA
        #   0.1 0.2 0.3, pA
        #   0.1 0.2 0.3,pA

        delims = unique(sorted(DELIMITERS.findall(s)))
        # print(f"0 sequences delims = {delims}")
        if len(delims) == 0:
            if any(s.startswith(c) for c in "([{"):
                if s in "([{":
                    return Tribool()

                if NUMBER_MATCH.match(s[1:]):
                    return Tribool()
                else:
                    return Tribool(False)
            else:
                if NUMBER_MATCH.match(s):
                    try:
                        return eval(s)
                    except:
                        return Tribool(False)

                elif DIMENSIONALITY_STRING.match(s):
                    return scw.unitQuantityFromNameOrSymbol(s)
                else:
                    return Tribool(False)

        elif len(delims) == 1 and delims[0] == " " or "," in delims[0]:
            parts = s.split(delims[0])

            if len(parts) == 1:
                if any(parts[0].startswith(c) for c in "([{"):
                    if parts[0] in "([{":
                        return Tribool()

                    if NUMBER_MATCH.match(parts[0][1:]):
                        return Tribool()
                    else:
                        return Tribool(False)
                else:
                    if NUMBER_MATCH.match(parts[0]):
                        try:
                            return eval(parts[0])
                        except:
                            return Tribool(False)

                    elif DIMENSIONALITY_STRING.match(parts[0]):
                        return scq.unitQuantityFromNameOrSymbol(parts[0])

                    else:
                        return Tribool(False)

            else:
                u = None
                v = list()

                for k,p in enumerate(parts[:-1]):
                    if k == 0 and any(p.startswith(c) for c in "([{"):
                        if p in "([{":
                            return Tribool()

                        if NUMBER_MATCH.match(p[1:]):
                            return Tribool()

                        else:
                            return Tribool(False)

                    else:
                        if any(parts[0].startswith(c) for c in "([{"):
                            return Tribool()

                        if NUMBER_MATCH.match(p):
                            try:
                                v.append(eval(p))
                            except:
                                return Tribool(False)
                        else:
                            return Tribool(False)

                if len(parts[-1].strip()):
                    if NUMBER_MATCH.match(parts[-1]):
                        try:
                            v.append(eval(parts[-1]))
                        except:
                            return Tribool(False)

                    elif DIMENSIONALITY_STRING.match(parts[-1]):
                        u = scq.unitQuantityFromNameOrSymbol(parts[-1])

                    else:
                        return Tribool(False)

                if len(v) == 0:
                    return Tribool()

                elif len(v) > 1:
                    val = np.array(v)
                    if isinstance(u, pq.Quantity):
                        return val * u
                    else:
                        return val

                else:
                    if isinstance(u, pq.Quantity):
                        return v[0] * u
                    else:
                        return v[0]

        else:
            return Tribool(False)

    return Tribool()

def str2sequence(s: str) -> typing.List[str]:
    r"""Splits a string representation of a sequence of elements, into its elements.

Returns a sequence of str. Elements are NOT further parsed into Python objects.

"""
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
                return ss.split()  # a list
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

def guess_sfx_sep(s, suppress_warnings:bool=False) -> str:
    nosepPattern = _re.compile(r"(.*?)??(\d*)$")
    try_match = nosepPattern.match(s)
    # print(f"try_match -> {try_match}")
    if try_match is not None and len(try_match.groups()) > 1:
        try:
            base, sfx = try_match.group(1,2)
            if base.endswith("_"):
                sep = "_"
            elif base.endswith(" "):
                sep = " "
            else:
                sep = ""
        except:
            if not suppress_warnings:
                scipywarn("Cannot guess whether separator is '_', ' ', or ''; assuming ''.")
            sep = ""

    else:
        if not suppress_warnings:
            scipywarn("Cannot guess whether separator is '_', ' ', or ''; assuming ''.")
        sep = ""

    return sep

def get_int_sfx(s: str, sep: str = "_",
                use_re: bool = False, bracketed:bool=False) -> typing.Tuple[str, int]:
    r"""Parses an integral suffix from the string.

.. |nbsp| unicode:: 0xA0
   :trim:

The suffix is delimited from the prefix by the sep string, which may be empty ("")

Returns the string base (the prefix) and the integer value as given by the literal suffix.

If a literal suffix is absent, the value is None.

Parameters:
===========
    :s: The string to be tested for the presence of an integral suffix

    :sep: The separator between the prefix and the suffix; default is "_" (underscore)

    :use_re: When True, use regular expressions (see ``re`` module in the standard Python library)
        Default is False.

.. note::
    When ``sep`` is not a string, or is an empty string, the function will |nbsp|
    *automatically* use regular expressions.

Examples:

::

    get_int_sfx("some_name", sep="_") -> ("some_name", None)

    # but:

    get_int_sfx("some_name_0", sep="_") -> ("some_name", 0)

    # whereas:

    get_int_sfx("some_name_1", sep="_") -> ("some_name", 1)

    # also:

    get_int_sfx("name0", sep="") -> ("name", 0)

    get_int_sfx("name(0)", sep="", bracketed=True) -> ("name", 0)

"""
    if not isinstance(s, str) or len(s.strip()) == 0:
        return ("", None)

    if bracketed:
        # pattern = _re.compile(r"\(\d+\)$")
        pattern = _re.compile(r"(.*?)??(\(\d+\))$")
        matches = _re.findall(pattern, s)
        if len(matches) == 0:
            return (s, None)
        else:
            match = matches[0]
            # print(f"match = {match}")
            ss = match[0].strip()
            val = int(match[1].strip("(").strip(")"))
            return (ss, val)

    elif not isinstance(sep, str) or len(sep) == 0 or use_re:
        # print("using regexp")
        # pattern = _re.compile(r"(.*?)??(\(\d+\))$")
        pattern = _re.compile(r"(.*?)??(\d*)$")
        re_match = pattern.match(s)
        if re_match is not None and len(re_match.groups()) > 1:
            try:
                base, sfx = re_match.group(1, 2)
                sfx = int(sfx)
            except:
                # base, sfx = s, 0
                base, sfx = s, None

        else:
            # base, sfx = s, 0
            base, sfx = s, None

    else:
        parts = s.split(sep)
        # print(f"parts -> {parts}")

        if len(parts) < 2:
            # return s, 0
            sfx = None
            base = s

        if len(parts) == 2:
            # make sure the 2nd part is not a number; if there is, then lump them back together
            try:
                sfx = int(parts[-1])
                base = parts[0]
            except:
                sfx = None
                base = sep.join(parts)

        elif len(parts) > 2:
            # there may be more than one sep e.g. some symbol named a_b_0, -> a_b_1, etc
            try:
                sfx = int(parts[-1])
                base = sep.join(parts[:-1])
            except:
                sfx = None
                base = sep.join(parts)

    return base, sfx

def counter_suffix(x:str, strings:typing.List[str], sep:str="_",
                   bracketed:bool=False, start:int=0,
                   use_re: bool = False,
                   returns_counter:typing.Optional[bool]=None) -> typing.Optional[typing.Union[str, int, typing.Tuple[str, int]]]:
    r"""Appends a counter suffix to x:str if x is found in the list of strings

Parameters:
==========

:x: string to check for existence

:strings: sequence of str to check for existence of x

:sep: default is "_"; suffix separator; valid values are "_", " " (single space),
    "" (the empty string), or "guess". When sep is "guess", the function will try
    to determine which separator is used in "x", i.e., either "_", " ", or "".

:use_re: When True, use regular expressions to detect integral suffixes in ``strings``

:bracketed: When True, uses the format <abc...> (x) where 'x' is the counter

.. note::

    Avoid this for setting identifier names, as the brackets are illegal characters for identifiers.

:start: start value for counter suffix

:returns_counter: tri-state flag ("three-valued logic"):

    * True ↦ the function returns the new counter (int).

    * False ↦ the function returns a suffixed string

    * None (the default) ↦ the function returns a tuple with the new string *and* the new counter.

"""
    if not isinstance(strings, (tuple, list)) and not hasattr(strings, "__iter__"):
        raise TypeError("Second positional parameter was expected to be an iterable; got %s instead" % type(strings).__name__)

    if len(strings) > 0 and not all ([isinstance(s, str) for s in strings]):
        raise TypeError("Second positional parameter was expected to contain str elements only")

    if not isinstance(sep, str):
        raise TypeError("Separator must be a str; got %s instead" % type(sep).__name__)

    if not isinstance(start, int):
        raise TypeError(f"'start' expected to be an int; got {type(start).__name__} instead")

    if start < 0:
        raise ValueError(f"'start' expected to be a positive int (>= 0); instead, got {start}")


    if isinstance(sep, str) and sep.lower() == "guess":
        sep = guess_sfx_sep(x)

    if len(strings):
        make_suffix = lambda c: f" ({c})" if bracketed else sep + f"{c}" if (isinstance(sep, str) and len(sep)) else f"{c}" # noqa

        base, cc = get_int_sfx(x, sep=sep, use_re=use_re, bracketed=bracketed)

        # print(f"counter_suffix: base = {base}, cc = {cc}")

        clashes = list(filter(lambda s: s.startswith(base), strings))

        # print(f"counter_suffix: clashes = {clashes}")

        if len(clashes) == 0:
            return None if returns_counter is True else x if returns_counter is False else (x, None)

        candidate_counters = list(filter(lambda t: isinstance(t, int), map(lambda s: get_int_sfx(s, sep=sep, use_re=use_re, bracketed=bracketed)[1], clashes)))

        # print(f"counter_suffix: candidate_counters = {candidate_counters}")

        if len(candidate_counters) == 0:
            if cc is None:
                cc = start
            new_x = base + make_suffix(cc)
            return (new_x, cc) if returns_counter is None else cc if returns_counter is True else new_x

        min_counter, max_counter = min(candidate_counters), max(candidate_counters)
        # print(f"counter_suffix: min_counter = {min_counter}, max_counter = {max_counter}")
        if min_counter > start:
            new_counter = max(range(start, min_counter))
        else:
            new_counter = max_counter+1

        new_x = base + make_suffix(new_counter)

        return (new_x, new_counter) if returns_counter is None else new_counter if returns_counter is True else new_x


    else:
        return (x, None) if returns_counter is None else None if returns_counter is True else x

def similar_strings(a:str, b:str) -> bool:
    r"""Similarity between two strings using difflib.SequenceMatcher./
See also jaccard
"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

def pluralize(s: str, n: int = 1) -> str:
    if not isinstance(s, str):
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

    .. :note:

        The reverse conversion is not directly suported, as it
        is more complicated: it depends on what the string contains (i.e.,
        comma-/ space-/ tab-separated values; are these strings representations
        of numbers, and if so, what format etc).

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

    if (
        all([isinstance(v, pq.Quantity) for v in val])
        and show_units
        ):
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
    r"""Returns True if string s can be evaluated to a numbers.Number

    Strings of the form [-/+]x.y[e][-/+]z return True.

    """
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False

    try:
        v = eval(s)
        return isinstance(v, numbers.Number)
    except: # noqa
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
    except: # noqa
        ret = False
    if not ret:
        pattern = r'<svg[^>]*>(.*?)<\/svg>'
        matches = _re.findall(pattern, s, _re.DOTALL)
        ret = len(matches)>0 and len(matches[0])>0

    return ret

# def qdbusmessage_str_to_dict(s: str) -> dict:
#     # Captures tokens like: "service='com.foo'" or 'path=/bar' or "member=SomeMethod"
#     # Handles values with quotes or without quotes, non-space chars.
#     pattern = _re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<val>'[^']*'|\"[^\"]*\"|\S+)")
#     out = {}
#     for m in pattern.finditer(s):
#         key = m.group("key")
#         val = m.group("val")
#         print(f"key {key} -> val = {val}")
#
#         # Strip surrounding quotes if present
#         if (len(val) >= 2) and ((val[0] == val[-1]) and val[0] in ("'", '"')):
#             val = val[1:-1]
#         out[key] = val
#
#     return out


def is_html(s:str) -> bool:
    from lxml import html
    if not isinstance(s, str) or len(s.strip()) == 0:
        return False
    try:
        test = html.fromstring(s) # noqa
        return True
    except: # noqa
        return False
    # return all(v in s for v in ("<html>", "</html>"))

def is_xml(s:str) -> bool:
    from lxml import etree
    try:
        test = etree.fromstring(s) # noqa
        return True
    except: # noqa
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
