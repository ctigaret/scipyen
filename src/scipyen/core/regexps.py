import re
from core import scipyen_quantities as scq
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

delim_pattern = r'[,\s;|]+'
pattern = r'[\[|\(|\{](.+?)[\]|\)|\}]' # original pattern in strutils.is_sequence   # OK for a_s -> single match, original string; if delim is ", " -> c'truct a list
                                                                                    # works for b_s but drops the units symbol; if delim is " " -> c'truct a numpy array
                                                                                    # works for c_s -> 2 matches; drops units symbol
# pattern0 = r'([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])(\s??)([a-zA-Z]{1,})'
pattern0 = r'([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])(\s+?)([a-zA-Z]{1,})'
pattern1 = r'(([\[|\(|\{]([0-9.+-]+?)[\]|\)|\}])|([0-9.+-]+?))(\s??)([a-zA-Z]{1,})' # works for d_s, e_s
pattern2 = r'([0-9.+-]+?)(\s??)([a-zA-Z]{1,})'                                      # OK for d_s, e_s
pattern3 =  r'[\[|\(|\{]([\s0-9.+-]+?)[\]|\)|\}]'                                   # works for b_s but drops units symbol
pattern4 =  r'[\[|\(|\{]([\s0-9.+-]+?)[\]|\)|\}](\s+?)([a-zA-Z]{1,})'               # OK for b_s



pattern5 =  r'[\[|\(|\{]([\s0-9.+-,]+?)[\]|\)|\}]([\sa-zA-Z]{0,})'                  # OK for a_s => 2 groups:
                                                                                    #   1. the list string repr
                                                                                    #   2. empty string
                                                                                    #
                                                                                    # even BETTER for b_s => two groups:
                                                                                    #   1 = the array string (delim is " ")
                                                                                    #   2 = and the units symbol (spaces included)
                                                                                    #
                                                                                    # OK for c_s => TWO matches, one per element, each with 2 groups:
                                                                                    #   1. magnitude (bracketed)
                                                                                    #   2. units

pattern6 = r'([0-9.+-]+?)([\sa-zA-Z]{1,})'                                          # OK for d_s, e_s, as pattern5 for b_s
# pattern1 = r'([\w.]+?)(\s??)([\w]+?)'
# pattern0 = r'([\[|\(|\{](.+?)[\]|\)|\}])(\s+?)(.+?)'

a_matches = re.findall(pattern, a_s)
a_matches0 = re.findall(pattern0, a_s)
a_matches1 = re.findall(pattern1, a_s)
a_matches2 = re.findall(pattern2, a_s)
a_matches3 = re.findall(pattern3, a_s)
a_delim = re.findall(delim_pattern, a_s)
b_matches = re.findall(pattern, b_s)
b_matches0 = re.findall(pattern0, b_s)
b_matches1 = re.findall(pattern1, b_s)
b_matches2 = re.findall(pattern2, b_s)
b_matches3 = re.findall(pattern3, b_s)
b_delim = re.findall(delim_pattern, b_s)
c_matches = re.findall(pattern, c_s)
c_matches0 = re.findall(pattern0, c_s)
c_matches1 = re.findall(pattern1, c_s)
c_matches2 = re.findall(pattern2, c_s)
c_delim = re.findall(delim_pattern, c_s)
d_matches = re.findall(pattern, d_s)
d_matches0 = re.findall(pattern0, d_s)
d_matches1 = re.findall(pattern1, d_s)
d_matches2 = re.findall(pattern2, d_s)
d_delim = re.findall(delim_pattern, d_s)
e_matches = re.findall(pattern, e_s)
e_matches0 = re.findall(pattern0, e_s)
e_matches1 = re.findall(pattern1, e_s)
e_matches2 = re.findall(pattern2, e_s)
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
