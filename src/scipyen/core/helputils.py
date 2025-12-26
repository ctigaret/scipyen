# -*- coding: utf-8 -*-
# $Id: helputils.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Helper script to replace pydoc "modules" & "apropos" invocation
in order to bypass the issues related to importing problematic modules.

Meant to be used by gui.pythonhelpwidget
"""
# WARNING: 2025-06-02 22:55:00
# DO NOT import any of scipyen's modules here, so that this can be run in a 
# separate python process

import sys, os, typing, inspect, types, importlib, io, dataclasses, inspect, re
import traceback
import itertools
import pydoc
import html
from functools import (singledispatch, partial)
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory

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


from IPython.core.interactiveshell import InteractiveShell
from IPython.core import magic, oinspect, page, prefilter, ultratb
from IPython.core.oinspect import (UnformattedBundle, Bundle, InfoDict)
from IPython.utils.text import (DollarFormatter, LSString, SList, 
                                format_screen, indent, dedent)
from IPython.utils.wildcard import list_namespace, typestr2type
from IPython.core.usage import (interactive_usage, quick_reference)

import markdown # for converstion of md to html
# from pymarkdown.api import PyMarkdownApi # MD linter
from pygments import highlight
from pygments.lexers import (PythonLexer, get_lexer_by_name, guess_lexer)
from pygments.formatters import HtmlFormatter
import docutils
import docutils.core, docutils.utils
from docutils.core import publish_parts
from gui import guiutils


_extra_info_fields = ["methods", "descriptors", "functions", "classes", "data"]
try:
    import docrepr.sphinxify as sphx

    def sphinxify(oinfo):
        wrapped_docstring = sphx.wrap_main_docstring(oinfo)

        def sphinxify_docstring(docstring):
            with TemporaryDirectory() as dirname:
                return {
                    "text/html": sphx.sphinxify(wrapped_docstring, dirname),
                    "text/plain": docstring,
                }

        return sphinxify_docstring
except ImportError:
    sphinxify = None

# NOTE: 2025-05-31 17:15:38
# do NOT place this file deeper than one level below scipyen directory
__module_path__ = os.path.abspath(os.path.dirname(__file__))
_scipyendir_ = os.path.dirname(__module_path__)

PYTHON_HELP_SECTIONS = ["NAME", 
                        "CLASSES",
                        "DATA", 
                        "DESCRIPTION", 
                        "FILE",
                        "FUNCTIONS",
                        "PACKAGE CONTENTS",
                        "SUBMODULES",
    ]

PythonHelpDict = typing.TypedDict("PythonHelpDict", dict(map(lambda x: (x.lower(), typing.Optional[typing.Union[str, typing.List[str]]]), PYTHON_HELP_SECTIONS)))

def isDarkGui() -> bool:
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    return v <= 128

def convert_rst_to_html(rst_content):
    r"""RST 2 HTML conversion using docutils.
Changes:
• Throwing pygments in the mix.


Original author: Dimity Margaret 
https://dnmtechs.com/converting-restructuredtext-to-html-using-python-3/
"""
    # settings = docutils.frontend.OptionParser().get_default_values()
    shut_up_level = docutils.utils.Reporter.SEVERE_LEVEL + 1
    settings_overrides={'output_encoding': 'unicode',
                        'output_encoding_error_handler': 'replace',
                        'input_encoding_error_handler': 'ignore',
                        'report_level': shut_up_level,
                        'syntax_highlight': 'long',
                        'table_style': 'borderless',
                        'math_output': 'mathjax',}

    html_content = docutils.core.publish_string(
        source=rst_content,
        writer_name='html',
        settings_overrides=settings_overrides,
    )
    return html_content

def writedoc(bf, thing, forceload=0):
    r"""Write HTML documentation to a file in the current directory.
Shamelessly copiued from the standard library module pydoc.
"""
    object, name = pydoc.resolve(thing, forceload)
    page = pydoc.HTMLDoc().page(describe(object), html.document(object, name))
    bf.write(page)
    # with open(name + '.html', 'w', encoding='utf-8') as file:
    #     file.write(page)
    # print('wrote', name + '.html')



def rst_to_html_with_highlighting(rst_text):
    r"""Another RST 2 HTML converter.
