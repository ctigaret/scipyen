# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


# FIXME/TODO 2022-10-23 21:59:40
import os, csv, unicodedata, traceback, codecs
import IPython.core.completer as completer

try:
    latex_symbols = completer.latex_symbols
except:
    import IPython.core.latex_symbols as ltx_sym
    latex_symbols = ltx_sym.latex_symbols

__module_path__ = os.path.abspath(os.path.dirname(__file__))


unicode_input = dict()

# with open(os.path.join(__module_path__,"unicode_input_table")) as src:
with codecs.open(os.path.join(__module_path__,"unicode_input_table.py"), 'r', encoding="utf-8", errors="ignore") as src:
    while True:
        l = str()
        try:
            l = src.readline()
        except:
            traceback.print_exc()
        if len(l) == 0:
            break
        items = l.split("\t")
        if len(items) != 4:
            break
        if "tab completion sequence" in items[2].lower():
            continue
        unicode_input[items[2]]=items[1]

symbols = latex_symbols

for k,i in unicode_input.items():
    if k not in latex_symbols:
        latex_symbols[k]=i

del unicode_input


def u(x:str):
    return symbols.get(x, x)

def uchar(x:str):
    return u(x)
        
# with open(os.path.join(__module_path__,"unicode_input_table")) as src:
#     reader = csv.reader(src, "excel-tab")
#     
#     try:
#         for row in reader:
#             # print(row)
#             unicode_table[row[2]] = row[1]
#             
#     except csv.Error as e:
#         sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))

# def sup(x:typing.Union[int, str]) -> str:
#     return _superscripts_(x)
