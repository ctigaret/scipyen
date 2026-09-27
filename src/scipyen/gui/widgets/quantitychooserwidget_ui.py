# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'quantitychooserwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QLabel,
    QSizePolicy, QWidget)

class Ui_QuantityChooserWidget(object):
    def setupUi(self, QuantityChooserWidget):
        if not QuantityChooserWidget.objectName():
            QuantityChooserWidget.setObjectName(u"QuantityChooserWidget")
        QuantityChooserWidget.resize(163, 94)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(QuantityChooserWidget.sizePolicy().hasHeightForWidth())
        QuantityChooserWidget.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(QuantityChooserWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.widget = QWidget(QuantityChooserWidget)
        self.widget.setObjectName(u"widget")
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.familyNameLabel = QLabel(self.widget)
        self.familyNameLabel.setObjectName(u"familyNameLabel")
        self.familyNameLabel.setScaledContents(False)

        self.gridLayout.addWidget(self.familyNameLabel, 0, 0, 1, 1)

        self.unitFamilyComboBox = QComboBox(self.widget)
        self.unitFamilyComboBox.setObjectName(u"unitFamilyComboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.unitFamilyComboBox.sizePolicy().hasHeightForWidth())
        self.unitFamilyComboBox.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.unitFamilyComboBox, 0, 1, 1, 1)

        self.unitLabel = QLabel(self.widget)
        self.unitLabel.setObjectName(u"unitLabel")

        self.gridLayout.addWidget(self.unitLabel, 1, 0, 1, 1)

        self.unitComboBox = QComboBox(self.widget)
        self.unitComboBox.setObjectName(u"unitComboBox")
        sizePolicy1.setHeightForWidth(self.unitComboBox.sizePolicy().hasHeightForWidth())
        self.unitComboBox.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.unitComboBox, 1, 1, 1, 1)


        self.gridLayout_2.addWidget(self.widget, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.familyNameLabel.setBuddy(self.unitFamilyComboBox)
        self.unitLabel.setBuddy(self.unitComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(QuantityChooserWidget)

        QMetaObject.connectSlotsByName(QuantityChooserWidget)
    # setupUi

    def retranslateUi(self, QuantityChooserWidget):
        QuantityChooserWidget.setWindowTitle(QCoreApplication.translate("QuantityChooserWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.familyNameLabel.setToolTip(QCoreApplication.translate("QuantityChooserWidget", u"Type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.familyNameLabel.setStatusTip(QCoreApplication.translate("QuantityChooserWidget", u"Type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.familyNameLabel.setWhatsThis(QCoreApplication.translate("QuantityChooserWidget", u"Type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(whatsthis)
        self.familyNameLabel.setText(QCoreApplication.translate("QuantityChooserWidget", u"Family:", None))
#if QT_CONFIG(tooltip)
        self.unitFamilyComboBox.setToolTip(QCoreApplication.translate("QuantityChooserWidget", u"Choose the type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.unitFamilyComboBox.setStatusTip(QCoreApplication.translate("QuantityChooserWidget", u"Choose the type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.unitFamilyComboBox.setWhatsThis(QCoreApplication.translate("QuantityChooserWidget", u"Choose the type of physical unit (Unit \"Family\")", None))
#endif // QT_CONFIG(whatsthis)
        self.unitLabel.setText(QCoreApplication.translate("QuantityChooserWidget", u"Unit:", None))
#if QT_CONFIG(tooltip)
        self.unitComboBox.setToolTip(QCoreApplication.translate("QuantityChooserWidget", u"Choose the physical unit from the family selected above", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.unitComboBox.setStatusTip(QCoreApplication.translate("QuantityChooserWidget", u"Choose the physical unit from the family selected above", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.unitComboBox.setWhatsThis(QCoreApplication.translate("QuantityChooserWidget", u"Choose the physical unit from the family selected above", None))
#endif // QT_CONFIG(whatsthis)
    # retranslateUi