This one  "ByWilliam	July 8, 2025
https://www.bomberbot.com/python/converting-restructuredtext-to-html-with-python-for-documentation/
 """
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style="default"
    settings = docutils.frontend.get_default_settings()
    shut_up_level = docutils.utils.Reporter.SEVERE_LEVEL + 1
    settings_overrides={'output_encoding': 'unicode',
                        'output_encoding_error_handler': 'replace',
                        'input_encoding_error_handler': 'ignore',
                        'report_level': shut_up_level,
                        # 'report_level': docutils.utils.Reporter.INFO_LEVEL,
                        'syntax_highlight': 'long',
                        'table_style': 'borderless',
                        'math_output': 'mathjax',}
    # parts = publish_parts(rst_text, writer_name='html')
    parts = publish_parts(rst_text, writer_name='html5', settings=setting,  settings_overrides=settings_overrides,)
    ret_html = parts['html_body']
    
    # print('<pre class=' in ret_html)

    # formatter = HtmlFormatter(noclasses=True, nobackground=True, style=style) # <--
    
    def replace_code_block(match):
        code = match.group(1)
        # lang = match.group(2)
        # print(f"lang = {lang}")
        # lexer = get_lexer_by_name(lang, stripall=True) # <--
        # formatter = HtmlFormatter(linenos=True, cssclass="source", noclasses=True, nobackground=True, style=style) # <--
        # formatter = HtmlFormatter(linenos=True, cssclass="source") # <--
        # return highlight(code, PythonLexer(stripall=True), formatter) # <--
        return mypylight(code)


    # import re # already imported at the top
    # pattern = r'<pre class="literal-block">\n(.+?)\n</pre>'
    pattern1 = r'<pre class="code python doctest">(.+?)</pre>'
    # pattern = r'<pre>\n(.+?)\n</pre>'
    # rematch = re.match(pattern1, ret_html, flags=re.DOTALL)
    # if rematch:
    #     print(f"group1:{rematch.group(1)}, group2: {rematch.group(2)}")
    ret_html = re.sub(pattern1, replace_code_block, ret_html, flags=re.DOTALL)
    ret_html = html.unescape(ret_html)

    return ret_html


def reSThighlight(text):
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style="default"
    
    formatter = HtmlFormatter(nobackground=True, noclasses=True, style=style)
    
    pattern1 = r'<pre class="code python doctest">(.+?)</pre>'
    # pattern2 = r"\<pre\>\<code\>[\s\S]*?\<\/code\>\<\/pre\>"
    
    rst_html = convert_rst_to_html(text)
    
    # formatter = HtmlFormatter(linenos=True, cssclass="github-dark", style='default') # <--
    
    for code_section in re.findall(recmd, rst_html):
        new_code_section = code_section.replace('<pre><code>', '')
        new_code_section = new_code_section.replace('</code></pre>', '')
        new_code_section = html.unescape(new_code_section)
        new_code_section_highlight = mypylight(new_code_section) #, lexer, formatter)
        # lexer = get_lexer_by_name("python", stripall=True) # <--
        # formatter = HtmlFormatter(linenos=True, cssclass="github-dark", style='default') # <--
        # new_code_section_highlight = highlight(new_code_section, lexer, formatter) # <--
        rst_html = rst_html.replace(code_section, new_code_section_highlight)
    
    
    return rst_html

def mdhighlight(text):
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style="default"
        
    # NOTE: 2025-10-14 22:34:50
    # there are issues with pip-installed pymarkdown:
# ### BEGIN
# from pymarkdown.api import PyMarkdown
# In /home/cezar/scipyenv/lib64/python3.13/site-packages/pymarkdown/core.py, line 159: 
# SyntaxWarning: invalid escape sequence '\w'
#   return not not re.match('^\w+\s*=', line)
# In /home/cezar/scipyenv/lib64/python3.13/site-packages/pymarkdown/core.py, line 159: 
# SyntaxWarning: invalid escape sequence '\w'
#   return not not re.match('^\w+\s*=', line)
# ---------------------------------------------------------------------------
# ModuleNotFoundError                       Traceback (most recent call last)
# Cell In[2], line 1
# ----> 1 from pymarkdown.api import PyMarkdown
# 
# File ~/scipyenv/lib64/python3.13/site-packages/pymarkdown/__init__.py:1
# ----> 1 from .core import process
# 
# File ~/scipyenv/lib64/python3.13/site-packages/pymarkdown/core.py:4
#       2 import re
#       3 from contextlib import contextmanager
# ----> 4 from StringIO import StringIO
#       5 import itertools
#       6 import sys
# 
# ModuleNotFoundError: No module named 'StringIO'
# ### END

#     linter = PyMarkdownApi()
#     
#     scan_result = linter.scan_string(text)
#     
#     if sum(map(lambda a: len(getattr(scan_result, a)), ["scan_failures", "pragma_errors", "critical_errors"])):
#         fix_result = linter.fix_string(text)
#         if fix_result.was_fixed:
#             text = fix_result.fixed_file
        
    md = markdown.Markdown(extensions=['markdown.extensions.extra','markdown.extensions.toc','markdown.extensions.nl2br'], 
                            safe_mode=True)
    
    formatted = md.convert(text)
    
    recmd = r"\<pre\>\<code\>[\s\S]*?\<\/code\>\<\/pre\>"
    
    # formatter = HtmlFormatter(nobackground=True, noclasses=True, style=style) # <--
    
    for code_section in re.findall(recmd, formatted):
        new_code_section = code_section.replace('<pre><code>', '')
        new_code_section = new_code_section.replace('</code></pre>', '')
        new_code_section = html.unescape(new_code_section)
        new_code_section_highlight = mypylight(new_code_section)
        formatted = formatted.replace(code_section, new_code_section_highlight)
        
    return formatted

def mypylight(text):
    r"""Highlights Python code in a text"""
    # return highlight(code, PythonLexer(), HtmlFormatter(noclasses=True, nobackground=True))
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style = "default"
        
    lexer = get_lexer_by_name("python", stripall=True)
    return highlight(text, lexer, HtmlFormatter(noclasses=True, nobackground=True, style=style))
    # return highlight(text, PythonLexer(), HtmlFormatter(noclasses=True, nobackground=True, style=style))

def make_multicolumn_html(strings:typing.List[str], columns:int=4, fn:typing.Callable = lambda s: s) -> str:
    r"""Emulates pydoc.HTMLDoc.multicolumn with configurable number of columns"""
    from gui import guiutils
    if not isinstance(columns, int) or columns <= 0:
        columns = 4
        
    slen, sw = zip(*map(lambda s: (len(s), guiutils.get_text_width(s)), strings))
    
    maxwidth = max(sw)+5
    
    maxlen = max(slen)+(5)
    
    fullwidth = maxwidth * (columns + 1)
    
    add_space = lambda s: s + "".join(["&nbsp;"] * (maxlen - len(s)))
    
    head = list()
    head.append("<colgroup>")
    for c in range(columns):
        head.append(f"<col span='1' style='width: {maxwidth}px';")
    head.append("</colgroup")
    
    thead = "\n".join(head)
    
    rows = (len(strings) + (columns-1)) // columns
    
    # result = f"<table style='width:{fullwidth}px'>{thead}"
#     for row in range(rows):
#         result = result + "<tr>"
#         
#         for col in range(columns):
#             k = row*columns + col
#             if k < len(strings):
#                 result = result  + '<td class="multicolumn">' + fn(strings[k]) + "</td>"
#             
#         result = result + "</tr>"
#     
#     result  = result + "</table>"
#     return result
        
    result = ""
    for col in range(columns):
        result = result + '<td class="multicolumn">'
        for i in range(rows*col, rows*col+rows):
            if i < len(strings):
                result = result + add_space(fn(strings[i])) + '<br>\n'
        result = result + '</td>'
    return f"<table style='width:{fullwidth}px'>{thead}<tr>{result}</tr></table>"

    
def make_HTML_table(msg:str|list[str], cols:int=4) -> str:
    r"""Formats a message to be displayed in a HTML table with ``cols`` columns.
