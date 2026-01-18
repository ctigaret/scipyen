# -*- coding: utf-8 -*-
# $Id: helputils.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
This module contains functions used by gui.pythonhelpwidget.

Output from the help systems of IPython (i.e., ``pinfo``, ``pinfo2``) and Python
(i.e., ``pydoc``) is converted to html with syntax highlighting of embedded Python 
code and with embedded LaTeX mathematical expressions rendered as PNG.

Additional functions include alternatives to Python's ``pydoc.modules`` and 
``pydoc.apropos`` to bypass the issues related to importing problematic modules.


.. note:: 
    Documentation strings (*docstrings*) should use reStructuredText (ReST) formatting.
    
    Python's ``pydoc`` help output does not always format the (entire) output as 
    ReST, so there is some "gymnastic" performed by helpsystem.scipyen_doc module.
    
    The idea is to format the help output as ReST, then generate HTML5 from it.
    
    **HOWEVER**, I am having trouble getting docutils to apply pygments syntax 
    highlighting for Python code included in ReST docstrings processed with the
    ``docutils`` package (I tried the directives ``.. code-block:: python3``
    and ``.. literal-block::``, to no avail).
    
    Therefore I am falling back on simply using the ``::`` directive in docstrings,
    so that the ``docutils.publish*`` functions will output the directive contents
    un-tagged text between ``<pre class="literal-block">`` and ``</pre>`` HTML tags
    and apply the pygments highlighter on *this* output.
    )

"""

import sys, os, typing, inspect, types, importlib, io, dataclasses, inspect, re
import traceback
import itertools
import pathlib
import pydoc
import html
from functools import (singledispatch, partial)
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
# from rst2html5 import HTML5Writer

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
from pygments.lexers import (PythonLexer, get_lexer_by_name, guess_lexer, )
from pygments.formatters import (HtmlFormatter, get_formatter_by_name)
import docutils
import docutils.core, docutils.utils

from docutils.core import publish_parts
from gui import guiutils
from core import prog


_extra_info_fields = ["methods", "inherited methods", "descriptors", "functions", "classes", "data", "access"]

docutils_settings_overrides={'output_encoding': 'unicode',
                             'output_encoding_error_handler': 'ignore',
                             'input_encoding_error_handler': 'ignore',
                             'report_level': 5,
                             'halt_level': 5,
                             'syntax_highlight': 'long',
                             'table_style': 'borderless',
                             'math_output': 'mathjax'}

try:
    import docrepr.sphinxify as sphx

    def sphinxify(oinfo:oinspect.InfoDict):
        # print(f"helpsystem.helputils.sphinxify(oinfo={oinfo})")
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

class HyperBundle(Bundle):
    # NOTE: 2026-01-08 23:28:06 QtConsole does NOT render HTML objects!
    def _ipython_display_(self):
        from core import strutils
        shell = guiutils.getScipyenConsoleShell()
        shell.display_pub.publish(data=self["text/html"])
        # if isinstance(f.expression, sympy.Basic) or (isinstance(f.expression, str) and strutils.is_latex(f.expression)):
        #     try:
        #         img = render_sympy(f.expression, out="bytes") if isinstance(f.expression, sympy.Basic) else render_latex(f.expression, out="bytes")
        #     except:
        #         img = None
        #     if isinstance(img, bytes):
        #         shell.display_pub.publish(data={"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}\n\nImplements:\n"})
        #         shell.display_pub.publish(data={"image/png": img})
        #         return
        # shell.display_pub.publish(data={"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}\n\n"})
    

class ReSTFormatter():
    _section_levels = {0:"=", 1:"-", 2:"~", 3:"_", 4:"#"}

    def bold(self, text):
        return f"**{text}**"

    def indent(self, text, prefix='    '):
        """Indent text by prepending a given prefix to each line."""
        if not text: return ''
        lines = [(prefix + line).rstrip() for line in text.split('\n')]
        return '\n'.join(lines)

    def render_code(self, text):
        return "\n".join(["::", "", self.indent(text), "", ""])

    def section(self, title, contents, level:int=0):
        clean_contents = contents.rstrip()
        if level < 0:
            level = 0
        elif level > 4:
            level = 4
        adornment = "".join([self._section_levels[level]]*len(title))
        return "\n".join([title, adornment, clean_contents, ""])

    def render_title(self, title:str) -> str:
        if len(title):
            adornment = "".join([self._section_levels[0]]*len(title))
            return "\n".join([adornment, title, adornment])

        return title

    def render_synopsis(self, txt:str):
        return "\n".join([self.section("Synopsis:", txt, 0)])

    def render_latex(self, txt:str, imagedir:typing.Union[TemporaryDirectory, pathlib.Path, str]) -> str:
        r"""Replace latex mathematical expressions with ReST image links"""
        from core import strutils

        if isinstance(imagedir, TemporaryDirectory):
            dest = imagedir.name

        elif isinstance(imagedir, pathlib.Path):
            if imagedir.is_dir():
                dest = imagedir.as_posix()
            else:
                raise ValueError(f"{imagedir} is not an accessible directory")

        elif isinstance(imagedir, str):
            if os.path.isdir(imagedir):
                dest = imagedir
            else:
                raise ValueError(f"{imagedir} does not exist")
        else:
            raise TypeError(f"Bad parameter 'imagedir': {type(imagedir).__name__}")

        # Combined regular expression to capture all types of LaTeX
        latex_combined_pattern = r'(\$\$([^$]*)\$\$|\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}|(\$[^\$]*\$|\\[a-zA-Z]+(?:\{[^\}]*\})?))'

        # Finding all matches
        matches = re.findall(latex_combined_pattern, txt, re.DOTALL)

        # return list(map(lambda m: strutils.render_latex(m[0], out="base64")))
        # self.imagesdir.cleanup()

        for k, match in enumerate(matches):
            # match[0] contains the complete matched substring
            ltx = match[0].strip()
            # print(f"ltx = {ltx}")
            ll = ltx.replace("\\\\", "\\")
            pngdata = strutils.render_latex(ll, out="bytes", wrap=ll.startswith("$$"))
            # print(f"pngdata = {pngdata}")
            filepath = pathlib.Path(dest) / f"png{k}.png"
            with open(filepath.as_posix(), "wb") as pngfile:
                pngfile.write(pngdata)

            snippet = f"\n .. image:: {filepath.as_posix()}\n"
            # snippet = f" .. image:: {filepath.as_posix()}\n    :alt: {ll}"

            if ll.startswith("$$"):
                snippet = "\n\n" + snippet + "\n\n"

            # else:
            #     snippet.replace(".. image:: ", ".. |eq{k}| image:: ")

            txt = txt.replace(ltx, snippet)

        return txt


# NOTE: 2025-12-27 13:43:03 the function below is moved to gui.guiutils module
# def isDarkGui() -> bool:
#     windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
#     _,_,v,_ = windowColor.getHsv()
#     return v <= 128

def convert_rst_to_html(rst_content):
    r"""RST 2 HTML conversion using docutils.

