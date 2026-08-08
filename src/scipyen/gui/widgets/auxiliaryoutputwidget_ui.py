# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'auxiliaryoutputwidget.ui'
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

class Ui_AuxiliaryOutputWidget(object):
    def setupUi(self, AuxiliaryOutputWidget):
        if not AuxiliaryOutputWidget.objectName():
            AuxiliaryOutputWidget.setObjectName(u"AuxiliaryOutputWidget")
        AuxiliaryOutputWidget.resize(440, 46)
        self.gridLayout = QGridLayout(AuxiliaryOutputWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(AuxiliaryOutputWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.nameLineEdit = QLineEdit(AuxiliaryOutputWidget)
        self.nameLineEdit.setObjectName(u"nameLineEdit")

        self.horizontalLayout.addWidget(self.nameLineEdit)

        self.label_2 = QLabel(AuxiliaryOutputWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.channelSpinBox = QSpinBox(AuxiliaryOutputWidget)
        self.channelSpinBox.setObjectName(u"channelSpinBox")

        self.horizontalLayout.addWidget(self.channelSpinBox)

        self.isDigTTLCheckBox = QCheckBox(AuxiliaryOutputWidget)
        self.isDigTTLCheckBox.setObjectName(u"isDigTTLCheckBox")
        self.isDigTTLCheckBox.setTristate(True)

        self.horizontalLayout.addWidget(self.isDigTTLCheckBox)

        self.createObjectPushButton = QPushButton(AuxiliaryOutputWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.createObjectPushButton)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.nameLineEdit)
        self.label_2.setBuddy(self.channelSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(AuxiliaryOutputWidget)

        QMetaObject.connectSlotsByName(AuxiliaryOutputWidget)
    # setupUi

    def retranslateUi(self, AuxiliaryOutputWidget):
        AuxiliaryOutputWidget.setWindowTitle(QCoreApplication.translate("AuxiliaryOutputWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("AuxiliaryOutputWidget", u"Name:", None))
        self.label_2.setText(QCoreApplication.translate("AuxiliaryOutputWidget", u"Channel:", None))
        self.isDigTTLCheckBox.setText(QCoreApplication.translate("AuxiliaryOutputWidget", u"TTL/DAC", None))
        self.createObjectPushButton.setText(QCoreApplication.translate("AuxiliaryOutputWidget", u"New", None))
    # retranslateUi