Useful when the message contains a list of names, keywords, etc.
NOTE: The resulted string MUST be embedded somewhere between <body> </body> HTML tags. 
"""
    from core.prog import scipywarn
    if isinstance(msg, str):
        items = list(sorted(map(lambda x: x.strip(), filter(lambda x: len(x.strip()), msg.replace("\n", " ").split(" ")))))
    elif isinstance(msg, list) and all(isinstance(s, str) for s in msg):
        items = msg
    else:
        scipywarn(f"Expecting a str or a list of str; instead got {type(msg).__name__}")
        return "<table></table>"
    # print(f"{len(items)} items, with {max(tuple(len(i) for i in items))}")
    out = list()
    out.append("<table style='width:100%'>")
    k = 0
    while k < len(items):
        c = 0
        while c < cols:
            if k == len(items):
                break
            if c == 0:
                # out.append("<tr style='width:100%'>")
                out.append("<tr>")
            # out += ["<td style='width:100%'>", items[k], "</td>"]
            out += ["<td class='multicolumn'>", items[k], "</td>"]
            k += 1
            if c == cols-1:
                out.append("</tr>")
            c += 1
                
    out.append("</table>")
    
    return "\n".join(out)

def module_infos(title:str, header:str, columns:int = 4) -> str:
    env_pkg_names, env_non_pkg_names, scipyen_pkg_names, scipyen_non_pkg_names, plugin_names = listmodules()
    out = list()
    out += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"',
            '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
            '<html>',]
    out += ["<head>", 
            f"<title>{title}</title>", 
            '<meta> name="generator" content="Kate Editor"</meta>', 
            "</head>"]
    
    out.append("<body>")
    out.append(f"<h1>{header}</h1>")
    out.append("<h2>Scipyen's package modules:</h2>")
    out.append(make_HTML_table(scipyen_pkg_names, columns))
    out.append("<p>")
    out.append("<h2>Scipyen's non-package modules:</h2>")
    out.append(make_HTML_table(scipyen_non_pkg_names, columns))
    out.append("<p>")
    out.append("<h2>Python package modules:</h2>")
    out.append(make_HTML_table(env_pkg_names, columns))
    out.append("<p>")
    if len(plugin_names):
        out.append("<h2>Scipyen's plugin modules:</h2>")
        out.append(make_HTML_table(plugin_names, columns))
        out.append("<p>")
    out.append("<h2>Python non-package modules:</h2>")
    out.append(make_HTML_table(env_non_pkg_names, columns))
    out.append("<p>")
    out.append("</body>")
    out.append("</html>")
    return "\n".join(out)

def listmodules() -> tuple:
    from core.workspacefunctions import getMainScipyenWindow
    from core.prog import walk_packages
    infos = list(filter(lambda i: "." not in i.name, walk_packages())) # list of available module infos
    
    userPluginsInfos = list()
    plugins = dict()
    mainWindow = getMainScipyenWindow()
    scipyeninfos = list(filter(lambda i: _scipyendir_ in i.module_finder.path, infos)) # list of module infos for scipyen's modules
    scipyen_pkginfos = list(filter(lambda i: i.ispkg, scipyeninfos))
    scipyen_pkg_names = list(sorted(map(lambda i: i.name, scipyen_pkginfos)))
    
    scipyen_nonpkginfos = list(filter(lambda i: not i.ispkg, scipyeninfos))
    scipyen_non_pkg_names = list(sorted(map(lambda i: i.name, scipyen_nonpkginfos)))
    
    envinfos = list(filter(lambda i: _scipyendir_ not in i.module_finder.path, infos)) # list of module infos for modules from outside of scipyen tree
    env_pkginfos = list(filter(lambda i: i.ispkg, envinfos))
    env_pkg_names = list(sorted(map(lambda i: i.name, env_pkginfos)))
    env_nonpkginfos = list(filter(lambda i: not i.ispkg, envinfos))
    env_non_pkg_names = list(sorted(map(lambda i: i.name, env_nonpkginfos)))
    
    if isinstance(mainWindow, QtWidgets.QMainWindow) and type(mainWindow).__name__ == "ScipyenWindow":
        userPluginsInfos = list(filter(lambda i: mainWindow.userPluginsDirectory in i.module_finder.path, infos)) # list of module infos for user plugins modules
        plugins = mainWindow.plugins # ordered dict of plugins imported in mainwindow
        
        # NOTE: 2025-10-10 22:43:04 list of module infos for scipyen's modules after dropping out plugin modules
        scipyeninfos = list(filter(lambda i: i.name not in plugins, scipyeninfos)) 
        scipyen_module_names = list(sorted(map(lambda i: i.name, scipyeninfos)))
        envinfos = list(filter(lambda i: i.name not in plugins, envinfos)) 
        env_module_names     = list(sorted(map(lambda i: i.name, envinfos)))
        
        # NOTE: 2025-10-10 22:41:45 list of (name, module) pairs imported in user's workspace
        # CAUTION: this will be different at each call if the user has
        # manually imported modules during a session
        modules_imported_in_shell = list(filter(lambda item: inspect.ismodule(item[1]) and item[1].__name__ not in plugins, mainWindow.workspace.items())) 
        
        # split in package and non-package modules
        packages_in_shell     = list(filter(lambda item: hasattr(item[1], "spec") and item[1].spec.loader.is_package(item[1].spec.name), modules_imported_in_shell))
        # packages_in_shell     = list(filter(lambda item: item[1].spec.loader.is_package(item[1].spec.name) if item[1].__name__ not in ("builtins", "sys") else False, modules_imported_in_shell))
        shell_package_names, shell_packages = zip(*packages_in_shell) if len(packages_in_shell) else ([], [])
        
        non_packages_in_shell = list(filter(lambda item: item[0] not in shell_package_names, modules_imported_in_shell))
        # non_packages_in_shell = list(filter(lambda item: not item[1].spec.loader.is_package(item[1].spec.name) if hasattr(item[1], "spec") else True, modules_imported_in_shell))
        # non_packages_in_shell = list(filter(lambda item: not item[1].spec.loader.is_package(item[1].spec.name) if item[1].__name__ not in ("builtins", "sys") else True, modules_imported_in_shell))
        shell_non_package_names, shell_non_packages = zip(*non_packages_in_shell) if len(non_packages_in_shell) else ([],[])
        
        
        # as in NOTE: 2025-10-10 22:41:45 above, but the name part in each pair augmented with the alias (if imported as alias) and split in package and non-package modules
        scipyen_modules_in_ns  = list(map(lambda item: f"{item[1].__name__} ({item[0]})" if item[0] != item[1].__name__ else item[1].__name__, filter(lambda item: item[0] in scipyen_module_names or (hasattr(item[1], "__file__") and isinstance(item[1].__file__, str) and _scipyendir_ in item[1].__file__), non_packages_in_shell)))
        scipyen_modules_not_in_ns = list(filter(lambda n: n not in shell_non_package_names, scipyen_module_names))
        
        scipyen_packages_in_ns = list(map(lambda item: f"{item[1].__name__} ({item[0]})" if item[0] != item[1].__name__ else item[1].__name__, filter(lambda item: item[0] in scipyen_module_names or (hasattr(item[1], "__file__") and isinstance(item[1].__file__, str) and _scipyendir_ in item[1].__file__), packages_in_shell)))
        scipyen_packages_not_in_ns = list(filter(lambda n: n not in shell_package_names, scipyen_module_names))
        
        scipyen_pkg_names = list(sorted(scipyen_packages_in_ns + scipyen_packages_not_in_ns))
        scipyen_non_pkg_names = list(sorted(scipyen_modules_in_ns + scipyen_modules_not_in_ns))
        
        env_modules_in_ns  = list(map(lambda item: f"{item[1].__name__} ({item[0]})" if item[0] != item[1].__name__ else item[1].__name__, filter(lambda item: item[0] not in scipyen_module_names and (not hasattr(item[1], "__file__") or (isinstance(item[1].__file__, str) and _scipyendir_ not in item[1].__file__)), non_packages_in_shell)))
        env_modules_not_in_ns  = list(filter(lambda n: n not in shell_non_package_names, env_module_names))
        
        env_non_pkg_names =  list(sorted(env_modules_in_ns + env_modules_not_in_ns))
        
        env_packages_in_ns = list(map(lambda item: f"{item[1].__name__} ({item[0]})" if item[0] != item[1].__name__ else item[1].__name__, filter(lambda item: item[0] not in scipyen_module_names and (not hasattr(item[1], "__file__") or (isinstance(item[1].__file__, str) and _scipyendir_ not in item[1].__file__)), packages_in_shell)))
        env_packages_not_in_ns  = list(filter(lambda n: n not in shell_package_names, env_module_names))
        
        env_pkg_names =  list(sorted(env_packages_in_ns + env_packages_not_in_ns))
        
        
    return env_pkg_names, env_non_pkg_names, scipyen_pkg_names, scipyen_non_pkg_names, list(sorted(plugins.keys()))
    
def info_scipyen_components(ns:dict) -> str:
    r"""Prepares the contents of the Software Components dialog.