Original author: Dimity Margaret 
https://dnmtechs.com/converting-restructuredtext-to-html-using-python-3/
"""
    print("helpsystem.helputils.convert_rst_to_html")
    # settings = docutils.frontend.OptionParser().get_default_values()
    # shut_up_level = docutils.utils.Reporter.SEVERE_LEVEL + 1
    # settings_overrides={'output_encoding': 'unicode',
    #                     'output_encoding_error_handler': 'ignore',
    #                     'input_encoding_error_handler': 'ignore',
    #                     'report_level': 5,
    #                     'halt_level': 5,
    #                     'syntax_highlight': 'long',
    #                     'table_style': 'borderless',
    #                     'math_output': 'mathjax',}

    html_content = docutils.core.publish_string(
        source=rst_content,
        writer_name='html',
        settings_overrides=docutils_settings_overrides,
    )
    return html_content

def writedoc(bf, thing, forceload=0):
    r"""Write HTML documentation to a file in the current directory.
Shamelessly copied from the standard library module pydoc.
"""
    object, name = pydoc.resolve(thing, forceload)
    page = pydoc.HTMLDoc().page(describe(object), html.document(object, name))
    bf.write(page)
    # with open(name + '.html', 'w', encoding='utf-8') as file:
    #     file.write(page)
    # print('wrote', name + '.html')
    
def parse_pydoc_output(s:str) -> dict:
    ret = dict()
    pyhelp_header_pattern = r"(Help on.*:)"
    pyhelp_header_matches = re.findall(pyhelp_header_pattern, s, re.MULTILINE)
    ret["pyhelp_header"] = list(map(lambda m: f"**{m}**", pyhelp_header_matches))
    
    
    return ret

def pub_rst(s:str) -> str:
    parts = publish_parts(s, writer_name='html5', settings_overrides=docutils_settings_overrides)
    ret_html = parts['html_body']
    return ret_html

def rst_latex_2_html(text:str, 
                     imgdir:typing.Optional[typing.Union[TemporaryDirectory, pathlib.Path, str]]=None) -> str:
    latex_formatter = partial(format_latex, imgdir=imgdir)
    
    # html = rst_to_html_with_highlighting(latex_formatter(text.replace("\n", "\n ")))
    html = rst_to_html_with_highlighting(latex_formatter(text))
    pattern = r'<img\s+[^>]*>'
    # pattern = r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>'
    # pattern = r'<img\s+[^>]*(src=["\']([^"\']+)["\'][^>]*)>'
    # src_pattern = r'src=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(pattern, html)
    for match in matches:
        # print(f"match = {match}")
        # src_match = re.findall(src_pattern, match)
        # print(f"src_match = {src_match}")
        # if len(src_match):
        #     src_match = src_match[0]
        #     match = match.replace(src_match, f"src='{src_match}'")
        #     smatch = match.replace(src_match)
        # html.replace(match, f"<div><br>{match}<br></div>")
        # html.replace(match, f"<div><table><tr><td>{match}</td></tr></table></div>")
        # html.replace(match, f"<p><div>{match}</div><p>")
        smatch = match.replace("/>", ' style="display: block; margin: 0 auto;" />')
        html.replace(match, f"<p><div>{smatch}</div><p>")
    
    return html

def rst_to_html_with_highlighting(rst_text) -> str:
    r"""Another RST 2 HTML converter.
