# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'biologicalproductwidget.ui'
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
    QLabel, QSizePolicy, QSpacerItem, QSplitter,
    QVBoxLayout, QWidget)

from gui.widgets.dataclasswidgets.dataexchangewidget import DataExchangeWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_BiologialProductWidget(object):
    def setupUi(self, BiologialProductWidget):
        if not BiologialProductWidget.objectName():
            BiologialProductWidget.setObjectName(u"BiologialProductWidget")
        BiologialProductWidget.resize(230, 73)
        self.gridLayout = QGridLayout(BiologialProductWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(BiologialProductWidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(3)
        self.dataExchangeWidget = DataExchangeWidget(self.splitter)
        self.dataExchangeWidget.setObjectName(u"dataExchangeWidget")
        self.splitter.addWidget(self.dataExchangeWidget)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.nameDescriptionWidget = NameDescriptionWidget(self.layoutWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.verticalLayout.addWidget(self.nameDescriptionWidget)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.bioProductTypeComboBox = QComboBox(self.layoutWidget)
        self.bioProductTypeComboBox.setObjectName(u"bioProductTypeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bioProductTypeComboBox.sizePolicy().hasHeightForWidth())
        self.bioProductTypeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.bioProductTypeComboBox)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.splitter.addWidget(self.layoutWidget)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.bioProductTypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BiologialProductWidget)

        QMetaObject.connectSlotsByName(BiologialProductWidget)
    # setupUi

    def retranslateUi(self, BiologialProductWidget):
        BiologialProductWidget.setWindowTitle(QCoreApplication.translate("BiologialProductWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("BiologialProductWidget", u"Type:", None))
    # retranslateUi