Parameters:
==========
ns: the namepace where modules have been imported
"""
    from core.prog import (get_module_version, walk_packages, get_qt_api_for_python)
    import IPython
    # modules = dict(filter(lambda i: inspect.ismodule(i[1]), ns.items()))
    
    modinfos = tuple(walk_packages())
    modnames = tuple(map(lambda m: m.name, modinfos))
    
    address_map = {"Data Analysis": {
                                     "numpy":       ("NumPy", "https://numpy.org", "The fundamental package for scientific computing with Python"),
                                     "scipy":       ("SciPy", "https://scipy.org", "Fundamental algorithms for scientific computing in Python"),
                                     "quantities":  ("Quantities", "https://github.com/python-quantities/python-quantities", "A Python package for handling physical quantities."),
                                     "vigra":       ("vigra", "http://ukoethe.github.io/vigra", "The VIGRA Computer Vision Library"),
                                     "neo":         ("Neo", "https://neuralensemble.org/neo", "Neo is a package for representing electrophysiology data in Python"),
                                     "pandas":      ("pandas", "https://pandas.pydata.org", "Open source data analysis and manipulation tool"),
                                     "h5py":        ("h5py", "https://www.h5py.org", "HDF5 for Python"),
                                     "pyABF":       ("pyABF", "https://github.com/swharden/pyABF", "A simple Python interface for Axon Binary Format (ABF) files"),
                                     "pywt":        ("PyWavelets", "https://pywavelets.readthedocs.io/en/latest/index.html", "Wavelet Transforms in Python"),
                                     },
                    "User Interface & Plotting Frameworks": {"matplotlib": ("Matplotlib", "https://matplotlib.org", "MatplotLib: Visualization with Python"),
                                                             "seaborn": ("Seaborn", "https://seaborn.pydata.org", "Statistical data visualization"),
                                                             "pyqtgraph": ("PyQtGraph", "https://www.pyqtgraph.org", "Scientific Graphics and GUI Library for Python."),
                                                             "qtpy": ("QtPy", "https://github.com/spyder-ide/qtpy", "Abstraction layer for PyQt5/PySide2/PyQt6/PySide6"),
                                                             },
                    }
    
    def _get_modules_info(name:str, minfo:tuple):
        if name in modnames:
            modndx = modnames.index(name)
            modinfo = modinfos[modndx]
            module = importlib.util.module_from_spec(modinfo.module_finder.find_spec(name))
        else:
            try:
                module = importlib.import_module(name)
            except:
                module=None
        if isinstance(module, types.ModuleType):
            if any(module.__name__.lower().startswith(s) for s in ("qtpy", "pyside" "pyqt")):
                pyqtAPIver = get_qt_api_for_python(module)
                if isinstance(pyqtAPIver, str) and len(pyqtAPIver.strip()):
                    return f'<li> <a href={minfo[1]}>{minfo[0]}</a> {minfo[2]}: {get_module_version(module)}, with {pyqtAPIver} - (see also <a href="scipyen://_slot_about_qt">"About Qt"</a>) </li>' 
                else:
                    return f'<li> <a href={minfo[1]}>{minfo[0]}</a> {minfo[2]}: {get_module_version(module)} </li>' 
            else:
                return f'<li> <a href={minfo[1]}>{minfo[0]}</a> {minfo[2]}: {get_module_version(module)} </li>' 
    
    
    
    txt = list()
    
    txt += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"',
            '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
            '<html>',
            '<head>',
            '<title>Third Party Software Available or Used in Scipyen</title>',
            '<meta charset="utf-8"/>',
            '<meta> name="generator" content="Kate Editor"</meta>',
            '</head>',
            '<body>',
            '<h2>Software Components of Scipyen</h2>',
            '(Click on the links below, for credits & licenses)']
    
    txt.append('<h3>Environment</h3>')
    txt.append("<ul>")
    txt.append(f'<li> <a href="https://www.python.org/">Python™</a>: {sys.version} </li>')
    txt.append(f'<li> <a href="https://ipython.org/">IPython</a> Interactive Computing: {get_module_version(IPython)} </li>')
    txt.append(f'<li> <a href="https://pypi.org/project/qtconsole/">qtconsole</a> Jupyter QtConsole: {get_module_version("qtconsole")} </li>')
    txt.append("</ul>")
    
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        pyinstaller_bundle = pathlib.Path(sys._MEIPASS)
        if pyinstaller_bundle.name == "_internal":
            bundle_name = pathlib.Path(sys._MEIPASS).parent.name
        else:
            bundle_name = pathlib.Path(sys._MEIPASS).parent.name
            
        txt.append(f'<p> Running in a <a href="https://pyinstaller.org/en/stable/">PyInstaller</a> bundle &emsp; {bundle_name}')
    
    txt.append('<h3>Data Analysis</h3>')
    txt.append("<ul>")
    for name, minfo in address_map["Data Analysis"].items():
        line = _get_modules_info(name, minfo)
        if isinstance(line, str) and len(line.strip()):
            txt.append(line)
    txt.append("</ul>")
    
    txt.append('<h3>User Interface & Plotting Frameworks</h3>')
    txt.append("<ul>")
    for name, minfo in address_map["User Interface & Plotting Frameworks"].items():
        line = _get_modules_info(name, minfo)
        if isinstance(line, str) and len(line.strip()):
            txt.append(line)
    txt.append('<li> <a href="https://develop.kde.org/frameworks/breeze-icons/">Breeze Icons</a> © <a href="https://kde.org">KDE</a> and licensed under the <a href="https://www.gnu.org/licenses/lgpl-3.0.en.html">GNU LGPL version 3 or later</a></li>')
    txt.append("</ul>")


    # txt.append("<p>¹Used or available for use at the console — this is not an exhaustive list, and excludes libraries installed after Scipyen's installation.</p>")
    txt.append("</body>")
    txt.append("</html>")
    
    return "\n".join(txt)

def format_common_help_reply(msg:str):
    parts = msg.split("\n")
    # parts[0] has "Help on 'package'|'module' <name>" or "Help on <type of the thing> 'in' <parent's name>"
    pp = parts[0].split(" ")
    if "in" in pp:
        ndx = pp.index("in")
        pp[ndx-1] = f"<strong>{pp[ndx-1]}</strong>"
        pp[ndx+1] = f"<strong>{pp[ndx+1][:-1]}</strong>:"
    else:
        pp[-1] = f"<strong>{pp[-1][:-1]}</strong>:"
        
    # parts[0] = f"<h3>{' '.join(pp)}</h3>"
    parts[0] = ' '.join(pp)
    
    for k,p in enumerate(parts[1:]):
        if p.isupper():
            parts[k+1] = f"<p style='color:BlueViolet>{p}</p>"
            
    return "<br>\n".join(parts)

def helpdisp(shell, bf:io.StringIO, obj, oname="", formatter=None, info:typing.Optional[oinspect.OInfo] = None,
        detail_level=0, enable_html=True, omit_sections=()):
    r"""Stand-in for oinspect.Inspector.pinfo"""
    from core.prog import scipywarn
    assert info is not None
    
    # original_pylight = oinspect.pylight
    # oinspect.pylight = mypylight
    # info_dict = shell.inspector.info(info.obj, oname, info, detail_level)
    # info_b = shell.inspector._get_info(
    #     obj, oname, formatter, info, detail_level)#, omit_sections=omit_sections
    info_dict = hinfo(shell, info.obj, oname, info, detail_level)
    info_b = hget_info(shell, obj, oname, formatter, info, detail_level, omit_sections=omit_sections)
    
    # oinspect.pylight = original_pylight
    
    if enable_html:
        strng = info_b["text/html"]
        strng = strng.replace("<br>", "").replace("\n", "<br>\n").replace("<p>", "<br>").replace("<br><br>", "<br>").replace("</h1><br>", "</h1>")
    else:
        strng = info_b['text/plain']

    bf_page(bf, strng)
    
def bf_page(bf:io.StringIO, strng:str):
    # print(f"bf_page split lines: {strng.splitlines()}")
    for line in strng.splitlines():
        bf.write(line)
   
def redirect_psearch(shell, bf, cmd:str):
    r"""Emulates NamespaceMagics.psearch"""
    # print(f"redirect_psearch({cmd})")
    # NOTE: 2025-10-13 12:00:25 
    # contextlib.redirect_stdout doesn't work here
    # so let's disembowel this a bit and use what we need
    #
    psearchfn = shell.find_line_magic("psearch") # the psearch magic function that shell would use
    magicobj = psearchfn.__self__ # the magics object that owns `psearchfn`
    def_search = ['user_local', 'user_global', 'builtin']
    
    opts, args = magicobj.parse_options(cmd, 'cias:e:l',list_all=True)
    opt = opts.get
    # shell = self.shell # NOTE: 2025-10-13 11:59:24 `shell` already provided
    # psearch = shell.inspector.psearch # NOTE: 2025-10-13 11:59:50 use our own `hpsearch`
    # select list object types
    list_types = False
    if 'l' in opts:
        list_types = True

    # select case options
    if 'i' in opts:
        ignore_case = True
    elif 'c' in opts:
        ignore_case = False
    else:
        ignore_case = not shell.wildcards_case_sensitive

    # Build list of namespaces to search from user options
    def_search.extend(opt('s',[]))
    ns_exclude = ns_exclude=opt('e',[])
    ns_search = [nm for nm in def_search if nm not in ns_exclude]

    # Call the actual search
    try:
        hpsearch(shell, bf, args, shell.ns_table, ns_search,
                ignore_case=ignore_case, show_all=opt('a'), list_types=list_types)
            
    except:
        traceback.print_exc()
        # shell.showtraceback()

    # return ret, True
        
def hpsearch(shell, bf:io.StringIO, pattern, ns_table, ns_search=[],
             ignore_case=False, show_all=False, *, list_types=False):
    r"""Emulates shell.inspector.psearch"""
    # print(f"hpsearch({pattern}, ns_table = {type(ns_table).__name__}, ns_search = {ns_search}, ignore_case={ignore_case}, show_all = {show_all}, list_types = {list_types})")
    type_pattern = 'all'
    filter = ''

    # list all object types
    if list_types:
        bf_page(bf, '\n'.join(sorted(typestr2type)))
        return

    cmds = pattern.split()
    
    len_cmds  =  len(cmds)
    if len_cmds == 1:
        # Only filter pattern given
        filter = cmds[0]
    elif len_cmds == 2:
        # Both filter and type specified
        filter,type_pattern = cmds
    else:
        raise ValueError('invalid argument string for psearch: <%s>' %
                            pattern)

    # filter search namespaces
    for name in ns_search:
        if name not in ns_table:
            raise ValueError('invalid namespace <%s>. Valid names: %s' %
                                (name, shell.ns_table.keys()))

    # print('type_pattern:',type_pattern)  # dbg
    search_result, namespaces_seen = set(), set()
    for ns_name in ns_search:
        ns = ns_table[ns_name]
        # Normally, locals and globals are the same, so we just check one.
        if id(ns) in namespaces_seen:
            continue
        namespaces_seen.add(id(ns))
        tmp_res = list_namespace(ns, type_pattern, filter,
                                ignore_case=ignore_case, show_all=show_all)
        search_result.update(tmp_res)

    bf_page(bf, '<p>\n'.join(list(sorted(search_result))))
    
def object_inspect(shell, oname=str, detail_level:int=0):
    r"""Emulates shell.object_inspect"""
    info = get_object_info(oname)
    if info.found:
        pass # TODO
    
def get_object_info(shell, oname=str, namespaces=None) -> oinspect.OInfo:
    r"""Emulates shell._object_find()"""
    if namespaces is None:
        namespaces = [ ('Interactive', shell.user_ns),
                        ('Interactive (global)', shell.user_global_ns),
                        ('Python builtin', shell.ns_table["builtin"]),
                        ]
    info = shell._object_find(oname, namespaces)
    if not info.found:
        # this might happen when either:
        # 1) the object exists in the namespaces, but has been imported under an alias
        oname1 = _find_by_alias(shell, oname, namespaces)
        if isinstance(oname1, str) and len(oname1.strip()):
            return shell._object_find(oname1, namespaces)
        # 2) the first part in oname is not found by the shell
        # a reason might be because oname contains a fully qualified object name
        # (e.g. 'X.Y.Z.…' such as a module which was imported directly e.g. from X import Y (hence
        # shell 'knows' nothing about 'X' but may know about 'Y' and what follows next)
        #
        # so let me try this here
        subname = oname
        parts = shell._find_parts(subname)
        sinfo = None
        if parts[0]:
            for part in parts[1]:
                subname = subname.replace(f"{part}.", "")
                # print(f"subname = {subname}")
                sinfo = shell._object_find(subname, namespaces)
                if sinfo.found:
                    info = sinfo
                    return info
                
            # if isinstance(info, oinspect.OInfo) and info.found:
            #     return info
        
            # do a reverse search
            subname = oname
            for part in reversed(parts[1]):
                subname = subname.replace(f".{part}", "")
                # print(f"subname = {subname}")
                sinfo = shell._object_find(subname, namespaces)
                if sinfo.found:
                    info = sinfo
                    return info
                
    return info

def happend_info_field(shell, bundle: UnformattedBundle,
        title: str,
        key: str,
        info,
        omit_sections: typing.List[str],
        formatter,
        ):
    # TODO 2025-10-13 13:25:09
    if title in omit_sections or key in omit_sections:
        return
    field = info[key]
    if field is not None:
        formatted_field = shell.inspector._mime_format(field, formatter)
        bundle["text/plain"].append((title, formatted_field["text/plain"]))
        bundle["text/html"].append((title, formatted_field["text/html"]))


def hmake_info_unformatted(shell, obj, info, formatter, detail_level, omit_sections) -> UnformattedBundle:
    r"""Emulates shell.inspector._make_info_unformatted"""
    # TODO 2025-10-13 13:25:09
    bundle: UnformattedBundle = {
        "text/plain": [],
        "text/html": [],
    }
    def append_field(shell, 
        bundle: UnformattedBundle, title: str, key: str, formatter=None
    ):
        happend_info_field(
            shell,
            bundle,
            title=title,
            key=key,
            info=info,
            omit_sections=omit_sections,
            formatter=formatter,
        )
        
    _format = lambda t: shell.inspector.format(t)

    def code_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': mypylight(text)
        }

    if info["isalias"]:
        append_field(shell, bundle, "Repr", "string_form")

    elif info['ismagic']:
        if detail_level > 0:
            append_field(shell, bundle, "Source", "source", code_formatter)
        else:
            append_field(shell, bundle, "Docstring", "docstring", formatter)
            
        append_field(shell, bundle, "File", "file")

    elif info['isclass'] or oinspect.is_simple_callable(obj):
        # Functions, methods, classes
        append_field(shell, bundle, "Signature", "definition", code_formatter)
        append_field(shell, bundle, "Init signature", "init_definition", code_formatter)
        append_field(shell, bundle, "Docstring", "docstring", formatter)
        
        if detail_level > 0 and info["source"]:
            append_field(shell, bundle, "Source", "source", code_formatter)
        else:
            append_field(shell, bundle, "Init docstring", "init_docstring", formatter)
            if not oinspect.is_simple_callable(obj):
                for field in _extra_info_fields:
                    if info[field]:
                        fmt = code_formatter if field in ("methods", "descriptors", "functions") else formatter
                        append_field(shell, bundle, field.capitalize(), field, fmt)

        append_field(shell, bundle, "File", "file")
        append_field(shell, bundle, "Type", "type_name")
        if not oinspect.is_simple_callable(obj):
            append_field(shell, bundle, "Subclasses", "subclasses")

    else:
        # General Python objects
        append_field(shell, bundle, "Signature", "definition", code_formatter)
        append_field(shell, bundle, "Call signature", "call_def", code_formatter)
        append_field(shell, bundle, "Type", "type_name")
        append_field(shell, bundle, "String form", "string_form")

        # Namespace
        if info["namespace"] != "Interactive":
            append_field(shell, bundle, "Namespace", "namespace")

        append_field(shell, bundle, "Class docstring", "class_docstring", formatter)
        append_field(shell, bundle, "Init docstring", "init_docstring", formatter)
        append_field(shell, bundle, "Call docstring", "call_docstring", formatter)
        
        append_field(shell, bundle, "Length", "length")
        append_field(shell, bundle, "File", "file")

        # Source or docstring, depending on detail level and whether
        # source found.
        if detail_level > 0 and info["source"]:
            append_field(shell, bundle, "Source", "source", code_formatter)
        else:
            append_field(shell, bundle, "Docstring", "docstring", formatter)
            for field in _extra_info_fields:
                if info[field]:
                    append_field(shell, bundle, field.capitalize(), field, code_formatter)
                    # fmt = code_formatter if field in ("methods", "descriptors", "functions", "classes", "data") else formatter
                    # append_field(shell, bundle, field.capitalize(), field, fmt)

    return bundle

def hinfo(shell, obj, oname:str="", info:typing.Optional[oinspect.OInfo]=None,
          detail_level:int = 0) -> oinspect.InfoDict:
    r"""Augments shell.inspect.info()
 """
    info_dict = shell.inspector.info(obj, oname=oname, info=info, detail_level=detail_level)
    info_dict.update(**{field: None for field in _extra_info_fields if field not in info_dict})
    
    def _get_sig_or_type(o):
        try:
            sig = inspect.signature(o)
        except:
            sig = f" <{type(o).__name__}>"
        return sig
    
    def _get_name(o):
        return getattr(o, "__qualname__", getattr(o, "__name__", f"{o}"))

    def _is_docstring(o:typing.Any, memberv):
        try:
            val = inspect.getmember(member[0])
            return data == o.__doc__ or (isinstance(val, str) and val == info_dict["doctring"])
        except:
            return False
        
    _test_docstring = partial(_is_docstring, obj)
            
    # NOTE: 2025-10-13 18:55:39
    # throughout below we exttratc only the public API
    
    _is_data = lambda x: not(inspect.isclass(x) or inspect.isroutine(x) or inspect.ismethod(x) or inspect.isfunction(x) or inspect.ismodule(x) or _test_docstring(x))
    
    _is_function = lambda x: inspect.isfunction(x) or inspect.isroutine(x) or inspect.ismethod(x)
    
    _is_method = lambda x: inspect.isfunction(x) or inspect.isroutine(x) or inspect.ismethod(x) or inspect.isgenerator(x)
    
    _is_descriptor = lambda x: inspect.isdatadescriptor(x) or inspect.ismemberdescriptor(x) or inspect.isgetsetdescriptor(x)
    
    # datas = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
    #                         filter(lambda f: not f[0].startswith("_"), inspect.getmembers_static(obj, _is_data)))))
    datas = list(sorted(map(lambda f: f"{f[0]}:{type(f[1]).__name__} = {f[1]}", 
                            filter(lambda f: not f[0].startswith("_"), inspect.getmembers_static(obj, _is_data)))))
    
    info_dict["data"] = "\n".join(datas) if len(datas) else None
    
    if inspect.ismodule(obj):
        functions = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_function)))))
        info_dict["functions"] = "\n".join(functions) if len(functions) else None
        
        # NOTE: one can define a class as a member of another class (usually that's 
        # private but we drop these)
        classes = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                                filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, inspect.isclass)))))
        info_dict["classes"] = "\n".join(classes) if len(classes) else None
        
    else:
        methods = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_method)))))
        descriptors = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_descriptor)))))
        info_dict["methods"] = "\n".join(methods) if len(methods) else None
        info_dict["descriptors"] = "\n".join(descriptors) if len(descriptors) else None
        
    return info_dict

def hget_info(shell, obj, oname:str="", formatter=None, info:typing.Optional[oinspect.OInfo]=None,
              detail_level:int = 0, omit_sections:typing.Union[typing.List[str], typing.Tuple[str]] = ()) -> tuple[dict]:
    r"""Emulates shell.inspector._get_info"""
    # TODO 2025-10-13 13:25:09
    
    # info_dict = shell.inspector.info(obj, oname=oname, info=info, detail_level=detail_level)
    info_dict = hinfo(shell, obj, oname=oname, info=info, detail_level=detail_level)
    omit_sections = list(omit_sections)
    
    bundle = hmake_info_unformatted(shell, obj, info_dict, formatter,
                                    detail_level = detail_level, 
                                    omit_sections = omit_sections) 
    
    if shell.inspector.mime_hooks:
        hook_data = oinspector.InspectorHookData(
            obj=obj,
            info=info,
            info_dict=info_dict,
            detail_level=detail_level,
            omit_sections=omit_sections,
        )
        for key, hook in self.mime_hooks.items():  # type:ignore
            required_parameters = [
                parameter
                for parameter in inspect.signature(hook).parameters.values()
                if parameter.default != inspect.Parameter.default
            ]
            if len(required_parameters) == 1:
                res = hook(hook_data)
            else:
                warnings.warn(
                    "MIME hook format changed in IPython 8.22; hooks should now accept"
                    " a single parameter (InspectorHookData); support for hooks requiring"
                    " two-parameters (obj and info) will be removed in a future version",
                    DeprecationWarning,
                    stacklevel=2,
                )
                res = hook(obj, info)
            if res is not None:
                bundle[key] = res
                
    return shell.inspector.format_mime(bundle)

    
    
def hpinfo(shell, cmd, namespaces = None, detail_level:int=0,
                                    enable_html:bool=True):
    r"""Emulates a IPython pinfo call"""
    ret = None
    reformat = False
    
    with io.StringIO() as bf:
        try:
            pinfo,qmark1,oname,qmark2 = re.match(r'(pinfo )?(\?*)(.*?)(\??$)',cmd).groups()
            if pinfo or qmark1 or qmark2:
                detail_level = 1
            if "*" in oname:
                redirect_psearch(shell, bf, oname)
                reformat=True
            else:
                hinspect(shell, bf, oname, namespaces=namespaces,
                                detail_level = detail_level,
                                enable_html = enable_html,
                                )
                reformat=False
                
            ret = bf.getvalue()

        except:
            traceback.print_exc()
    
    return ret, reformat
     
def hinspect(shell:InteractiveShell, bf:io.StringIO, oname=str, namespaces=None, **kw):
    r"""Stand-in for shell._inspect, called by pinfo magic.
    Named as `hinspect` to avoid clash with the standard library module `inspect`.

