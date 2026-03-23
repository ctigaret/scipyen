# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Various helpers for GUI
"""
import sys, os, typing, warnings, math, io, pathlib, traceback, numbers
from enum import IntEnum
import numpy as np
from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
from core.utilities import get_least_pwr10

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


# import qtpy
# qtpy.API = os.environ["QT_API"]
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import (QtCore, QtWidgets, QtGui)
#     QAction = QtGui.QAction
# else:
#     from qtpy import (QtCore, QtWidgets, QtGui)
#     QAction = QtWidgets.QAction

from gui.painting_shared import (FontStyleType, standardQtFontStyles,
                                 FontWeightType, standardQtFontWeights)

import quantities as pq
from core.pyqtgraph_patch import pyqtgraph as pg

from core import strutils, xmlutils

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4


class UnitsStringValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super(UnitsStringValidator, self).__init__(parent)

    def validate(self, s, pos):
        try:
            u = eval("1*%s" % (s[0:pos]), pq.__dict__)
            return QtGui.QValidator.Acceptable

        except:
            return QtGui.QValidator.Invalid

class NumericStringValidator(QtGui.QValidator):
    r"""WARNING: Don't use yet"""
    def __init__(self, parent = None):
        super().__init__(parent)

    # def validate(self, s:str, pos: int) -> QtGui.QValidator.State:
    def validate(self, s:str, pos: int) -> tuple:
        r"""Implements Validator.validate().
.. warning::

    Unlike the Qt6 class, which returns only, QtGui.QValidator.State,  PyQt6 this is supposed to return a triple: QtGui.QValidator.State, str, int

"""
        from core.strutils import isnumber, is_sequence
        import core.scipyen_quantities as scq
        # from core.datatypes import is_numeric_string

        ss = s[0:pos] if (pos >=-len(s) or pos < len(s)) else s

        # print(f"{self.__class__.__name__}.validate('{s}', {pos}) -> '{ss}'")

        if s is None or isinstance(s, str) and len(s.strip()) == 0:
            # print(f"{self.__class__.__name__}: None or empty string -> Intermediate")
            return QtGui.QValidator.Intermediate, s, pos

        if not isinstance(s, str):
            # print(f"{self.__class__.__name__}.validate: no string -> Invalid")
            return QtGui.QValidator.Invalid, s, pos

        if pos > len(s) or pos < -len(s):
            # print(f"{self.__class__.__name__}.validate: out of bounds -> Invalid")
            return QtGui.QValidator.Invalid, s, pos

        if not isnumber(ss) and not is_sequence(ss):
            # print(f"{self.__class__.__name__}.validate: not a number or sequence -> Intermediate")
            return QtGui.QValidator.Intermediate, s, pos

        try:
            # BUG: 2026-03-20 16:26:39 FIXME/TODO:
            # allow naked sequence forms and naked quantity forms e.g.
            # 0.2 s, 0.3 s
            u = eval(ss)
            # print(f"{self.__class__.__name__}.validate: Acceptable")
            return QtGui.QValidator.Acceptable, s, pos

        except SyntaxError:
            flag, match, string, delims = is_sequence(ss, True, True)
            # print(f"{self.__class__.__name__}.validate: -> delims = {delims}")
            if len(delims) and len(delims[-1].strip()):
                try:
                    # parts = tuple(map(lambda x: scq.str2quantity(x), ss.split(delims[-1])))
                    parts = tuple(map(lambda x: scq.str2quantity_2(x), ss.split(delims[-1])))
                    # print(f"{self.__class__.__name__}.validate: -> parts = {parts}")
                    if all(isinstance(v, (numbers.Number, pq.Quantity)) for v in parts):
                        if len(ss) == len(s):
                            # print(f"\t: => Acceptable")
                            return QtGui.QValidator.Acceptable, s, pos
                        else:
                            # print(f"\t: => Intermediate")
                            return QtGui.QValidator.Intermediate, s, pos

                    else:
                        # print(f"\t: => Invalid")
                        return QtGui.QValidator.Invalid, s, pos

                except:
                    traceback.print_exc()
                    # print(f"{self.__class__.__name__}.validate: -> cannot parse inner string => Invalid")
                    return QtGui.QValidator.Invalid, s, pos
            else:
                # print(f"{self.__class__.__name__}.validate: -> no delims => Intermediate")
                traceback.print_exc()
                return QtGui.QValidator.Intermediate, s, pos

        except Exception as e:
            # print(f"{self.__class__.__name__}.validate: -> {e} => Invalid")
            traceback.print_exc()
            return QtGui.QValidator.Invalid, s, pos

