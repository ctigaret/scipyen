# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cellwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QSizePolicy, QSpacerItem, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.small_widgets import LineEdit

class Ui_CellWidget(object):
    def setupUi(self, CellWidget):
        if not CellWidget.objectName():
            CellWidget.setObjectName(u"CellWidget")
        CellWidget.resize(230, 71)
        self.gridLayout = QGridLayout(CellWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(CellWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(CellWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.cellTypeNameEdit = LineEdit(CellWidget)
        self.cellTypeNameEdit.setObjectName(u"cellTypeNameEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cellTypeNameEdit.sizePolicy().hasHeightForWidth())
        self.cellTypeNameEdit.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.cellTypeNameEdit)

        self.label_2 = QLabel(CellWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.cellSubTypeNameEdit = LineEdit(CellWidget)
        self.cellSubTypeNameEdit.setObjectName(u"cellSubTypeNameEdit")
        sizePolicy.setHeightForWidth(self.cellSubTypeNameEdit.sizePolicy().hasHeightForWidth())
        self.cellSubTypeNameEdit.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.cellSubTypeNameEdit)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(207, 3, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.cellTypeNameEdit)
        self.label_2.setBuddy(self.cellSubTypeNameEdit)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(CellWidget)

        QMetaObject.connectSlotsByName(CellWidget)
    # setupUi

    def retranslateUi(self, CellWidget):
        CellWidget.setWindowTitle(QCoreApplication.translate("CellWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("CellWidget", u"Type:", None))
        self.label_2.setText(QCoreApplication.translate("CellWidget", u"Subtype:", None))
    # retranslateUi

