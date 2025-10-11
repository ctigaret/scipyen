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

import sys, os, typing, inspect, types, importlib, io, dataclasses, inspect
from functools import (singledispatch, partial)
from contextlib import redirect_stdout

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

# NOTE: 2025-05-31 17:15:38
# do NOT place this file deeper than one level below scipyen directory
__module_path__ = os.path.abspath(os.path.dirname(__file__))
_scipyendir_ = os.path.dirname(__module_path__)

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
        scipywarn(f"Expecting a str ot a list of str; instead got {type(msg).__name__}")
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
    out.append(f"<h3>{header}</h3>")
    out.append("<h4>Python package modules:</h4>")
    out.append(make_HTML_table(env_pkg_names, columns))
    out.append("<p>")
    out.append("<h4>Python non-package modules:</h4>")
    out.append(make_HTML_table(env_non_pkg_names, columns))
    out.append("<p>")
    out.append("<h4>Scipyen's package modules:</h4>")
    out.append(make_HTML_table(scipyen_pkg_names, columns))
    out.append("<p>")
    out.append("<h4>Scipyen's non-package modules:</h4>")
    out.append(make_HTML_table(scipyen_non_pkg_names, columns))
    out.append("<p>")
    if len(plugin_names):
        out.append("<h4>Scipyen's plugin modules:</h4>")
        out.append(make_HTML_table(plugin_names, columns))
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
    
def info_components(ns:dict) -> str:
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
    
    def _get_info_(name:str, minfo:tuple):
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
        line = _get_info_(name, minfo)
        if isinstance(line, str) and len(line.strip()):
            txt.append(line)
    txt.append("</ul>")
    
    txt.append('<h3>User Interface & Plotting Frameworks</h3>')
    txt.append("<ul>")
    for name, minfo in address_map["User Interface & Plotting Frameworks"].items():
        line = _get_info_(name, minfo)
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

def dummy_pager(self, data, start, screen_lines, out = None):
    if isinstance(data, dict):
        data = data['text/plain']
        
    print(f"data: {data}", file=out)
    # return data
    

def run_help_command(cmd:str, shell:typing.Optional[object]=None) -> str | None:
    import pydoc, importlib, types, traceback, contextlib
    if not isinstance(cmd, str) or len(cmd.strip()) == 0:
        return

    # return pydoc.render_doc(eval(cmd), title = cmd, forceload = 1, renderer = pydoc.html)

    ret = None
    
    with io.StringIO() as bf:
        helper = pydoc.Helper(output = bf)
        try:
            helper.help(cmd)
            ret = bf.getvalue()
            bf.flush()
        except:
            traceback.print_exc()

            
    # if isinstance(ret, str) and any(v in ret for v in ("No Python documentation found", "not found")):
    #     if shell:
    #         with io.StringIO() as bf, contextlib.redirect_stdout(bf):
    #             shell.run_line_magic("pinfo", cmd)
    #             ret = bf.getvalue()
                
    if isinstance(ret, str) and any(v in ret for v in ("No Python documentation found", "not found")):
        ret += "\nCheck the spelling; you may need to enter a valid dotted path e.g. 'package.module.object.member'"
        
    return ret
                
