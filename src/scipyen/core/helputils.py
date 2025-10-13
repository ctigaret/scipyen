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
from IPython.utils.text import DollarFormatter, LSString, SList, format_screen
from IPython.utils.wildcard import list_namespace, typestr2type
from IPython.core.usage import interactive_usage as shell_usage

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

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

def isDarkGui() -> bool:
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    return v <= 128

def mypylight(code):
    # return highlight(code, PythonLexer(), HtmlFormatter(noclasses=True, nobackground=True))
    if isDarkGui():
        style = "KeplerDark"
    else:
        style="default"
    return highlight(code, PythonLexer(), HtmlFormatter(noclasses=True, nobackground=True, style=style))
    # return highlight(code, PythonLexer(), HtmlFormatter(nobackground=True, style="native"))

def make_HTML_table(msg:str|list[str], cols:typing.Optional[int] = None) -> str:
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
    # if cols is None:
        
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
            out += ["<td>", items[k], "</td>"]
            k += 1
            if c == cols-1:
                out.append("</tr>")
            c += 1
                
    out.append("</table>")
    
    return "\n".join(out)

# def help_query_scipyen(items:list[str]): 
#     # TODO 2025-06-01 12:41:50 finalize me
#     env_pkginfos, env_nonpkginfos, scipyen_pkginfos, scipyen_nonpkginfos, plugins = listmodules()
#     # env_pkgnames = list(map(lambda i: i.name, env_pkginfos))
#     # env_nonpkgnames = list(map(lambda i: i.name, env_nonpkginfos))
#     scipyen_pkgnames = list(map(lambda i: i.name, scipyen_pkginfos))
#     scipyen_nonpkgnames =list(map(lambda i: i.name, scipyen_nonpkginfos))
#     
#     for item in items:
#         if isinstance(item, str) and len(item.strip()):
#             if item in scipyen_pkgnames:
#                 index = scipyen_pkgnames.index[item]
#                 info = scipyen_pkginfos[index]
#                 
# def help_data_workspace(items:list[str]):
#     # TODO 2025-06-01 12:41:50 finalize me
#     from core.prog import scipywarn
#     if len(items) == 0 or not all(isinstance(i, str) for i in items):
#         scipywarn(f"Invalid items for help_data_workspace: {items}")
#         return
    
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
   # infos = list(filter(lambda s: "." not in s, map(lambda i: i.name, walk_packages())))
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
        detail_level=0, enable_html=True):#, omit_sections=()):#,
        # start: int = 0, screen_lines: int = 0, ):
    r"""Stand-in for oinspect.Inspector.pinfo"""
    from core.prog import scipywarn
    assert info is not None
    
    original_pylight = oinspect.pylight
    oinspect.pylight = mypylight
    info_dict = shell.inspector.info(info.obj, oname, info, detail_level)
    info_b = shell.inspector._get_info(
        obj, oname, formatter, info, detail_level)#, omit_sections=omit_sections
    
    # TODO: 2025-10-13 02:07:14 BUG/FIXME
    # supplement with a list of method signatures when detail_level is 0
    # source = info_dict.get("source", None)
    # if not inspect.ismodule(obj) and (not isinstance(source, str) or len(source) == 0):
    #     methods = inspect.getmembers_static(obj, inspect.isfunction)
    #     if len(methods):
    #         methods_html = list()
    #         methods_txt = list()
    #         methods_txt.append("METHODS")
    #         for m in methods:
    #             m_name = m[0]
    #             m_sig = f"{m[1].__module__}.{m[1].__qualname__}{str(inspect.signature(m[1]))}"
    #             # methods_html.append(f"<h3>{m_name}:</h3><br>{m_sig}")
    #             methods_html.append(f"{m_sig}")
    #             methods_txt.append(f"{m_name}: {m_sig}")
    #         info_b["text/html"] += f"<h1>Methods<h1>{oinspect.pylight('\n'.join(methods_html)).replace('\n', '<br>')}"
    #         info_b["text/plain"] += "\n".join(methods_txt)
        
    oinspect.pylight = original_pylight
    
    if enable_html:
        strng = info_b["text/html"]
        strng = strng.replace("<br>", "").replace("\n", "<br>\n").replace("<p>", "<br>").replace("<br><br>", "<br>").replace("</h1><br>", "</h1>")
    else:
        strng = info_b['text/plain']

    bf_page(bf, strng)
    
def bf_page(bf:io.StringIO, strng:str):
    for line in strng.splitlines():
        bf.write(line)
   
        
