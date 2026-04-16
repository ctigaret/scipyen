# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2022-2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import typing, warnings, math, cmath, os, traceback, dataclasses, sys
import numbers
import numpy as np
import quantities as pq
import pandas as pd
from tribool import Tribool

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


from core.utilities import (get_least_pwr10, unique)
from core.inputspec import InputSpec
from gui.painting_shared import (FontStyleType, standardQtFontStyles,
                                 FontWeightType, standardQtFontWeights)

from gui import quickdialog as qd
from gui.guiutils import (DisplayHint,
    InftyDoubleValidator, ComplexValidator, validatorString, NumericStringValidator,
    get_elided_text, get_text_width)

from core import scipyen_quantities as scq
from core import strutils as strutils
from core import prog
from core import datatypes as dt
from iolib.navigation.navigator import UrlNavigatorButtonBase

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class ElidedPushButton(UrlNavigatorButtonBase):
    def __init__(self, text: str = "", elideText: bool = True, parent = None):
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self._elideText_ = elideText is True
        self.setElideTextAction = QtGui.QAction("Elide text", self)
        self.setElideTextAction.setCheckable(True)
        self.setElideTextAction.setChecked(self._elideText_ is True)
        self.setElideTextAction.toggled.connect(self._slot_setElideText)
        self._text_ = ""
        if isinstance(text, str) and len(text.strip()):
            self.setText(text)

    def paintEvent(self, evt: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        font = QtGui.QFont(self.font())
        painter.setFont(font)
        buttonWidth = self.width()
        preferredWidth = self.sizeHint().width()
        if preferredWidth < self.minimumWidth():
            preferredWidth = self.minimumWidth()

        if buttonWidth > preferredWidth:
            buttonWidth = preferredWidth

        buttonHeight = self.height()
        fgColor = self.foregroundColor()

        self.drawHoverBackground(painter)

        textLeft = 0
        textWidth = buttonWidth

        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        option.rect = QtCore.QRect(0, 0, int(self.width()), int(self.height()))
        option.palette = self.palette()
        option.palette.setColor(QtGui.QPalette.Text, fgColor)
        option.palette.setColor(QtGui.QPalette.WindowText, fgColor)
        option.palette.setColor(QtGui.QPalette.ButtonText, fgColor)

        painter.setPen(fgColor)

        clipped = self.isTextClipped()
        # print(f"{self.__class__.__name__}<{self.plainText()}> clipped: {clipped}")
        textRect = QtCore.QRect(textLeft, 0, textWidth, buttonHeight)

        text = self.plainText()

        if clipped:
            if self._elideText_:
                w = get_text_width(text)
                if w >= buttonWidth:
                    text = get_elided_text(
                            text,
                            buttonWidth,
                            # self.size().width(),
                            QtCore.Qt.ElideMiddle
                    )
            else:
                bgColor = QtGui.QColor(fgColor)
                bgColor.setAlpha(0)
                if __has_PyQt6__ or __has_PySide6__:
                    gradient = QtGui.QLinearGradient(QtCore.QPointF(textRect.topLeft()),
                                                    QtCore.QPointF(textRect.topRight()))
                else:
                    gradient = QtGui.QLinearGradient(textRect.topLeft(), textRect.topRight())
                if leftToRight:
                    gradient.setColorAt(0.8, fgColor)
                    gradient.setColorAt(1.0, bgColor)
                else:
                    gradient.setColorAt(0.0, bgColor)
                    gradient.setColorAt(0.2, fgColor)

                pen = QtGui.QPen()
                pen.setBrush(QtGui.QBrush(gradient))
                painter.setPen(pen)

        textFlags = QtCore.Qt.AlignVCenter if clipped else QtCore.Qt.AlignCenter

        # painter.drawText(textRect, textFlags, self.plainText())
        painter.drawText(textRect, textFlags, text)

    def enterEvent(self, evt:QtGui.QEnterEvent):
        super().enterEvent(evt)

        if self.isTextClipped():
            self.setToolTip(self.plainText())

        evt.accept()

    def leaveEvent(self, evt:QtCore.QEvent):
        super().leaveEvent(evt)

        self.setToolTip("")

        self.update()
        evt.accept()

    def isTextClipped(self):
        availableWidth = self.width() - 2 * self.BorderWidth
        font = self.font()
        return QtGui.QFontMetrics(font).size(QtCore.Qt.TextSingleLine, self._text_).width() >= availableWidth

    def drawHoverBackground(self, painter:QtGui.QPainter):
        backgroundColor = self.palette().color(QtGui.QPalette.Highlight) if self.isHighlighted else QtCore.Qt.transparent
        if not self._active_ and self.isHighlighted:
            backgroundColor.setAlpha(128)
        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)
        option.viewItemPosition = QtWidgets.QStyleOptionViewItem.OnlyOne
        primitive = QtWidgets.QStyle.PE_PanelItemViewItem

        if self.isHighlighted:
            option.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_MouseOver
        else:
            option.state = QtWidgets.QStyle.State_Enabled

        painter.setBackground(backgroundColor)
        self.style().drawPrimitive(primitive, option, painter, self)

    def setText(self, text:str):
        self._text_ = text
        super().setText(self._text_)
        self.updateMinimumWidth()

    def text(self) -> str:
        return self._text_

    def plainText(self) -> str:
        return self._text_

    def resizeEvent(self, evt: QtGui.QResizeEvent):
        self.setText(self._text_)
        super().resizeEvent(evt)
        evt.accept()

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent):
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.setElideTextAction)
        menu.exec(evt.globalPos())

    def sizeHint(self) -> QtCore.QSize:
        font = self.font()
        fontMetric = QtGui.QFontMetrics(font)

        width = fontMetric.size(QtCore.Qt.TextSingleLine,
                                self._text_).width() + 4 * self.BorderWidth
        return QtCore.QSize(width, super().sizeHint().height())

    @property
    def isHighlighted(self) ->bool:
        return self.isDisplayHintEnabled(DisplayHint.EnteredHint) or self.isDisplayHintEnabled(DisplayHint.DraggedHint) or self.isDisplayHintEnabled(DisplayHint.PopupActiveHint)

    @property
    def elideText(self) -> bool:
        return self._elideText_

    @elideText.setter
    def elideText(self, val: bool):
        self._elideText_ = val is True
        signalBlocker = QtCore.QSignalBlocker(self.setElideTextAction)
        self.setElideTextAction.setChecked(self._elideText_ is True)
        self.update()

    @Slot(bool)
    def _slot_setElideText(self, val: bool):
        self.elideText = val is True

    def updateMinimumWidth(self):
        oldMinWidth = self.minimumWidth()
        minWidth = self.sizeHint().width()

        if minWidth < 40:
            minWidth = 40

        elif minWidth > 150:
            minWidth = 150

        if oldMinWidth != minWidth:
            self.setMinimumWidth(minWidth)

Ui_QuantityChooserWidget, QWidget = loadUiType(
    os.path.join(__module_path__,
                 "quantitychooserwidget.ui")
    )

class QuantityChooserWidget(Ui_QuantityChooserWidget, QWidget):
    r"""Compound widget allowing the user to choose a physical dimensionality.
    Convenience UI elements to attach quantities to various numeric variables.

    By default, the user is prompted to select a unit quantity from one of several
    "families" of unit quantities (e.t., Time, Length, etc)

    This choice can be restricted to a single family.
    """
    valueChanged = Signal(object, name="valueChanged")

    _default_units_ = pq.dimensionless

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 unit:typing.Optional[pq.Quantity]=None,
                 unitsFamily:typing.Optional[str]=None):
        r"""
        Named parameters:
        =================
        parent:     the parent QWidget; optional, default is None
        unit:       pre-selected unit; optional, default is None
        unitFamily: str, restrict options or a given unit family;
                    optional, default is None
                    For a list of units families, type `scq.unitFamilies()` in
                    Scipyen's console
        """
        QWidget.__init__(self, parent=parent)

        _irreds = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducible"])]
        _derived = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducible"])==0]
        self._family_names, self._families = zip(*list(scq.UNITS_DICT.items()))

        myunits = unit.units if isinstance(unit, pq.Quantity) else self._default_units_

        self._getUnitFamilyAndUnitFamilyUnits(myunits)

        self._restrictedToFamily_ = None

        self._units_ = myunits

        self._configureUI_() # will also assign the initial value of self._currentUnitsFamily

    def _configureUI_(self):
        self.setupUi(self)

        self._setupFamilyCombo()

        self.unitFamilyComboBox.currentIndexChanged.connect(self._slot_unitsFamilyChanged)

        self._setupUnitCombo()

        self.unitComboBox.setCurrentIndex(0)

        self._unitIndexInFamily = self.unitComboBox.currentIndex()
        self.unitComboBox.currentIndexChanged.connect(self._slot_unitsComboIndexChanged)

        self._units_ = self._currentUnitFamilyUnits[self._unitIndexInFamily]

    def _getUnitFamilyAndUnitFamilyUnits(self, unit:pq.Quantity):
        # print(f"{self.__class__.__name__}._getUnitFamilyAndUnitFamilyUnits (unit = {unit})")
        family_name, directly_found = scq.getUnitFamily(unit, show_components=False,
                                                   as_string=True,
                                                   indicate_if_directly_found=True)


        self._currentUnitsFamilyName = family_name
        self._currentUnitsFamily = scq.UNITS_DICT[self._currentUnitsFamilyName]
        self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(family_name)), key = lambda x: x.name)

        if not directly_found:
            self._currentUnitFamilyUnits.insert(0, unit.units)

        self._familyIndex = list(scq.UNITS_DICT).index(family_name)

        self._unitIndexInFamily = self._currentUnitFamilyUnits.index(unit.units)

        # print(f"{self.__class__.__name__}._getUnitFamilyAndUnitFamilyUnits: unit = {unit}")
        # print(f"\tfamily -> {family_name}")
        # print(f"\tdirectly_found -> {directly_found}")
        # print(f"\t_currentUnitsFamily -> {self._currentUnitsFamily}")
        # print(f"\t_currentUnitsFamilyName -> {self._currentUnitsFamilyName}")
        # print(f"\t_currentUnitFamilyUnits -> {self._currentUnitFamilyUnits}")
        # print(f"\t_familyIndex -> {self._familyIndex}")
        # print(f"\t_unitIndexInFamily -> {self._unitIndexInFamily}")

    def _setupFamilyCombo(self):
        r"""Called by _configureUI_ but also when manually setting the units family
        """
        signalBlocker = QtCore.QSignalBlocker(self.unitFamilyComboBox)
        # signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.unitFamilyComboBox, self.unitComboBox)]
        self.unitFamilyComboBox.clear()
        self.unitFamilyComboBox.addItems(self._family_names)
        if self._currentUnitsFamilyName in self._family_names:
            self.unitFamilyComboBox.setCurrentIndex(self._families.index(self._currentUnitsFamily))
        else:
            self.unitFamilyComboBox.setCurrentIndex(0)
            self._currentUnitsFamily = self._families[self.unitFamilyComboBox.currentIndex()]
            self._currentUnitsFamilyName = self._family_names[self.unitFamilyComboBox.currentIndex()]
            self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(self._family_names[self.unitFamilyComboBox.currentIndex()])), key = lambda x: x.name)

    def _setupUnitCombo(self):
        r"""Called by _configureUI_ but also when manually setting up a unit
        """
        # self._generateCurrentFamilyUnits()
        signalBlocker = QtCore.QSignalBlocker(self.unitComboBox)
        self.unitComboBox.clear()
        u_names = list(map(lambda x: x.name, self._currentUnitFamilyUnits))
        u_names_display = list(map(lambda x: f"{x.name} ({x.dimensionality.unicode})" if (x != pq.dimensionless and x.name != x.dimensionality.unicode) else x.name, self._currentUnitFamilyUnits))
        self.unitComboBox.addItems(u_names_display)
        u_name = scq.unitName(self._units_)
        # print(f"{self.__class__.__name__}._setupUnitCombo: u_name -> {u_name}")
        if u_name in u_names:
            self.unitComboBox.setCurrentIndex(u_names.index(u_name))
        else:
            self.unitComboBox.setCurrentIndex(0)

    @Slot(int)
    def _slot_unitsFamilyChanged(self, value):
        # print(f"{self.__class__.__name__}._slot_unitsFamilyChanged: value = {value}")
        self._currentUnitsFamilyName = self._family_names[self.unitFamilyComboBox.currentIndex()]
        self._currentUnitsFamily = scq.UNITS_DICT[self._currentUnitsFamilyName]
        # print(f"\nself._currentUnitsFamily -> {self._currentUnitsFamily}")
        self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(self._currentUnitsFamilyName)), key = lambda x: x.name)
        self._setupUnitCombo()
        self._units_ = self._currentUnitFamilyUnits[self.unitComboBox.currentIndex()]
        self.valueChanged.emit(self._units_)

    @Slot(int)
    def _slot_unitsComboIndexChanged(self, value):
        self._units_ = self._currentUnitFamilyUnits[self.unitComboBox.currentIndex()]
        self.valueChanged.emit(self._units_)

    @property
    def unitFamily(self):
        return self._currentUnitsFamilyName

    @unitFamily.setter
    def unitFamily(self, value:typing.Optional[str]=None):
        if value in scq.UNITS_DICT:
            self._unitFamilies = [value]
            self._currentUnitsFamilyName = value
            self._currentUnitsFamily = scq.UNITS_DICT[value]
            self._setupFamilyCombo()
            self._setupUnitCombo()

    @property
    def units(self):
        return self._units_

    @units.setter
    def units(self, value:typing.Optional[typing.Union[pq.UnitQuantity, pq.Quantity]]=None):
        # print(f"{self.__class__.__name__}.units.setter: value = {value}")
        if value is None:
            value = pq.dimensionless

        self._getUnitFamilyAndUnitFamilyUnits(value)
        self._units_ = self._currentUnitFamilyUnits[self._unitIndexInFamily]
        # print(f"\n{self.__class__.__name__}.units.setter:  _units_ -> {self._units_}")

        signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.unitFamilyComboBox, self.unitComboBox)]
        currentUnitComboboxIndex = self.unitFamilyComboBox.currentIndex()
        # print(f"\n{self.__class__.__name__}.units.setter: ")
        # print(f"\t_familyIndex -> {self._familyIndex}")
        # print(f"\tcurrentUnitComboboxIndex -> {currentUnitComboboxIndex}")

        if currentUnitComboboxIndex != self._familyIndex:
            self.unitFamilyComboBox.setCurrentIndex(self._familyIndex)
            self._setupUnitCombo()
        else:
            self.unitComboBox.setCurrentIndex(self._unitIndexInFamily)

    def value(self):
        r"""For compatibilty with qd.QuickDialog"""
        return self.units

    def setValue(self, value:typing.Optional[pq.Quantity]=None):
        r"""For compatibilty with qd.QuickDialog"""
        if value is None:
            value = pq.dimensionless
        self.units = value

    def validate(self, *args):
        r"""For compatibilty with qd.QuickDialog"""
        return True

    def restrictToCurrentUnitFamily(self, value:bool=False):
        self.unitFamilyComboBox.setEnabled(value)

    @property
    def familyRestriction(self) -> str:
        return self._restrictedToFamily_

    @familyRestriction.setter
    def familyRestriction(self, value:typing.Optional[str] = None):
        if isinstance(value, str):
            if value not in self._family_names:
                scipywarn(f"Family of units named {value} not found")
                return
            self._restrictedToFamily_ = value
            self.unitFamily = value
            self.unitFamilyComboBox.setEnabled(False)
        else:
            self.unitFamilyComboBox.setEnabled(True)

