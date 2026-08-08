# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cellcompartmentwidget.ui'
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
    QLabel, QSizePolicy, QSpacerItem, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_CellCompartmentWidget(object):
    def setupUi(self, CellCompartmentWidget):
        if not CellCompartmentWidget.objectName():
            CellCompartmentWidget.setObjectName(u"CellCompartmentWidget")
        CellCompartmentWidget.resize(229, 73)
        self.gridLayout = QGridLayout(CellCompartmentWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(CellCompartmentWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(CellCompartmentWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.typeComboBox = QComboBox(CellCompartmentWidget)
        self.typeComboBox.setObjectName(u"typeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.typeComboBox.sizePolicy().hasHeightForWidth())
        self.typeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.typeComboBox)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(126, 2, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.typeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(CellCompartmentWidget)

        QMetaObject.connectSlotsByName(CellCompartmentWidget)
    # setupUi

    def retranslateUi(self, CellCompartmentWidget):
        CellCompartmentWidget.setWindowTitle(QCoreApplication.translate("CellCompartmentWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("CellCompartmentWidget", u"Type:", None))
    # retranslateUi