class InftyDoubleValidator(QtGui.QDoubleValidator):
    def __init__(self, bottom:float=-math.inf, top:float=math.inf,
                 decimals:int=4, suffix:str="", prefix:str="",
                 parent=None):
        QtGui.QDoubleValidator.__init__(self,parent)
        self.setBottom(bottom)
        self.setTop(top)
        self.setDecimals(decimals)
        self.suffix = suffix if isinstance(suffix, str) and len(suffix.strip()) else ""
        self.prefix = prefix if isinstance(suffix, str) and len(prefix.strip()) else ""

    def validate(self, s:str, pos:int) -> tuple:
        sfxndx = s.find(self.suffix)
        ss = s
        if sfxndx > 0:
            ss = ss[:sfxndx]

        if len(self.prefix):
            ss = ss[len(self.prefix):]

        ss = ss.strip()

        # ss = s.strip(self.suffix)
        # ### BEGIN
        # pname = f"{self.parent.objectName()}: " if isinstance(self.parent, QtWidgets.QWidget) else ""
        # print(f"{pname}{self.__class__.__name__}.validate(s={s}, pos={pos}): ss -> {ss}")
        # ### END

        if ss.lower() in ("-", "-i", "i", "-in", "in"):
            # print('\tone of "-", "-i", "i", "-in", "in"')
            ret = (QtGui.QValidator.Intermediate, ss, pos)

        elif ss.lower() in ("-inf", "inf"):
            ret = (QtGui.QValidator.Acceptable, ss, pos)

        elif strutils.isnumber(ss):
            ret = (QtGui.QValidator.Acceptable, ss, pos)

        else:
            ret = super().validate(ss, pos)

        # state, substring, pos = (ret[0], ret[1], ret[2])
        state, substring, pos = (ret[0], ret[1] + self.suffix, ret[2])

        # oName = ""
        # objectName = ""
        # if self.parent():
        #     objectName = self.parent().objectName()
        #     if objectName:
        #         oName = objectName + ": "
        # if objectName.endswith("startSpinBox"):
        #     print(f"{oName}{self.__class__.__name__}.validate(s = '{s}', pos={pos}): suffix = '{self.suffix}', ss = '{ss}' -> {state}")

        return (state, substring, pos)

class ComplexValidator(InftyDoubleValidator):
    def __init__(self, bottom:float=-math.inf, top:float=math.inf, decimals:int=4, parent=None):
        InftyDoubleValidator.__init__(self, bottom, top, decimals, parent)
        self.setBottom(bottom)
        self.setTop(top)
        self.setDecimals(decimals)

    def validate(self, s:str, pos:int):
        valid = super().validate(s, pos)
        if valid[0] not in (QtGui.QValidator.Intermediate, QtGui.QValidator.Acceptable):
            s_ = s.strip("()") # strip away the parantheses & any space
            s_parts = s.split("+") # is it canonical form?
            if len(s_parts) == 2:
                real = s_parts[0]
                imag = s_parts[1]
            elif len(s_parts) == 1:
                real = s_parts[1]
                imag = None

            real_valid = super().validate(real, pos)

            if real_valid[0] in (QtGui.QValidator.Intermediate, QtGui.QValidator.Acceptable):
                if imag is None:
                    return (real_valid[0], s, pos)
                else:
                    if imag.lower().endswith("j"):
                        imag = imag.lower().strip("j")

                    imag_valid = super().validate(imag, pos)
                    return (imag_valid[0], s, pos)

            else:
                return (QtGui.QValidator.Invalid, s, pos)

def getDesktopScreen():
    if os.environ["QT_API"] == "pyside6":
        return QtWidgets.QApplication.primaryScreen()
    else:
        desktop = QtWidgets.QApplication.desktop()
        # geometry = desktop.screenGeometry(desktop.primaryScreen())
        return  QtWidgets.QApplication.screens()[desktop.primaryScreen()]


def getDesktopHeight():
    return getDesktopGeometry().height()

def getDesktopGeometry():
    # if os.environ["QT_API"] == "pyside6":
    if __has_PyQt6__ or __has_PySide6__:
        pos = QtGui.QCursor.pos()
        screen = QtWidgets.QApplication.screenAt(pos)
        if(screen):
            return screen.geometry()
        else:
            raise RuntimeError("No screens found!")
    else:
        return QtWidgets.QApplication.desktop().geometry()

def getScipyenMainWindow() -> QtWidgets.QMainWindow | None:
    # NOTE: 2026-01-04 22:33:13
    # this is redundant: there's already core.workspacefunctions.getMainScipyenWindow()
    # but I'd rather use this one as it is more direct (the one in workspacefunctions
    # is a bit convoluted as it walks up the call stack — or frames — and may fail)
    windows = list(filter(lambda w: "ScipyenWindow" in type(w).__name__, QtWidgets.QApplication.topLevelWidgets()))
    assert len(windows)==1, "Not a Scipyen session"
    mainWindow = windows[0]
    return mainWindow

