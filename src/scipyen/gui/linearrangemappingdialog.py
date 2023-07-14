from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__)

# Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))
Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__ui_path__, "linearrangemappingwidget.ui"))

# TODO