class LazyLineEdit(QtWidgets.QLineEdit):
    sig_enterPressed = Signal(str, name="sig_enterPressed")

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            # print(f"{self.__class__.__name__}.keyPressEvent: text = '{self.text()}'")
            self.sig_enterPressed.emit(self.text())
        else:
            super().keyPressEvent(event)

class LineEdit(QtWidgets.QLineEdit):
    r"""Line editor widget with custom context menu and, optional lazy notifications of text changes.

    To constrain for numeric values/arrays, including Quantity arrays, use it with guiutils.NumericStringValidator.
"""
    sig_enterPressed = Signal(str, name="sig_enterPressed")
    sig_lazy = Signal(bool, name="sig_lazy")
    def __init__(self, contents: typing.Optional[str] = None,
                 parent: typing.Optional[QtWidgets.QWidget] = None,
                 lazy: bool = False,
                 validator: typing.Optional[QtGui.QValidator] = None):
        super().__init__(parent=parent)
        self._variable_ = contents
        self._lazy_: bool = lazy is True
        self._custom_menu_: typing.Optional[QtWidgets.QMenu] = None
        self._validator_: typing.Optional[QtGui.QValidator] = None

        if isinstance(validator, QtGui.QValidator):
            self._validator_ = validator
            self._validator_.parent = self

        if isinstance(self._variable_, str):
            self.setText(self._variable_)

    def value(self) -> str:
        self._variable_ = super().text()
        return self._variable_

    def setValue(self, val: str):
        if not isinstance(val, str):
            raise TypeError(f"Expecting a string, got a {type(val).__name__} instead")

        self._variable_ = val
        super().setText(self._variable_)

    def text(self) -> str:
        return self.value()

    def setText(self, val:str):
        self.setValue(val)

    def keyPressEvent(self, event):
        if not self._lazy_:
            super().keyPressEvent(event)
        else:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                # print(f"{self.__class__.__name__}.keyPressEvent: text = '{self.text()}'")
                # self.textChanged.emit(self.text())
                self.sig_enterPressed.emit(self.text())
            else:
                # needed in order to update the widget
                super().keyPressEvent(event)

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent):
        stdMenu = self.createStandardContextMenu()
        if isinstance(self._custom_menu_, QtWidgets.QMenu):
            menu = QtWidgets.QMenu(self)
            for action in self._custom_menu_.actions():
                menu.addAction(action)
            menu.addSeparator()
            for action in stdMenu.actions():
                menu.addAction(action)
            menu.exec(evt.globalPos())
        else:
            stdMenu.exec(evt.globalPos())

    def validate(self, *args) -> bool:
        r"""For compatibilty with qd.QuickDialog"""
        if self._validator_ is None:
            return True

        else:
            # print(f"{self.__class__.__name__}.validate({args})")
            if len(args):
                if isinstance(args[0], str):
                    ret = self._validator_.validate(args[0], len(args[0]))
                    # print(f"{self.__class__.__name__}.validate({args}) -> {ret}")
                    return ret[0] == QtGui.QValidator.Acceptable
                else:
                    return False
            else:
                return True

    def setValidator(self, val):
        self.validator = val

    @property
    def validator(self) -> typing.Optional[QtGui.QValidator]:
        return self._validator_

    @validator.setter
    def validator(self, val:QtGui.QValidator):
        if not isinstance(val, QtGui.QValidator):
            self._validator_ = None

        else:
            self._validator_ = val
            self._validator_.parent = self

        super().setValidator(self._validator_)

        if isinstance(self._validator_, NumericStringValidator):
            tip = self.toolTip()
            tt = "\n".join(["For numeric 1D arrays enter numbers separated by spaces;",
                                  "a physical unit symbol at the end generates a Quantity.",
                                  "",
                                  "Comma-separated numbers, optionally enclosed between round brackets, generate a tuple.",
                                  "Enclose in square brackets for a list, or curly brackets for a set of numbers"])
            if len(tip.strip()):
                tip = "\n".join([tip,
                                  "---",
                                  tt])
            else:
                tip = tt
            self.setToolTip(tip)

    def setValidator(self, val: QtGui.QValidator):
        self.validator = val

    @property
    def customMenu(self) -> QtWidgets.QMenu | None:
        return self._custom_menu_

    @customMenu.setter
    def customMenu(self, menu: QtWidgets.QMenu):
        if isinstance(menu, QtWidgets.QMenu):
            self._custom_menu_ = menu

    @property
    def lazy(self) -> bool:
        r"""When True, the widget emits sig_enterPressed after pressing the Enter (Return) key.
    The textChanged signal should NOT be connected to any slot in your UI.
    Instead, connect the sig_enterPressed signal of this widget to your UI slot(s).

    When, False, then you should connect the textChanged signal to your UI slot(s)
    as per usual.

    To be notified by changes in the "lazy" status, connect to the sig_lazy signal

    .. warning::
        If sig_enterPressed is also connected you may obtain undesired, duplicate
        notifications.
    """
        return self._lazy_

    @lazy.setter
    def lazy(self, val: bool):
        self._lazy_ = val is True
        self.sig_lazy.emit(self._lazy_)


class ArrayEditorWidget(QtWidgets.QFrame):
    r"""Widget for editing (small) numeric arrays"""
    sig_valueChanged = Signal(object, name = "sig_valueChanged")

    def __init__(self, value: typing.Optional[
                        typing.Union[np.ndarray, typing.Sequence, typing.Set]
                        ] = None,
                 parent = None):
        super().__init__(parent = parent)
        if isinstance(parent, QtWidgets.QWidget):
            parent.addWidget(self)

        self._inputWidget_ = None

        if (isinstance(value, np.ndarray) and issubclass(value.dtype.type, np.number)
            or (isinstance(value, (typing.Sequence, typing.Set)) and all(isinstance(v, numbers.Number) for v in value))):
            self._value_ = value
        else:
            self._value_ = None

        self._configureUI_()

    def _configureUI_(self):
        self._layout_ = QtWidgets.QHBoxLayout(self)
        self._layout_.setSpacing(0)
        self._layout_.setContentsMargins(0,0,0,0)
        # self.setLayout(self._layout_) # already added in layout c'tor with parent=self
        self._setup_widgets_()

    def _setup_widgets_(self):
        if self._value_ is None or (isinstance(self._value_, (typing.Sequence, typing.Set)) and all(isinstance(v, numbers.Number) for v in self._value_)):
            w = LineEdit(parent=self)
            w.redoAvailable = True
            w.undoAvailable = True
            w.setClearButtonEnabled(True)
            w.setValidator(NumericStringValidator(self))
            if self._value_ is not None:
                w.setText(f"{self._value_}")
            w.textChanged.connect(self._slot_valuesEdited)
            w.sig_lazy.connect(self._slot_lazyTextChanges)

        elif isinstance(self._value_, np.ndarray):
            if not dt.is_vector(self._value_) or self._value_.size > 5: # seems like a good compromise?
                if self._value_.ndim < 3:
                    # w = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("table"), f"Edit {type(self._value_).__name__} with size {self._value_.size} and shape {self._value_.shape}", self)
                    w = ElidedPushButton(self)
                    w.setText(f"Edit {type(self._value_).__name__} with size {self._value_.size} and shape {self._value_.shape}")
                    w.setIcon(QtGui.QIcon.fromTheme("table"))
                    w.clicked.connect(self._slot_editExternally)
                else:
                    w = QtWidgets.QLabel(parent=self)
                    w.setText(f"{type(self._value_).__name__} with size {self._value_.size} and shape {self._value_.shape}")

            else:
                w = LineEdit(parent=self)
                w.redoAvailable = True
                w.undoAvailable = True
                w.setClearButtonEnabled(True)
                w.setValidator(NumericStringValidator(self))
                w.setText(f"{self._value_}")
                w.textChanged.connect(self._slot_valuesEdited)
                w.sig_lazy.connect(self._slot_lazyTextChanges)

        self._inputWidget_ = w

        self._layout_.addWidget(self._inputWidget_)

        self._layout_.setStretchFactor(self._inputWidget_,1)

    def _update_(self):
        signalBlockers = QtCore.QSignalBlocker(self._inputWidget_)
        self._layout_.removeWidget(self._inputWidget_)
        self._inputWidget_.deleteLater()
        self._setup_widgets_()


    @Slot()
    def _slot_editExternally(self):
        from gui.widgets.tableeditorwidget import TableEditorWidget
        dlg = qd.QuickDialog(self, title = "Edit array values")
        te = TableEditorWidget(parent=dlg)
        te.setValue(self._value_)
        dlg.addWidget(te)
        dlg.adjustSize()

        if dlg.exec():
            self._value_ = te.value()

    @Slot(bool)
    def _slot_lazyTextChanges(self, val:bool):
        if not isinstance(self._inputWidget_, LineEdit):
            return
        if val is True:
            if self._inputWidget_.receivers(self._inputWidget_.textChanged) > 0:
                self._inputWidget_.textChanged.disconnect(self._slot_timesChanged)
            self._inputWidget_.sig_enterPressed.connect(self._slot_timesChanged)
        else:
            if self.timesLineEdit.receivers(self.timesLineEdit.sig_enterPressed) > 0:
                self.timesLineEdit.sig_enterPressed.disconnect(self._slot_timesChanged)
            self.timesLineEdit.textChanged.connect(self._slot_timesChanged)

    @Slot(str)
    def _slot_valuesEdited(self, value: str):
       if len(value.strip()) == 0:
           self._value_ = None
       else:
           try:
               v = eval(value) # will eval numeric sequences; will fail for arrays
               self._value_ = v
           except:
                try:
                    v = scq.str2quantity_2(value)
                    self._value_ = v
                except:
                    return

    def value(self):
        return self._value_

    def setValue(self, value: typing.Optional[
                        typing.Union[np.ndarray, typing.Sequence, typing.Set]
                        ] = None):
        if (isinstance(value, np.ndarray) and issubclass(value.dtype.type, np.number)
            or (isinstance(value, (typing.Sequence, typing.Set)) and all(isinstance(v, numbers.Number) for v in value))):
            self._value_ = value
        else:
            self._value_ = None

        self._update_()

