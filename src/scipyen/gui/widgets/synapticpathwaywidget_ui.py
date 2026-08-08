# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'synapticpathwaywidget.ui'
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_SynapticPathwayWidget(object):
    def setupUi(self, SynapticPathwayWidget):
        if not SynapticPathwayWidget.objectName():
            SynapticPathwayWidget.setObjectName(u"SynapticPathwayWidget")
        SynapticPathwayWidget.resize(304, 179)
        self.gridLayout = QGridLayout(SynapticPathwayWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(SynapticPathwayWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(SynapticPathwayWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.adcSpinBox = QSpinBox(SynapticPathwayWidget)
        self.adcSpinBox.setObjectName(u"adcSpinBox")

        self.horizontalLayout.addWidget(self.adcSpinBox)

        self.label_3 = QLabel(SynapticPathwayWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.dacSpinBox = QSpinBox(SynapticPathwayWidget)
        self.dacSpinBox.setObjectName(u"dacSpinBox")

        self.horizontalLayout.addWidget(self.dacSpinBox)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_4 = QLabel(SynapticPathwayWidget)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_2.addWidget(self.label_4)

        self.electrodeModeComboBox = QComboBox(SynapticPathwayWidget)
        self.electrodeModeComboBox.setObjectName(u"electrodeModeComboBox")
        self.electrodeModeComboBox.setFrame(True)

        self.horizontalLayout_2.addWidget(self.electrodeModeComboBox)

        self.label_5 = QLabel(SynapticPathwayWidget)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_2.addWidget(self.label_5)

        self.pathTypeComboBox = QComboBox(SynapticPathwayWidget)
        self.pathTypeComboBox.setObjectName(u"pathTypeComboBox")
        self.pathTypeComboBox.setFrame(True)

        self.horizontalLayout_2.addWidget(self.pathTypeComboBox)


        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.stimulusPushButton = QPushButton(SynapticPathwayWidget)
        self.stimulusPushButton.setObjectName(u"stimulusPushButton")
        self.stimulusPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.stimulusPushButton)

        self.schedulePushButton = QPushButton(SynapticPathwayWidget)
        self.schedulePushButton.setObjectName(u"schedulePushButton")
        self.schedulePushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.schedulePushButton)

        self.measurementsPushButton = QPushButton(SynapticPathwayWidget)
        self.measurementsPushButton.setObjectName(u"measurementsPushButton")
        self.measurementsPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.measurementsPushButton)


        self.gridLayout.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.createObjectPushButton = QPushButton(SynapticPathwayWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout_4.addWidget(self.createObjectPushButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout_4, 4, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_2.setBuddy(self.adcSpinBox)
        self.label_3.setBuddy(self.adcSpinBox)
        self.label_4.setBuddy(self.electrodeModeComboBox)
        self.label_5.setBuddy(self.pathTypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SynapticPathwayWidget)

        QMetaObject.connectSlotsByName(SynapticPathwayWidget)
    # setupUi

    def retranslateUi(self, SynapticPathwayWidget):
        SynapticPathwayWidget.setWindowTitle(QCoreApplication.translate("SynapticPathwayWidget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("SynapticPathwayWidget", u"ADC:", None))
        self.label_3.setText(QCoreApplication.translate("SynapticPathwayWidget", u"DAC:", None))
#if QT_CONFIG(tooltip)
        self.label_4.setToolTip(QCoreApplication.translate("SynapticPathwayWidget", u"Electrode mode", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_4.setStatusTip(QCoreApplication.translate("SynapticPathwayWidget", u"Electrode mode", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_4.setWhatsThis(QCoreApplication.translate("SynapticPathwayWidget", u"Electrode mode", None))
#endif // QT_CONFIG(whatsthis)
        self.label_4.setText(QCoreApplication.translate("SynapticPathwayWidget", u"Electrode:", None))
        self.label_5.setText(QCoreApplication.translate("SynapticPathwayWidget", u"Type:", None))
        self.stimulusPushButton.setText(QCoreApplication.translate("SynapticPathwayWidget", u"Stimulus...", None))
        self.schedulePushButton.setText(QCoreApplication.translate("SynapticPathwayWidget", u"Schedule...", None))
        self.measurementsPushButton.setText(QCoreApplication.translate("SynapticPathwayWidget", u"Measurements...", None))
        self.createObjectPushButton.setText(QCoreApplication.translate("SynapticPathwayWidget", u"New", None))
    # retranslateUi