This one  "By William	July 8, 2025
https://www.bomberbot.com/python/converting-restructuredtext-to-html-with-python-for-documentation/
 """
    # print(f"helpsystem.helputils.rst_to_html_with_highlighting()")
    # print(f"helpsystem.helputils.rst_to_html_with_highlighting(rst_text={rst_text})")

    parts = publish_parts(rst_text, writer_name='html5', settings_overrides=docutils_settings_overrides)
    body_html = parts['html_body']
    # ret_html = parts['whole']
    
    def replace_code_block(match):
        # print(f"helputils.rst_to_html_with_highlighting.replace_code_block(match = {match})")
        code = match.group(1)
        code = html.unescape(code)
        return mypylight(code)

    # NOTE: 2025-12-31 00:07:08 — see the Note module docstring;
    # I'm having trouble with how the ``.. code-block::`` directive is rendered
    # but WITHOUT colour highlighting...
    pattern = r'<pre class="literal-block">(.+?)</pre>' 
    
#     try:
#         matches = re.findall(pattern, body_html, re.DOTALL|re.MULTILINE)
#         for k, match in matches:
#             print(f"helputils.rst_to_html_with_highlighting: match {k} = {match[0]}")
#             snippet = replace_code_block(match[0])
#             body_html = body_html.replace(match[0], snippet)
#         
#         out_html = body_html
#     except:
#         traceback.print_exc()
#         out_html = body_html
        
    # out_html = body_html
    
    try:
        out_html = re.sub(pattern, replace_code_block, body_html, flags=re.DOTALL|re.MULTILINE)
    except:
        traceback.print_exc()
        out_html = body_html
        
    # NOTE: 2026-01-10 14:07:32 FIXME/TODO
    # finally, make then inline images "stand" on their own
    
    return out_html

def mdhighlight(text):
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style = "default"
        
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
    r"""Highlights Python code in a text.
    This can also be applied to un-tagged literal block of text enclosed between 
    ``<pre class="literal-block">``  and ``</pre>`` HTML tags, as output by
    docutils.publish* functions using the docutils "html5" writer.
 
    Uses ``pygments.highlight()`` function with pygments' ``HTMLFormatter`` and 
    the "python" lexer.
    """
    # print(f"hyelpsystem.mypylight(text = {text})")
    # uses pygments.highlight()
    # return highlight(code, PythonLexer(), HtmlFormatter(noclasses=True, nobackground=True))
    if guiutils.isDarkGui():
        style = "KeplerDark"
    else:
        style = "default"
        
    lexer = get_lexer_by_name("python", stripall=True)

    return _fix_html_py_highlight(highlight(text, lexer, HtmlFormatter(noclasses=True, nobackground=True, style=style)))
    # return highlight(text, lexer, HtmlFormatter(noclasses=True, nobackground=True, style=style))

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
    r"""A faster module walker which groups modules according to their availability.
Returns:
========

