# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


# FIXME/TODO 2022-10-23 21:59:40
import os, csv, unicodedata
import IPython.core.completer as completer

__module_path__ = os.path.abspath(os.path.dirname(__file__))


unicode_input = dict()

with open(os.path.join(__module_path__,"unicode_input_table")) as src:
    while True:
        l = src.readline()
        if len(l) == 0:
            break
        items = l.split("\t")
        if len(items) != 4:
            break
        if "tab completion sequence" in items[2].lower():
            continue
        unicode_input[items[2]]=items[1]

for k,i in unicode_input.items():
    if k not in completer.latex_symbols:
        completer.latex_symbols[k]=i
        
del unicode_input

symbols = completer.latex_symbols

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

# def sup(x:typing.union[int, str]) -> str:
#     return _superscripts_(x)
