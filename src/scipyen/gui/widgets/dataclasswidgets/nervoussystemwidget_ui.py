# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nervoussystemwidget.ui'
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

from gui.widgets.bgatlasstructurewidget import BGAtlasStructureLookupWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_NervousSystemWidget(object):
    def setupUi(self, NervousSystemWidget):
        if not NervousSystemWidget.objectName():
            NervousSystemWidget.setObjectName(u"NervousSystemWidget")
        NervousSystemWidget.resize(229, 78)
        self.gridLayout = QGridLayout(NervousSystemWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(NervousSystemWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.brainAtlasComboBox = QComboBox(NervousSystemWidget)
        self.brainAtlasComboBox.setObjectName(u"brainAtlasComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.brainAtlasComboBox.sizePolicy().hasHeightForWidth())
        self.brainAtlasComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.brainAtlasComboBox)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.nameDescriptionWidget = NameDescriptionWidget(NervousSystemWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.bgStructureWidget = BGAtlasStructureLookupWidget(NervousSystemWidget)
        self.bgStructureWidget.setObjectName(u"bgStructureWidget")

        self.gridLayout.addWidget(self.bgStructureWidget, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.brainAtlasComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(NervousSystemWidget)

        QMetaObject.connectSlotsByName(NervousSystemWidget)
    # setupUi

    def retranslateUi(self, NervousSystemWidget):
        NervousSystemWidget.setWindowTitle(QCoreApplication.translate("NervousSystemWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("NervousSystemWidget", u"Atlas:", None))
    # retranslateUi