:env_pkg_names: list of names of package modules available in Scipyen's virtual environment but outside Scipyen
:env_non_pkg_names: list of names of non-package modules available in Scipyen's virtual environment but outside Scipyen
:scipyen_pkg_names: list of names of package modules in Scipyen's tree
:scipyen_non_pkg_names: list of names of non-package modules in Scipyen's tree
:scipyen_plugins: list of Scipyen plugin modules
"""
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

def _fix_html_py_highlight(s:str) -> str:
    s = s.replace("<br>", " ").replace("\n", "<br>").replace("<p>", "<br>").replace("<br><br>", "<br>").replace("</h1><br>", "</h1>")
    return s

def helpdisp(imgdir:TemporaryDirectory, info:oinspect.OInfo,
             bf:typing.Optional[io.StringIO]=None, oname:str="", detail_level=0, omit_sections=(),
             candidates_msg:typing.Optional[str] = None,
             shell:typing.Optional[InteractiveShell]=None):
    r"""Stand-in for oinspect.Inspector.pinfo.
    Outpout is redirected to a buffered IO stream.
    """
    from core.prog import scipywarn
    assert isinstance(info, oinspect.OInfo), f"Expecting an oinspect.OInfo object; got {type(info).__name__} instead"
    
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
   
    info_b = hget_info(imgdir, info.obj, oname, info, detail_level, 
                       omit_sections=omit_sections, candidates_msg=candidates_msg, shell=shell)
    
    # strng = info_b["text/html"]
    # bf_page(bf, strng)
    
    if isinstance(bf, io.StringIO):
        bf_page(bf, info_b["text/html"])
    else:
        shell.display(info_b)
    
def bf_page(bf:io.StringIO, strng:str):
    for line in strng.splitlines():
        bf.write(line)
   
def redirect_psearch(bf:io.StringIO, cmd:str, shell:typing.Optional[InteractiveShell]=None):
    r"""Emulates NamespaceMagics.psearch, redirecting to a ``io.StringIO`` object."""
    # print(f"redirect_psearch({cmd})")
    # NOTE: 2025-10-13 12:00:25 
    # contextlib.redirect_stdout doesn't work here
    # so let's disembowel this a bit and use what we need
    #
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
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
        hpsearch(bf, args, shell.ns_table, ns_search,
                ignore_case=ignore_case, show_all=opt('a'), list_types=list_types,
                shell=shell)
            
    except:
        traceback.print_exc()
        # shell.showtraceback()

    # return ret, True
        
def hpsearch(bf:io.StringIO, pattern, ns_table, ns_search=[],
             ignore_case=False, show_all=False, *, list_types=False,
             shell:typing.Optional[InteractiveShell]=None):
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

    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()

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
    
def happend_info_field(bundle: UnformattedBundle,
        title: str,
        key: str,
        info:oinspect.InfoDict,
        omit_sections: typing.List[str],
        formatter:typing.Optional[types.FunctionType],
        hide_title_in_html:bool,
        shell:typing.Optional[InteractiveShell]=None
        ):
    r"""Emulates shell.inspector._append_field.
    Allows omitting sections from the *info* parameter and/or the section title
 """
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
    if title in omit_sections or key in omit_sections:
        return
    if key not in info:
        return
    field = info[key]
    if field is not None:
        formatted_field = shell.inspector._mime_format(field, formatter)
        bundle["text/plain"].append((title, formatted_field["text/plain"]))
        bundle["text/html"].append(("" if hide_title_in_html else title, formatted_field["text/html"]))


def hmake_info_unformatted(obj:object, info:oinspect.InfoDict, detail_level:int, 
                           imgdir:TemporaryDirectory, 
                           omit_sections:typing.Union[typing.List[str], typing.Tuple[str]]=list(), 
                           shell:typing.Optional[InteractiveShell]=None) -> UnformattedBundle:
    r"""Emulates shell.inspector._make_info_unformatted.
    The "text/html" firelds of the resulting unformatted mime bundle accommodates rendering LaTeX expressions as png files.
