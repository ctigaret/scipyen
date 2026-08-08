# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'brainglobeatlasstructurelookup.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QToolButton, QWidget)

from gui.widgets.small_widgets import LineEdit

class Ui_BGAtlasStructureLookupWidget(object):
    def setupUi(self, BGAtlasStructureLookupWidget):
        if not BGAtlasStructureLookupWidget.objectName():
            BGAtlasStructureLookupWidget.setObjectName(u"BGAtlasStructureLookupWidget")
        BGAtlasStructureLookupWidget.resize(283, 192)
        self.gridLayout_2 = QGridLayout(BGAtlasStructureLookupWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.structureIDAcroNameLabel = QLabel(BGAtlasStructureLookupWidget)
        self.structureIDAcroNameLabel.setObjectName(u"structureIDAcroNameLabel")

        self.horizontalLayout.addWidget(self.structureIDAcroNameLabel)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.detailsToolButton = QToolButton(BGAtlasStructureLookupWidget)
        self.detailsToolButton.setObjectName(u"detailsToolButton")
        icon = QIcon(QIcon.fromTheme(u"view-list-tree"))
        self.detailsToolButton.setIcon(icon)
        self.detailsToolButton.setCheckable(False)
        self.detailsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.detailsToolButton)


        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.groupBox = QGroupBox(BGAtlasStructureLookupWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.acronymOrNameEdit = LineEdit(self.groupBox)
        self.acronymOrNameEdit.setObjectName(u"acronymOrNameEdit")

        self.gridLayout.addWidget(self.acronymOrNameEdit, 0, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.ancestorComboBox = QComboBox(self.groupBox)
        self.ancestorComboBox.setObjectName(u"ancestorComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ancestorComboBox.sizePolicy().hasHeightForWidth())
        self.ancestorComboBox.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.ancestorComboBox, 1, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.descendantComboBox = QComboBox(self.groupBox)
        self.descendantComboBox.setObjectName(u"descendantComboBox")
        sizePolicy.setHeightForWidth(self.descendantComboBox.sizePolicy().hasHeightForWidth())
        self.descendantComboBox.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.descendantComboBox, 2, 1, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 1, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.acronymOrNameEdit)
        self.label_2.setBuddy(self.ancestorComboBox)
        self.label_3.setBuddy(self.descendantComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BGAtlasStructureLookupWidget)

        QMetaObject.connectSlotsByName(BGAtlasStructureLookupWidget)
    # setupUi

    def retranslateUi(self, BGAtlasStructureLookupWidget):
        BGAtlasStructureLookupWidget.setWindowTitle(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.structureIDAcroNameLabel.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"BrainGlobe Struture Acronym (Name: ID)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.structureIDAcroNameLabel.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"BrainGlobe Struture Acronym (Name: ID)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.structureIDAcroNameLabel.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"BrainGlobe Struture Acronym (Name: ID)", None))
#endif // QT_CONFIG(whatsthis)
        self.structureIDAcroNameLabel.setText(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Acronym (Name: ID)", None))
        self.detailsToolButton.setText(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Details", None))
        self.groupBox.setTitle(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Atlas Structure", None))
#if QT_CONFIG(tooltip)
        self.label.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym or Name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym or Name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym or Name", None))
#endif // QT_CONFIG(whatsthis)
        self.label.setText(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Acronym or Name:", None))
#if QT_CONFIG(tooltip)
        self.acronymOrNameEdit.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym Or Name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.acronymOrNameEdit.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym Or Name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.acronymOrNameEdit.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Find Structure by Acronym Or Name", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.label_2.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Ancestor", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_2.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Ancestor", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_2.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Ancestor", None))
#endif // QT_CONFIG(whatsthis)
        self.label_2.setText(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Ancestor:", None))
#if QT_CONFIG(tooltip)
        self.ancestorComboBox.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select an Ancestor (Parent) Structure", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.ancestorComboBox.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select an Ancestor (Parent) Structure", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.ancestorComboBox.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select an Ancestor (Parent) Structure", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.label_3.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Descendant", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_3.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Descendant", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_3.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Descendant", None))
#endif // QT_CONFIG(whatsthis)
        self.label_3.setText(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select Descendant:", None))
#if QT_CONFIG(tooltip)
        self.descendantComboBox.setToolTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select a Descendant (Child) Structure", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.descendantComboBox.setStatusTip(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select a Descendant (Child) Structure", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.descendantComboBox.setWhatsThis(QCoreApplication.translate("BGAtlasStructureLookupWidget", u"Select a Descendant (Child) Structure", None))
#endif // QT_CONFIG(whatsthis)
    # retranslateUi

