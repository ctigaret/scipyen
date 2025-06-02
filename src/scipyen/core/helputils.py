# -*- coding: utf-8 -*-
# $Id: helputils.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Helper script to replace pydoc "modules" & "apropos" invocation
in order to bypass the issues related to importing problematic modules.
"""
import sys, os, typing, inspect, types, importlib
from qtpy import QtCore, QtWidgets
from core.prog import (safewrapper, safeguiwrapper, scipywarn, print_styled, walk_packages, get_qt_api_for_python)
from core.workspacefunctions import getMainScipyenWindow

# NOTE: 2025-05-31 17:15:38
# do NOT place this file deeper than one level below scipyen directory
__module_path__ = os.path.abspath(os.path.dirname(__file__))
_scipyendir_ = os.path.dirname(__module_path__)

# my_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
# conda_env_prefix = os.environ.get("CONDA_PREFIX", None)
# 
# my_virtualenv = os.environ.get("VIRTUAL_ENV", None)

def make_HTML_table(msg:str|list[str], cols:int) -> str:
    r"""Formats a message to be displayed in a HTML table with ``cols`` columns.
Useful when the message contains a list of names, keywords, etc.
NOTE: The resulted string MUST be embedded somewhere between <body> </body> HTML tags. 
"""
    if isinstance(msg, str):
        items = list(sorted(map(lambda x: x.strip(), filter(lambda x: len(x.strip()), msg.replace("\n", " ").split(" ")))))
    elif isinstance(msg, list) and all(isinstance(s, str) for s in msg):
        items = msg
    else:
        scipywarn(f"Expecting a str ot a list of str; instead got {type(msg).__name__}")
        return "<table></table>"
    
    out = list()
    out.append("<table>")
    k = 0
    while k < len(items):
        c = 0
        while c < cols:
            if k == len(items):
                break
            if c == 0:
                out.append("<tr>")
            out += ["<td>", items[k], "</td>"]
            k += 1
            if c == 3:
                out.append("</tr>")
            c += 1
                
    out.append("</table>")
    
    return "\n".join(out)

def help_query_scipyen(items:list[str]): 
    # TODO 2025-06-01 12:41:50 finalize me
    env_pkginfos, env_nonpkginfos, scipyen_pkginfos, scipyen_nonpkginfos, plugins = listmodules()
    # env_pkgnames = list(map(lambda i: i.name, env_pkginfos))
    # env_nonpkgnames = list(map(lambda i: i.name, env_nonpkginfos))
    scipyen_pkgnames = list(map(lambda i: i.name, scipyen_pkginfos))
    scipyen_nonpkgnames =list(map(lambda i: i.name, scipyen_nonpkginfos))
    
    for item in items:
        if isinstance(item, str) and len(item.strip()):
            if item in scipyen_pkgnames:
                index = scipyen_pkgnames.index[item]
                info = scipyen_pkginfos[index]
                
def help_data_workspace(items:list[str]):
    # TODO 2025-06-01 12:41:50 finalize me
    if len(items) == 0 or not all(isinstance(i, str) for i in items):
        scipywarn(f"Invalid items for help_data_workspace: {items}")
        return
    
def format_infos(title:str, header:str, columns:int = 4) -> str:
    env_pkginfos, env_nonpkginfos, scipyen_pkginfos, scipyen_nonpkginfos, plugins = listmodules()
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
    out.append(make_HTML_table(list(sorted(map(lambda i: i.name, env_pkginfos))), columns))
    out.append("<p>")
    out.append("<h4>Python non-package modules:</h4>")
    out.append(make_HTML_table(list(sorted(map(lambda i: i.name, env_nonpkginfos))), columns))
    out.append("<p>")
    out.append("<h4>Scipyen's package modules:</h4>")
    out.append(make_HTML_table(list(sorted(map(lambda i: i.name, scipyen_pkginfos))), columns))
    out.append("<p>")
    out.append("<h4>Scipyen's non-package modules:</h4>")
    out.append(make_HTML_table(list(sorted(map(lambda i: i.name, scipyen_nonpkginfos))), columns))
    out.append("<p>")
    if len(plugins):
        out.append("<h4>Scipyen's plugin modules:</h4>")
        out.append(make_HTML_table(list(sorted(tuple(plugins.keys()))), columns))
        out.append("<p>")
    out.append("</body>")
    out.append("</html>")
    return "\n".join(out)

def listmodules() -> tuple:
    # infos = list(filter(lambda s: "." not in s, map(lambda i: i.name, walk_packages())))
    infos = list(filter(lambda i: "." not in i.name, walk_packages()))
    
    userPluginsInfos = list()
    plugins = dict()
    mainWindow = getMainScipyenWindow()
    scipyeninfos = list(filter(lambda i: _scipyendir_ in i.module_finder.path, infos))
    envinfos = list(filter(lambda i: _scipyendir_ not in i.module_finder.path, infos))
    if isinstance(mainWindow, QtWidgets.QMainWindow) and type(mainWindow).__name__ == "ScipyenWindow":
        userPluginsInfos = list(filter(lambda i: mainWindow.userPluginsDirectory in i.module_finder.path, infos))
        plugins = mainWindow.plugins
        scipyeninfos = list(filter(lambda i: i.name not in plugins, scipyeninfos))
        
    scipyen_pkginfos = list(filter(lambda i: i.ispkg, scipyeninfos))
    scipyen_nonpkginfos = list(filter(lambda i: not i.ispkg, scipyeninfos))
    
    env_pkginfos = list(filter(lambda i: i.ispkg, envinfos))
    env_nonpkginfos = list(filter(lambda i: not i.ispkg, envinfos))
        
        
    return env_pkginfos, env_nonpkginfos, scipyen_pkginfos, scipyen_nonpkginfos, plugins
    
def info_components(ns:dict) -> str:
    r"""Prepares the contents of the Software Components dialog.