"""
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
    # latex_formatter = partial(format_latex, imgdir=imgdir)
    rst_latex_fmt = partial(rst_latex_2_html, imgdir=imgdir)
    bundle: UnformattedBundle = {
        "text/plain": [],
        "text/html": [],
    }
    def append_field(bundle: UnformattedBundle, title: str, key: str, 
                     formatter:typing.Optional[types.FunctionType]=None, 
                     hide_title_in_html:bool=False,
                     shell:typing.Optional[InteractiveShell]=None
    ):
        happend_info_field(
            bundle,
            title=title,
            key=key,
            info=info,
            omit_sections=omit_sections,
            formatter=formatter,
            hide_title_in_html=hide_title_in_html,
            shell=shell
        )
        
    _format = lambda t: shell.inspector.format(t)

    def rst_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            # 'text/html': rst_to_html_with_highlighting(latex_formatter(text.replace("\n", "\n ")))
            'text/html': rst_latex_fmt(text)
        }
    def py_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': mypylight(text)
        }
    def bland_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': text
        }

    if info["isalias"]:
        append_field(bundle, "Repr", "string_form", shell=shell)

    elif info['ismagic']:
        if detail_level > 0:
            append_field(bundle, "Source", "source", py_formatter, shell=shell)
        else:
            append_field(bundle, "Docstring", "docstring", rst_formatter, hide_title_in_html=True, shell=shell)
            
        append_field(bundle, "File", "file", shell=shell)

    elif info['isclass'] or oinspect.is_simple_callable(obj):
        # Functions, methods, classes
        append_field(bundle, "Signature", "definition", py_formatter, shell=shell)
        append_field(bundle, "Init signature", "init_definition", py_formatter, shell=shell)
        append_field(bundle, "Docstring", "docstring", rst_formatter, hide_title_in_html=True, shell=shell)

        if detail_level > 0 and info["source"]:
            append_field(bundle, "Source", "source", py_formatter, shell=shell)
        else:
            append_field(bundle, "Init docstring", "init_docstring", rst_formatter, shell=shell)
            if not oinspect.is_simple_callable(obj):
                for field in _extra_info_fields:
                    if info[field]:
                        append_field(bundle, field.capitalize(), field, py_formatter, shell=shell)

        append_field(bundle, "File", "file", shell=shell)
        append_field(bundle, "Type", "type_name", py_formatter, shell=shell)
        # append_field(bundle, "Access", "access", py_formatter, shell=shell)
        
        if not oinspect.is_simple_callable(obj):
            append_field(bundle, "Subclasses", "subclasses", py_formatter, shell=shell)

    else:
        # General Python objects
        append_field(bundle, "Signature", "definition", py_formatter, shell=shell)
        append_field(bundle, "Call signature", "call_def", py_formatter, shell=shell)
        append_field(bundle, "Type", "type_name", py_formatter, shell=shell)
        append_field(bundle, "String form", "string_form", rst_formatter, shell=shell)

        # Namespace
        if info["namespace"] != "Interactive":
            append_field(bundle, "Namespace", "namespace", shell=shell)

        append_field(bundle, "Class docstring", "class_docstring", rst_formatter, shell=shell)
        append_field(bundle, "Init docstring", "init_docstring", rst_formatter, shell=shell)
        append_field(bundle, "Call docstring", "call_docstring", py_formatter, shell=shell)
        
        append_field(bundle, "Length", "length", shell=shell)
        append_field(bundle, "File", "file", shell=shell)

        # Source or docstring, depending on detail level and whether
        # source found.
        if detail_level > 0 and info["source"]:
            append_field(bundle, "Source", "source", py_formatter, shell=shell)
        else:
            append_field(bundle, "Docstring", "docstring", rst_formatter, shell=shell)
            for field in _extra_info_fields:
                if info[field]:
                    append_field(bundle, field.capitalize(), field, py_formatter, shell=shell)


    if "candidates" in info:
        append_field(bundle, "See also", "candidates", rst_formatter, shell=shell)

    # shell.user_ns["help_unformatted_bundle"] = bundle
    return bundle

def hinfo(info:oinspect.OInfo, obj:object, oname:str="", detail_level:int = 0, 
          candidates_msg:typing.Optional[str]=None,
          shell:typing.Optional[InteractiveShell]=None) -> oinspect.InfoDict:
    r"""Augments the result of shell.inspector.info() with additional fields.
    
    The actual doctring is mapped to the "docstring" key of the returned object.
    
    .. note::
        Additional fields are defined at module level as ``helputils._extra_info_fields``
    
    Returns:
    ========
    An ``IPython.core.oinspect.InfoDict`` object with additional fields: "methods", 
    "inherited methods", "descriptors", "functions", "classes", "data".
    
 """
    # from core import prog
    from helpsystem import scipyen_doc
    from core.utilities import unique
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()

    # NOTE: 2026-01-02 14:46:25
    # this is the 'basic' oinspect.InfoDict object that the shell's current inspector
    # (by default, an oinspect.Inspector) returns.
    info_dict = shell.inspector.info(obj, oname=oname, info=info, detail_level=detail_level)
    
    # NOTE: 2026-01-08 23:45:18
    # also correct for duplicate subclass names returned by shell.inspector
    subclasses = info_dict.get("subclasses", "")
    if isinstance(subclasses, str) and len(subclasses.strip()):
        subclassnames = sorted(unique(list(map(lambda s: s.__name__, type.__subclasses__(obj)))))
        if len(subclassnames) < 10:
            info_dict["subclasses"] = ", ".join(subclassnames)
        else:
            info_dict["subclasses"] = ", ".join(subclassnames[:10] + ["..."])
    
    # NOTE: 2026-01-02 14:47:36
    # adding the extra fields, to be populated further below
    info_dict.update(**{field: None for field in _extra_info_fields if field not in info_dict})
    
    def _get_sig_or_type(o):
        try:
            sig = f" {inspect.signature(o)}"
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
    # throughout below we extract only the public API
    
    _is_data = lambda x: not(inspect.isclass(x) or inspect.isroutine(x) or inspect.ismethod(x) or inspect.isfunction(x) or inspect.ismodule(x) or _test_docstring(x))
    
    _is_function = lambda x: inspect.isfunction(x) or inspect.isroutine(x) or inspect.ismethod(x)
    
    _is_method = lambda x: inspect.isfunction(x) or inspect.isroutine(x) or inspect.ismethod(x) or inspect.isgenerator(x)
    
    _is_descriptor = lambda x: inspect.isdatadescriptor(x) or inspect.ismemberdescriptor(x) or inspect.isgetsetdescriptor(x)

    # _no_angle = lambda s: s.replace("<", "").replace(">", "")
    # _simple_repr = lambda o: "" if (f"{o}".startswith("<property") and type(o).__name__ == "property") else "(property)" if f"{o}".startswith("<property") else _no_angle(f"{o}")

    _simple_repr = lambda o: "" if type(o).__name__ == "property" else "(" + scipyen_doc.stripid(f"{o}").replace("<", "").replace(">", "") + ")"

    datas = list(sorted(map(lambda f: f"{f[0]} <{type(f[1]).__name__}> {_simple_repr(f[1])}",
                            filter(lambda f: not f[0].startswith("_"), inspect.getmembers_static(obj, _is_data)))))

    # datas = list(sorted(map(lambda f: f"{f[0]}: {type(f[1]).__name__} {_simple_repr(f[1])}",
    #                         filter(lambda f: not f[0].startswith("_"), inspect.getmembers_static(obj, _is_data)))))

    # print(f"helputils.hinfo: datas = {datas}")
    #

    data_str = "\n".join(datas) if len(datas) else ""

    # info_dict["data"] = data_str if len(data_str) else None
    info_dict["data"] = ReSTFormatter().render_code(data_str) if len(data_str) else None
    
    if inspect.ismodule(obj):
        functions = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_function)))))
        info_dict["functions"] = "\n".join(functions) if len(functions) else None
        
        # NOTE: one can define a class as a member of another class (usually that's 
        # private but we drop these)
        classes = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                                filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, inspect.isclass)))))
        info_dict["classes"] = "\n".join(classes) if len(classes) else None
        if "." in obj.__name__:
            pok, parts = shell._find_parts(obj.__name__)
            accmsg = f"    from {'.'.join(parts[:-1])} import {parts[-1]}"
        else:
            accmsg = f"    import {obj.__name__}"
        info_dict["access"] = "\n".join(["Example:", accmsg])

    else:
        objparent = info.obj.__module__ if info.parent is None else info.parent

        objname = prog._get_pyobj_name_(info.obj) or _get_name(info.obj)

        info_dict["access"] = "\n".join(["Example:", f"   from {_get_name(objparent)} import {objname}"])
        
        methods = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_method)))))
        
        ownmethods = list(sorted(filter(lambda f:       f.startswith(info.obj.__name__ if isinstance(info.obj, type) else type(info.obj).__name__), methods)))
        inherited  = list(sorted(filter(lambda f: not   f.startswith(info.obj.__name__ if isinstance(info.obj, type) else type(info.obj).__name__), methods)))
        
        descriptors = list(sorted(map(lambda f: f"{_get_name(f[1])}{_get_sig_or_type(f[1])}", 
                             filter(lambda f: not _get_name(f[1]).startswith("_"), inspect.getmembers_static(obj, _is_descriptor)))))
        # info_dict["methods"] = "\n".join(methods) if len(methods) else None
        info_dict["methods"] = "\n".join(ownmethods) if len(ownmethods) else None
        info_dict["inherited methods"] = "\n".join(inherited) if len(inherited) else None
        info_dict["descriptors"] = "\n".join(descriptors) if len(descriptors) else "\n".join(methods) if len(methods) else None

    if isinstance(candidates_msg, str) and len(candidates_msg.strip()):
        info_dict["candidates"] = candidates_msg
        
    return info_dict

def format_latex(txt:str, imgdir:typing.Optional[typing.Union[TemporaryDirectory, pathlib.Path, str]]=None)->str:
    r"""Replace LaTeX mathematical expressions with ReST ``image`` links.
