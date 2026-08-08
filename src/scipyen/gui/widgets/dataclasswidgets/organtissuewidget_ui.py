# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'organtissuewidget.ui'
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

class Ui_OrganTissueWidget(object):
    def setupUi(self, OrganTissueWidget):
        if not OrganTissueWidget.objectName():
            OrganTissueWidget.setObjectName(u"OrganTissueWidget")
        OrganTissueWidget.resize(225, 22)
        self.gridLayout = QGridLayout(OrganTissueWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(OrganTissueWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)


        self.retranslateUi(OrganTissueWidget)

        QMetaObject.connectSlotsByName(OrganTissueWidget)
    # setupUi

    def retranslateUi(self, OrganTissueWidget):
        OrganTissueWidget.setWindowTitle(QCoreApplication.translate("OrganTissueWidget", u"Form", None))
    # retranslateUi

