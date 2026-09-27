# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'simpleprocedurewidget.ui'
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
    QLabel, QSizePolicy, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_SimpleProcedureWidget(object):
    def setupUi(self, SimpleProcedureWidget):
        if not SimpleProcedureWidget.objectName():
            SimpleProcedureWidget.setObjectName(u"SimpleProcedureWidget")
        SimpleProcedureWidget.resize(300, 62)
        self.gridLayout_4 = QGridLayout(SimpleProcedureWidget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.nameDescriptionWidget = NameDescriptionWidget(SimpleProcedureWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout_4.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(SimpleProcedureWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.typeComboBox = QComboBox(SimpleProcedureWidget)
        self.typeComboBox.setObjectName(u"typeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.typeComboBox.sizePolicy().hasHeightForWidth())
        self.typeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.typeComboBox)


        self.gridLayout_4.addLayout(self.horizontalLayout, 1, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.typeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SimpleProcedureWidget)

        QMetaObject.connectSlotsByName(SimpleProcedureWidget)
    # setupUi

    def retranslateUi(self, SimpleProcedureWidget):
        SimpleProcedureWidget.setWindowTitle(QCoreApplication.translate("SimpleProcedureWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("SimpleProcedureWidget", u"Type:", None))
    # retranslateUi

