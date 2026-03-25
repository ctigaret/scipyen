import re
import quantities as pq
from core.regexps import DELIMIMTERS

r"""Testbed for sequence detection in strings.


.. |nbsp| unicode:: 0xA0
   :trim:

Do NOT import this in your code, but comments in the regexps.py module may |nbsp|
refer to the contents of this module.

"""

s = str(list(map(lambda x: f"{x}", [0.021, 0.022, np.array([0.23, 0.24]), [1, 2, 3, (4, 5, 6)], (10,20,30), {100:200, 300:400}])))



# seqtype = lambda b,c0,c1: (tuple if (c0 == "(" and c1 == ")") else
#                            list  if (c0 == "[" and c1 == "]") else
#                            )

class Node:
   def __init__(self, value,
                depth: int = 1,
                children: typing.Sequence[typing.Self] = None):
      self.value = value
      self.depth = depth
      self.children = children

class KeyVal(Node):
   def __init__(self, key, value, /,
                depth: int = 1,
                children: typing.Sequence[typing.Self] = list()):
      from core.prog import is_hashable
      if is_hashable(key):
         self.key = key
         self.value = value
      else:
         raise TypeError(f"'key' must be a hashable type; instead, got {type(key).__name__}")

      self.depth = depth
      self.children = children


def eval_seq(s: str):
   import ast
   import re
   s = re.sub(r"\s{2,}", " ", s) # eat out duplicate spaces
   delims = unique(sorted(DELIIMITERS.findall(s))) # check for delimiters
   if len(delims):
      if len(delims) == 1:
         if " " in delims:
            val = np.array(list(map(eval, s.split()))) # 1D arrays are repr-ed as [x y z ...]

         elif any(sc in delims for sc in (",", ", ")):
            val = ast.literal_eval(s) # python sequences are repr-ed as [x, y, z, ...] or (x, y, z, ...)

         elif any(sc in delims for sc in (";", "; ")): # allow to unorthodox sequencs
            ss = s.split(delims[-1])
            val = list(map(eval_seq, ss))

         else:
            raise SyntaxError(f"Cannot parse the string {s}")

      else:
         if any(sc in delims for sc in (";", "; ")):
            axis2 = list(filter(lambda x: len(x)>0, s.split(";")))
            if len(axis2) == 1:
               val = eval_seq(axis2[0]) # eat out the spurious ';'
            else:
               if not all(len(row) == len(axis2[0]) for row in axis2):
                  raise SyntaxError("The string seems to specify an array of irregular shape")

               val = list(map(eval_seq, axis2))

         else:
            raise SyntaxError(f"Cannot parse string {s}")

   else:
      val = ast.literal_eval(s)

   return val

def test_parse(s):
   seqdepth = lambda x: x[2]
   seqstring = lambda x,y: y[x[0]+1: x[1]] # string between brackets
   bseqstring = lambda x,y: y[x[0]: x[1]+1]# as the above but with enclosing brackets

   seqs = strutils.detect_nested_sequences(s)
   maxdepth = max(map(seqdepth, seqs))
   sdict = dict(
               map(
                  lambda x: (
                        x[0],
                        {
                           "sequence": x[1],
                           "open": x[1][-2],
                           "close": x[1][-1],
                           "substring": seqstring(x[1],s)
                        }
                     ),
                  enumerate(seqs)
               )
            )


   nodes = list()
   for depth, d in sdict.items():
      bracketed_string = d["open"]+d["substring"]+d["close"]
      try:
         val = test_parse(bracketed_string)
      except SyntaxError:
         delims = unique(sorted(DELIIMITERS.findall(d["substring"])))
         if len(delims):
            substring = d["substring"]
            if len(delims) == 1 and " " in delims:
               val = np.array(list(map(eval, substring.split())))
            else:
               if any(sc in delims for sc in (";", "; ")):
                  axis2 = substring.split(";")
                  if len(axis2) == 1:
                     substring = axis2[0] # eat out the spurious ';'
                  else:
                     if not all(len(a) == len(axis2[0])):
                        raise ValueError("The string seems to specify an array of irregular shape")



                     row = lambda x: list(map(eval, x.split()))
                     val = list(map(lambda x: row(x), axis2))

            for dl in delims:
               if "," not in dl:
                  substring = substring.replace(dl, ", ")
            re.sub(r"[,]{2,}", ", ", substring)

            bracketed_string = d["open"]+substring+d["close"]

            try:
               val = ast.literal_eval(bracketed_string)

      node = Node(ast.literal_eval(string), depth)
      if len(nodes) == 0:
         nodes.append(node)
      else:
         to_add = True
         for n in nodes:
               if n.depth == node.depth-1:
                  if n.value in node.value:
                     continue

                  else:
                     n.children.append(node)
                  to_add = False
               else:
                  to_add = True

         if to_add:
               nodes.append(node)

# ss = list(map(lambda x: s[x[0]+1: x[1]], seqs))
# sseqs = reversed(sorted(seqs, key = seqdepth))
# # sss = list(map(lambda x: s[x[0]+1: x[1]], sseqs))
#
#
# ssdict = dict(
#             map(
#                lambda x: (
#                      x[0],
#                      {
#                         "sequence": x[1],
#                         "substring": bseqstring(x[1],s)
#                      }
#                   ),
#                enumerate(sseqs)
#             )
#          )
#
# cache = None
#
#
#
# for depth, d in ssdict.items():
#    try:
#       val = ast.literal_eval(d["substring"])
#       if cache is None:
#          cache = val
#       else:
#          if isinstance(cache, typing.Sequence):
#             if val in cache:
#                continue
#             else:
#                cache = cache + type(cache)((val,))
#
#    except:
#       continue
#
#
# def eval_seq(s):
#    import ast
#    if "," in s:
#       return ast.literal_eval(s)
#    else:


