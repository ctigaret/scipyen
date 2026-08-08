# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'auxiliaryinputwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpinBox, QWidget)

class Ui_AuxiliaryInputWidget(object):
    def setupUi(self, AuxiliaryInputWidget):
        if not AuxiliaryInputWidget.objectName():
            AuxiliaryInputWidget.setObjectName(u"AuxiliaryInputWidget")
        AuxiliaryInputWidget.resize(440, 46)
        self.gridLayout = QGridLayout(AuxiliaryInputWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(AuxiliaryInputWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.nameLineEdit = QLineEdit(AuxiliaryInputWidget)
        self.nameLineEdit.setObjectName(u"nameLineEdit")

        self.horizontalLayout.addWidget(self.nameLineEdit)

        self.label_2 = QLabel(AuxiliaryInputWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.channelSpinBox = QSpinBox(AuxiliaryInputWidget)
        self.channelSpinBox.setObjectName(u"channelSpinBox")

        self.horizontalLayout.addWidget(self.channelSpinBox)

        self.isCommandCheckBox = QCheckBox(AuxiliaryInputWidget)
        self.isCommandCheckBox.setObjectName(u"isCommandCheckBox")
        self.isCommandCheckBox.setTristate(True)

        self.horizontalLayout.addWidget(self.isCommandCheckBox)

        self.createObjectPushButton = QPushButton(AuxiliaryInputWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.createObjectPushButton)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.nameLineEdit)
        self.label_2.setBuddy(self.channelSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(AuxiliaryInputWidget)

        QMetaObject.connectSlotsByName(AuxiliaryInputWidget)
    # setupUi

    def retranslateUi(self, AuxiliaryInputWidget):
        AuxiliaryInputWidget.setWindowTitle(QCoreApplication.translate("AuxiliaryInputWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("AuxiliaryInputWidget", u"Name:", None))
        self.label_2.setText(QCoreApplication.translate("AuxiliaryInputWidget", u"Channel:", None))
        self.isCommandCheckBox.setText(QCoreApplication.translate("AuxiliaryInputWidget", u"Command/TTL", None))
        self.createObjectPushButton.setText(QCoreApplication.translate("AuxiliaryInputWidget", u"New", None))
    # retranslateUi