def getScipyenConsoleShell() -> InProcessInteractiveShell:
    # windows = list(filter(lambda w: "ScipyenWindow" in type(w).__name__, QtWidgets.QApplication.topLevelWidgets()))
    # assert len(windows)==1, "Not a Scipyen session"
    # mainWindow = windows[0]
    mainWindow = getScipyenMainWindow()
    shell = mainWindow.shell
    assert isinstance(shell, InProcessInteractiveShell), "Not using an in-process interactive shell"
    return shell

def validatorString(val:typing.Union[QtGui.QValidator.State, int]):
    r"""String representation of a QValidator.State value
    """
    if not isinstance(val, (QtGui.QValidator.State, int)):
        return "Invalid"

    return "Acceptable" if val == QtGui.QValidator.Acceptable else "Intermediate" if val == QtGui.QValidator.Intermediate else "Invalid"

def getPlotItemDataBoundaries(item:pg.PlotItem):
    r"""Calculates actual data bounds (data domain, `X`, and data range, `Y`)
    NOTE: 2022-11-21 16:11:36
    Unless there is data plotted, this does not rely on PlotItem.viewRange()
    because this extends outside of the data domain and data range.
    """
    [[vxmin, vxmax], [vymin, vymax]] = item.viewRange()
    plotDataItems = [i for i in item.listDataItems() if isinstance(i, pg.PlotDataItem) and all(v is not None for v in (i.xData, i.yData))]
    if len(plotDataItems): # no data plotted
        mfun = lambda x: -np.inf if x is None else x
        pfun = lambda x: np.inf if x is None else x

        xmin = min(map(mfun, [min(p.xData) for p in plotDataItems]))
        xmax = max(map(pfun, [max(p.xData) for p in plotDataItems]))
        ymin = min(map(mfun, [min(p.yData) for p in plotDataItems]))
        ymax = max(map(pfun, [max(p.yData) for p in plotDataItems]))

        if np.isinf(xmin) or np.isnan(xmin):
            xmin = vxmin

        if np.isinf(xmax) or np.isnan(xmax):
            xmax = vxmax

        if np.isinf(ymin) or np.isnan(ymin):
            ymin = vymin

        if np.isinf(ymax) or np.isnan(ymax):
            ymax = vymax

    else:
        xmin = vxmin
        xmax = vxmax
        ymin = vymin
        ymax = vymax
        # [[xmin, xmax], [ymin, ymax]] = item.viewRange()

    return [[xmin, xmax], [ymin, ymax]]

def getMenuActionsTree(w: typing.Optional[QtWidgets.QWidget] = None):
    return dict(map(lambda a: (a.text().replace("&", ""), (a, getMenuActionsTree(a.menu()))), w.actions())) if w else None

def get_QDoubleSpinBox_params(x:typing.Sequence):
    r"""Return stepSize and decimals for a QDoubleSpinBox given x.

    x is a sequence of numbers
    """
    dd = get_least_pwr10(x)
    if dd < 0:
        return (abs(dd), 10**dd)
    return (0, 1)

def csqueeze(s:str, w:int):
    r"""Returns text elided to the right
    """
    if len(s) > w and w > 3:
        part = (w-3)//2
        return s[0:part] + "..."
    return s

def rsqueeze(s:str, w:int):
    r"""Returns text elided to the right
    """
    if len(s) > w:
        part = w - 3
        return s[0:part] + "..."
    return s

def lsqueeze(s:str, w:int):
    r"""Returns text elided to the left
    """
    if len(s) > w:
        part = w - 3
        return "..." + s[part:]
    return s

def get_current_font_metrics():
    if os.environ["QT_API"] in ("pyqt5", "pyside2"):
        fm = QtWidgets.QApplication.fontMetrics()
    else:
        fm = QtGui.QFontMetrics(QtWidgets.QApplication.instance().font())

    return fm

def get_elided_text(s:str, w:int, elideMode = QtCore.Qt.ElideRight):
    fm = get_current_font_metrics()
    # fm = QtWidgets.QApplication.fontMetrics()
    return fm.elidedText(s, elideMode, w)