LaTeX mathematical expressions are rendered as `*.png` files stored in *imgdir*.
 
Returns:
--------
reStructuredText-formatted text with ``.. image::`` directives
"""
    from core import strutils
    # Combined regular expression to capture all types of LaTeX
    latex_combined_pattern = r'(\$\$([^$]*)\$\$|\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}|(\$[^\$]*\$|\\[a-zA-Z]+(?:\{[^\}]*\})?))'

    if isinstance(imgdir, TemporaryDirectory):
        destdir = imgdir.name
    elif isinstance(imgdir, pathlib.Path):
        if not imgdir.is_dir():
            destdir = os.getcwd()
        else:
            destdir = imgdir.as_posix()
    elif isinstance(imgdir, str):
        if not os.path.isdir(imgdir):
            destdir = os.getcwd()
        else:
            destdir = imgdir
    else:
        destdir = os.getcwd()
        
    # Finding all matches
    matches = re.findall(latex_combined_pattern, txt, re.DOTALL)
    
    for k, match in enumerate(matches):
        # match[0] contains the complete matched substring
        # print(f"helputils.format_latex: match {k} = {match[0]}")
        ltx = match[0].strip()
        ll = ltx.replace("\\\\", "\\")
        filepath = pathlib.Path(destdir) / f"png{k}.png"
        pngdata = strutils.render_latex(ll, out="bytes", wrap=ll.startswith("$$"))
        if pngdata:
            with open(filepath.as_posix(), "wb") as pngfile:
                pngfile.write(pngdata)
                
            snippet = f"\n .. image:: {filepath.as_posix()}\n"
            # print(f"\tsnippet {k} = {snippet}")
            
            # snippet = f"\n\n\n .. image:: \n    {filepath.as_posix()}\n    :align: left\n\n"
            
            # if ll.startswith("$$"):
            #     snippet = "\n\n" + snippet + "\n\n"
                
            txt = txt.replace(ltx, snippet)
        else:
            prog.scipywarn(f"LaTeX rendering error for string {ltx}")
        
    return txt
    
def hget_info(imgdir:TemporaryDirectory,
              obj:object, oname:str="",
              info:typing.Optional[oinspect.OInfo]=None,
              detail_level:int = 0, omit_sections:typing.Union[typing.List[str], typing.Tuple[str]] = (),
              candidates_msg:typing.Optional[str]=None,
              shell:typing.Optional[InteractiveShell]=None) -> Bundle:
    r"""Emulates shell.inspector._get_info.