?symbol or symbol? in console triggers the following call chain:

    NamespaceMagics.pinfo (parameter_s = "", namespaces = None) 
        with `parameter_s` = the symbol and 'namespaces set to None (default)
    ↓
        • pinfo,qmark1,oname,qmark2 = re.match(r'(pinfo )?(\?*)(.*?)(\??$)',parameter_s).groups()
        
    shell._inspect("pinfo", oname)
    ↓
    page.page(data, start, screen_lines, pager_cmd) with: 
        data: a Bundle/dict generated in shell._inspect(); 
        start: 0
        screen_lines: 0
        pager_cmd: None
    ⇊
    eiher 
        • shell.hooks.show_in_pager
        • page.pager_page(data)
"""
    from core.prog import scipywarn
    detail_level = kw.get("detail_level", 0)
    enable_html = kw.get("enable_html", True)
    info = get_object_info(shell, oname, namespaces)
    # print(f"core.helputils.hinspect: info = {info}")
    if namespaces is None:
        namespaces = [ ('Interactive', shell.user_ns),
                        ('Interactive (global)', shell.user_global_ns),
                        ('Python builtin', shell.ns_table["builtin"]),
                        ]
    
    if info.found or hasattr(info.parent, oinspect.HOOK_NAME):
        # info_dict = shell.inspector.info(info.obj, oname, info, detail_level)
        info_dict = hinfo(shell, info.obj, oname, info, detail_level)
        if shell.sphinxify_docstring:
            if sphinxify is None:
                raise ImportError("Module ``docrepr`` required but missing")
            docformat = sphinxify(shell.object_inspect(oname))
        else:
            if "docstring" in info_dict:
                docformat = format_screen
            else:
                docformat = None

        # pmethod = getattr(shell.inspector, meth)
        # TODO: only apply format_screen to the plain/text repr of the mime
        # bundle.
        formatter = format_screen if info.ismagic else docformat
        helpdisp(shell, bf, info.obj, oname, formatter, info, detail_level, enable_html)
    else:
        bf.write("No Python documentation found")
        # scipywarn('Object `%s` not found.' % oname)
        # return 'not found'  # so callers can take other action
        
def _find_by_alias(shell, oname:str, namespaces=None):
    r"""Find an object by its alias - typically applies to imported modules