def shellpsearch(shell, bf:io.StringIO, parameter_s='', 
                 list_types:bool=False, ignore_case:typing.Optional[bool]=None,
                 show_all:bool=True):
        def_search = ['user_local', 'user_global', 'builtin']

        # Process options/args
        # opts,args = parse_options(parameter_s,'cias:e:l',list_all=True)
        # opt = opts.get
        # psearch = shell.inspector.psearch
        
        # # select list object types
        # list_types = False
        # if 'l' in opts:
        #     list_types = True
        # 
        # # select case options
        # if 'i' in opts:
        #     ignore_case = True
        # elif 'c' in opts:
        #     ignore_case = False
        # else:
        if not isinstance(ignore_case, bool):
            ignore_case = not shell.wildcards_case_sensitive

        # Build list of namespaces to search from user options
        # def_search.extend(opt('s',[]))
        # ns_exclude = ns_exclude=opt('e',[])
        # ns_search = [nm for nm in def_search if nm not in ns_exclude]
        ns_search = def_search
        # Call the actual search
        try:
            hpsearch(shell, bf, parameter_s, ns_search,
                    show_all=show_all, ignore_case=ignore_case, list_types=list_types)
        except:
            shell.showtraceback()
    
        
def hpsearch(shell, bf:io.StringIO, pattern, ns_search=[],
             ignore_case=False, show_all=False, list_types=False):
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
            if name not in shell.ns_table:
                raise ValueError('invalid namespace <%s>. Valid names: %s' %
                                 (name, shell.ns_table.keys()))

        # print('type_pattern:',type_pattern)  # dbg
        search_result, namespaces_seen = set(), set()
        for ns_name in ns_search:
            ns = shell.ns_table[ns_name]
            # Normally, locals and globals are the same, so we just check one.
            if id(ns) in namespaces_seen:
                continue
            namespaces_seen.add(id(ns))
            tmp_res = list_namespace(ns, type_pattern, filter,
                                    ignore_case=ignore_case, show_all=show_all)
            search_result.update(tmp_res)

        bf_page(shell, bf, '\n'.join(sorted(search_result)))
    
def get_object_info(shell, oname=str, namespaces=None) -> oinspect.OInfo:
    info = shell._object_find(oname, namespaces)
    if not info.found:
        # this happens when the first part in oname is not found by the shell
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
                    break
                
        if isinstance(sinfo, oinspect.OInfo) and sinfo.found:
            return sinfo
        # else:
        #     return oinspect.object_info(name=oname, found=False)
            
    return info
    
def hpinfo(shell, cmd, namespaces = None, detail_level:int=0,
                                    enable_html:bool=True):
    ret = None
    reformat = False
    
    with io.StringIO() as bf:
        try:
            pinfo,qmark1,oname,qmark2 = re.match(r'(pinfo )?(\?*)(.*?)(\??$)',cmd).groups()
            if pinfo or qmark1 or qmark2:
                detail_level = 1
            if "*" in oname:
                shellpsearch(shell, bf, oname)
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
    
    if info.found or hasattr(info.parent, oinspect.HOOK_NAME):
        info_dict = shell.inspector.info(info.obj, oname, info, detail_level)
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

def run_python_help(cmd:str) -> str | None:
    import pydoc, traceback
    ret = None
    with io.StringIO() as bf:
        helper = pydoc.Helper(output = bf)
        try:
            helper.help(cmd)
            ret = bf.getvalue()
            reformat=True
            # bf.flush()
        except:
            traceback.print_exc()
    if not isinstance(ret, str) or len(ret.strip()) == 0:
        ret = f"No Python documentation found for {cmd}"
        ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
    return ret

def format_python_help_output(data:str):
    lines = data.splitlines()
    formatted_lines = list()
    for line in lines:
        if line.startswith("Help on"):
            formatted_lines.append(f"<h1>{line}</h1>")
        elif any(line.startswith(v) for v in PYTHON_HELP_SECTIONS):
            formatted_lines.append(f"<h2>{line}</h2>")
        else:
            formatted_lines.append(f"{line}<br>")
    return "\n".join(formatted_lines)

def run_help_command(shell, cmd:str, namespaces=None, **kw) -> str | None:
    """
kw: 
enable_html: bool, default, is True
detail_level: int, 0 or 1
"""
    # print(f"core.helputils.run_help_command({cmd})")
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
        ret = run_python_help(cmd)
        reformat = True
        
    else:
        if cmd in ("?", "??"):
            # bf_page(bf, shell_usage)
            ret = shell_usage
            reformat=True
            
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
                                    enable_html = enable_html,
                                    )

               
        if isinstance(ret, str):
            if ret.startswith("No Python documentation found"):
                ret = run_python_help(cmd)
                reformat = True
        else:
            ret = f"No Python documentation found for {cmd}"
            ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
            reformat = True
        
    return ret, reformat