def get_text_width(s:str, fm:typing.Optional[QtGui.QFontMetrics]=None, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    if not isinstance(fm, QtGui.QFontMetrics):
        fm = get_current_font_metrics()
    if os.environ["QT_API"] == "pyside6":
        sz = fm.size(flags, s, tabStops)
    else:
        sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width()

def get_text_height(s:str, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = get_current_font_metrics()
    # fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.height()

def get_text_width_and_height(s:str, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    # fm = QtWidgets.QApplication.fontMetrics()
    fm = get_current_font_metrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width(), sz.height()

def get_font_style(val:typing.Union[str, FontStyleType]) -> typing.Union[int, QtGui.QFont.Style]:
    r"""Returns an int or a QtGui.QFont.Style enum value

    Always returns QtGui.QFont.StyleNormal if val has wrong type or value.

    Parameter:
    ==========

    val: int (0,1,2)

         str = a font style name (case-sensitive), one of :
            StyleNormal
            StyleItalic
            StyleOblique

        QtGui.QFont.Style enum value (see Qt documentation for details)

    """
    # print(f"guiutils.get_font_style(val: {val} [type {type(val).__name__}])")
    if isinstance(val, str) and len(val.strip()):
        ret = standardQtFontStyles.get(val, None) # --> int or None if not found
        if ret is None:
            return QtGui.QFont.StyleNormal

        return ret # --> int

    elif isinstance(val, int):
        if val not in standardQtFontStyles.values():
            # NOTE: 2021-08-29 10:25:46
            # this os different from Qt behavioru where if font.setTyle() is
            # passed an int val < 0 or > 2 it assigns the largest Style value
            # (oblique)
            return QtGui.QFont.StyleNormal

        return val # OK to feed an int to font.setStyle()

    elif isinstance(val, QtGui.QFont.Style):
        return QtGui.QFont.Style(val) # issues when casting in PyQt6 via qtpy
        # return val

    else:
        return QtGui.QFont.StyleNormal


def get_font_weight(val:typing.Union[str, FontWeightType]) -> typing.Union[int, QtGui.QFont.Weight]:
    r"""Returns an int or a QtGui.QFont.Weight eunm value

    Always returns QtGui.QFont.Normal if val has wrong type or value
    """

    if isinstance(val, str) and len(val.strip()):
        ret = standardQtFontWeights.get(val, None)
        if ret is None:
            return QtGui.QFont.Normal

        return ret

    elif isinstance(val, int):
        if val not in standardQtFontWeights.values():
            return QtGui.QFont.Normal

        return val

    elif isinstance(val, QtGui.QFont.Weight):
        return val

    else:
        return QtGui.QFont.Normal

def treeWidgetItems(tree: QtWidgets.QTreeWidget):
    r"""Generator that iterates the QTreeWidgetItems in a QTreeWidget 'tree'
    """
    it = QtWidgets.QTreeWidgetItemIterator(tree)
    while isinstance(it.value(), QtWidgets.QTreeWidgetItem):
        yield it.value()
        it += 1

def isDarkGui() -> bool:
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    return v <= 128

def svgFileForIcon(icon:QtGui.QIcon) -> typing.Sequence[pathlib.Path]:
    name = icon.name()
    if not isinstance(name, str) or len(name.strip()) == 0:
        return list()

    themeName = icon.themeName()
    if not isinstance(themeName, str) or len(themeName.strip()) == 0:
        return list()


    iconFileDirectories = list(filter(lambda p: p.exists(), map(lambda s: pathlib.Path(s), icon.themeSearchPaths())))
    if len(iconFileDirectories) == 0:
        return list()

    found = list()

    for p in iconFileDirectories:
        files = list(filter(lambda x: icon.themeName() in x.as_posix(), p.rglob(f"{name}.svg")))
        if len(files):
            found.extend(list(files))

    if len(found):
        return list(set(found))

    return list()

def svg2pixmap(s:str, scale:float=1.0) -> QtGui.QPixmap:
    if not strutils.is_svg(s) and not isinstance(s, xmlutils.xml.dom.minidom.Document):
        return QtGui.QPixmap()

    w, h = xmlutils.get_svg_size(s)

    if all([v is None for v in (w,h)]):
        return QtGui.QPixmap()
    if w is None:
        w = h
    elif h is None:
        h = w
    pix = QtGui.QPixmap(QtCore.QSize(int(w),int(h)))
    renderer = QtSvg.QSvgRenderer()
    if isinstance(s, str):
        renderer.load(QtCore.QByteArray(bytes(s.encode())))
    else:
        renderer.load(QtCore.QByteArray(bytes(s.toprettyxml().encode())))
    pix.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pix)
    if renderer.isValid():
        defSize = renderer.defaultSize()
        renderSize = defSize * scale
        painter.save()
        bounds = QtCore.QRectF((w - renderSize.width()) / 2,
                            (h - renderSize.height()) / 2,
                            renderSize.width(), renderSize.height())
        painter.setClipRect(bounds)
        renderer.render(painter, bounds)
        painter.restore()
    painter.end()
    return pix




# def testme():
#     import pywt
#     old_stdout = sys.stdout
#     sys.stdout = buffer = io.StringIO()
#
#     help(pywt.wavelist)
#
#     sys.stdout = old_stdout
#
#     txt = buffer.getvalue()
#
#     return txt
