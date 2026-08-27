# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'curvefittingtool.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
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
    QLabel, QMainWindow, QMenuBar, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QWidget)

from gui.widgets.modelfittingwidget import ModelFittingWidget

class Ui_CurveFittingWindow(object):
    def setupUi(self, CurveFittingWindow):
        if not CurveFittingWindow.objectName():
            CurveFittingWindow.setObjectName(u"CurveFittingWindow")
        CurveFittingWindow.resize(800, 600)
        self.centralwidget = QWidget(CurveFittingWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.modelLabel = QLabel(self.centralwidget)
        self.modelLabel.setObjectName(u"modelLabel")

        self.horizontalLayout.addWidget(self.modelLabel)

        self.modelFunctionsComboBox = QComboBox(self.centralwidget)
        self.modelFunctionsComboBox.setObjectName(u"modelFunctionsComboBox")

        self.horizontalLayout.addWidget(self.modelFunctionsComboBox)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.openDataPushButton = QPushButton(self.centralwidget)
        self.openDataPushButton.setObjectName(u"openDataPushButton")
        self.openDataPushButton.setEnabled(False)
        icon = QIcon(QIcon.fromTheme(u"document-open"))
        self.openDataPushButton.setIcon(icon)

        self.horizontalLayout.addWidget(self.openDataPushButton)

        self.importDataPushButton = QPushButton(self.centralwidget)
        self.importDataPushButton.setObjectName(u"importDataPushButton")
        icon1 = QIcon(QIcon.fromTheme(u"document-import"))
        self.importDataPushButton.setIcon(icon1)

        self.horizontalLayout.addWidget(self.importDataPushButton)

        self.plotDataPushButton = QPushButton(self.centralwidget)
        self.plotDataPushButton.setObjectName(u"plotDataPushButton")
        icon2 = QIcon(QIcon.fromTheme(u"labplot-xy-curve-segments"))
        self.plotDataPushButton.setIcon(icon2)

        self.horizontalLayout.addWidget(self.plotDataPushButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.fittingWidget = ModelFittingWidget(self.centralwidget)
        self.fittingWidget.setObjectName(u"fittingWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fittingWidget.sizePolicy().hasHeightForWidth())
        self.fittingWidget.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.fittingWidget, 1, 0, 1, 1)

        CurveFittingWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(CurveFittingWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 26))
        CurveFittingWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(CurveFittingWindow)
        self.statusbar.setObjectName(u"statusbar")
        CurveFittingWindow.setStatusBar(self.statusbar)

        self.retranslateUi(CurveFittingWindow)

        QMetaObject.connectSlotsByName(CurveFittingWindow)
    # setupUi

    def retranslateUi(self, CurveFittingWindow):
        CurveFittingWindow.setWindowTitle(QCoreApplication.translate("CurveFittingWindow", u"MainWindow", None))
#if QT_CONFIG(tooltip)
        self.modelLabel.setToolTip(QCoreApplication.translate("CurveFittingWindow", u"Select model function", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.modelLabel.setStatusTip(QCoreApplication.translate("CurveFittingWindow", u"Select model function", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.modelLabel.setWhatsThis(QCoreApplication.translate("CurveFittingWindow", u"Select model function", None))
#endif // QT_CONFIG(whatsthis)
        self.modelLabel.setText(QCoreApplication.translate("CurveFittingWindow", u"Model Function:", None))
        self.label.setText(QCoreApplication.translate("CurveFittingWindow", u"Data vector:", None))
#if QT_CONFIG(tooltip)
        self.openDataPushButton.setToolTip(QCoreApplication.translate("CurveFittingWindow", u"Open curve data (numpy array, signal-like)", None))
#endif // QT_CONFIG(tooltip)
        self.openDataPushButton.setText(QCoreApplication.translate("CurveFittingWindow", u"Open curve data...", None))
#if QT_CONFIG(tooltip)
        self.importDataPushButton.setToolTip(QCoreApplication.translate("CurveFittingWindow", u"Import curve data from the workspace", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.importDataPushButton.setStatusTip(QCoreApplication.translate("CurveFittingWindow", u"Import curve data from the workspace", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.importDataPushButton.setWhatsThis(QCoreApplication.translate("CurveFittingWindow", u"Import curve data from the workspace", None))
#endif // QT_CONFIG(whatsthis)
        self.importDataPushButton.setText(QCoreApplication.translate("CurveFittingWindow", u"Import...", None))
#if QT_CONFIG(tooltip)
        self.plotDataPushButton.setToolTip(QCoreApplication.translate("CurveFittingWindow", u"Plot the curve to be fitted.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.plotDataPushButton.setStatusTip(QCoreApplication.translate("CurveFittingWindow", u"Plot the curve to be fitted.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.plotDataPushButton.setWhatsThis(QCoreApplication.translate("CurveFittingWindow", u"Plot the curve to be fitted.", None))
#endif // QT_CONFIG(whatsthis)
        self.plotDataPushButton.setText(QCoreApplication.translate("CurveFittingWindow", u"Plot", None))
    # retranslateUi

