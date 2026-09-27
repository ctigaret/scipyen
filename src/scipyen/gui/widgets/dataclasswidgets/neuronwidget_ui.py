# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'neuronwidget.ui'
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

class Ui_NeuronWidget(object):
    def setupUi(self, NeuronWidget):
        if not NeuronWidget.objectName():
            NeuronWidget.setObjectName(u"NeuronWidget")
        NeuronWidget.resize(226, 68)
        self.gridLayout = QGridLayout(NeuronWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(NeuronWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameDescriptionWidget.sizePolicy().hasHeightForWidth())
        self.nameDescriptionWidget.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(NeuronWidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_2)

        self.neuronTypeComboBox = QComboBox(NeuronWidget)
        self.neuronTypeComboBox.setObjectName(u"neuronTypeComboBox")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.neuronTypeComboBox.sizePolicy().hasHeightForWidth())
        self.neuronTypeComboBox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.neuronTypeComboBox)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(38, 2, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_2.setBuddy(self.neuronTypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(NeuronWidget)

        QMetaObject.connectSlotsByName(NeuronWidget)
    # setupUi

    def retranslateUi(self, NeuronWidget):
        NeuronWidget.setWindowTitle(QCoreApplication.translate("NeuronWidget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("NeuronWidget", u"Type", None))
    # retranslateUi