WARNING: Potentially problematic...
 """
    if namespaces is None:
        namespaces = [ ('Interactive', shell.user_ns),
                        ('Interactive (global)', shell.user_global_ns),
                        ('Python builtin', shell.ns_table["builtin"]),
                        ]
        
    for nsname,ns in namespaces:
        obj_list = list(filter(lambda x: inspect.ismodule(x[1]) and oname in x[1].__name__, ns.items()))
        if len(obj_list):
            return obj_list[0][0]
        
    return
    
def run_python_help(shell, cmd:str, enable_html=True, ) -> str | None:
    ret = None
    with io.StringIO() as bf:
        helper = pydoc.Helper(output = bf)
        try:
            helper.help(cmd)
            ret = bf.getvalue()
            # bf.flush()
        except:
            traceback.print_exc()
            
    if not isinstance(ret, str) or len(ret.strip()) == 0:
        ret = f"No Python documentation found for {cmd}"
        ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
    else:
        special = cmd if cmd in ("keywords", "symbols", "topics") else None
        ret_bundle = shell.inspector.format_mime(format_python_help_output(shell, make_python_help_dict(ret, special)))
        if enable_html:
            strng = ret_bundle["text/html"]
            strng = strng.replace("<br>", "").replace("\n", "<br>")#.replace("<p>", "<br>").replace("<br><br>", "<br>").replace("</h1><br>", "</h1>")
        else:
            strng = ret_bundle['text/plain']
            
        with io.StringIO() as bf:
            bf_page(bf, strng)
            ret = bf.getvalue()
        
    return ret

def make_python_help_dict(s:str, special:typing.Optional[str] = None) -> dict:
    # from pydoc import HTMLDoc
    # htmlPydoc = HTMLDoc()
    
    # lines = list(filter(lambda l: len(l.strip()) > 0, s.splitlines()))
    lines = s.splitlines()
    # NOTE 2025-10-14 11:55:56 
    # treat special cases (e.g. "help('topics')", "help('symbols')", etc)
    # as well as those that start with a topic (e.g. "help('EXECUTION')")
    if special:
        if special.lower() in ("topics", "symbols", "keywords"):
            title = f"<h1>{lines[1]}</h1>"
            body = title + make_multicolumn_html(list(sorted(itertools.chain.from_iterable(map(lambda s: s.split(), lines[2:])))))
            
            return {special.capitalize(): body}
            
        else:
            return {special.capitalize(): s}
        
    elif not lines[0].startswith("Help on"):
        if len(lines[0].strip()):
            special = lines[0]
            return {lines[0]: "\n".join(lines)}
        else:
            return {lines[0]: "\n".join(lines[1:])}
    # else:
    #     return {lines[0]: "\n".join(lines[1:])}
    
    sections = list(map(lambda x: x.lower(), PYTHON_HELP_SECTIONS))
    helpdict = PythonHelpDict(**{field:None for field in sections})
    
    section = special if special else None
    
    for k, line in enumerate(lines):
        if k==0:# and line.startswith("Help on"):
            helpdict[line] = None
            if "function" in line:
                helpdict[line] = list()
                section = line
            # if section:
            #     helpdict[section] = None
            # else:
            #     helpdict[line] = None
            # NOTE: 2025-10-14 11:57:53
            # now, this is moot, see NOTE 2025-10-14 11:55:56
            # if not line.startswith("Help on"): 
            #     section = line
        else:
            if line.lower() in helpdict:
                section = line.lower()
            else:
                if section:
                    if section not in helpdict or not isinstance(helpdict[section], list):
                        helpdict[section] = list()
                    # helpdict[section].append(f"{line}<br>")
                    helpdict[section].append(line)
                    
    for section in helpdict:
        slist = helpdict[section]
        if isinstance(slist, list):
            helpdict[section] = "\n".join(slist)
            
    return helpdict

def format_python_help_output(shell, data:PythonHelpDict, formatter=None):
    r"""Attempt for format standard Python help output similarly to IPython's help output.
 """
    bundle: UnformattedBundle = {
        "text/plain": [],
        "text/html": [],
    }
    
    if formatter is None:
        formatter = format_screen

    _format = lambda t: shell.inspector.format(t)
    
    def code_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': mypylight(text)
        }
    
    def pyhelp_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': rst_to_html_with_highlighting(text)
            }
    
    def append_field(shell, bundle:UnformattedBundle, title:str, key:str, hd:PythonHelpDict, formatter):
        field = hd[key]
        if field is not None:
            formatted_field = shell.inspector._mime_format(field, formatter)
            bundle["text/plain"].append((title, formatted_field["text/plain"]))
            bundle["text/html"].append((title, formatted_field["text/html"]))
        else:
            bundle["text/plain"].append((title, ""))
            bundle["text/html"].append((title, ""))
    
    titlekey = list(filter(lambda k: k.upper() not in PYTHON_HELP_SECTIONS, data.keys()))

    if len(titlekey):
        titlekey = titlekey[0]
        title = titlekey #if titlekey not in data else ""
        try:
            append_field(shell, bundle, title, titlekey, data, pyhelp_formatter)
        except:
            # traceback.print_exc()
            append_field(shell, bundle, title, titlekey, data, format_screen)
                
    else:
        titlekey = ""
        
    for key in data:
        if key != titlekey:
            if data[key]:
                fmt = code_formatter if key in ("data", "classes", "functions") else formatter
                append_field(shell, bundle, key.capitalize(), key, data, fmt)
        
    return bundle
    

def run_help_command(shell, cmd:str, namespaces=None, **kw) -> str | None:
    """
