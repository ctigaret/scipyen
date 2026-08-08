# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'synapticstimuluswidget.ui'
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_SynapticStimulusChannelWidget(object):
    def setupUi(self, SynapticStimulusChannelWidget):
        if not SynapticStimulusChannelWidget.objectName():
            SynapticStimulusChannelWidget.setObjectName(u"SynapticStimulusChannelWidget")
        SynapticStimulusChannelWidget.resize(213, 99)
        self.gridLayout = QGridLayout(SynapticStimulusChannelWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(SynapticStimulusChannelWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(SynapticStimulusChannelWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.outputChannelSpinBox = QSpinBox(SynapticStimulusChannelWidget)
        self.outputChannelSpinBox.setObjectName(u"outputChannelSpinBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.outputChannelSpinBox.sizePolicy().hasHeightForWidth())
        self.outputChannelSpinBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.outputChannelSpinBox)

        self.isDigitalCheckBox = QCheckBox(SynapticStimulusChannelWidget)
        self.isDigitalCheckBox.setObjectName(u"isDigitalCheckBox")

        self.horizontalLayout.addWidget(self.isDigitalCheckBox)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.createObjectPushButton = QPushButton(SynapticStimulusChannelWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.createObjectPushButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_2.setBuddy(self.outputChannelSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SynapticStimulusChannelWidget)

        QMetaObject.connectSlotsByName(SynapticStimulusChannelWidget)
    # setupUi

    def retranslateUi(self, SynapticStimulusChannelWidget):
        SynapticStimulusChannelWidget.setWindowTitle(QCoreApplication.translate("SynapticStimulusChannelWidget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("SynapticStimulusChannelWidget", u"Channel:", None))
        self.isDigitalCheckBox.setText(QCoreApplication.translate("SynapticStimulusChannelWidget", u"Digital", None))
        self.createObjectPushButton.setText(QCoreApplication.translate("SynapticStimulusChannelWidget", u"New", None))
    # retranslateUi