Returns:
--------
A formatted (complete) mime bundle with two fields:
• text/plain
• text/html
"""
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
        
    info_dict = hinfo(info, obj, oname=oname, detail_level=detail_level,
                      candidates_msg=candidates_msg, shell=shell)
    
    # WARNING NOTE: 2026-01-17 22:17:04 for debugging only; comment out when finished
    # shell.user_ns["mainWindow"].assignToWorkspace("info_dict", info_dict)

    omit_sections = list(omit_sections)
    
    bundle = hmake_info_unformatted(obj, info_dict,
                                    detail_level = detail_level, 
                                    omit_sections = omit_sections,
                                    imgdir = imgdir,
                                    shell = shell) 
    
    # ### BEGIN NOTE: 2026-01-03 16:27:39 I don't think this is necessary
    #
    # if shell.inspector.mime_hooks:
    #     hook_data = oinspector.InspectorHookData(
    #         obj=obj,
    #         info=info,
    #         info_dict=info_dict,
    #         detail_level=detail_level,
    #         omit_sections=omit_sections,
    #     )
    #     for key, hook in self.mime_hooks.items():  # type:ignore
    #         required_parameters = [
    #             parameter
    #             for parameter in inspect.signature(hook).parameters.values()
    #             if parameter.default != inspect.Parameter.default
    #         ]
    #         if len(required_parameters) == 1:
    #             res = hook(hook_data)
    #         else:
    #             warnings.warn(
    #                 "MIME hook format changed in IPython 8.22; hooks should now accept"
    #                 " a single parameter (InspectorHookData); support for hooks requiring"
    #                 " two-parameters (obj and info) will be removed in a future version",
    #                 DeprecationWarning,
    #                 stacklevel=2,
    #             )
    #             res = hook(obj, info)
    #         if res is not None:
    #             bundle[key] = res
    #
    # ### END   NOTE: 2026-01-03 16:27:39 I don't think this is necessary
                
    # ret = HyperBundle()
    # ret.update(shell.inspector.format_mime(bundle))
    # return ret
    return shell.inspector.format_mime(bundle)
    
def hpinfo(cmd, namespaces = None, detail_level:int=0, imgdir=None,
           to_console:bool=False,
           shell:typing.Optional[InteractiveShell]=None) -> tuple:
    r"""Emulates a IPython pinfo call"""
    # NOTE: 2026-01-17 22:09:35:
    # to fix bugs, bypass hinspect and use:
    # in sequence, prog.object_find then helpdisp, or
    # hget_info

    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
    ret = None
    reformat = False
    
    with io.StringIO() as bf:
        try:
            pinfo,qmark1,oname,qmark2 = re.match(r'(pinfo )?(\?*)(.*?)(\??$)',cmd).groups()
            if pinfo or qmark1 or qmark2:
                detail_level = 1
            if "*" in oname:
                redirect_psearch(bf, oname, shell=shell)
                reformat=True
            else:
                # NOTE: 2025-12-27 13:53:06
                # this branch actually runs the ipython "help" algorithm ↦
                # extracts various useful information about the object, including 
                # its docstring; imgdir, if present, is used when rendering LaTeX
                # strings embedded in the docstrings
                hinspect(bf, oname, namespaces=namespaces,
                         detail_level = detail_level,
                         imgdir=imgdir,
                         shell=shell
                         )
                reformat=False
                
            ret = bf.getvalue()

        except:
            traceback.print_exc()
            
    if to_console:
        ret = HyperBundle()
        ret.update({"text/plain":"", "text/html":ret})
        return ret
    
    return ret, reformat
     
def hinspect(bf:io.StringIO, oname=str, namespaces=None,
             imgdir:typing.Optional[TemporaryDirectory]=None,
             shell:typing.Optional[InteractiveShell]=None, **kw):
    r"""Stand-in for shell._inspect, called by pinfo magic.
    Named as `hinspect` to avoid clash with the standard library module `inspect`.

    NOTE: executing '?symbol' or 'symbol?' in console triggers the following call 
    chain:

    NamespaceMagics.pinfo (parameter_s = "", namespaces = None) 
        with 'parameter_s' being the symbol and 'namespaces' set to None (default)
    ↓
    pinfo,qmark1,oname,qmark2 = re.match(r'(pinfo )?(\?*)(.*?)(\??$)',parameter_s).groups()
        
    shell._inspect("pinfo", oname) ← role taken up by THIS function, which also 
                                     redirects output to 'bf' (a StringIO )
    ↓
    page.page(data, start, screen_lines, pager_cmd) with:       
        data: a Bundle/dict generated in shell._inspect() — actually, here, by hinspect; 
        start: 0
        screen_lines: 0
        pager_cmd: None
                                    ← role of page is taken up by bf_page function
                                      in this module
    ⇊
    eiher 
        • shell.hooks.show_in_pager
        • page.pager_page(data)
