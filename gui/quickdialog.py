"""quickdialog module adaptedfrom vigranumpy.pyqt.quickdialog
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
# Adaptation for use with PyQt5
# Copyright 209-2021 by Cezar M. Tigaret (cezar.tigaret@gmail.com, TigaretC@cardiff.ac.uk)
#########################################################################
import os, typing
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

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
    def __init__(self, parent, label, filter):
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
    def __init__(self, parent, label, filter):
        FileDialog.__init__(self, parent, label, filter)
        #self.connect(self.filebrowser, SIGNAL("clicked()"), self.browse)
        self.filebrowser.clicked.connect(self.browse)
        
    def browse(self):
        fn = QtWidgets.QFileDialog.getOpenFileName( "", self.filter, self)
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
    def __init__(self, parent, label, filter):
        FileDialog.__init__(self, parent, label, filter)
        #self.connect(self.filebrowser, SIGNAL("clicked()"), self.browse)
        self.filebrowser.clicked.connect(self.browse)
        
    def browse(self):
        fn = QtWidgets.QFileDialog.getSaveFileName( self, "Save File", "", self.filter)
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
    def __init__(self, parent, label):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QLineEdit()
        self.variable.setValidator(self._QValidator(self.variable))

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        
        self.setLayout(self._layout)
                    
    def setFocus(self):
        self.variable.setFocus()
        
    def setValue(self, text):
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

class OptionalFloatInput(_OptionalValueInput):
    _QValidator = QtGui.QDoubleValidator
    _text2Value = float
    _mustContain = "a float"

class FloatInput(OptionalFloatInput):
    def value(self):
        return float(self.text())

class OptionalStringInput(QtWidgets.QFrame):
    def __init__(self, parent, label):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QLineEdit()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        
        self.setLayout(self._layout)
                    
    def setFocus(self):
        self.variable.setFocus()
            
    def setText(self, text):
        self.variable.setText(text)
    
    def text(self):
        return str(self.variable.text())
    
    def unicode(self):
        return unicode(self.variable.text())

class StringInput(OptionalStringInput):
    def __init__(self, parent, label):
        OptionalStringInput.__init__(self, parent, label)
            
    def validate(self):
        if self.text() == "":
            QtWidgets.QMessageBox.critical(None, "Error","Field '%s' empty" % (self.label.text()))
            return False
        return True

OutputVariable = StringInput
InputVariable = StringInput
OptionalInputVariable = OptionalStringInput

class CheckBox(QtWidgets.QCheckBox):
    def __init__(self, parent, label):
        QtWidgets.QCheckBox.__init__(self, label, parent)
        parent.addWidget(self)

    def selection(self):
        return self.isChecked()

class Choice(QtWidgets.QFrame):
    def __init__(self, parent, label, vertical = 0):
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
    
    def addButton(self, label, result):
        self.buttons.append(QtWidgets.QRadioButton(label))
        self.buttonBox.layout.addWidget(self.buttons[-1])
        self.results.append(result)
        self.buttons[0].setChecked(True)
        
    def addSpacing(self, spacing):
        self.buttonBox.addSpace(spacing)
        
    def selectButton(self, index):
        if index >= 0 and index < len(self.buttons):
            self.buttons[index].setChecked(True)
        
    def selection(self):
        for k in range(len(self.buttons)):
            if self.buttons[k].isChecked():
                return self.results[k]
        return None # should never happen

class HChoice(Choice):
    def __init__(self, parent, label):
        Choice.__init__(self, parent, label, 0)
        
class VChoice(Choice):
    def __init__(self, parent, label):
        Choice.__init__(self, parent, label, 1)
        
class DialogGroup(QtWidgets.QFrame):
    def __init__(self, parent, vertical = 0):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        if vertical:
            self.layout = QtWidgets.QVBoxLayout(self)
            self.defaultAlignment = QtCore.Qt.AlignLeft
        else:
            self.layout = QtWidgets.QHBoxLayout(self)
            self.defaultAlignment = QtCore.Qt.AlignTop
        self.widgets = []
               
    def addWidget(self, widget, stretch = 0, alignment = None):
        if alignment is None:
            alignment = self.defaultAlignment
        self.layout.addWidget(widget, stretch, alignment)
        self.widgets.append(widget)
        
    def addSpacing(self, spacing):
        self.layout.addSpacing(spacing)

    def addStretch(self, stretch):
        self.layout.addStretch(stretch)
        
    def addLabel(self, labelString):
        label = QtWidgets.QLabel(labelString, self)
        self.addWidget(label, 0, QtCore.Qt.AlignLeft)
        
    def validate(self):
        for i in self.widgets:
            try:
                if i.validate() == 0:
                    return False
            except AttributeError:
                continue
        return True

class HDialogGroup(DialogGroup):
    def __init__(self, parent):
        DialogGroup.__init__(self, parent, 0)
        
class VDialogGroup(DialogGroup):
    def __init__(self, parent):
        DialogGroup.__init__(self, parent, 1)
       
class QuickDialogComboBox(QtWidgets.QFrame):
    """A combobox to use with a QuickDialog.
    
    The combobox is nothing fancy -- only accepts a list of text items
    """
    def __init__(self, parent, label):
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
        
    def setItems(self, textList):
        if not isinstance(textList, (tuple, list)):
            raise TypeError("Expecting a sequence; got %s instead" % type(textList).__name__ )
        
        if not all([isinstance(v, str) for v in textList]):
            raise TypeError("Expecting a sequence of strings")
        
        self.variable.clear()
        
        for text in textList:
            self.variable.addItem(text)
            
    def setValue(self, index):
        if isinstance(index, int) and index >= -1 and index < self.variable.model().rowCount():
            self.variable.setCurrentIndex(index)
            
    def setText(self, text):
        if isinstance(text, str):
            self.variable.setCurrentText(text)
            
    def value(self):
        return self.variable.currentIndex()
    
    def text(self):
        return self.variable.currentText()
    
    def connectTextChanged(self, slot):
        self.currentTextChanged[str].connect(slot)
        
    def connectIndexChanged(self, slot):
        """Connects the combobox currentIndexChanged signal.
        NOTE: this is an overlaoded signal, with to versions 
        (respectively, with a str and int argument).
        
        Therefore it is expected that the connected slot is also overloaded
        to accept a str or an int
        """
        self.variable.currentIndexChanged[str].connect(slot)
        
    def disconnect(self):
        self.variable.currentIndexChanged[str].disconnect()
        
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
    """
    Cezar M. Tigaret
    """
    class VarNameValidator(QtGui.QValidator):
        def __init__(self, parent=None):
            super().__init__(parent)
            
        def validate(self, s, pos):
            if not s.isidentifier() or keyword.iskeyword(s):
                ret = QtGui.QValidator.Invalid
                #if s[0:pos].isidentifier() and not keyword.iskeyword(s[0:pos]):
                    #ret = QtGui.QValidator.Intermediate
                #else:
                    #ret = QtGui.QValidator.Invalid
            else:
                ret = QtGui.QValidator.Acceptable
                
            #print("validate returns: ", ret)
            return ret
        
        
        def fixup(self, s):
            return validate_varname(s)
            
            
    def __init__(self, parent, label, ws):
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
    
class QuickDialog(QtWidgets.QDialog):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, title:typing.Optional[str]=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addStretch(5)
        self.layout.addSpacing(20)
        
        self.insertButtons()
        
        self.widgets = []
        if not isinstance(title, str) or len(title.strip()) == 0:
            title = "QuickDialog"
        self.setWindowTitle(title)
        #self.setOrientation(QtCore.Qt.Vertical)
        self.resize(500,-1)
        
    def insertButtons(self):
        self.buttons = QtWidgets.QFrame(self)
        self.buttons.OK = QtWidgets.QPushButton("OK", self.buttons)
        self.buttons.Cancel = QtWidgets.QPushButton("Cancel", self.buttons)
        self.buttons.OK.setDefault(1)
        self.buttons.Cancel.clicked.connect(self.reject)
        self.buttons.OK.clicked.connect(self.tryAccept)
        #self.connect(self.buttons.Cancel, SIGNAL("clicked()"), self.reject)
        #self.connect(self.buttons.OK, SIGNAL("clicked()"), self.tryAccept)
        
        self.buttons.layout = QtWidgets.QHBoxLayout(self.buttons)
        self.buttons.layout.addStretch(5)
        self.buttons.layout.addWidget(self.buttons.OK)
        self.buttons.layout.addWidget(self.buttons.Cancel)
        self.layout.addWidget(self.buttons)
        
    def addWidget(self, widget, stretch = 0, alignment = None):
        if alignment is None:
            alignment = QtCore.Qt.AlignTop
        self.layout.insertWidget(len(self.widgets), widget, stretch, alignment)
        self.widgets.append(widget)
        
    def addSpacing(self, spacing):
        self.layout.insertSpacing(len(self.widgets), spacing)
        self.widgets.append(None)

    def addStretch(self, stretch):
        self.layout.insertStretch(len(self.widgets), stretch)
        self.widgets.append(None)

    def addLabel(self, labelString):
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
