import re
import quantities as pq

r"""Various compiled regular expression Pattern objects I found useful


.. |nbsp| unicode:: 0xA0
   :trim:


To understand the comments, see the accompanying test_regexps.py module.

Usage:
======
Import this module in your module; this will compile several re.Pattern objects |nbsp|
which will become available in the namespace of the importing module.

You may then use these pattern objects by calling their methods, e.g.:

::

    # Quantity arrays:

    from core.regexps import * # imports all re.Pattern objects defined here
    from core.utilities import unique
    from core.strutils import isnumber
    from core.scipyen_quantities import unitQuantityFromNameOrSymbol

    a = np.array([0.1, 0.2])*pq.pA

    # the string representation of a is:

    f"{a}"
    -> '[0.1 0.2] pA'

    # note that this looks like a " "—delimited sequence, enclosed in square brackets
    # i.e., bracketed numeric sequence, optionally terminated with a units symbol

    # find the delimiters in the sequence:
    # if needed, the found delimiters can be sorted
    # (NOTE: the space " " has the lowest rank)

    sorted(DELIMITERS.findall(f"{a}"))
    -> [' ', ' ']

    # and duplicates can be removed

    unique(sorted(DELIMITERS.findall(f"{a}")))
    -> [' ']

    # retrieve a from its string representation, in a few steps
    # (WARNING: you will likely loose numerical precision)
    #
    # step 1. detect the sequence => one match found with two groups
    matches = BRACKETED_NUMERIC_SEQUENCE.findall(f"{a}")
    matches
    -> [('0.1 0.2', ' pA')]

    #
    # step 2. detect delimiters (see above)
    # The delimiters suggest what object was represented:
    # " " as a sole delimiter: numpy array, possibly a Quantity array
    # " " and ", ": the presence of ", " delimiter indicates a Python sequence
    # (list, tuple, deque), possibly with units symbols (separated by " ")
    delims = unique(sorted(DELIMITERS.findall(f"{a}")))
    delims
    -> [' ']

    # step 3. on each match, perform the following test steps:
    # step 3.1: first group must resolve to numbers;
    #   use the detected delimiters to split, then test for numbers:
    # step 3.2: second group must resolve to a Quantity (dimensionality) symbol
    #
    result = list()

    for m in matches:
        values = list(map(lambda v: eval(v), filter(lambda s: isnumber(s), m[0].split(delims[0]))))

        # check for units symbol;

        units = unitQuantityFromNameOrSymbol(m[1]) if len(m[1].strip()) else None

        if delims[-1] == " ":
            # the string representation was generated from a numpy array
            # if, in addition, these is a units symbol, then the object is a
            # Quantity array
            #
            # WARNING: This methos will NOT follow the array's dimensions!
            # Therefore you should avoid it for non-vector arrays.
            #
            values = np.array(values)
            if units:
                values *= units
            result.append(values)

        else:
            # when the highest ranking delimiter is not space, the object is a
            # sequence of numbers;
            # ATTENTION: For a sequence of Quantities, the BRACKETED_NUMERIC_SEQUENCE
            # will find several matches (one for each Quantity object in the sequence)

            result.append(values)


"""

DELIMITERS = re.compile(r'[,\s;|]+')

BRACKETED_SEQUENCE = re.compile(r'[\[|\(|\{](.+?)[\]|\)|\}]')
# original pattern in strutils.is_sequence   # OK for a_s -> single match, original string; if delim is ", " -> c'truct a list
# works for b_s but drops the units symbol; if delim is " " -> c'truct a numpy array
# works for c_s -> 2 matches; drops units symbol



BRACKETED_NUMERIC_SEQUENCE = re.compile(r'[\[|\(|\{]([\[|\(\{]{0,1}[\s0-9.+-,]+?[\]|\)\}]{0,1})[\]|\)|\}]')

BRACKETED_QUANTITY_SEQUENCE = re.compile(r'[\[|\(|\{]([\[|\(\{]{0,1}[\s0-9.+-,]+?[\]|\)\}]{0,1})[\]|\)|\}](\s\*\s){0,1}([\sa-zA-Z]{1,})')
# Expects 3 groups per match
# OK for a_s => 2 groups:
#   1. the list string repr
#   2. empty string
#
# even BETTER for b_s, f_s => two groups:
#   1 = the array string (delim is " ")
#   2 = and the units symbol (spaces included)
#
# OK for c_s => TWO matches, one per element, each with 2 groups:
#   1. magnitude (bracketed)
#   2. units



NAKED_NUMERIC_SEQUENCE = re.compile(r'([0-9.+-]+?[,]{0,1})') # ([\s])(\s\*\s){0,1}([\sa-zA-Z]{0,})')
NAKED_QUANTITY_SEQUENCE = re.compile(r'([0-9.+-]+?[,]{0,1})([\s])(\s\*\s){0,1}([\sa-zA-Z]{1,})')


# OK for d_s, e_s, like pattern5 for b_s, but prone for false positives in free-form strings
# do NOT use for b_s;
# does NOT work for a_s

# pattern7 = r'(\b[0-9.+-]+?)([\sa-zA-Z]{1,})'

