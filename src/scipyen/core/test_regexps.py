import re
import quantities as pq

r"""Testbed for regular expression patterns.


.. |nbsp| unicode:: 0xA0
   :trim:

Do NOT import this in your code, but comments in the regexps.py module may |nbsp|
refer to the contents of this module.

"""

# # ### BEGIN: NOTE: 2026-03-24 10:37:56 GPT-5 mini, via Duck.ai
# # in answer to query "stack-based python code for detecting nested sequences in a string"
# from typing import List, Tuple, Dict
#
# # Return type: list of (open_index, close_index, depth, open_char, close_char)
# def detect_nested_sequences(s: str,
#                             pairs: Dict[str, str] = None) -> List[Tuple[int,int,int,str,str]]:
#     if pairs is None:
#         pairs = {'(': ')', '[': ']', '{': '}'}
#     open_to_close = pairs
#     close_to_open = {c: o for o, c in open_to_close.items()}
#     stack: List[Tuple[str,int,int]] = []  # (open_char, index, depth)
#     results: List[Tuple[int,int,int,str,str]] = []
#     max_depth = 0
#
#     for i, ch in enumerate(s):
#         if ch in open_to_close:
#             depth = len(stack) + 1
#             stack.append((ch, i, depth))
#             if depth > max_depth:
#                 max_depth = depth
#         elif ch in close_to_open:
#             if not stack:
#                 # unmatched closing; skip or handle as needed
#                 continue
#             open_ch, open_i, open_depth = stack.pop()
#             expected_open = close_to_open[ch]
#             if open_ch != expected_open:
#                 # mismatched pair: discard or try to recover (here we skip)
#                 # If needed, you can implement error handling/recovery here.
#                 continue
#             results.append((open_i, i, open_depth, open_ch, ch))
#
#     # results currently in order of encountering closes; sort by open index if desired
#     results.sort(key=lambda x: x[0])
#     return results
#
# # Example
# if __name__ == "__main__":
#     s = "a(b[c]{d(e)})f"
#     spans = detect_nested_sequences(s)
#     for open_i, close_i, depth, o, c in spans:
#         print(f"{o}@{open_i} ... {c}@{close_i}  depth={depth}  substring='{s[open_i:close_i+1]}'")
#
# # ### END  : NOTE: 2026-03-24 10:37:56 GPT-5 mini, via Duck.ai

a = [0.1, 0.2]
a_s = f"{a}"                                                # '[0.1, 0.2]'

b = np.array(a)*pq.pA
b_s = f"{b}"                                                # '[0.1 0.2] pA'

c = list(map(lambda v: np.array([v])*pq.pA, a))
c_s = ", ".join(list(map(lambda v: f"{v}", c)))             # [0.1] pA, [0.2] pA'

d = list(map(lambda v: np.array(v)*pq.pA, a))
d_s = ", ".join(list(map(lambda v: f"{v}", d)))             # '0.1 pA, 0.2 pA'

e = list(map(lambda v: v*pq.pA, a))
e_s = ", ".join(list(map(lambda v: f"{v}", e)))             # '0.1 pA, 0.2 pA'

# d, e are equivalent; d_s, e_s are equivalent

f = b.magnitude
f_s = f"{b}"                                                # '[0.1 0.2]'

delim_pattern = r'[,\s;|]+'
pattern = r'[\[|\(|\{](.+?)[\]|\)|\}]' # original pattern in strutils.is_sequence   # OK for a_s, f_s -> single match, original string; if delim is ", " -> c'truct a list
                                                                                    # works for b_s but drops the units symbol; if delim is " " -> c'truct a numpy array
                                                                                    # works for c_s -> 2 matches; drops units symbol
# pattern0 = r'([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])(\s??)([a-zA-Z]{1,})'
pattern0 = r'([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])(\s+?)([a-zA-Z]{1,})'                # works for c_s but too detailed

# pattern1 = r'(([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])|([0-9.+-]+?))(\s??)([a-zA-Z]{1,})' # works for d_s, e_s
# pattern2 = r'([0-9.+-]+?)(\s??)([a-zA-Z]{1,})'                                      # OK for d_s, e_s
pattern3 =  r'[\[|\(|\{]([\s0-9.+-]+?)[\]|\)|\}]'                                   # works for b_s but drops units symbol
pattern4 =  r'[\[|\(|\{]([\s0-9.+-]+?)[\]|\)|\}](\s+?)([a-zA-Z]{1,})'               # OK for b_s



pattern5 =  r'[\[|\(|\{]([\s0-9.+-,]+?)[\]|\)|\}]([\sa-zA-Z]{0,})'                  # OK for a_s, f_s => 2 groups:
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

pattern6 = r'([0-9.+-]+?)([\sa-zA-Z]{1,})'                                          # OK for d_s, e_s, like pattern5 for b_s, but prone for false positives in free-form strings
                                                                                    # do NOT use for b_s;
                                                                                    # does NOT work for a_s

pattern7 = r'(\b[0-9.+-]+?)([\sa-zA-Z]{1,})'

# pattern1 = r'([\w.]+?)(\s??)([\w]+?)'
# pattern0 = r'([\[|\(|\{](.+?)[\]|\)|\}])(\s+?)(.+?)'

a_matches = re.findall(pattern, a_s)
a_matches0 = re.findall(pattern0, a_s)
a_matches5 = re.findall(pattern5, a_s)
a_matches6 = re.findall(pattern6, a_s)
a_delim = re.findall(delim_pattern, a_s)
b_matches = re.findall(pattern, b_s)
b_matches0 = re.findall(pattern0, b_s)
b_matches5 = re.findall(pattern5, b_s)
b_matches6 = re.findall(pattern6, b_s)
b_delim = re.findall(delim_pattern, b_s)
c_matches = re.findall(pattern, c_s)
c_matches0 = re.findall(pattern0, c_s)
c_matches5 = re.findall(pattern5, c_s)
c_matches6 = re.findall(pattern6, c_s)
c_delim = re.findall(delim_pattern, c_s)
d_matches = re.findall(pattern, d_s)
d_matches0 = re.findall(pattern0, d_s)
d_matches5 = re.findall(pattern5, d_s)
d_matches6 = re.findall(pattern6, d_s)
d_delim = re.findall(delim_pattern, d_s)
e_matches = re.findall(pattern, e_s)
e_matches0 = re.findall(pattern0, e_s)
e_matches5 = re.findall(pattern5, e_s)
e_matches6 = re.findall(pattern6, e_s)
e_delim = re.findall(delim_pattern, e_s)

# variable  string                  pattern matches     pattern0 matches
#===============================================================================
# a_s       '[0.1, 0.2]'            ['0.1, 0.2']        []
#
# b_s       '[0.1 0.2] pA'          ['0.1 0.2']         [('[0.1 0.2]', '0.1 0.2', ' ', 'pA')]
#
# c_s       '[0.1] pA, [0.2] pA'    ['0.1', '0.2']      [('[0.1]', '0.1', ' ', 'pA'), ('[0.2]', '0.2', ' ', 'pA')]
#
# d_s       '0.1 pA, 0.2 pA'        []                  []
#
# e_s       '0.1 pA, 0.2 pA'        []                  []