"""
    from core.prog import scipywarn
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()

    detail_level = kw.get("detail_level", 0)

    info, msg, candidates = prog.object_find(oname, namespaces, shell=shell, with_candidates=True) # info is an oinspect.OInfo object

    candidates_msg = None
    
    if len(candidates):
        rstfmt = ReSTFormatter()
        get_parent_name = lambda o: f"in '{prog._get_pyobj_name_(o)}' {type(o).__name__}" if o is not None else f'{prog._get_pyobj_name_(o)}'

        cndlst = "\n".join(list(map(lambda c: f"• {c[0]} {get_parent_name(c[1].parent)}", sorted(list(candidates), key=lambda x: x[0]))))
        candidates_msg = rstfmt.render_code(cndlst)
    
    if info.found or hasattr(info.parent, oinspect.HOOK_NAME):
        helpdisp(imgdir, info, bf, oname, detail_level, candidates_msg=candidates_msg, shell=shell)
    else:
        bf.write(msg)
        
def run_python_help(cmd:str, enable_html=True, imgdir=None,
                    shell:typing.Optional[InteractiveShell]=None) -> str | None:
    print(f"helpsystem.helputils.run_python_help → pydoc.Helper(cmd={cmd})")
    ret = None
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
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
        ret_bundle = shell.inspector.format_mime(format_python_help_output(make_python_help_dict(ret, special), shell=shell))
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
    
    sections = list(map(lambda x: x.lower(), PYTHON_HELP_SECTIONS))
    helpdict = PythonHelpDict(**{field:None for field in sections})
    
    section = special if special else None
    
    for k, line in enumerate(lines):
        if k==0:# and line.startswith("Help on"):
            helpdict[line] = None
            if "function" in line:
                helpdict[line] = list()
                section = line
        else:
            if line.lower() in helpdict:
                section = line.lower()
            else:
                if section:
                    if section not in helpdict or not isinstance(helpdict[section], list):
                        helpdict[section] = list()
                    helpdict[section].append(line)
                    
    for section in helpdict:
        slist = helpdict[section]
        if isinstance(slist, list):
            helpdict[section] = "\n".join(slist)
            
    return helpdict

def format_python_help_output(data:PythonHelpDict, formatter=None,
                              shell:typing.Optional[InteractiveShell]=None):
    r"""Attempt for format standard Python help output similarly to IPython's help output.
 """
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
        
    bundle: UnformattedBundle = {
        "text/plain": [],
        "text/html": [],
    }
    
    if formatter is None:
        formatter = format_screen

    _format = lambda t: shell.inspector.format(t)
    
    def pyrst_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': mypylight(text)
        }
    
    def pyhelp_formatter(text) -> Bundle:
        return {
            'text/plain': _format(text),
            'text/html': rst_to_html_with_highlighting(text)
            }
    
    def pyappend_field(bundle:UnformattedBundle, title:str, key:str, hd:PythonHelpDict, formatter):
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
            pyappend_field(bundle, title, titlekey, data, pyhelp_formatter)
        except:
            # traceback.print_exc()
            pyappend_field(bundle, title, titlekey, data, format_screen)
                
    else:
        titlekey = ""
        
    for key in data:
        if key != titlekey:
            if data[key]:
                fmt = pyrst_formatter if key in ("data", "classes", "functions") else formatter
                pyappend_field(bundle, key.capitalize(), key, data, fmt)
        
    return bundle
    

def run_help_command(cmd:str, namespaces=None, imgdir=None,
                     shell:typing.Optional[InteractiveShell]=None, **kw) -> str | None:
    """
kw: 
enable_html: bool, default, is True
detail_level: int, 0 or 1, default is 0
"""
    # NOTE: 2025-10-13 11:21:18
    # code shamelessly adapted/copied from IPython
    
    # print(f"helpsystem.helputils.run_help_command({cmd})")
    from IPython.core.magic import Magics, magics_class, line_magic, magic_escapes 
    import pydoc, traceback
    if not isinstance(cmd, str) or len(cmd.strip()) == 0:
        return
    
    if not isinstance(shell, InteractiveShell):
        shell = guiutils.getScipyenConsoleShell()
    
    detail_level = kw.get("detail_level", 0)
    # enable_html = kw.get("enable_html", True)
    
    ret = None
    reformat:bool = False
    
    if cmd.startswith("help"):
        cmd = cmd.strip("help").strip("(").strip(")").strip("\"")
        if len(cmd) == 0:
            cmd = "help"
        ret = run_python_help(cmd, imgdir=imgdir, shell=shell)
        reformat = False
        
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
                    redirect_psearch(bf, s, shell=shell)
                    ret = bf.getvalue()
                    if len(ret.strip()) == 0:
                        ret = f"Nothing found matching the pattern {s}<p>"
                    # print(f"run_help_command {cmd} -> ret = {ret}")
                    reformat = True
                    
            else:
                ret, reformat = hpinfo("psearch", namespaces, detail_level = detail_level,
                                       imgdir=imgdir, shell=shell)#, enable_html=enable_html)
                
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
            # print(f"helpsystem.helputils.run_help_command for ? command: cmd = {cmd}")
            
            # NOTE: 2026-01-03 22:11:32
            # this also works when cmd does not have '?' in it 
            ret, reformat = hpinfo(cmd, namespaces, detail_level = detail_level,
                                   imgdir=imgdir, shell=shell)#, enable_html = enable_html)

        if not isinstance(ret, str):
            ret = f"No Python documentation found for {cmd}"
            ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
            reformat = True
        elif ret.startswith("No Python documentation found"):
            ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
            reformat = True
        
    return ret, reformat

