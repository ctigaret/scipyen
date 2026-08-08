# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pplprotocolstepwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_PPLProtocolStepWidget(object):
    def setupUi(self, PPLProtocolStepWidget):
        if not PPLProtocolStepWidget.objectName():
            PPLProtocolStepWidget.setObjectName(u"PPLProtocolStepWidget")
        PPLProtocolStepWidget.resize(224, 22)
        self.gridLayout = QGridLayout(PPLProtocolStepWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(PPLProtocolStepWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)


        self.retranslateUi(PPLProtocolStepWidget)

        QMetaObject.connectSlotsByName(PPLProtocolStepWidget)
    # setupUi

    def retranslateUi(self, PPLProtocolStepWidget):
        PPLProtocolStepWidget.setWindowTitle(QCoreApplication.translate("PPLProtocolStepWidget", u"Form", None))
    # retranslateUi

