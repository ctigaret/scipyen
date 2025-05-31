# -*- coding: utf-8 -*-
# $Id: helputils.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Helper script to replace pydoc "modules" & "apropos" invocation
in order to bypass the issues related to importing problematic modules.
"""
import sys, os, typing
from qtpy import QtWidgets
from core.prog import (safewrapper, safeguiwrapper, scipywarn, print_styled, walk_packages)
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
    
