# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""quickdialog module adapted from vigranumpy.pyqt.quickdialog
Useful to have even when vigranumpy is not installed.

"""
#######################################################################
#                                                                      
#         Copyright 2009-2010 by Ullrich Koethe                        
#                                                                      
#    This file is part of the VIGRA computer vision library.           
#    The VIGRA Website is                                              
#        http://hci.iwr.uni-heidelberg.de/vigra/                       
#    Please direct questions, bug reports, and contributions to        
#        ullrich.koethe@iwr.uni-heidelberg.de    or                    
#        vigra@informatik.uni-hamburg.de                               
#                                                                      
#    Permission is hereby granted, free of charge, to any person       
#    obtaining a copy of this software and associated documentation    
#    files (the "Software"), to deal in the Software without           
#    restriction, including without limitation the rights to use,      
#    copy, modify, merge, publish, distribute, sublicense, and/or      
#    sell copies of the Software, and to permit persons to whom the    
#    Software is furnished to do so, subject to the following          
#    conditions:                                                       
#                                                                      
#    The above copyright notice and this permission notice shall be    
#    included in all copies or substantial portions of the             
#    Software.                                                         
#                                                                      
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND    
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES   
#    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND          
#    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT       
#    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,      
#    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING      
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR     
#    OTHER DEALINGS IN THE SOFTWARE.                                   
#                                                                      
#######################################################################
# NOTE: 2019-10-06 00:43:44
# Adaptation for use with PyQt5/6
# Copyright 209-2021 by Cezar M. Tigaret (cezar.tigaret@gmail.com, TigaretC@cardiff.ac.uk)
#########################################################################
import os, typing, inspect, math, types, functools, traceback
import numpy as np
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
    

from gui.guiutils import(InftyDoubleValidator, ComplexValidator, UnitsStringValidator)
from core.prog import scipywarn
import quantities as pq

def alignLabels(*args):
    m = 0
    for dialogElement in args:
        fontMetrics = QtGui.QFontMetrics(dialogElement.font())
        for line in dialogElement.label.text().ascii().split('\n'):
            labelWidth = fontMetrics.width(line)
            m = max(m, labelWidth)
    for dialogElement in args:
        dialogElement.label.setFixedWidth(m+10)

class FileDialog(QtWidgets.QFrame):
    r"""A file dialog. 
NOTE: It is better to use Qt file dialogs directly
"""
    def __init__(self, parent:QtWidgets.QWidget, label:str, filter:str):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        self.filter = filter
        self.label = QtWidgets.QLabel(label)
        self.filename = QtWidgets.QLineEdit()
        self.filebrowser = QtWidgets.QPushButton("Browse...")
        self.filebrowser.setFocusPolicy(QtCore.Qt.NoFocus)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.filename, 1)
        self._layout.addWidget(self.filebrowser)
        
        self.setLayout(self._layout)
            
    def text(self):
        return str(QtCore.QFile.encodeName(self.filename.text()))
        
    def setFocus(self):
        self.filename.setFocus()

class InputFile(FileDialog):
    def __init__(self, parent:QtWidgets.QWidget, label:str, filter:str):
        FileDialog.__init__(self, parent, label, filter)
        #self.connect(self.filebrowser, SIGNAL("clicked()"), self.browse)
        self.filebrowser.clicked.connect(self.browse)
        
    def browse(self):

        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}


        fn = QtWidgets.QFileDialog.getOpenFileName( "", self.filter, self, **kw)
        if not fn.isNull():
            self.filename.setText(fn)
        
    def validate(self):
        try:
            filename = str(QtCore.QFile.encodeName(self.filename.text()))
            file = open(filename)
            file.close()
            return True
        except IOError:
            QtWidgets.QMessageBox.critical(None, "Error", "File '" + filename + "' not found")
            return False

class OutputFile(FileDialog):
    def __init__(self, parent:QtWidgets.QWidget, label:str, filter:str):
        FileDialog.__init__(self, parent, label, filter)
        #self.connect(self.filebrowser, SIGNAL("clicked()"), self.browse)
        self.filebrowser.clicked.connect(self.browse)
        
    def browse(self):
        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        fn = QtWidgets.QFileDialog.getSaveFileName( self, "Save File", "", self.filter, **kw)
        if not fn.isNull():
            self.filename.setText(fn)
        
    def validate(self):
        try:
            filename = str(QtCore.QFile.encodeName(self.filename.text()))
            file = open(filename)
            file.close()
            return not QtWidgets.QMessageBox.warning(
                None, "Warning", "File '" + filename + "' exists",
                "Overwrite", "Cancel")
        except IOError:
            return True

class _OptionalValueInput(QtWidgets.QFrame):
    r"""Widget for entering a value (number or string).
