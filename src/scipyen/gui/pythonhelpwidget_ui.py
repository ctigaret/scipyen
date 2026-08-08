# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pythonhelpwidget.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QSizePolicy, QTextBrowser, QToolButton, QWidget)

class Ui_PythonHelpWidget(object):
    def setupUi(self, PythonHelpWidget):
        if not PythonHelpWidget.objectName():
            PythonHelpWidget.setObjectName(u"PythonHelpWidget")
        PythonHelpWidget.resize(378, 300)
        icon = QIcon(QIcon.fromTheme(u"help-browser"))
        PythonHelpWidget.setWindowIcon(icon)
        self.gridLayout = QGridLayout(PythonHelpWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.queryComboBox = QComboBox(PythonHelpWidget)
        self.queryComboBox.setObjectName(u"queryComboBox")
        self.queryComboBox.setEditable(True)
        self.queryComboBox.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)

        self.horizontalLayout.addWidget(self.queryComboBox)

        self.prevToolButton = QToolButton(PythonHelpWidget)
        self.prevToolButton.setObjectName(u"prevToolButton")
        self.prevToolButton.setEnabled(False)
        icon1 = QIcon(QIcon.fromTheme(u"go-previous"))
        self.prevToolButton.setIcon(icon1)
        self.prevToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.prevToolButton)

        self.nextToolButton = QToolButton(PythonHelpWidget)
        self.nextToolButton.setObjectName(u"nextToolButton")
        self.nextToolButton.setEnabled(False)
        icon2 = QIcon(QIcon.fromTheme(u"go-next"))
        self.nextToolButton.setIcon(icon2)
        self.nextToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.nextToolButton)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.helpDisplay = QTextBrowser(PythonHelpWidget)
        self.helpDisplay.setObjectName(u"helpDisplay")
        self.helpDisplay.setAcceptDrops(False)
        self.helpDisplay.setReadOnly(True)

        self.gridLayout.addWidget(self.helpDisplay, 1, 0, 1, 1)


        self.retranslateUi(PythonHelpWidget)

        QMetaObject.connectSlotsByName(PythonHelpWidget)
    # setupUi

    def retranslateUi(self, PythonHelpWidget):
        PythonHelpWidget.setWindowTitle(QCoreApplication.translate("PythonHelpWidget", u"Python help", None))
#if QT_CONFIG(tooltip)
        PythonHelpWidget.setToolTip(QCoreApplication.translate("PythonHelpWidget", u"Help viewer", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        PythonHelpWidget.setStatusTip(QCoreApplication.translate("PythonHelpWidget", u"Help viewer", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        PythonHelpWidget.setWhatsThis(QCoreApplication.translate("PythonHelpWidget", u"Help viewer", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.queryComboBox.setToolTip(QCoreApplication.translate("PythonHelpWidget", u"Help query", None))
#endif // QT_CONFIG(tooltip)
        self.queryComboBox.setPlaceholderText(QCoreApplication.translate("PythonHelpWidget", u"Type a query", None))
#if QT_CONFIG(tooltip)
        self.prevToolButton.setToolTip(QCoreApplication.translate("PythonHelpWidget", u"Previous page", None))
#endif // QT_CONFIG(tooltip)
        self.prevToolButton.setText(QCoreApplication.translate("PythonHelpWidget", u"Previous", None))
#if QT_CONFIG(tooltip)
        self.nextToolButton.setToolTip(QCoreApplication.translate("PythonHelpWidget", u"Forward page", None))
#endif // QT_CONFIG(tooltip)
        self.nextToolButton.setText(QCoreApplication.translate("PythonHelpWidget", u"Forward", None))
        self.helpDisplay.setPlaceholderText(QCoreApplication.translate("PythonHelpWidget", u"Enter a help topic in the field above (e.g., \"topics\", \"pywt.Wavelet\", etc)", None))
    # retranslateUi

