from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot, QEnum, Property
from qtpy.uic import loadUiType as __loadUiType__
# from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
# from PyQt5.uic import loadUiType as __loadUiType__
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "linearrangemappingwidget.ui")

# Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))
Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(__ui_path__)

# TODO
