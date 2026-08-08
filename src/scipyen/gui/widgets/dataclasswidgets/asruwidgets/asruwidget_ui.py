# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'asruwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGridLayout, QLabel,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.small_widgets import LineEdit

class Ui_ASRUWidget(object):
    def setupUi(self, ASRUWidget):
        if not ASRUWidget.objectName():
            ASRUWidget.setObjectName(u"ASRUWidget")
        ASRUWidget.resize(294, 143)
        self.gridLayout = QGridLayout(ASRUWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(ASRUWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.verticalLayout.addWidget(self.nameDescriptionWidget)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.licenseIDLabel = QLabel(ASRUWidget)
        self.licenseIDLabel.setObjectName(u"licenseIDLabel")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.licenseIDLabel)

        self.licenseIDLineEdit = LineEdit(ASRUWidget)
        self.licenseIDLineEdit.setObjectName(u"licenseIDLineEdit")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.licenseIDLineEdit)

        self.holderNameLabel = QLabel(ASRUWidget)
        self.holderNameLabel.setObjectName(u"holderNameLabel")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.holderNameLabel)

        self.holderNameLineEdit = LineEdit(ASRUWidget)
        self.holderNameLineEdit.setObjectName(u"holderNameLineEdit")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.holderNameLineEdit)

        self.holderEMailLabel = QLabel(ASRUWidget)
        self.holderEMailLabel.setObjectName(u"holderEMailLabel")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.holderEMailLabel)

        self.holderEMailLineEdit = LineEdit(ASRUWidget)
        self.holderEMailLineEdit.setObjectName(u"holderEMailLineEdit")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.holderEMailLineEdit)


        self.verticalLayout.addLayout(self.formLayout)

        self.verticalSpacer = QSpacerItem(58, 13, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.licenseIDLabel.setBuddy(self.licenseIDLineEdit)
        self.holderNameLabel.setBuddy(self.holderNameLineEdit)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ASRUWidget)

        QMetaObject.connectSlotsByName(ASRUWidget)
    # setupUi

    def retranslateUi(self, ASRUWidget):
        ASRUWidget.setWindowTitle(QCoreApplication.translate("ASRUWidget", u"Form", None))
        self.licenseIDLabel.setText(QCoreApplication.translate("ASRUWidget", u"License ID: ", None))
        self.holderNameLabel.setText(QCoreApplication.translate("ASRUWidget", u"Holder Name: ", None))
        self.holderEMailLabel.setText(QCoreApplication.translate("ASRUWidget", u"Holder e-mail: ", None))
    # retranslateUi