WARNING: Data is internally represented as a string.
"""
    valueChanged = Signal(str, name="valueChanged")
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QLineEdit()
        self.variable.setValidator(self._QValidator(parent=self.variable))
        self.variable.textChanged[str].connect(self._slot_valueChanged)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        
        self.setLayout(self._layout)
    
    @Slot(str)
    def _slot_valueChanged(self, val:str):
        self.valueChanged.emit(val)
    
    def setFocus(self):
        self.variable.setFocus()
        
    def setValue(self, text:str):
        self.variable.setText(str(self._text2Value(text)))
    
    def value(self):
        text = self.text()
        if text == "":
            return None
        return self._text2Value(text)

    def text(self):
        return str(self.variable.text())
        
    def validate(self):
        try:
            v = self.value()
            if v == None:
                return True
        except:
            QtWidgets.QMessageBox.critical(None, "Error","Field '%s' must contain " % self.label.text() +self._mustContain)
                #QtCore.QString("Field '%1' must contain "+self._mustContain).arg(
                    #self.label.text()))
            return False
        try:
            if v < self.min:
                QtWidgets.QMessageBox.critical(None, "Error", "Field '%s' value must be >= %s" % (self.label.text()+str(self.min)))
                    #QtCore.QString("Field '%1' value must be >= "+str(self.min)).arg(
                        #self.label.text()))
                return False
        except AttributeError:
            pass
        try:
            if v > self.max:
                QtWidgets.QMessageBox.critical(None, "Error", "Field '%%' value must be <= %s" % (self.label.text(), str(self.max)))
                    #QtCore.QString("Field '%1' value must be <= "+str(self.max)).arg(
                        #self.label.text()))
                return False
        except AttributeError:
            pass
        return True
            
class OptionalIntegerInput(_OptionalValueInput):
    _QValidator = QtGui.QIntValidator
    _text2Value = int
    _mustContain = "an integer"

class IntegerInput(OptionalIntegerInput):
    def value(self):
        return int(self.text())
    
    
class ComplexInput(_OptionalValueInput):
    _QValidator = ComplexValidator
    _text2Value = complex
    _mustContain = "a complex value"
    
    def setValue(self, x:typing.Union[complex, str]):
        if isinstance(x, complex):
            super().setValue(str(x))
        else:
            super().setValue(x)
        
    def value(self):
        return complex(self.text())

class OptionalFloatInput(_OptionalValueInput):
    # _QValidator = QtGui.QDoubleValidator
    _QValidator = InftyDoubleValidator
    _text2Value = float
    _mustContain = "a float"

class FloatInput(OptionalFloatInput):
    def setValue(self, x:typing.Union[float, str]):
        if isinstance(x, float):
            super().setValue(str(x))
        else:
            super().setValue(x)
        
    def value(self):
        return float(self.text())

class OptionalStringInput(QtWidgets.QFrame):
    r"""Widget for plain text input"""
    valueChanged = Signal(str, name="valueChanged")
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QLineEdit()
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        self.variable.textChanged[str].connect(self._slot_textChanged)
        self.setLayout(self._layout)
    
    @Slot(str)
    def _slot_textChanged(self, val:str):
        self.valueChanged.emit(val)

    def setToolTip(self, tip:str):
        self.variable.setToolTip(tip)
        self.label.setToolTip(tip)
    
    def setFocus(self):
        self.variable.setFocus()
        
    def setValue(self, text:str):
        self.variable.setText(text)

    def value(self) -> str:
        return self.text()

    def setText(self, text:str):
        self.variable.setText(text)

    def text(self):
        return str(self.variable.text())

    def unicode(self):
        return unicode(self.variable.text())

class StringInput(OptionalStringInput):
    def __init__(self, parent:QtWidgets.QWidget, label:str,
                 allowEmptyString:bool = False):
        OptionalStringInput.__init__(self, parent, label)
        self._allowEmptyString_ = allowEmptyString is True
            
    def validate(self):
        if len(self.text().strip()) == 0 and not self._allowEmptyString_:
            QtWidgets.QMessageBox.critical(None, "Error","Field '%s' empty" % (self.label.text()))
            return False
        return True

    @property
    def allowEmptyString(self) -> bool:
        return self._allowEmptyString_

    @allowEmptyString.setter
    def allowEmptyString(self, val: bool):
        self._allowEmptyString_ = val is True
    
OutputVariable = StringInput
InputVariable = StringInput
OptionalInputVariable = OptionalStringInput

class CheckBox(QtWidgets.QCheckBox):
    r"""(Tri-)Boolean value input.