Parameters:
==========
ns: the namepace where modules have been imported
"""
    from core.prog import get_module_version
    import IPython
    # modules = dict(filter(lambda i: inspect.ismodule(i[1]), ns.items()))
    
    modinfos = tuple(walk_packages())
    modnames = tuple(map(lambda m: m.name, modinfos))
    
    address_map = {"Data Analysis": {
                                     "numpy":      ("NumPy", "https://numpy.org", "The fundamental package for scientific computing with Python"),
                                     "scipy":   ("SciPy", "https://scipy.org", "Fundamental algorithms for scientific computing in Python"),
                                     "quantities":      ("Quantities", "https://github.com/python-quantities/python-quantities", "A Python package for handling physical quantities."),
                                     "vigra":   ("vigra", "http://ukoethe.github.io/vigra", "The VIGRA Computer Vision Library"),
                                     "neo":     ("Neo", "https://neuralensemble.org/neo", "Neo is a package for representing electrophysiology data in Python"),
                                     "pandas":      ("pandas", "https://pandas.pydata.org", "Open source data analysis and manipulation tool"),
                                     "h5py":    ("h5py", "https://www.h5py.org", "HDF5 for Python"),
                                     "pyABF":   ("pyABF", "https://github.com/swharden/pyABF", "A simple Python interface for Axon Binary Format (ABF) files"),
                                     "pywt":    ("PyWavelets", "https://pywavelets.readthedocs.io/en/latest/index.html", "Wavelet Transforms in Python"),
                                     },
                    "User Interface & Plotting Frameworks": {"matplotlib": ("Matplotlib", "https://matplotlib.org", "MatplotLib: Visualization with Python"),
                                                             "seaborn": ("seaborn", "https://seaborn.pydata.org", "Statistical data visualization"),
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
            '<h2>Software Components of Scipyen¹</h2>',
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
    txt.append('<li> <a href="https://develop.kde.org/frameworks/breeze-icons/">Breeze Icons</a> © <a href="https://kde.org">KDE</a> and licenced under the <a href="https://www.gnu.org/licenses/lgpl-3.0.en.html">GNU LGPL version 3 or later</a></li>')
    txt.append("</ul>")


    txt.append("<p>¹Used or available for use at the console — this is not an exhaustive list, and excludes libraries installed after Scipyen's installation.</p>")
    txt.append("</body>")
    txt.append("</html>")
    
    return "\n".join(txt)

