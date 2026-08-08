# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'biologicalsourcewidget.ui'
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
    QLabel, QSizePolicy, QToolButton, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_BiologicalSourceWidget(object):
    def setupUi(self, BiologicalSourceWidget):
        if not BiologicalSourceWidget.objectName():
            BiologicalSourceWidget.setObjectName(u"BiologicalSourceWidget")
        BiologicalSourceWidget.resize(204, 98)
        self.gridLayout = QGridLayout(BiologicalSourceWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(BiologicalSourceWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameDescriptionWidget.sizePolicy().hasHeightForWidth())
        self.nameDescriptionWidget.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(BiologicalSourceWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.bioSourceTypeComboBox = QComboBox(BiologicalSourceWidget)
        self.bioSourceTypeComboBox.setObjectName(u"bioSourceTypeComboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.bioSourceTypeComboBox.sizePolicy().hasHeightForWidth())
        self.bioSourceTypeComboBox.setSizePolicy(sizePolicy1)

        self.horizontalLayout_2.addWidget(self.bioSourceTypeComboBox)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(BiologicalSourceWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.specimenNameLabel = QLabel(BiologicalSourceWidget)
        self.specimenNameLabel.setObjectName(u"specimenNameLabel")

        self.horizontalLayout.addWidget(self.specimenNameLabel)

        self.toggleSpecimenEditorToolButton = QToolButton(BiologicalSourceWidget)
        self.toggleSpecimenEditorToolButton.setObjectName(u"toggleSpecimenEditorToolButton")
        icon = QIcon(QIcon.fromTheme(u"document-properties"))
        self.toggleSpecimenEditorToolButton.setIcon(icon)
        self.toggleSpecimenEditorToolButton.setCheckable(True)
        self.toggleSpecimenEditorToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.toggleSpecimenEditorToolButton)

        self.replaceSpecimenToolButton = QToolButton(BiologicalSourceWidget)
        self.replaceSpecimenToolButton.setObjectName(u"replaceSpecimenToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"document-replace"))
        self.replaceSpecimenToolButton.setIcon(icon1)
        self.replaceSpecimenToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.replaceSpecimenToolButton)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.bioSourceTypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BiologicalSourceWidget)

        QMetaObject.connectSlotsByName(BiologicalSourceWidget)
    # setupUi

    def retranslateUi(self, BiologicalSourceWidget):
        BiologicalSourceWidget.setWindowTitle(QCoreApplication.translate("BiologicalSourceWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.label.setToolTip(QCoreApplication.translate("BiologicalSourceWidget", u"Specify Category", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label.setStatusTip(QCoreApplication.translate("BiologicalSourceWidget", u"Specify Category", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label.setWhatsThis(QCoreApplication.translate("BiologicalSourceWidget", u"Specify Category", None))
#endif // QT_CONFIG(whatsthis)
        self.label.setText(QCoreApplication.translate("BiologicalSourceWidget", u"Category:", None))
        self.label_2.setText(QCoreApplication.translate("BiologicalSourceWidget", u"Specimen:", None))
        self.specimenNameLabel.setText(QCoreApplication.translate("BiologicalSourceWidget", u"TextLabel", None))
#if QT_CONFIG(tooltip)
        self.toggleSpecimenEditorToolButton.setToolTip(QCoreApplication.translate("BiologicalSourceWidget", u"Edit specimen", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleSpecimenEditorToolButton.setStatusTip(QCoreApplication.translate("BiologicalSourceWidget", u"Edit specimen", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleSpecimenEditorToolButton.setWhatsThis(QCoreApplication.translate("BiologicalSourceWidget", u"Edit specimen", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleSpecimenEditorToolButton.setText(QCoreApplication.translate("BiologicalSourceWidget", u"...", None))
#if QT_CONFIG(tooltip)
        self.replaceSpecimenToolButton.setToolTip(QCoreApplication.translate("BiologicalSourceWidget", u"Replace specimen", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.replaceSpecimenToolButton.setStatusTip(QCoreApplication.translate("BiologicalSourceWidget", u"Replace specimen", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.replaceSpecimenToolButton.setWhatsThis(QCoreApplication.translate("BiologicalSourceWidget", u"Replace specimen", None))
#endif // QT_CONFIG(whatsthis)
        self.replaceSpecimenToolButton.setText(QCoreApplication.translate("BiologicalSourceWidget", u"Replace Specimen", None))
    # retranslateUi