Inherits directly from QCheckBox. Supports tri-state: use the inherited 
checkState() method returning a QtCore.Qt.CheckState value
"""
    def __init__(self, parent:QtWidgets.QWidget, label:str, tristate:bool=False):
        QtWidgets.QCheckBox.__init__(self, label, parent)
        self.setTristate(tristate)
        parent.addWidget(self)

    def selection(self):
        return self.isChecked()
    
    def value(self) -> QtCore.Qt.CheckState:
        return self.checkState()
    
    def validate(self, *args):
        return True
    
class ComplexSpinBox(QtWidgets.QFrame):
    r"""Compound widget for editing complex numbers"""
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        pass
    
class SpinBox(QtWidgets.QFrame):
    r"""Alternative to IntegerInput and FloatInput, with support for python Quantities.

"""
    def __init__(self, parent:QtWidgets.QWidget, label:str, vertical:int|bool = 0,
                 widget_type:str="i", **kwargs):
        from gui.widgets.small_widgets import (QuantitySpinBox, ComplexSpinBox)
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        if widget_type not in ("i", "d", "f", "q", "c"):
            widget_type = "i"
        self._type_ = widget_type
        self.label = QtWidgets.QLabel(text=label, parent=self)
        # self.spinBox = QtWidgets.QSpinBox(parent=self) if self._type_ == "i" else QtWidgets.QDoubleSpinBox(parent=self) if self._type_ in ("d", "f") else QuantitySpinBox(parent=self)
        self.spinBox = QtWidgets.QSpinBox(parent=self) if self._type_ == "i" else ComplexSpinBox(parent=self) if self._type_ == "c" else QtWidgets.QDoubleSpinBox(parent=self) if self._type_ in ("d", "f") else QuantitySpinBox(parent=self, **kwargs)
        if vertical:
            self.layout = QtWidgets.QVBoxLayout(self)
        else:
            self.layout = QtWidgets.QHBoxLayout(self)
            
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.spinBox)
        self.layout.addStretch(5)
        
    def setValue(self, value:int|float|pq.Quantity):
        if isinstance(value, pq.Quantity) and value.size != 1:
            raise TypeError("Cannot set value to a non-scalar quantity")
        if self._type_ == "i":
            self.spinBox.setValue(round(value))
        # elif self._type_ == "q" and isinstance(value, pq.Quantity):
        #     self.spinBox.setValue(value)
        else:
            self.spinBox.setValue(value)
        
    def value(self) -> int|float|pq.Quantity:
        return self.spinBox.value()
    
    def minimum(self) -> int|float|pq.Quantity:
        return self.spinBox.minimum()
    
    def setMinimum(self, value:int|float|pq.Quantity):
        if isinstance(value, pq.Quantity) and value.size != 1:
            raise TypeError("Cannot set value to a non-scalar quantity")
        if self._type_ == "i":
            self.spinBox.setMinimum(round(value))
        else:
            self.spinBox.setMinimum(value)
        
    def maximum(self) -> int|float|pq.Quantity:
        return self.spinBox.maximum()
    
    def setMaximum(self, value:int|float|pq.Quantity):
        if isinstance(value, pq.Quantity) and value.size != 1:
            raise TypeError("Cannot set value to a non-scalar quantity")
        if self._type_ == "i":
            self.spinBox.setMaximum(round(value))
        else:
            self.spinBox.setMaximum(value)
        
    def singleStep(self) -> int|float|pq.Quantity:
        return self.spinBox.singleStep()
    
    def setSingleStep(self, val:int|float|pq.Quantity):
        if isinstance(value, pq.Quantity) and value.size != 1:
            raise TypeError("Cannot set value to a non-scalar quantity")
        if self._type_ == "i":
            self.spinBox.setSingleStep(round(val))
        else:
            self.spinBox.setSingleStep(val)
        
    def decimals(self) -> int:
        if self._type_ == "i":
            return 0
        return self.spinBox.decimals()
    
    def setDecimals(self, val:int):
        if self._type_ != "i":
            if val < 0: 
                val = 0
            self.spinBox.setDecimals(val)
            
    def stepType(self) -> QtWidgets.QAbstractSpinBox.StepType:
        return self.spinBox.stepType()
    
    def setStepType(self, val: QtWidgets.QAbstractSpinBox.StepType):
        self.spinBox.setStepType(val)
        
    def prefix(self) -> str:
        return self.spinBox.prefix()
    
    def setPrefix(self, val:str):
        if self._type_ == "q":
            return
        self.spinBox.setPrefix(val)
        
    def suffix(self) -> str:
        return self.spinBox.suffix()
    
    def setSuffix(self, val:str):
        if self._type_ == "q":
            return
        self.spinBox.setSuffix(val)
        
    def displayIntegerBase(self) -> int:
        return self.spinBox.displayIntegerBase()
        
    def setDisplayIntegerBase(self, val:int):
        self.spinBox.setDisplayIntegerBase(val)
        
    def setRange(self, minimum:int|float, maximum:int|float):
        if self._type_ == "i":
            self.spinBox.setRange(round(minimum), round(maximum))
        else:
            self.spinBox.setRange(float(minimum), float(maximum))
            
    def specialValueText(self) -> str:
        return self.spinBox.specialValueText()
    
    def setSpecialValueText(self, val:str):
        self.spinBox.setSpecialValueText(val)
        
class VSpinBox(SpinBox):
    def __init__(self, parent:QtWidgets.QWidget, label:str, widget_type:str = "i", **kwargs):
        SpinBox.__init__(self, parent, label, 1, widget_type, **kwargs)
        
class HSpinBox(SpinBox):
    def __init__(self, parent:QtWidgets.QWidget, label:str, widget_type:str = "i", **kwargs):
        SpinBox.__init__(self, parent, label, 0, widget_type, **kwargs)

class Choice(QtWidgets.QFrame):
    r"""Radio buttons"""
    def __init__(self, parent:QtWidgets.QWidget, label:str, vertical:int|bool = 0):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        
        self.buttonBox = QtWidgets.QGroupBox(label, self)
        if vertical:
            self.buttonBox.layout = QtWidgets.QVBoxLayout(self.buttonBox)
        else:
            self.buttonBox.layout = QtWidgets.QHBoxLayout(self.buttonBox)
        
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.buttonBox)
        self.layout.addStretch(5)
        
        self.buttons = []
        self.results = []
    
    def addButton(self, label:str, result:typing.Any):
        self.buttons.append(QtWidgets.QRadioButton(label))
        self.buttonBox.layout.addWidget(self.buttons[-1])
        self.results.append(result)
        self.buttons[0].setChecked(True)
        
    def addSpacing(self, spacing:int):
        self.buttonBox.addSpace(spacing)
        
    def selectButton(self, index:int):
        if index >= 0 and index < len(self.buttons):
            self.buttons[index].setChecked(True)
        
    def selection(self):
        for k in range(len(self.buttons)):
            if self.buttons[k].isChecked():
                return self.results[k]
        return None # should never happen
    
class HChoice(Choice):
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        Choice.__init__(self, parent, label, 0)
        
class VChoice(Choice):
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        Choice.__init__(self, parent, label, 1)
        
class DialogGroup(QtWidgets.QFrame):
    def __init__(self, parent:QtWidgets.QWidget, vertical:bool|int = 0, validate:bool=True):
        QtWidgets.QFrame.__init__(self, parent)
        self.bypassValidation = not validate
        parent.addWidget(self)
        if vertical:
            self.layout = QtWidgets.QVBoxLayout(self)
            self.defaultAlignment = QtCore.Qt.AlignLeft
        else:
            self.layout = QtWidgets.QHBoxLayout(self)
            self.defaultAlignment = QtCore.Qt.AlignTop
        self.widgets = []
               
    def addWidget(self, widget:QtWidgets.QWidget, stretch:int = 0, alignment:typing.Optional[QtCore.Qt.AlignmentFlag] = None):
        if alignment is None:
            alignment = self.defaultAlignment
        self.layout.addWidget(widget, stretch, alignment)
        self.widgets.append(widget)
        
    def addSpacing(self, spacing:int):
        self.layout.addSpacing(spacing)

    def addStretch(self, stretch:int):
        self.layout.addStretch(stretch)
        
    def addLabel(self, labelString:str):
        label = QtWidgets.QLabel(labelString, self)
        self.addWidget(label, 0, QtCore.Qt.AlignLeft)
        
    def validate(self):
        if self.bypassValidation:
            # allow the use of stock Qt widgets which have their own validator
            # (abd their validate() method takes extra mandatory arguments)
            return True
        
        for i in self.widgets:
            try:
                if i.validate() == 0:
                    return False
            except AttributeError:
                continue
            
        return True

class HDialogGroup(DialogGroup):
    def __init__(self, parent:QtWidgets.QWidget, validate:bool=True):
        DialogGroup.__init__(self, parent, vertical=False, validate=validate)
        
class VDialogGroup(DialogGroup):
    def __init__(self, parent:QtWidgets.QWidget, validate:bool=True):
        DialogGroup.__init__(self, parent, vertical=True, validate=validate)
        
class QuickDialogComboBox(QtWidgets.QFrame):
    r"""A combobox to use with a QuickDialog.
    
    The combobox is nothing fancy: it only accepts a list of text items
    """
    def __init__(self, parent:QtWidgets.QWidget, label:str):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QComboBox()
        
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        
        self.setLayout(self._layout)
        
    def setFocus(self):
        self.variable.setFocus()
        
    def setItems(self, textList:typing.Sequence[str]):
        r"""Set the entry list; if empty, all existing entries will be removed"""
        if not isinstance(textList, (tuple, list)):
            raise TypeError("Expecting a sequence; got %s instead" % type(textList).__name__ )
        
        if not all([isinstance(v, str) for v in textList]):
            raise TypeError("Expecting a sequence of strings")
        
        self.variable.clear()
        
        for text in textList:
            self.variable.addItem(text)
            
    def setCurrentIndex(self, value:int):
        self.setValue(value)
            
    def setValue(self, index:int):
        if isinstance(index, int) and index >= -1 and index < self.variable.model().rowCount():
            self.variable.setCurrentIndex(index)
            
    def setText(self, text:str):
        if isinstance(text, str):
            self.variable.setCurrentText(text)
            
    def value(self):
        return self.variable.currentIndex()
    
    def text(self):
        return self.variable.currentText()
    
    def connectTextChanged(self, slot:object):
        self.variable.currentTextChanged[str].connect(slot)
        
    def connectIndexChanged(self, slot:object):
        r"""Connects the combobox currentIndexChanged signal.
        """
        # NOTE: this is an overlaoded signal, with two versions 
        # (respectively, with a str and int argument).
        # Therefore it is expected that the connected slot is also overloaded
        # to accept a str or an int
        # NOTE:2026-01-26 22:39:23
        # as of Qt6.10 there seems to be NO MORE overloading; only int arguments are used

        self.variable.currentIndexChanged[int].connect(slot)
        
    def disconnect(self):
        self.variable.currentIndexChanged[int].disconnect()
        self.variable.currentTextChanged[str].disconnect()
        
#class DialogStack(qt.QWidgetStack):
#    def __init__(self, parent, widgetMapping = None):
#        qt.QWidgetStack.__init__(self, parent)
#        parent.addWidget(self)
#        self.widgetMapping = widgetMapping
#        self.size = 0
#            
#    def raiseWidget(self, index):
#        if self.widgetMapping:
#            qt.QWidgetStack.raiseWidget(self, self.widgetMapping[index])
#        else:
#            qt.QWidgetStack.raiseWidget(self, index)
#
#    def addWidget(self, widget):
#        qt.QWidgetStack.addWidget(self, widget, self.size)
#        self.size = self.size + 1
#        
#    def validate(self):
#        try:
#            return self.visibleWidget().validate()
#        except AttributeError:
#            pass

# TODO FIXME: when using my custom QValidator python (or pyqt5) crashes with
# TypeError: invalid result from VarNameValidator.validate()
class VariableNameStringInput(StringInput):
    r"""
    Cezar M. Tigaret
    """
    class VarNameValidator(QtGui.QValidator):
        def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
            super().__init__(parent)
            
        def validate(self, s:str, pos:int):
            if not s.isidentifier() or keyword.iskeyword(s):
                ret = (QtGui.QValidator.Invalid, s, pos)
                #if s[0:pos].isidentifier() and not keyword.iskeyword(s[0:pos]):
                    #ret = QtGui.QValidator.Intermediate
                #else:
                    #ret = QtGui.QValidator.Invalid
            else:
                ret = (QtGui.QValidator.Acceptable, s, pos)
                
            #print("validate returns: ", ret)
            return ret 
        
        
        def fixup(self, s:str):
            return validate_varname(s)
            
            
    def __init__(self, parent:QtWidgets.QWidget, label:str, ws:object):
        super().__init__(parent, label)
        self.variable.setClearButtonEnabled(True)
        self.variable.undoAvailable = True
        self.variable.redoAvailable = True
        #self.variable.setValidator(VariableNameStringInput.VarNameValidator(self))
        
    def validate(self):
        if self.text() == "":
            QtWidgets.QMessageBox.critical(None, "Error","Field '%s' empty" % (self.label.text()))
            return False
        else:
            self.variable.setText(validate_varname(self.text()))
        return True
    
class QuickWidget(QtWidgets.QWidget):
    r"""Quick creation of a custom widget
    TODO: 2022-10-28 11:27:24 Finalize me
    """
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, layoutType:type=QtWidgets.QVBoxLayout):
        QtWidgets.QWidget.__init__(self, parent)
        if QtWidgets.QLayout in inspect.getmro(layoutType):
            self.layout = layoutType(self)
        else:
            self.layout = QtWidgets.QVBoxLayout(self)
            
        if isinstance(self.layout, QtWidgets.QGridLayout):
            self.layout.setColumnStretch(5)
            self.layout.setRowStretch(5)
            self.layout.setVerticalSpacing(20)
            self.layout.setHorizontalSpacing(20)
        else:
            self.layout.addStretch(5)
            self.layout.addSpacing(20)
            
        self.widgets = list()
        self.resize(500, -1)
        
    def addWidget(self, widget, stretch = 0, alignment = None):
        if alignment is None:
            alignment = QtCore.Qt.AlignTop
        self.layout.insertWidget(len(self.widgets), widget, stretch, alignment)
        self.widgets.append(widget)
        
            
    def addSpacing(self, spacing):
        self.layout.insertWidget(len(self.widgets), spacing)
        self.widgets.append(None)
        
    def addStretch(self, stretch):
        self.layout.insertStretch(len(self.widgets), stretch)
        self.widgets.append(None)

    def addLabel(self, labelString):
        label = QtWidgets.QLabel(labelString, self)
        self.addWidget(label, 0, QtCore.Qt.AlignLeft)
    
class QuickDialog(QtWidgets.QDialog):
    r"""From vigranumpy.pyqt.quickdialog"""
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, 
                 title:typing.Optional[str]=None, 
                 addStretch=True, 
                 addSpacing=True):
        QtWidgets.QDialog.__init__(self, parent)
        
        self._cb_ = list()

        self.layout = QtWidgets.QVBoxLayout(self)
        if isinstance(addStretch, bool):
            if addStretch:
                self.layout.addStretch(5)
                
        elif isinstance(addStretch, int):
            self.layout.addStretch(addStretch)
                
        if isinstance(addSpacing, bool):
            if addSpacing:
                self.layout.addSpacing(20)
                
        elif isinstance(addSpacing, int):
            self.layout.addSpacing(addSpacing)
        
        self.insertButtons()
        
        self.widgets = []
        if not isinstance(title, str) or len(title.strip()) == 0:
            title = "QuickDialog"
            
        self.setWindowTitle(title)
        #self.setOrientation(QtCore.Qt.Vertical)
        self.resize(500,-1)
        
    @property
    def callbacks(self) -> list:
        return self._cb_
    
    def addCallback(self, f:typing.Union[types.FunctionType, types.MethodType, functools.partial]) -> None:
        if not isinstance(f, (types.FunctionType, types.MethodType, functools.partial)):
            raise TypeError(f"Expecting a types.FunctionType, types.MethodType, or a functools.partial; got {type(f).__name__} instead")
        
        self._cb_.append(f)
        
    def removeCallback(self, f:typing.Union[types.FunctionType, types.MethodType, functools.partial]) -> None:
        if not isinstance(f, (types.FunctionType, types.MethodType, functools.partial)):
            raise TypeError(f"Expecting a types.FunctionType, types.MethodType, or a functools.partial; got {type(f).__name__} instead")
        
        if f in self._cb_:
            index = self._cb_.index(f)
            del(self._cb_[index])
            
    def clearCallbacks(self):
        self._cb_.clear()
        
    @Slot(str)
    def _slot_valueChanged(self, val:str):
        if len(self._cb_):
            for f in self._cb_:
                try:
                    f(val)
                except:
                    scipywarn(f"In {self.__class__.__name__}._slot_valueChanged: Bad callback call for {f}")
                    traceback.print_exc()
            
        
    def insertButtons(self):
        self.buttons = QtWidgets.QFrame(self)
        self.buttons.OK = QtWidgets.QPushButton("OK", self.buttons)
        self.buttons.Cancel = QtWidgets.QPushButton("Cancel", self.buttons)
        self.buttons.OK.setDefault(1)
        self.buttons.Cancel.clicked.connect(self.reject)
        self.buttons.OK.clicked.connect(self.tryAccept)
        
        self.buttons.layout = QtWidgets.QHBoxLayout(self.buttons)
        self.buttons.layout.addStretch(5)
        self.buttons.layout.addWidget(self.buttons.OK)
        self.buttons.layout.addWidget(self.buttons.Cancel)
        self.layout.addWidget(self.buttons)
        
    def addWidget(self, widget:QtWidgets.QWidget, stretch:int = 0, alignment:typing.Optional[QtCore.Qt.AlignmentFlag] = None):
        if alignment is None:
            alignment = QtCore.Qt.AlignTop
        self.layout.insertWidget(len(self.widgets), widget, stretch, alignment)
        self.widgets.append(widget)
        
    def addSpacing(self, spacing:int):
        self.layout.insertSpacing(len(self.widgets), spacing)
        self.widgets.append(None)

    def addStretch(self, stretch:int):
        self.layout.insertStretch(len(self.widgets), stretch)
        self.widgets.append(None)

    def addLabel(self, labelString:str):
        label = QtWidgets.QLabel(labelString, self)
        self.addWidget(label, 0, QtCore.Qt.AlignLeft)
        
    def setHelp(self, *functionSeq):
        helpString = ""
        functionList = list(*functionSeq)
        while len(functionList) > 0:
            function = functionList.pop()
            if (len(functionList) == 0) and (function.__doc__):
                helpString = helpString + function.__doc__
            elif function.__doc__:
                helpString = helpString + function.__doc__ + os.linesep + \
                    "--------------------------------------------------------"+\
                    "--------------------------------" + os.linesep
        
        if not hasattr(self.buttons, "Help"):
            self.buttons.Help = QtWidgets.QPushButton("Help", self.buttons)
            self.buttons.Help.setToggleButton(1)
            self.buttons.layout.insertWidget(3, self.buttons.Help)
            self.connect(self.buttons.Help, SIGNAL("toggled(bool)"), self.showExtension)
        
        if int(QtCore.qVersion()[0]) < 3:
            self.help = QtWidgets.QTextEdit(self)
            self.help.setText(helpString)
            if self.help.numLines() > 20:
                self.help.setFixedVisibleLines(20)
            else:
                self.help.setFixedVisibleLines(self.help.numLines()+1)

            self.help.setReadOnly(1)
            self.help.setWordWrap(QtWidgets.QTextEdit.WidgetWidth)
        else:
            #self.help = qt.QVBox(self)
            self.help = QtWidgets.QVGroupBox(self)
            self.help.setLayout(QtWidgets.QVBoxLayout())
            #self.help.text = QtCore.QtextEdit(self.help)
            self.help.text = QtWidgets.QTextEdit(self.help)
            self.help.text.setText(helpString)
            self.help.text.setReadOnly(1)
            self.help.text.setWordWrap(QtWidgets.QTextEdit.WidgetWidth)
            total_height = self.help.text.heightForWidth(self.help.width())
            if  total_height > self.help.text.height():
                self.help.text.setMinimumSize(self.help.text.width(), min(300, total_height))
                
        self.setExtension(self.help)
        
    def tryAccept(self):
        for i in self.widgets:
            try:
                if not isinstance(i, QtWidgets.QAbstractSpinBox) and i.validate() == 0:
                    return
            except AttributeError:
                continue
        self.accept()
