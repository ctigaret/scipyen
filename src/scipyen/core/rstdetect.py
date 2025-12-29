import re

# Sample Python docstring
docstring = """
This is an example of a docstring.

:param x: Description of parameter x.
:type x: int
:returns: Description of the return value.
:rtype: str

**Important:** This should be noted.
.. note::
   This is a note directive.

Section Header
===============
"""

# Regular expressions to detect common reST patterns
rst_pattern = r'(:[a-z]+:|^\s*[-=~^]+$|^\s*\.\. (note|warning|tip|attention|seealso|note|code|seealso)::|^\s*\*{1,2}.*)$'

# Finding all matches
matches = re.findall(rst_pattern, docstring, re.MULTILINE)

# Detect if the docstring follows reST formatting
if matches:
    print("This docstring appears to be written in reStructuredText.")
else:
    print("This docstring does not appear to be written in reStructuredText.")