kw: 
enable_html: bool, default, is True
detail_level: int, 0 or 1
"""
    # NOTE: 2025-10-13 11:21:18
    # code shamelessly adapted/copied from IPython
    
    # print(f"core.helputils.run_help_command({cmd})")
    from IPython.core.magic import Magics, magics_class, line_magic, magic_escapes 
    import pydoc, traceback
    if not isinstance(cmd, str) or len(cmd.strip()) == 0:
        return
    
    detail_level = kw.get("detail_level", 0)
    enable_html = kw.get("enable_html", True)
    
    ret = None
    reformat:bool = False
    
    if cmd.startswith("help"):
        cmd = cmd.strip("help").strip("(").strip(")").strip("\"")
        if len(cmd) == 0:
            cmd = "help"
        ret = run_python_help(shell, cmd)
        reformat = True
        
    else:
        if cmd in ("?", "??"):
            # bf_page(bf, interactive_usage)
            ret = interactive_usage
            reformat=True
            
        elif cmd == "quickref":
            mman = shell.magics_manager
            docs = mman.lsmagic_docs(True, missing='No documentation')
            format_string = '%s%s:\n%s\n'
            magicdocs = "".join(
                [format_string % (magic_escapes['line'], fname,
                              indent(dedent(fndoc)))
                for fname, fndoc in sorted(docs['line'].items())]
                +
                [format_string % (magic_escapes['cell'], fname,
                              indent(dedent(fndoc)))
                for fname, fndoc in sorted(docs['cell'].items())]
                )
            ret = quick_reference + magicdocs
            reformat=True
            
        elif cmd.startswith("lsmagic"): # NOTE: 2025-10-13 11:27:34 also allow `lsmagics`
            from IPython.core.magics.basic import MagicsDisplay
            mmd = MagicsDisplay(shell.magics_manager, ignore=[])
            ret = mmd._lsmagic()
            reformat=True
            
        elif cmd.startswith("psearch"):
            s = cmd.strip("psearch").strip()
            if len(s):
                with io.StringIO() as bf:
                    redirect_psearch(shell, bf, s)
                    ret = bf.getvalue()
                    if len(ret.strip()) == 0:
                        ret = f"Nothing found matching the pattern {s}<p>"
                    # print(f"run_help_command {cmd} -> ret = {ret}")
                    reformat = True
                    
            else:
                ret, reformat = hpinfo(shell, "psearch", namespaces, detail_level = detail_level,
                                    enable_html = enable_html)
                
        else:
            if cmd.startswith("?") or cmd.endswith("?"):
                def_cmd = shell.input_transformer_manager.transform_cell(cmd)
                # this is of the form:
                # get_ipython().run_line_magic(<method>, <target>)
                method_name, target = def_cmd.strip("get_ipython().run_line_magic(").strip(")\n").replace("'", "").split(", ")
                if method_name == "pinfo2":
                    method_name = "pinfo"
                elif method_name == "pinfo":
                    method_name = ""
                    
                cmd = " ".join([method_name, target])
            
            ret, reformat = hpinfo(shell, cmd, namespaces, detail_level = detail_level,
                                    enable_html = enable_html)

               
        if isinstance(ret, str):
            if ret.startswith("No Python documentation found"):
                ret = run_python_help(shell, cmd)
                reformat = True
        else:
            ret = f"No Python documentation found for {cmd}"
            ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
            reformat = True
        
    return ret, reformat