class QuantitySpinBox(QtWidgets.QDoubleSpinBox):
    r"""Subclass of QDoubleSpinBox aware of Python quantities.
    Single step, number of decimals and units suffix are all configurable.

    Most methods are inherited directly from QDoubleSpinBox, with the following
    exceptions:

    • setMinimum(), setMaximum(), setRange(), are overloaded to accept quantity
    scalars as well as float arguments, or None;
        ∘ when None, the 'minimum' and 'maximum' properties will be set to
            -math.inf and math.inf, respectively.

    • minimum() and maximum() are overloaded to return python Quantity scalars
        WARNING: This means that the minimum() and maximum() values will ALWAYS
        be quantities (even if their units are `dimensionless`)

    By default, the 'minimum' property is set to -math.inf.

    """
    sig_valueChanged:Signal = Signal(object, name="sig_valueChanged")

    _default_units_:pq.Quantity         =  pq.dimensionless
    # _default_internal_minimum_:float    = -math.inf
    # _default_internal_maximum_:float    =  math.inf
    _default_internal_minimum_:float    = sys.float_info.min
    _default_internal_maximum_:float    = sys.float_info.max

    _default_singleStep_:int = 1
    _default_stepType_:QtWidgets.QAbstractSpinBox.StepType = QtWidgets.QAbstractSpinBox.DefaultStepType
    _default_decimals_:int = np.get_printoptions()["precision"]

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]=None,
                 units: typing.Optional[typing.Union[pq.Quantity,
                                                     float, int, complex,
                                                     np.integer, np.floating,
                                                     np.complexfloating]] = None,
                 singleStep: typing.Optional[float] = None,
                 stepType: typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 decimals: typing.Optional[int] = None,
                 # minimum: typing.Optional[typing.Union[pq.Quantity, float]] = sys.float_info.min,
                 # maximum: typing.Optional[typing.Union[pq.Quantity, float]] = sys.float_info.max,
                 minimum: typing.Optional[typing.Union[pq.Quantity, float]] = None,
                 maximum: typing.Optional[typing.Union[pq.Quantity, float]] = None,
                 unitsFamily: typing.Optional[str] = None,
                 fixUnitFamily: typing.Optional[typing.Union[str, bool]] = None,
                 rescaleWithUnitsChange: bool = False,
                 keepDimensionless: bool = False,
                 disableUnitChange: bool = False,
                 enforceImmutableUnits: bool = False,
                 ):
        r"""
        Named parameters:
        =================
        parent: parent widget; optional, default is None
        units: initial units, or initial value; optional, default is pq.dimensionless
        unitFamily: restrict to units in given family; optional, default is None

        """
        # minimum, maximum: min & max values of the spin box - to be set manually

        QtWidgets.QDoubleSpinBox.__init__(self, parent=parent)

        # FIXME/TODO: 2022-11-07 13:32:41
        # This setting is not right; NA should be somewhat mapped to NA, NOT
        # to minimum - what do we do if minimum is set to 0 which is a valid value?
        # super().setSpecialValueText("NA") # shown when value is at minimum

        # self._default_units_ = pq.dimensionless

        # self._lineEdit_ = LazyLineEdit(self)
        self._lineEdit_ = LineEdit(self)

        self.setLineEdit(self._lineEdit_)

        self._keepDimensionless_: bool = keepDimensionless
        self._disableUnitChange_: bool = disableUnitChange
        self._enforceImmutableUnits_: bool = enforceImmutableUnits
        if self._enforceImmutableUnits_:
            self._disableUnitChange_ = True
        self._restrictedToFamily_: typing.Optional[str] = None
        self._rescaleOnUnitChange_: bool = False
        self._forceDimensionless_: bool = False

        self._validText_: QtGui.QValidator.State = QtGui.QValidator.Invalid

        self._units_: pq.Quantity = self._default_units_
        self._magnitude_: float = 0.0
        self._prefix_ = ""
        self._suffix_ = ""
        self._specialValueText_: str = ""

        if isinstance(units, pq.Quantity):
            self._units_ = units.units

            if not isinstance(units, pq.UnitQuantity):
                if units.size != 1:
                    raise TypeError(f"Expecting a scalar quantity; instead, got a Quantity array with {units.size} elements")

                self._magnitude_ = float(units.magnitude)

        else:
            if isinstance(units, (float, np.floating)):
                self._magnitude_ = units

            elif isinstance(units, (int, np.integer)):
                self._magnitude_ = float(units)

            elif isinstance(units, (complex, np.complexfloating)):
                self._magnitude_ = abs(units)

            elif units is not None:
                raise TypeError(f"Invalid 'units' argument: {units}")

            self._units_ = self._default_units_

        self._unitFamily_ = scq.getUnitFamily(self._units_)

        if self._units_.dimensionality == pq.dimensionless.dimensionality:
            self._suffix_ = ""
            self._prefix_ = ""
        else:
            if not (self._keepDimensionless_ or self._forceDimensionless_):
                symbol = self._units_.dimensionality.unicode
                if self._unitFamily_ == "Currency":
                    self._suffix_ = ""
                    self._prefix_ = f"{symbol} "
                else:
                    self._suffix_ = f" {symbol}"
                    self._prefix_ = ""


        if isinstance(singleStep,float):
            self._singleStep_ = singleStep

        elif singleStep is None:
            self._singleStep_ = self._default_singleStep_
        else:
            raise TypeError(f"singleStep expected to be a float or None; instead, got {singleStep}")


        if isinstance(decimals, int) and decimals >= 0:
            self._decimals_ = decimals

        elif decimals is None:
            self._decimals_ = np.get_printoptions()["precision"]
            # self._decimals_ = -int(math.log10(abs(self._singleStep_))) if (self._singleStep_ < 1 and self._singleStep_ > -1) else self._default_decimals_
            # self._decimals_ = self._default_decimals_

        else:
            raise TypeError(f"decimals expected to be an int >= 0 or None; instead, got {decimals}")

        # print(f"{self.objectName()}: {self.__class__.__name__}.__init__:  decimals -> {self.decimals}")

        self._internal_minimum = self._default_internal_minimum_
        self._internal_maximum = self._default_internal_maximum_

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        # print(f"{self.objectName()}: {self.__class__.__name__}.__init__ DONE")

        # super().setSuffix(self._suffix_)
        # super().setPrefix(self._prefix_)

        self.setSingleStep(self._singleStep_)
        self.setDecimals(self._decimals_)
        # super().setValue(self._magnitude_) # will also set prefix suffix and specialValueText

        if isinstance(stepType, QtWidgets.QAbstractSpinBox.StepType):
            self._stepType_ = stepType
        else:
            self._stepType_ = self._default_stepType_

        super().setStepType(self._stepType_)

        super().setRange(self._internal_minimum, self._internal_maximum)

        # if isinstance(units, pq.Quantity) and not isinstance(units, pq.UnitQuantity):
        #     self.setValue(units)

        self.setValue(self._magnitude_ * self._units_)

        # super().valueChanged.connect(self._slot_valueChanged)
        # self.lineEdit().setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._lineEdit_.sig_enterPressed.connect(self._slot_valueTextChanged)

        # self.lineEdit().installEventFilter(self)

    @property
    def units(self) -> pq.Quantity:
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._units_

    def getUnits(self) -> pq.Quantity:
        return self.units

    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        self.setUnits(value)

    def setUnits(self, value:typing.Optional[pq.Quantity] = None):
        # print(f"{self.__class__.__name__}.setUnits: value = {value}")
        if self._keepDimensionless_ or self._forceDimensionless_:
            return

        if not isinstance(value, pq.Quantity):
            value = pq.dimensionless

        if self._rescaleOnUnitChange_ and scq.unitsConvertible(value, self._units_) and float(self.value()) not in (math.nan, np.nan, -math.inf, math.inf, -np.inf, np.inf):
            newval = self.value().rescale(value)
            newfval = float(newval.magnitude)
            ratio = newfval/self._magnitude_
            self._singleStep_ *= ratio
            self._magnitude_ = float(newval.magnitude)
            self._units_ = newval.units
            # self.setValue(self._magnitude_)
            self.setSingleStep(self._singleStep_)
        else:
            self._units_ = value.units

        self._unitFamily_ = scq.getUnitFamily(self._units_)

        self._suffix_ = ""
        self._prefix_ = ""

        if self._units_.dimensionality != pq.dimensionless.dimensionality:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._suffix_ = ""
                self._prefix_ = f"{symbol} "
            else:
                self._suffix_ = f" {symbol}"
                self._prefix_ = ""

        else:
            self._suffix_ = ""
            self._prefix_ = ""

        if np.isnan(self._magnitude_):
            text = "NaN"
            self._specialValueText_ = text
            # super().setSpecialValueText(text)

        elif np.isinf(self._magnitude_):
            text = "-Inf" if self._magnitude_ in (-np.inf, -math.inf) else "Inf"
            self._specialValueText_ = text
            # super().setSpecialValueText(text)
        else:
            text = f"{self._magnitude_:.{self.decimals}}"
            self._specialValueText_ = ""
            # super().setSpecialValueText("")

        super().setSuffix(self._suffix_)
        super().setPrefix(self._prefix_)

        if len(self._specialValueText_):
            text = self._specialValueText_

        if len(self._prefix_):
            text = f"{self._prefix_}{text}"

        if len(self._suffix_):
            text = f"{text}{self._suffix_}"

        super().setSpecialValueText(self._specialValueText_)
        super().setValue(self._magnitude_)

        # print(f"{self.objectName()}: {self.__class__.__name__}.units.setter({value}): text -> {text}")
        signalBlock = QtCore.QSignalBlocker(self.lineEdit())
        self.lineEdit().setText(text)

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    def _slot_valueTextChanged(self, s:str):
        # print(f"{self.__class__.__name__}._slot_valueTextChanged")

        if self._validText_ == QtGui.QValidator.Acceptable:
            try:
                val = self.valueFromText(s)
                # if objectName.endswith("startSpinBox"):
                #     print(f"{oname}{self.__class__.__name__}._slot_valueTextChanged(s = '{s}') -> val = {val}")
                if isinstance(val, (pq.Quantity, float)):
                    self._magnitude_ = float(val)
                    # self.setValue(self._magnitude_ * self._units)
                    self.sig_valueChanged.emit(self.value())
            except:
                traceback.print_exc()

    @Slot(bool)
    def _slot_keepDimensionless(self, val:bool):
        self.keepDimensionless = val

    def contextMenuEvent(self, evt):
        # print(f"{self.objectName()}: {self.__class__.__name__}.contextMenuEvent: _enforceImmutableUnits_ = {self._enforceImmutableUnits_}")
        cm = QtWidgets.QMenu("Options", self)
        if not (self._keepDimensionless_ or self._forceDimensionless_ or self._disableUnitChange_ or self._enforceImmutableUnits_):
            setUnitsAction = cm.addAction("Set units")
            setUnitsAction.triggered.connect(self._slot_setUnitsGUI)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimalsGUI)
        setSingleStepAction = cm.addAction("Set single step")
        setSingleStepAction.triggered.connect(self._slot_setSingleStepGUI)
        adaptiveStepAction = cm.addAction("Adaptive step")
        adaptiveStepAction.setCheckable(True)
        adaptiveStepAction.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        adaptiveStepAction.toggled.connect(self._slot_setAdaptiveStep)
        setRangeAction = cm.addAction("Set range (min, max)")
        setRangeAction.triggered.connect(self._slot_setRangeGUI)
        if not (self._keepDimensionless_ or self._forceDimensionless_ or self._disableUnitChange_):
            cm.addSeparator()
            rescaleValueAction = cm.addAction("Rescale on unit change")
            rescaleValueAction.setCheckable(True)
            rescaleValueAction.setChecked(self._rescaleOnUnitChange_)
            rescaleValueAction.toggled.connect(self._slot_rescaleValueChanged)
            restrictAction = cm.addAction("Fix units family")
            restrictAction.setCheckable(True)
            restrictAction.setChecked(isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT)
            restrictAction.toggled.connect(self._slot_familyRestrictionChanged)

        cm.addSeparator()
        if not (self._forceDimensionless_ or self._disableUnitChange_):
            toggleDimensionlessAction = cm.addAction("Ignore dimensionality")
            toggleDimensionlessAction.setCheckable(True)
            toggleDimensionlessAction.setChecked(self._keepDimensionless_)
            toggleDimensionlessAction.toggled.connect(self._slot_keepDimensionless)

        if not self._enforceImmutableUnits_:
            toggleUnitChange = cm.addAction("Immutable units")
            toggleUnitChange.setCheckable(True)
            toggleUnitChange.setChecked(self._disableUnitChange_)
            toggleUnitChange.toggled.connect(self._slot_toggleImmutableUnits)

        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(self.mapToGlobal(evt.pos()))

    def setMinimum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setMinimum, to accept:
        • a None
        • a float
        • a scalar Quantity

        When None, the minimum value will be set to -math.inf
        """
        if value is None:
            super().setMinimum(self._default_internal_minimum_)

        elif isinstance(value, float):
            super().setMinimum(value)

        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMinimum(val)
            self.units = units

        self._internal_minimum = super().minimum()

    def setMaximum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setMaximum, to accept:
        • a None
        • a float
        • a scalar Quantity

        When None, the maximum value will be set to math.inf
        """
        if value is None:
            super().setMaximum(self._default_internal_maximum_)

        elif isinstance(value, float):
            super().setMaximum(value)

        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMaximum(val)
            self.units = units

        self._internal_maximum = super().maximum()

    def setRange(self, minimum:typing.Optional[typing.Union[float, pq.Quantity]]=None, maximum:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setRange to accept:
        • floats
        • scalar Quantity
        • None

        for either 'minimum' or 'maximum'

        When either is None, the 'minimum' and 'maximum' will be set to
        -math.inf and math.inf, respectively.
        """

        if all(isinstance(v, pq.Quantity) for v in (minimum, maximum)):
            # NOTE: 2022-11-07 09:55:43
            # sanity check when both are quantities
            if any(v.size > 1 for v in (minimum, maximum)):
                raise TypeError("Expecting scalar quantities for both minimum and maximum ")

            if scq.unitsConvertible(minimum, maximum):
                # NOTE: 2022-11-09 09:07:15
                # rescale to minimum units explicitly,
                # in case minimum magnitude is 0 (and thus raise exception)
                maximum = maximum.rescale(minimum.units)

            else:
                raise TypeError(f"{minimum} and {maximum} have incompatible units")

        else:
            # NOTE: 2022-11-07 09:57:07
            # DO accept None
            if minimum is None:
                minimum = -math.inf

            if maximum is None:
                maximum = math.inf

            # NOTE: 2022-11-07 09:55:58
            # propagate units from one the other if only one is a quantity
            if isinstance(minimum, pq.Quantity):
                if minimum.size > 1:
                    raise TypeError("Expecting a scalar quantity for 'minimum")
                maximum = maximum * minimum.units

            elif isinstance(maximum, pq.Quantity):
                if maximum.size>1:
                    raise TypeError("Expecting a scalar quantity for maximum")
                minimum = minimum * maximum.units

            elif not all(isinstance(v, (float, type(None))) for v in (minimum, maximum)):
                # NOTE: 2022-11-07 09:56:09
                # finally, only accept  scalar floats or None
                raise TypeError("Expecting floats, scalar quantities or None as minimum and maximum")

        minVal = float(minimum.magnitude) if isinstance(minimum, pq.Quantity) else minimum
        minUnits = minimum.units if isinstance(minimum, pq.Quantity) else None
        maxVal = float(maximum.magnitude) if isinstance(maximum, pq.Quantity) else maximum
        maxUnits = maximum.units if isinstance(maximum, pq.Quantity) else None

        # NOTE: 2022-11-07 10:00:21
        # both minUnits and maxUnits should have been checked and now be identical
        # see NOTE: 2022-11-07 09:55:43 and NOTE: 2022-11-07 09:55:58
        #
        super().setMinimum(minVal)
        super().setMaximum(maxVal)
        self.units = minUnits

    def minimum(self):
        ret = super().minimum()
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return ret  * self.units

    def maximum(self):
        ret = super().maximum()
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return ret * self.units

    def value(self) -> typing.Union[pq.Quantity, float, type(pd.NA)]:
        r""" Reimplements QDoubleSpinBox.value() to return a quantity
        """
        if self.specialValueText() == "NA":
            return pd.NA

        elif self.specialValueText() == "NaN":
            return np.nan if self._keepDimensionless_ else np.nan * self.units

        else:
            ret = self._magnitude_
            if self._keepDimensionless_ or self._forceDimensionless_:
                return ret

            return ret * self.units

    def getDecimals(self) -> int:
        """
    """
        return self._decimals_

    @property
    def decimals(self) -> int:
        return self._decimals_

    @decimals.setter
    def decimals(self, val:int):
        self.setDecimals(val)

    def setDecimals(self, val:int):
        if val < 0:
            val = 0
        self._decimals_ = val
        super().setDecimals(self._decimals_)

    def validate(self, text:str, pos:int):
        validator = InftyDoubleValidator(parent=self)
        validator.suffix = self.suffix()
        validator.prefix = self.prefix()
        validator.setDecimals(self.getDecimals())
        valid = validator.validate(text, pos)
        self._validText_ = valid[0]

        if valid[0] == QtGui.QValidator.Acceptable:
            v = valid[1]
            if len(self.suffix()) and self.suffix() in v:
                sfndx = v.find(self.suffix())
                if sfndx > 0:
                    v = v[:sfndx]
            if len(self.prefix()):
                v = v[len(self.prefix()):]

            v = v.strip()

            self._magnitude_ = float(v)
            # NOTE: 2026-01-20 14:32:14
            # do NOT emit sig_valueChanged signal as it will create an inifinite loop
            # try:
            #     newVal = self._magnitude_ * self._units_.units if isinstance(self._units_, pq.Quantity) else self._magnitude_*pq.dimensionless
            #     self.sig_valueChanged.emit(newVal)
            # except:
            #     traceback.print_exc()

        return valid

    def valueFromText(self, text:str):
        suffix = self._suffix_
        prefix = self._prefix_
        s = text
        if len(suffix):
            sfndx = s.find(suffix)
            if sfndx > 0:
                s = s[:sfndx]

        if len(prefix):
            s = s[len(prefix):]

        s = s.strip()

        s = s.replace(",", "") # BUG: 2026-01-20 14:18:03 FIXME/TODO use locales!

        if s == "NA":
            ret = pd.NA
        elif s.lower() == "nan":
            ret = math.nan * self.units
        else:
            if len(s.strip()) == 0:
                ret = math.nan
            else:
                if s.startswith("e"):
                    s = "1"+s
                elif s.startswith("+e"):
                    s = s.replace("+e", "+1e")
                elif s.startswith("-e"):
                    s = s.replace("-e", "-1e")

                ret = float(s)
                # try:
                # except ValueError:
                #     pass
            units = self.units
            ret = ret * units.units if isinstance(units, pq.Quantity) else ret

        return ret


    def textFromValue(self, value:typing.Union[float, pq.Quantity, np.ndarray]):
        # print(f"{self.objectName()}: {self.__class__.__name__}.textFromValue({value})")
        if isinstance(value, (pq.Quantity, np.ndarray)):
            if value.size > 1:
                return "NA"

            units = value.units if isinstance(value, pq.Quantity) else pq.dimensionless

            prefix = ""
            suffix = ""
            family = scq.getUnitFamily(units)
            if family == "Currency":
                prefix = f"{units.dimensionality.unicode}"
            else:
                suffix = f"{units.dimensionality.unicode}"

            fval = float(value.magnitude)

            if np.isnan(fval):
                ret = "NaN"
            elif np.isinf(fval):
                ret = "-Inf" if fval in (-np.inf, -math.inf) else "Inf"
            else:
                ret = f"{fval:.{self.decimals}}"
                # ret = super().textFromValue(float(value.magnitude))

            if len(prefix):
                ret = f"{prefix} {ret}"
            if len(suffix):
                ret = f"{ret} {suffix}"

            # print(f"\t ret -> {ret}")

            return ret

        elif isinstance(value, float):
            if np.isnan(value):
                ret = "NaN"
            elif np.isinf(value):
                ret = "-Inf" if value == -np.inf else "Inf"
            else:
                ret = f"{value:.{self.decimals}}"
                # ret = super().textFromValue(value)

            # print(f"\t ret -> {ret}")
            return ret

        else:
            return "NA"

    def setValue(self, value:typing.Union[pq.Quantity, float, int, type(pd.NA)]):
        r"""Also allows changing the units if not convertible to current ones.
        Otherwise the value will be rescaled to current units.
    WARNING: This is different from the case when new units are chosen while
    self.rescaleOnUnitChange is True.
    """
        from core.regexps import SCIENTIFIC_NUMBER_FORMAT_MATCH
        # traceback.print_stack()

        # print(f"{self.__class__.__name__}.setValue({value})")

        if isinstance(value, pq.Quantity):
            if value.size > 1:
                # return # Only scalar quantities are allowed
                raise TypeError("Only scalar quantities are allowed")

            fval = float(value.magnitude)

            if not (self._keepDimensionless_ or self._forceDimensionless_):
                if value.units != self.units:
                    if scq.unitsConvertible(self.units, value.units):
                        if fval > -math.inf and fval < math.inf:
                            fval = float(value.rescale(self.units).magnitude)
                    else:
                        self.units = value.units

            self._magnitude_ = fval

        elif value is pd.NA or value in(math.nan, np.nan):
            self._magnitude_ = value
            self.units = None

        elif isinstance(value, float):
            self._magnitude_ = value
            self.units = None

        elif isinstance(value, int):
            self._magnitude_ = float(value)
            self.units = None

        elif isinstance(value, (np.float64, np.int64)):
            self._magnitude_ = float(value)
            self.units = None

        else:
            raise ValueError(f"Incompatible value: {value} ({type(value).__name__})")

        self._update_()

    def _update_(self,
                 forceSgStep: typing.Optional[typing.Union[int, float]] = None,
                 forceDecimals: typing.Optional[int] = None):
        signalBlockers = list(map(QtCore.QSignalBlocker, (self, self.lineEdit())))
        if self._magnitude_ is pd.NA:
            self.setMinimum(-math.inf)
            specialText = r"NA"
            self._specialValueText_ = specialText

            if len(self._prefix_):
                text = f"{self._prefix_} {self._specialValueText_}"

            if len(self._suffix_):
                text = f"{text} {self._suffix_}"

            super().setSpecialValueText(self._specialValueText_)
            super().setValue(self._magnitude_)

            self.lineEdit().setText(text)

        elif self._magnitude_ in (math.nan, np.nan):
            self.setMinimum(-math.inf)
            specialText = r"NaN"
            self._specialValueText_ = specialText

            if len(self._prefix_):
                text = f"{self._prefix_} {self._specialValueText_}"

            if len(self._suffix_):
                text = f"{text} {self._suffix_}"

            super().setSpecialValueText(self._specialValueText_)
            super().setValue(self._magnitude_)

            self.lineEdit().setText(text)

        elif isinstance(self._magnitude_, (float, int)):
            if self._magnitude_ in (-math.inf, -np.inf):
                specialText = r"-Inf"

            elif self._magnitude_ in (math.inf, np.inf):
                specialText = r"Inf"

            else:
                # NOTE: 2026-03-29 12:14:37
                # the next line formats self._magnitude_ according to the number of decimals
                # HOWEVER, this does NOT work when the generated text is in scientific format
                # e.g., '1e-8'
                text = f"{self._magnitude_:.{self.decimals+1}}"
                mantissa, exponent, decimals = strutils.parse_sci_string(text)
                if exponent != 0:
                    sign = "+" if exponent > 0 else "" # '-' wil be automatically inserted by Python library
                    text = f"{mantissa:.{self.decimals}}e{sign}{exponent}"
                else:
                    text = f"{mantissa:.{self.decimals}}"

                if not isinstance(forceSgStep, (int, float)):
                    if self._magnitude_ < self._singleStep_:
                        if exponent < 0 and abs(exponent) > self.decimals:
                            step = 10**exponent
                        else:
                            step = 10**(-self.decimals + exponent)
                        # print(f"\tnew step proposed: {step}")
                        self.setSingleStep(step) # good fallback?

                    elif self._magnitude_ > self._singleStep_:
                        if exponent > self.decimals:
                            step = 10**(exponent - self.decimals)
                            # print(f"\tnew step proposed: {step}")
                            self.setSingleStep(step) # good fallback?

                specialText = ""

            self._specialValueText_ = specialText


            if len(self._specialValueText_):
                # super().setSpecialValueText(specialText)
                text = self._specialValueText_

            if len(self._prefix_):
                text = f"{self._prefix_} {text} "

            if len(self._suffix_):
                text = f"{text} {self._suffix_}"

            super().setSpecialValueText(self._specialValueText_)
            super().setValue(self._magnitude_)

            # print(f"{self.objectName()}: {self.__class__.__name__}.setValue({value}) -> text = {text}")

            # signalBlock = QtCore.QSignalBlocker(self.lineEdit())
            # print(f"\tsetting text to {text}")
            self.lineEdit().setText(text)

            # print(f"\tvalue after update: {self.value()}")

        else:
            raise TypeError(f"_magnitude_ expected to be a scalar quantity, a float or pd.NA; instead, got {type(value).__name__}")


    @property
    def disableUnitChange(self) -> bool:
        return self._disableUnitChange_

    @disableUnitChange.setter
    def disableUnitChange(self, val:bool):
        self._disableUnitChange_ = val

    @property
    def rescaleOnUnitChange(self)->bool:
        if self._keepDimensionless_ or self._forceDimensionless_:
            return False
        return self._rescaleOnUnitChange_

    @rescaleOnUnitChange.setter
    def rescaleOnUnitChange(self, val:bool):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            self._rescaleOnUnitChange_ = val

    @property
    def unitFamily(self):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._unitFamily_

    @property
    def familyRestriction(self) -> str:
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._restrictedToFamily_

    @familyRestriction.setter
    def familyRestriction(self, value:typing.Optional[typing.Union[str, bool]] = None):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return

        if isinstance(value, str):
            if value in scq.UNITS_DICT:
                self._restrictedToFamily_ = value

            elif isinstance(value, bool):
                if value:
                    self._restrictedToFamily_ = scq.getUnitFamily(self.units)
        else:
            self._restrictedToFamily_ = None

    @Slot()
    def _slot_setUnitsGUI(self):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        dlg = qd.QuickDialog(parent = self, title="Set units")
        quantityWidget = QuantityChooserWidget(parent = dlg)
        quantityWidget.units = self._units_
        if isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT:
            quantityWidget.familyRestriction = self._restrictedToFamily_
        else:
            quantityWidget.familyRestriction = None

        dlg.addWidget(quantityWidget)
        dlg.adjustSize()
        if dlg.exec():
            self.units = quantityWidget.units

    @Slot()
    def _slot_setSingleStepGUI(self):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        dlg = qd.QuickDialog(parent=self, title="Set single step")
        # stepInput = qd.HSpinBox(dlg, "Step (float)", widget_type="d")
        stepInput = qd.HSpinBox(dlg, "Step (float|Scalar quantity):", widget_type="q")
        stepInput.familyRestriction = scq.getUnitFamily(self.units)
        stepInput.rescaleOnUnitChange = True
        stepInput.units = self.units
        stepInput.setDecimals(3)
        stepInput.setValue(self.singleStep())
        adaptiveCheckBox = qd.CheckBox(dlg, "Adaptive")
        adaptiveCheckBox.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        dlg.addWidget(stepInput)
        dlg.addWidget(adaptiveCheckBox)
        dlg.adjustSize()
        if dlg.exec():
            value = stepInput.value()
            stepType = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            if value != self.singleStep():
                self.setSingleStep(value)

            if stepType != self.stepType():
                self.setStepType(stepType)

    @Slot(bool)
    def _slot_toggleImmutableUnits(self, val:bool):
        self.disableUnitChange = val

    @Slot(bool)
    def _slot_familyRestrictionChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return

        if value:
            family = scq.getUnitFamily(self.units)
            self._restrictedToFamily_ = family
        else:
            self._restrictedToFamily_ = None

    @Slot(bool)
    def _slot_setAdaptiveStep(self, value:bool):
        stepType = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if value else QtWidgets.QAbstractSpinBox.DefaultStepType

        if stepType != self.stepType():
            self.setStepType(stepType)

    @Slot(bool)
    def _slot_rescaleValueChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        self._rescaleOnUnitChange_ = value

    @Slot()
    def _slot_setDecimalsGUI(self):
        dlg = qd.QuickDialog(parent=self, title="Set decimals")
        decimalsInput = qd.HSpinBox(dlg, "Decimals (int) >= 0:")
        decimalsInput.setValue(self._decimals_)
        decimalsInput.setMinimum(0)
        dlg.addWidget(decimalsInput)
        dlg.adjustSize()
        if dlg.exec():
            value = decimalsInput.value()
            if value < 0:
                value  = 0
            self.setDecimals(value)

    @Slot()
    def _slot_setRangeGUI(self):
        dlg = qd.QuickDialog(parent=self, title="Set range (min, max)")
        group = qd.DialogGroup(dlg)
        unitsLabel = ""
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            unitsLabel = self._prefix_ if len(self._prefix_) else self._suffix_ if len(self._suffix_) else ""
        minimumInput = qd.HSpinBox(group, f"Minimum:", widget_type="q", decimals=3)
        minimumInput.setValue(self._default_internal_minimum_ * self.units)
        maximumInput = qd.HSpinBox(group, f"Maximum:", widget_type="q", decimals=3)
        maximumInput.setValue(self._default_internal_maximum_ * self.units)
        group.addWidget(minimumInput)
        group.addWidget(maximumInput)
        dlg.addWidget(group)
        dlg.adjustSize()

        if dlg.exec():
            minimum = minimumInput.value()
            maximum = maximumInput.value()
            self.setMinimum(minimum)
            self.setMaximum(maximum)

    @Slot()
    def _slot_reset(self):
        self.setSingleStep(self._default_singleStep_)
        self.setDecimals(self._default_decimals_)
        self.units = self._default_units_
        self._magnitude_ = 0.

    def _calculateAdaptiveDecimalStep(self, steps:int) -> float:
        """Subject to future teaks, this is almost exactly what
    QAbstractSpinBox.calculateAdaptiveDecimalStep() does.
    The difference is that we use self._magnitude_ instead of self.value()
    """
        value = self._magnitude_
        decimals = self.decimals
        minStep = math.pow(10, -decimals)
        absVal = abs(value)

        if absVal < minStep:
            return minStep

        valNeg = value < 0
        stepsNeg = steps < 0

        if valNeg != stepsNeg:
            absVal /= 1.01

        shift = math.pow(10, 1 - math.floor(math.log(10, absVal)))
        absRound = round(absVal * shift, decimals) / shift
        logVal = math.floor(math.log(10, absRound)) - 1
        return max(minStep, math.pow(10, logVal))

    def stepBy(self, steps:int):
        signalBlocker = QtCore.QSignalBlocker(self._lineEdit_)
        step = self._singleStep_ * steps
        # print(f"{self.__class__.__name__}.stepBy({steps})")
        # print(f"\tsingle step = {self._singleStep_}; step  = {step}")
        # print(f"\tcurrent magnitude: {self._magnitude_}")
        if isinstance(self._singleStep_, pq.Quantity):
            if self._singleStep_.size != 1:
                raise ValueError(f"Single step must be a scalar; instead got {self._singleStep_}")
            stepUnits = self._singleStep_.units
            if isinstance(self._units_, pq.Quantity):
                if all(self._units_ != pq.dimensionless) and all(stepUnits != self._units_):
                    if not scq.unitsConvertible(stepUnits, self._units_):
                        raise ValueError(f"Step units ({stepUnits}) are incompatible with value's units ({self._units_})")

                    sgStep = self._singleStep_.rescale(self._units_).magnitude
            else:
                sgStep = self._singleStep_.magnitude

        elif isinstance(self._singleStep_, (int, float)):
            sgStep = self._singleStep_
        else:
            raise TypeError(f"singleStep has wrong object type: {type(self._singleStep_).__name__}")

        self._magnitude_ = self._magnitude_ + sgStep * steps
        # print(f"\tnew magnitude: {self._magnitude_}")
        decimals = self._decimals_
        self._lineEdit_.lazy = True
        self._update_(forceSgStep = sgStep)
        self._lineEdit_.lazy = False
        # restore single step & decimals
        # self._singleStep_ = sgStep
        # self._decimals_ = decimals
        # value = self._magnitude_ + steps * self._singleStep_
        # super().stepBy(steps)
        # txt = self.lineEdit().displayText()
        # val = self.valueFromText(txt)
        # self._magnitude_ = float(val)
        # print(f"\tnew magnitude again: {self._magnitude_}")
        self.sig_valueChanged.emit(self.value())

    def singleStep(self) -> typing.Union[pq.Quantity, float, int]:
        ret = self._singleStep_
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        else:
            return ret * self.units

    def setSingleStep(self, value:float|pq.Quantity):
        if isinstance(value, pq.Quantity):
            if value.size != 1:
                raise TypeError("Scalar quantity expected")

            if value.units != self.units:
                if not scq.unitsConvertible(value, self.units):
                    raise ValueError(f"Cannot set single step with units ({value.units}) that are not scalable to the current units ({self.units})")
                v = float(value.rescale(self.units).magnitude)

            else:
                v = float(value.units)

        elif isinstance(value, (float, int)):
            v = float(value)
        else:
            raise TypeError(f"Expecting a scalar quantity or float; instead, got a {type(value).__name__}")

        self._singleStep_ = v

        # super().setSingleStep(self._singleStep_)

    @property
    def keepDimensionless(self) -> bool:
        return self._keepDimensionless_

    @keepDimensionless.setter
    def keepDimensionless(self, val:bool):
        self._keepDimensionless_ = val
        if self._keepDimensionless_ or self._forceDimensionless_:
            super().setSuffix("")
            super().setPrefix("")
        else:
            super().setSuffix(self._suffix_)
            super().setPrefix(self._prefix_)

        self.update()

    @property
    def forceDimensionless(self) -> bool:
        return self._forceDimensionless_

    @forceDimensionless.setter
    def forceDimensionless(self, val:bool):
        self._forceDimensionless_ = val
        self.update()

class ComplexSpinBox(QtWidgets.QFrame):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    _default_units_                =  pq.dimensionless
    _default_internal_minimum_real = _default_internal_minimum_imag = -math.inf
    _default_internal_maximum_real = _default_internal_maximum_imag =  math.inf

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 units:typing.Optional[typing.Union[pq.Quantity, float, complex, int]]=None,
                 singleStepReal:typing.Optional[float]=None,
                 singleStepImag:typing.Optional[float]=None,
                 stepTypeReal:typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 stepTypeImag:typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 decimals:typing.Optional[int]=None,
                 decimalsReal:typing.Optional[int]=None,
                 decimalsImag:typing.Optional[int]=None,
                 minimumImag:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 maximumReal:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 maximumImag:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 minimumReal:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 useQuantities:bool=False,
                 unitsFamily:typing.Optional[str]=None,
                 fixUnitFamily:typing.Optional[typing.Union[str, bool]]=None,
                 rescaleWithUnitsChange:bool=False,
                 keepDimensionless:bool=False,
                 ):
        QtWidgets.QFrame.__init__(self, parent)
        if isinstance(parent, QtWidgets.QWidget):
            parent.addWidget(self)
        self._layout_ = QtWidgets.QHBoxLayout(self)
        self._layout_.setSpacing(0)
        self.prefixLabel = QtWidgets.QLabel(self)
        self.prefixLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.prefixLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        # self.realSpinBox = QtWidgets.QSpinBox(self)
        self.realSpinBox = QuantitySpinBox(self, decimals=3)#, keepDimensionless = True)
        self.realSpinBox.forceDimensionless = True
        self.realSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        # self.imagSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.imagSpinBox = QuantitySpinBox(self, decimals=3)#, keepDimensionless = True)
        self.imagSpinBox.forceDimensionless = True
        self.imagSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        self.plusLabel = QtWidgets.QLabel(self)
        self.plusLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.plusLabel.setText(" + ")
        self.plusLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.jLabel = QtWidgets.QLabel(self)
        self.jLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.jLabel.setText(" × j")
        self.jLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.suffixLabel = QtWidgets.QLabel(self)
        self.suffixLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.suffixLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        self._layout_.addWidget(self.prefixLabel)
        self._layout_.addWidget(self.realSpinBox)
        self._layout_.addWidget(self.plusLabel)
        self._layout_.addWidget(self.imagSpinBox)
        self._layout_.addWidget(self.jLabel)
        self._layout_.addWidget(self.suffixLabel)
        self._layout_.addStretch(5)
        # self.setLayout(self._layout_)

        self._restrictedToFamily_:typing.Optional[str] = None
        self._rescaleOnUnitChange_:bool = False
        self._keepDimensionless_ = keepDimensionless
        self._forceDimensionless_:bool = False

        self._units_:pq.Quantity = self._default_units_
        self._magnitude_:complex = complex(0.0, 0.0)
        self._prefix_ = ""
        self._suffix_ = ""

        if isinstance(units, pq.Quantity):
            self._units_ = units.units
            if not isinstance(units, pq.UnitQuantity):
                if units.size != 1:
                    raise TypeError(f"Expecting a scalar quantity; instead, got a Quantity array with {units.size} elements")
                self._magnitude_ = complex(units.magnitude)
        else:
            if isinstance(units, (float, int)):
                self._magnitude_ = complex(units)
            elif isinstance(units, complex):
                self._magnitude_ = units
            elif units is not None:
                raise TypeError(f"Invalid 'units' argument: {units}")

            self._units_ = self._default_units_

        self._unitFamily_ = scq.getUnitFamily(self._units_)

        if self._units_.dimensionality == pq.dimensionless.dimensionality:
            self._prefix_ = ""
            self._suffix_ = ""
        else:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._prefix_ = f"{symbol} "
                self._suffix_ = ""
            else:
                self._prefix_ = ""
                self._suffix_ = f" ({symbol})"

        self._default_singleStep_real = self.realSpinBox.singleStep()

        if isinstance(singleStepReal,float):
            self._singleStepReal_ = singleStepReal

        elif singleStepReal is None:
            self._singleStepReal_ = self._default_singleStep_real
        else:
            raise TypeError(f"singleStepReal expected to be a float or None; instead, got {singleStepReal}")

        self._default_singleStep_imag = self.imagSpinBox.singleStep()
        if isinstance(singleStepImag,float):
            self._singleStepImag_ = singleStepImag

        elif singleStepImag is None:
            self._singleStepImag_ = self._default_singleStep_imag
        else:
            raise TypeError(f"singleStepImag expected to be a float or None; instead, got {singleStepImag}")

        self._default_decimals_real = -int(math.log10(abs(self._singleStepReal_))) if (self._singleStepReal_ < 1 and self._singleStepReal_ > -1) else 1
        self._decimals_real = self._default_decimals_real

        if isinstance(decimalsReal, int) and decimalsReal >= 0:
            self._decimals_real = decimalsReal

        elif decimalsReal is None:
            if isinstance(decimals, int) and decimals >= 0:
                self._decimals_real = decimals
            else:
                self._decimals_real = self._default_decimals_real

        else:
            raise TypeError(f"decimalsReal expected to be an int >= 0 or None; instead, got {decimalsReal}")

        self._default_decimals_imag = -int(math.log10(abs(self._singleStepImag_))) if (self._singleStepImag_ < 1 and self._singleStepImag_ > -1) else 1
        self._decimals_imag = self._default_decimals_imag

        if isinstance(decimalsImag, int) and decimalsImag >= 0:
            self._decimals_imag = decimalsImag

        elif decimalsImag is None:
            if isinstance(decimals, int) and decimals >= 0:
                self._decimals_imag = decimals
            else:
                self._decimals_imag = self._default_decimals_imag

        else:
            raise TypeError(f"decimalsImag expected to be an int >= 0 or None; instead, got {decimalsImag}")

        self._internal_minimum_real = self._default_internal_minimum_real
        self._internal_maximum_real = self._default_internal_maximum_real

        self._internal_minimum_imag = self._default_internal_minimum_imag
        self._internal_maximum_imag = self._default_internal_maximum_imag

        if isinstance(stepTypeReal, QtWidgets.QAbstractSpinBox.StepType):
            self._stepType_real = stepTypeReal
        else:
            self._stepType_real = QtWidgets.QAbstractSpinBox.DefaultStepType

        if isinstance(stepTypeImag, QtWidgets.QAbstractSpinBox.StepType):
            self._stepType_imag = stepTypeImag
        else:
            self._stepType_imag = QtWidgets.QAbstractSpinBox.DefaultStepType

        self._setupSpinBox_(self.realSpinBox, self._internal_minimum_real,
                            self._internal_maximum_real, self._decimals_real,
                            self._singleStepReal_, self._stepType_real, self._magnitude_.real)

        self.realSpinBox.sig_valueChanged.connect(self._slot_valueChanged)

        self._setupSpinBox_(self.imagSpinBox, self._internal_minimum_imag,
                            self._internal_maximum_imag, self._decimals_imag,
                            self._singleStepImag_, self._stepType_imag,
                            self._magnitude_.imag)

        self.imagSpinBox.sig_valueChanged.connect(self._slot_valueChanged)

        self.prefixLabel.setText(self._prefix_)
        self.suffixLabel.setText(self._suffix_)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def _setupSpinBox_(self, spinBox, minimum, maximum, decimals, singleStep, stepType, value):
        spinBox.setMinimum(minimum)
        spinBox.setMaximum(maximum)
        spinBox.setDecimals(decimals)
        spinBox.setSingleStep(singleStep)
        spinBox.setStepType(stepType)
        spinBox.setValue(value)

    def value(self) -> complex | pq.Quantity:
        ret = self._magnitude_
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret

        return ret * self._units_

    def validate(self, *args):
        r"""For compatibilty with qd.QuickDialog"""
        return True

    def setValue(self, value:typing.Union[complex, float, int, pq.Quantity]):
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                # return # Only scalar quantities are allowed
                raise TypeError("Only scalar quantities are allowed")

            if value.dtype == np.dtype("complex"):
                cval = complex(value.magnitude)
            else:
                cval = complex(float(value.magnitude), 0.0)

            if not (self._keepDimensionless_ or self._forceDimensionless_):
                if scq.unitsConvertible(self.units, value.units):
                    if any( (v > -math.inf and v < math.inf) for v in (cval.real, cval.imag)):
                        cval = complex((cval*value.units).rescale(self.units).magnitude)
                else:
                    self.units = value.units

            self._magnitude_ = cval

        elif value in (pd.NA, math.nan, np.nan):
            self._magnitude_ = complex(value, value)

        elif isinstance(value, float):
            self._magnitude_ = complex(value, 0.0)

        elif isinstance(value, int):
            self._magnitude_ = complex(float(value), 0.0)

        else:
            raise ValueError(f"Incompatible value: {value}")

        self.realSpinBox.setValue(self._magnitude_.real)
        self.imagSpinBox.setValue(self._magnitude_.imag)

    @property
    def decimals(self) -> tuple:
        return (self.realSpinBox.getDecimals(), self.imagSpinBox.getDecimals())

    @decimals.setter
    def decimals(self, value:tuple[int]):
        self.setDecimals(value)

    def setDecimals(self, value:typing.Union[int, typing.Sequence[int]]):
        if isinstance(value, typing.Sequence) and all(isinstance(v, int) for v in value):
            if any (v<0 for v in value):
                raise ValueError("Decimals must be >= 0")

            if len(value) < 2:
                self.realSpinBox.setDecimals(value[0])
                self.imagSpinBox.setDecimals(value[0])
            else:
                self.realSpinBox.setDecimals(value[0])
                self.imagSpinBox.setDecimals(value[1])

        elif isinstance(value, int):
            if value < 0:
                raise ValueError("Decimals must be >= 0")
            self.realSpinBox.setDecimals(value)
            self.imagSpinBox.setDecimals(value)

    def singleStep(self) -> tuple:
        ret = (self.realSpinBox.singleStep(), self.imagSpinBox.singleStep())
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return tuple(map(lambda v: v * self.units, ret))

    def setSingleStep(self, value:typing.Union[typing.Sequence[float|int|pq.Quantity], float, int, pq.Quantity]):
        if isinstance(value, pq.Quantity):
            if value.size == 1:
                realStep = imagStep = float(value.magnitude)
            elif value.size == 2:
                realStep, imagStep = tuple(map(lambda v: float(v.magnitude), value))
            else:
                raise TypeError(f"Invalid number of elements in value argument: {value.size}; expecting 1 or 2")

            if not scq.unitsConvertible(value, self.units):
                raise ValueError(f"Cannot set single step with units ({value.units}) that are not scalable to the current units ({self.units})")
            realStep = float((realStep*value.units).rescale(self.units).magnitude)
            imagStep = float((imagStep*value.units).rescale(self.units).magnitude)


        elif isinstance(value, (float, int)):
            realStep = imagStep = float(value)

        elif isinstance(value, typing.Sequence):
            if len(value) == 1:
                value = value[0]
                if isinstance(value, (float, int)):
                    realStep = imagStep = float(value)

                elif isinstance(value, pq.Quantity):
                    if not scq.unitsConvertible(value, self.units):
                        raise ValueError(f"Cannot set single step with units ({value.units}) that are not scalable to the current units ({self.units})")
                    realStep = imagStep = float(value.rescale(self.units).magnitude)
                else:
                    raise TypeError(f"Wrong value type: {type(value).__name__}")

            elif len(value) >= 2:
                realStep, imagStep = value[0:2]

                if isinstance(realStep, (float, int)):
                    realStep = float(realStep)

                elif isinstance(realStep, pq.Quantity):
                    if not scq.unitsConvertible(realStep, self.units):
                        raise ValueError(f"Cannot set single step with units ({realStep.units}) that are not scalable to the current units ({self.units})")
                    realStep = float(realStep.rescale(self.units).magnitude)

                else:
                    TypeError(f"Wrong real value type: {type(realStep).__name__}")

                if isinstance(imagStep, (float, int)):
                    imagStep = float(imagStep)

                elif isinstance(imagStep, pq.Quantity):
                    if not scq.unitsConvertible(imagStep, self.units):
                        raise ValueError(f"Cannot set single step with units ({imagStep.units}) that are not scalable to the current units ({self.units})")
                    imagStep = float(imagStep.rescale(self.units).magnitude)

                else:
                    TypeError(f"Wrong real value type: {type(imagStep).__name__}")

            else:
                raise TypeError("Expecting at least one value in the sequence")
        else:
            raise TypeError(f"Expecting a scalar quantity, float, int or a sequence of at least twpo of these data types; instead, got a {type(value).__name__}")

        self.realSpinBox.setSingleStep(realStep)
        self.imagSpinBox.setSingleStep(imagStep)

    def stepType(self) -> tuple:
        return (self.realSpinBox.stepType(), self.imagSpinBox.stepType())

    def setStepType(self, value:typing.Sequence[QtWidgets.QAbstractSpinBox.StepType]):
        if isinstance(value, typing.Sequence) and len(value) == 2 and all(isinstance(v, QtWidgets.QAbstractSpinBox.StepType) for v in value):
            self.realSpinBox.setStepType(value[0])
            self.imagSpinBox.setStepType(value[1])

        else:
            raise ValueError(f"Incorrect step type specification ({value}); expecting a sequence of two QtWidgets.QAbstractSpinBox.StepType enum values")

    def contextMenuEvent(self, evt):
        cm = QtWidgets.QMenu("Options", self)
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            setUnitsAction = cm.addAction("Set units")
            setUnitsAction.triggered.connect(self._slot_setUnitsGUI)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimalsGUI)
        setSingleStepAction = cm.addAction("Set single step")
        setSingleStepAction.triggered.connect(self._slot_setSingleStepGUI)
        adaptiveStepAction = cm.addAction("Adaptive step")
        adaptiveStepAction.setCheckable(True)
        adaptiveStepAction.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        adaptiveStepAction.toggled.connect(self._slot_setAdaptiveStep)
        setRangeAction = cm.addAction("Set range (min, max)")
        setRangeAction.triggered.connect(self._slot_setRangeGUI)
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            cm.addSeparator()
            rescaleValueAction = cm.addAction("Rescale on unit change")
            rescaleValueAction.setCheckable(True)
            rescaleValueAction.setChecked(self._rescaleOnUnitChange_)
            rescaleValueAction.toggled.connect(self._slot_rescaleValueChanged)
            restrictAction = cm.addAction("Fix units family")
            restrictAction.setCheckable(True)
            restrictAction.setChecked(isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT)
            restrictAction.toggled.connect(self._slot_familyRestrictionChanged)
        cm.addSeparator()
        if not self.forceDimensionless:
            toggleDimensionlessAction = cm.addAction("Ignore dimensionality")
            toggleDimensionlessAction.setCheckable(True)
            toggleDimensionlessAction.setChecked(self._keepDimensionless_)
            toggleDimensionlessAction.toggled.connect(self._slot_keepDimensionless)
        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(self.mapToGlobal(evt.pos()))

    # @Slot(float)
    # def _slot_valueChanged(self, val):
    #     self.sig_valueChanged.emit(self.value())

    @Slot(bool)
    def _slot_keepDimensionless(self, val:bool):
        self.keepDimensionless = val

    @Slot()
    def _slot_setDecimalsGUI(self):
        realVal = self._decimals_real
        imagVal = self._decimals_imag
        dlg  = qd.QuickDialog(parent=self, title="Set decimals")
        realInput = qd.HSpinBox(dlg, "Decimals, real part (int) >= 0:")
        realInput.setMinimum(0)
        realInput.setValue(realVal)
        imagInput = qd.HSpinBox(dlg, "Decimals, imaginary part (int) >= 0:")
        imagInput.setMinimum(0)
        imagInput.setValue(imagVal)
        dlg.addWidget(realInput)
        dlg.addWidget(imagInput)
        dlg.adjustSize()
        if dlg.exec():
            realVal = realInput.value()
            if realVal < 0:
                realVal = 0
            imagVal = imagInput.value()
            if imagVal < 0:
                imagVal = 0
        self.realSpinBox.setDecimals(realVal)
        self.imagSpinBox.setDecimals(imagVal)

    @Slot()
    def _slot_setSingleStepGUI(self):
        realVal = self._singleStepReal_
        imagVal = self._singleStepImag_
        dlg  = qd.QuickDialog(parent=self, title="Set single step")
        realGrp = qd.DialogGroup(dlg)
        realInput = qd.HSpinBox(realGrp, "Real part:", widget_type="f")
        realInput.setValue(realVal)
        adaptiveRealCheckBox = qd.CheckBox(realGrp, "Adaptive")
        adaptiveRealCheckBox.setChecked(self.stepType()[0] == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        realGrp.addWidget(realInput, QtCore.Qt.AlignVCenter)
        realGrp.addWidget(adaptiveRealCheckBox, QtCore.Qt.AlignVCenter)
        # realInput.setMinimum(0)
        imagGrp = qd.DialogGroup(dlg)
        imagInput = qd.HSpinBox(imagGrp, "Imaginary part:", widget_type="f")
        imagInput.setValue(imagVal)
        adaptiveImagCheckBox = qd.CheckBox(imagGrp, "Adaptive")
        adaptiveImagCheckBox.setChecked(self.stepType()[1] == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        imagGrp.addWidget(imagInput, QtCore.Qt.AlignVCenter)
        imagGrp.addWidget(adaptiveImagCheckBox, QtCore.Qt.AlignVCenter)
        # imagInput.setMinimum(0)

        # dlg.addWidget(realInput)
        # dlg.addWidget(imagInput)
        dlg.addWidget(realGrp)
        dlg.addWidget(imagGrp)
        dlg.adjustSize()
        if dlg.exec():
            realVal = realInput.value()
            imagVal = imagInput.value()
            adaptiveReal = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveRealCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            adaptiveImag = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveImagCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            self.realSpinBox.setSingleStep(realVal)
            self.realSpinBox.setStepType(adaptiveReal)
            self.imagSpinBox.setSingleStep(imagVal)
            self.imagSpinBox.setStepType(adaptiveImag)

    @Slot()
    def _slot_setUnitsGUI(self):
        dlg = qd.QuickDialog(parent = self, title="Set units")
        quantityWidget = QuantityChooserWidget(parent = dlg)
        quantityWidget.units = self._units_
        if isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT:
            quantityWidget.familyRestriction = self._restrictedToFamily_
        else:
            quantityWidget.familyRestriction = None

        dlg.addWidget(quantityWidget)
        dlg.adjustSize()
        if dlg.exec():
            self.units = quantityWidget.units

    @Slot(bool)
    def _slot_rescaleValueChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        self._rescaleOnUnitChange_ = value
        # self.realSpinBox.rescaleOnUnitChange = value
        # self.imagSpinBox.rescaleOnUnitChange = value

    @Slot(bool)
    def _slot_familyRestrictionChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return

        if value:
            family = scq.getUnitFamily(self.units)
            self._restrictedToFamily_ = family
        else:
            self._restrictedToFamily_ = None

    @Slot(object)
    def _slot_valueChanged(self, val_:object):
        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_reset(self):
        for w in (self.realSpinBox, self.imagSpinBox):
            w.self_reset()
        self.units = self._default_units_

    @property
    def units(self):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._units_

    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        # print(f"{self.__class__.__name__}.units.setter: value = {value}")
        if self._keepDimensionless_ or self._forceDimensionless_:
            return

        if not isinstance(value, pq.Quantity):
            value = pq.dimensionless

        myVal = self.value()

        if isinstance(myVal, pq.Quantity) and myVal.dtype == np.dtype("complex"):
            myReal = float(myVal.magnitude.real)
            myImag = float(myVal.magnitude.imag)
        else:
            myReal = float(myVal.magmitude)
            myImag = 0.0

        if self._rescaleOnUnitChange_ and scq.unitsConvertible(value, self._units_) and any(v not in (math.nan, np.nan, -math.inf, math.inf, -np.inf, np.inf) for v in (myReal, myImag)):
            scaledval = self.value().rescale(value)
            newval = complex(scaledval.magnitude) if scaledval.dtype == np.dtype("complex") else float(scaledval.magnitude)
            ratio = newval/self._magnitude_
            realStep = self.realSpinBox.singleStep() * ratio
            imagStep = self.imagSpinBox.singleStep() * ratio
            self._magnitude_ = complex(scaled.magnitude) if scaledval.dtype == np.dtype("complex") else float(scaledval.magnitude)
            self._units_ = newval.units
            self.realSpinBox.setValue(self._magnitude_.real)
            self.realSpinBox.setSingleStep(realStep)
            self.imagSpinBox.setValue(self._magnitude_.imag)
            self.imagSpinBox.setsingleStep(imagStep)
        else:
            self._units_ = value.units

        self._unitFamily_ = scq.getUnitFamily(self._units_)

        self._suffix_ = ""
        self._prefix_ = ""

        if self._units_.dimensionality != pq.dimensionless.dimensionality:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._prefix_ = f"{symbol} "
                self._suffix_ = ""
            else:
                self._prefix_ = ""
                self._suffix_ = f" ({symbol})"

        self.prefixLabel.setText(self._prefix_)
        self.suffixLabel.setText(self._suffix_)

    @property
    def keepDimensionless(self) -> bool:
        return self._keepDimensionless_

    @keepDimensionless.setter
    def keepDimensionless(self, val:bool):
        self._keepDimensionless_ = val
        if self._keepDimensionless_ or self._forceDimensionless_:
            super().setSuffix("")
            super().setPrefix("")
        else:
            super().setSuffix(self._suffix_)
            super().setPrefix(self._prefix_)

        self.update()

    @property
    def forceDimensionless(self) -> bool:
        return self._forceDimensionless_

    @forceDimensionless.setter
    def forceDimensionless(self, val:bool):
        self._forceDimensionless_ = val
        self.update()

    @property
    def rescaleOnUnitChange(self)->bool:
        if self._keepDimensionless_ or self._forceDimensionless_:
            return False
        return self._rescaleOnUnitChange_

    @rescaleOnUnitChange.setter
    def rescaleOnUnitChange(self, val:bool):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            self._rescaleOnUnitChange_ = val

class GenericInputWidget(QtWidgets.QFrame):
    r"""GUI to instantiate new POD values"""

    sig_valueChanged = Signal(object, name = "sig_valueChanged")

    SUPPORTED_TYPES = (bool, Tribool, int, float, complex,
                       np.integer, np.floating, np.complexfloating,
                       pq.UnitQuantity, pq.Quantity, str, type(None), type(pd.NA))

    # TODO: 2026-04-09 01:14:54
    # implement instantiation of objects with default (0-argument) c'tor -- maybe in a separate widget

    def __init__(self, varType: typing.Union[
                            typing.Set[type], typing.Sequence[type],
                            typing.Sequence[numbers.Number],
                            pq.UnitQuantity, pq.Quantity,
                            InputSpec, dataclasses.Field,
                            type(None),
                            type(dataclasses.MISSING)
                            ] = dataclasses.MISSING,
                 default = dataclasses.MISSING,
                 value = dataclasses.MISSING,
                 valueChoices: typing.Optional[
                     typing.Union[typing.Set, typing.Sequence]
                     ] = None,
                 parent = None):
        super().__init__(parent = parent)
        if isinstance(parent, QtWidgets.QWidget):
            parent.addWidget(self)

        self._inputWidget_ = None
        self._typeCombo_ = None
        self._value_ = dataclasses.MISSING

        if varType == dataclasses.MISSING:
            # NOTE: 2026-04-06 22:13:01
            # allow default c'tor, needed to use this by PythonItemDelegate
            self._vartype_ = varType

        elif varType in (None, type(None)):
            self._vartype_ = type(None)

        elif varType in (pd.NA, type(pd.NA)):
            self._vartype_ = type(pd.NA)

        else:
            if isinstance(varType, InputSpec):
                default = varType.default
                valueChoices = varType.allowed_values
                if value is dataclasses.MISSING and varType.value is not dataclasses.MISSING:
                    value = varType.value
                varType = varType.type

            elif isinstance(varType, dataclasses.Field):
                varType, default, value_ = InputSpec.parse_args(varType, None)
                if value is dataclasses.MISSING and value is not dataclasses.MISSING:
                    value = value_

            elif isinstance(varType, typing._Final):
                t = prog.unwind_type(varType)
                if len(t) == 0:
                    if default not in (dataclasses.MISSING, None): # get it from default's type
                        t = {type(default)}
                    else:
                        t = {object}

                varType = t

            # print(f"{self.__class__.__name__}.__init__ -> varType is a {type(varType).__name__}: {varType}")

            if isinstance(varType, type) and varType in self.SUPPORTED_TYPES:
                self._vartype_ = varType

            # elif isinstance(varType, (typing.Set, typing.Sequence)):
            #     if len(varType):

            if not ((isinstance(varType, type) and varType in self.SUPPORTED_TYPES)
                    or (
                        isinstance(varType, (typing.Set, typing.Sequence))
                        and len(varType)>0
                        and all(dt.check_type(v, self.SUPPORTED_TYPES).value for v in varType)
                        # and all((isinstance(v, type) and dt.check_type(v, self.SUPPORTED_TYPES).value) for v in varType)
                        )
                    ):
                raise TypeError(f"Expecting a type, or a non-empty set or sequence of types, with all types being one of {self.SUPPORTED_TYPES}; instead, got {varType}")

            self._vartype_ = varType

        if self._vartype_ == dataclasses.MISSING:
            self._vartype_names_ = list()
            self._current_vartype_ = dataclasses.MISSING
            self._default_ = dataclasses.MISSING

        else:
            if isinstance(self._vartype_, type):
                self._vartype_names_ = self._vartype_.__name__
                self._current_vartype_ = self._vartype_

                if type(default) is self._vartype_:
                    self._default_ = default

                else:
                    self._default_ = dataclasses.MISSING

            else:
                if isinstance(self._vartype_, set):
                    self._vartype_ = tuple(self._vartype_)

                ndx = 0
                if type(default) in self._vartype_:
                    ndx = self._vartype_.index(type(default))
                    self._default_ = default
                else:
                    self._default_ = dataclasses.MISSING

                self._current_vartype_ = self._vartype_[ndx]

                self._vartype_names_ = list(map(lambda t: t.__name__, self._vartype_))

            if isinstance(valueChoices, set):
                valueChoices = list(valueChoices)

        # NOTE: 2026-04-06 15:52:20
        #  self._value_choices_ is the mapping value_type -> sequence of values of type 'value_type'
        # print(f"{self.__class__.__name__}.__init__: _vartype_ = {self._vartype_}")
        if isinstance(valueChoices, typing.Sequence) and len(valueChoices):
            if all(isinstance(c, self._vartype_) for c in valueChoices):
                if isinstance(self._vartype_, type):
                     self._value_choices_ = {self._vartype_: valueChoices}

                else:
                     self._value_choices_ = dict(map(lambda t: (t, unique(list(filter(lambda c: isinstance(c, t), valueChoices)))), self._vartype_))
        else:
             self._value_choices_ = dict()

        self._validator_ = None

        if value is not dataclasses.MISSING:
            if dt.check_type(value, self._vartype_).value:
                self._value_ = value

        else:
            self._value_ = self._default_

        # print(f"{self.__class__.__name__}.__init__ -> _vartype_ = {self._vartype_}, _default_ = {self._default_}")
        self._configureUI_()

        self._cached_value_ = {self._current_vartype_: self._value_}

    def _configureUI_(self):
        self._layout_ = QtWidgets.QHBoxLayout(self)
        self._layout_.setSpacing(0)
        self._layout_.setContentsMargins(0,0,0,0)
        # self.setLayout(self._layout_) # already added in layout c'tor with parent=self

        self._setup_widgets_()

    def _setup_widgets_(self):
        if self._vartype_ == dataclasses.MISSING:
            self._inputWidget_ = self._createInputWidget_(self._vartype_)

        elif isinstance(self._vartype_, type):
            self._inputWidget_ = self._createInputWidget_(self._vartype_)
            self._typeCombo_ = None
        else:
            self._typeCombo_ = QtWidgets.QComboBox(parent=self)
            self._typeCombo_.setEditable(False)
            self._typeCombo_.insertItems(0, self._vartype_names_)
            if self._current_vartype_ in self._vartype_:
                ndx = self._vartype_.index(self._current_vartype_)
                self._typeCombo_.setCurrentIndex(ndx)
            #     self._current_vartype_ = self._vartype_[0]
            #     ndx = 0
            # else:
            self._inputWidget_ = self._createInputWidget_(self._current_vartype_)
            self._typeCombo_.currentIndexChanged.connect(self._slot_typeIndexChanged)

        if self._typeCombo_:
            self._layout_.addWidget(self._typeCombo_)

        self._layout_.addWidget(self._inputWidget_)

        self._layout_.setStretchFactor(self._inputWidget_,1)

    @Slot(object)
    @Slot(bool)
    @Slot(Tribool)
    @Slot(int)
    @Slot(float)
    @Slot(complex)
    @Slot(str)
    @Slot(np.integer)
    @Slot(np.floating)
    @Slot(np.complexfloating)
    @Slot(pq.UnitQuantity)
    @Slot(pq.Quantity)
    @Slot(QtCore.Qt.CheckState)
    def _slot_inputValueChanged(self, val:object):
        if isinstance(self._vartype_, type):
            self._current_vartype_ = self._vartype_
        else:
            if not isinstance(self._typeCombo_, QtWidgets.QComboBox):
                return
            ndx = self._typeCombo_.currentIndex()
            if ndx < 0 or ndx >= len(self._vartype_):
                return
            self._current_vartype_ = self._vartype_[ndx]

        if isinstance(val, QtCore.Qt.CheckState):
            if self._current_vartype_  is Tribool:
                v_ = None if val == QtCore.Qt.PartiallyChecked else True if val == QtCore.Qt.Checked else False
                self._cached_value_[self._current_vartype_] = Tribool(v_)

            elif self._current_vartype_ is bool:
                v_ = val == QtCore.Qt.Checked
                self._cached_value_[self._current_vartype_] = v_

        elif isinstance(val, self._current_vartype_):
            self._cached_value_[self._current_vartype_] = val

        else:
            return

        self.sig_valueChanged.emit(self._cached_value_[self._current_vartype_])

    @Slot(int)
    def _slot_valueChoiceIndexChanged(self, ndx:int):
        if len(self._value_choices_) == 0:
            return
        choices =  self._value_choices_.get(self._current_vartype_, list())
        if len(choices) == 0:
            return

        if ndx < 0 or ndx >= len(choices):
            return

        value = choices[ndx]

        if isinstance(value, self._current_vartype_):
            self._cached_value_[self._current_vartype_] = value

            self.sig_valueChanged.emit(self._cached_value_[self._current_vartype_])

    @Slot(int)
    def _slot_typeIndexChanged(self, val: int):
        if self._typeCombo_:
            self._layout_.removeWidget(self._inputWidget_)
            self._current_vartype_ = self._vartype_[val]
            if self._current_vartype_ in self._cached_value_:
                cachedVal = self._cached_value_[self._current_vartype_]
            else:
                cachedVal = dataclasses.MISSING

            self._inputWidget_ = self._createInputWidget_(self._current_vartype_)

            if isinstance(self._inputWidget_, QtWidgets.QComboBox):
                if self._current_vartype_ in self._value_choices_:
                    choices = self._value_choices_[self._current_vartype_]
                    if isinstance(cachedVal, self._current_vartype_):
                        if cachedVal != dataclasses.MISSING and isinstance(cachedVal, self._current_vartype_):
                            if cachedVal in choices:
                                sigBlock = QtCore.QSignalBlocker(self._inputWidget_)
                                self._inputWidget_.setCurrentIndex(choices.index(cachedVal))

                    ndx = self._inputWidget_.currentIndex()

                    if ndx >=0 and ndx < len(choices):
                        self._cached_value_[self._current_vartype_] = choices[ndx]

            elif isinstance(self._inputWidget_, QtWidgets.QCheckBox):
                if isinstance(cachedVal, Tribool):
                    checkState = QtCore.Qt.Checked if cachedVal.value == True else QtCore.Qt.Checked if cachedVal.value == False else QtCore.Qt.PartiallyChecked
                    self._inputWidget_.setCheckState(checkState)

                elif isinstance(cachedVal, bool):
                    self._inputWidget_.setChecked(cachedVal == True)

                state = self._inputWidget_.checkState()

                if self._current_vartype_  == Tribool:
                    v_ = None if state == QtCore.Qt.PartiallyChecked else True if state == QtCore.Qt.Checked else False
                    self._cached_value_[self._current_vartype_] = Tribool(v_)

                elif self._current_vartype_ == bool:
                    v_ = state == QtCore.Qt.Checked
                    self._cached_value_[self._current_vartype_] = v_

            else:
                if cachedVal != dataclasses.MISSING:
                    self._inputWidget_.setValue(cachedVal)

                self._cached_value_[self._current_vartype_] = self._inputWidget_.value()

            self._layout_.addWidget(self._inputWidget_)

    def value(self):
        if self._cached_value_[self._current_vartype_] == dataclasses.MISSING:
            if isinstance(self._inputWidget_, QtWidgets.QComboBox):
                ndx = self._inputWidget_.currentIndex()
                choices =  self._value_choices_.get(self._current_vartype_, list())
                if ndx >= 0 and ndx < len(choices):
                    self._cached_value_[self._current_vartype_] = choices[ndx]
            else:
                self._cached_value_[self._current_vartype_] = self._inputWidget_.value()

        return self._cached_value_[self._current_vartype_]

    def setValue(self, val: InputSpec | object):
        if isinstance(val, InputSpec):
            default = val.default
            valueChoices = val.choices
            self._vartype_ = val.type
        else:
            default = val
            valueChoices = None
            self._vartype_ = type(val)

        if isinstance(self._vartype_, type):
            self._vartype_names_ = self._vartype_.__name__
            self._current_vartype_ = self._vartype_

            if type(default) == self._vartype_:
                self._default_ = default

            else:
                self._default_ = dataclasses.MISSING

        else:
            if isinstance(self._vartype_, set):
                self._vartype_ = tuple(self._vartype_)

            ndx = 0
            if type(default) in self._vartype_:
                ndx = self._vartype_.index(type(default))
                self._default_ = default
            else:
                self._default_ = dataclasses.MISSING

            self._current_vartype_ = self._vartype_[ndx]

            self._vartype_names_ = list(map(lambda t: t.__name__, self._vartype_))

        if isinstance(valueChoices, set):
            valueChoices = list(valueChoices)

        # NOTE: 2026-04-06 15:52:20
        #  self._value_choices_ is the mapping value_type -> sequence of values of type 'value_type'
        # print(f"{self.__class__.__name__}.__init__: _vartype_ = {self._vartype_}")
        if isinstance(valueChoices, typing.Sequence) and len(valueChoices):
            if all(isinstance(c, self._vartype_) for c in valueChoices):
                if isinstance(self._vartype_, type):
                     self._value_choices_ = {self._vartype_: valueChoices}

                else:
                     self._value_choices_ = dict(map(lambda t: (t, unique(list(filter(lambda c: isinstance(c, t), valueChoices)))), self._vartype_))
        else:
            self._value_choices_ = dict()

        if self._inputWidget_:
            self._layout_.removeWidget(self._inputWidget_)

        if self._typeCombo_:
            self._layout_.removeWidget(self._typeCombo_)

        self._cached_value_.clear()

        # print(f"{self.__class__.__name__}.setValue -> self._default_ = {self._default_}, self._current_vartype_ = {self._current_vartype_}")

        self._setup_widgets_()

        sigBlock = QtCore.QSignalBlocker(self._inputWidget_)

        if not isinstance(self._inputWidget_, QtWidgets.QLabel):
            if self._typeCombo_:
                self._current_vartype_ = self._vartype_[self._typeCombo_.currentIndex()]

            if self._current_vartype_ in self._cached_value_:
                cachedVal = self._cached_value_[self._current_vartype_]
            else:
                cachedVal = dataclasses.MISSING

            if isinstance(self._inputWidget_, QtWidgets.QComboBox):
                if self._current_vartype_ in self._value_choices_:
                    choices = self._value_choices_[self._current_vartype_]
                    if isinstance(cachedVal, self._current_vartype_):
                        if cachedVal != dataclasses.MISSING and isinstance(cachedVal, self._current_vartype_):
                            if cachedVal in choices:
                                self._inputWidget_.setCurrentIndex(choices.index(cachedVal))

                    ndx = self._inputWidget_.currentIndex()

                    if ndx >=0 and ndx < len(choices):
                        self._cached_value_[self._current_vartype_] = choices[ndx]

            elif isinstance(self._inputWidget_, QtWidgets.QCheckBox):
                if isinstance(cachedVal, Tribool):
                    checkState = QtCore.Qt.Checked if cachedVal.value == True else QtCore.Qt.Checked if cachedVal.value == False else QtCore.Qt.PartiallyChecked
                    self._inputWidget_.setCheckState(checkState)
                elif isinstance(cachedVal, bool):
                    self._inputWidget_.setChecked(cachedVal == True)

                state = self._inputWidget_.checkState()

                if self._current_vartype_  == Tribool:
                    v_ = None if state == QtCore.Qt.PartiallyChecked else True if state == QtCore.Qt.Checked else False
                    self._cached_value_[self._current_vartype_] = Tribool(v_)

                elif self._current_vartype_ == bool:
                    v_ = state == QtCore.Qt.Checked
                    self._cached_value_[self._current_vartype_] = v_

            else:
                if cachedVal != dataclasses.MISSING:
                    self._inputWidget_.setValue(cachedVal)

                self._cached_value_[self._current_vartype_] = self._inputWidget_.value()

    def _createInputWidget_(self, t: typing.Union[type, type(dataclasses.MISSING)],
                            c: typing.Optional[typing.Sequence] = None
                            ) -> QtWidgets.QWidget:
        # print(f"{self.__class__.__name__}._createInputWidget_({t})")
        value = self._default_ if self._value_ is dataclasses.MISSING else self._value_
        if t in self._value_choices_ and len(self._value_choices_[t]):
            w = QtWidgets.QComboBox(parent = self)
            w.setEditable(False)
            w.insertItems(0, list(map(lambda v: f"{v}",  self._value_choices_[t])))
            if isinstance(value, t) and value in  self._value_choices_[t]:
                ndx =  self._value_choices_[t].index(self._default_)
                w.setCurrentIndex(ndx)
            else:
                w.setCurrentIndex(0)

            w.currentIndexChanged.connect(self._slot_valueChoiceIndexChanged)

        else:
            if t == bool:
                w = QtWidgets.QCheckBox(parent = self)
                w.setTristate(False)
                if isinstance(value, bool):
                    w.setChecked(value is True)
                w.toggled.connect(self._slot_inputValueChanged)

            elif t == Tribool:
                w = QtWidgets.QCheckBox(parent = self)
                w.setTristate(True)
                if isinstance(value, Tribool):
                    checkState = QtCore.Qt.Checked if value.value is True else QtCore.Qt.Unckecked if value.value is False else QtCore.Qt.PartiallyChecked
                    w.setCheckState(checkState)
                w.toggled.connect(self._slot_inputValueChanged)

            elif t in (int, np.integer):
                w = QtWidgets.QSpinBox(parent = self)
                w.setMinimum(-2147483648)
                w.setMaximum(2147483647)

                if isinstance(value, t):
                    w.setValue(value)
                w.valueChanged.connect(self._slot_inputValueChanged)

            elif t in (float, np.floating):
                w = QtWidgets.QDoubleSpinBox(parent = self)
                w.setMinimum(sys.float_info.min)
                w.setMaximum(sys.float_info.max)

                if isinstance(value, t):
                    w.setValue(value)
                w.valueChanged.connect(self._slot_inputValueChanged)

            elif t == (complex, np.complexfloating):
                w = ComplexSpinBox(parent = self)
                w.setMinimum(sys.float_info.min)
                w.setMaximum(sys.float_info.max)
                if isinstance(value, t):
                    w.setValue(value)
                w.sig_valueChanged.connect(self._slot_inputValueChanged)

            elif t == str:
                # print(f"LineEdit -> {self._default_}")
                w = LineEdit(parent=self)
                w.undoAvailable=True
                w.redoAvailable=True
                w.setClearButtonEnabled(True)
                if isinstance(value, str):
                    w.setText(value)
                w.textChanged.connect(self._slot_inputValueChanged)

            elif t == pq.UnitQuantity:
                w = QuantityChooserWidget(parent=self)
                if value is None:
                    value = pq.dimensionless
                elif isinstance(value, pq.Quantity) and not isinstance(value, pq.UnitQuantity):
                    if len(value.units.dimensionality) == 1:
                        if value == self._default_:
                            self._default_ = self._default_.units.dimensionality[0][0]
                            # self._value_ = self._value_.units.dimensionality[0][0]
                        # else:
                        #     self._value_ = self._value_.units.dimensionality[0][0]

                if isinstance(value, pq.UnitQuantity):
                    w.setValue(value)

                w.valuechanged.connect(self._slot_inputValueChanged)

            elif t in (pq.Quantity, np.ndarray):
                if isinstance(value, t):
                    if value.size == 1:
                        w = QuantitySpinBox(parent=self)
                    else:
                        w = ArrayEditorWidget(parent=self)
                    w.setValue(value)
                else:
                    w = QuantitySpinBox(parent=self)

                w.sig_valueChanged.connect(self._slot_inputValueChanged)

            elif t in (tuple, list, set):
                if isinstance(value, t):
                    if all(isinstance(v, numbers.Number) for v in value):
                        w = ArrayEditorWidget(parent=self)
                        w.setValue(value)

                    else:
                        raise TypeError("Only sequence of numbers are currently supported")

            elif t is type(None):
                w = QtWidgets.QLabel(parent=self)
                w.setText(f"{value}")

            elif t == dataclasses.MISSING:
                # FIXME: 2026-04-06 22:10:42
                # what to do with unsupported types?
                # currently uses a QLabel with no text, as a placeholder
                w = QtWidgets.QLabel(parent=self)
            else:
                raise TypeError(f"Unsupported data type {t.__name__}")

            if isinstance(w, QtWidgets.QLabel):
                if w.text() == "None":
                    self._default_ = None
                elif w.text() == f"{pd.NA}":
                    self._default_ = pd.NA
                else:
                    self._default_ = dataclasses.MISSING

            elif isinstance(w, QtWidgets.QCheckBox):
                state = w.checkState()

                if self._current_vartype_  == Tribool:
                    v_ = None if state == QtCore.Qt.PartiallyChecked else True if state == QtCore.Qt.Checked else False
                    self._value_ = Tribool(v_)

                elif self._current_vartype_ == bool:
                    v_ = state == QtCore.Qt.Checked
                    self._value_ = v_
            else:
                self._value_ = w.value()

        w.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                        QtWidgets.QSizePolicy.Fixed)

        return w

    def _check_update_value_choices_(self, t: type, val: typing.Any):
        if t in  self._value_choices_ and len( self._value_choices_[t]):
            if isinstance(val, t) and val not in  self._value_choices_[t]:
                 self._value_choices_[t].insert(0, val)


    def validate(self, *args) -> bool:
        return True # for now...
