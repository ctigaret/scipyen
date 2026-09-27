# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'biometricswidget.ui'
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
    QLabel, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.small_widgets import (LineEdit, QuantitySpinBox)

class Ui_BiometricsWidget(object):
    def setupUi(self, BiometricsWidget):
        if not BiometricsWidget.objectName():
            BiometricsWidget.setObjectName(u"BiometricsWidget")
        BiometricsWidget.resize(273, 190)
        self.gridLayout = QGridLayout(BiometricsWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.nameDescriptionWidget = NameDescriptionWidget(BiometricsWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameDescriptionWidget.sizePolicy().hasHeightForWidth())
        self.nameDescriptionWidget.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label = QLabel(BiometricsWidget)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)

        self.horizontalLayout_6.addWidget(self.label)

        self.genotypeLineEdit = LineEdit(BiometricsWidget)
        self.genotypeLineEdit.setObjectName(u"genotypeLineEdit")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.genotypeLineEdit.sizePolicy().hasHeightForWidth())
        self.genotypeLineEdit.setSizePolicy(sizePolicy2)

        self.horizontalLayout_6.addWidget(self.genotypeLineEdit)


        self.gridLayout.addLayout(self.horizontalLayout_6, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(BiometricsWidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_2)

        self.geneticSexComboBox = QComboBox(BiometricsWidget)
        self.geneticSexComboBox.setObjectName(u"geneticSexComboBox")
        sizePolicy2.setHeightForWidth(self.geneticSexComboBox.sizePolicy().hasHeightForWidth())
        self.geneticSexComboBox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.geneticSexComboBox)

        self.label_3 = QLabel(BiometricsWidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_3)

        self.devStageComboBox = QComboBox(BiometricsWidget)
        self.devStageComboBox.setObjectName(u"devStageComboBox")
        sizePolicy2.setHeightForWidth(self.devStageComboBox.sizePolicy().hasHeightForWidth())
        self.devStageComboBox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.devStageComboBox)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.ageLabel = QLabel(BiometricsWidget)
        self.ageLabel.setObjectName(u"ageLabel")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.ageLabel.sizePolicy().hasHeightForWidth())
        self.ageLabel.setSizePolicy(sizePolicy3)

        self.verticalLayout.addWidget(self.ageLabel)

        self.ageSpinBox = QuantitySpinBox(BiometricsWidget)
        self.ageSpinBox.setObjectName(u"ageSpinBox")

        self.verticalLayout.addWidget(self.ageSpinBox)


        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_4 = QLabel(BiometricsWidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy3.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy3)

        self.verticalLayout_2.addWidget(self.label_4)

        self.weightSpinBox = QuantitySpinBox(BiometricsWidget)
        self.weightSpinBox.setObjectName(u"weightSpinBox")

        self.verticalLayout_2.addWidget(self.weightSpinBox)


        self.horizontalLayout_4.addLayout(self.verticalLayout_2)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_5 = QLabel(BiometricsWidget)
        self.label_5.setObjectName(u"label_5")
        sizePolicy3.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy3)

        self.verticalLayout_3.addWidget(self.label_5)

        self.heightSpinBox = QuantitySpinBox(BiometricsWidget)
        self.heightSpinBox.setObjectName(u"heightSpinBox")

        self.verticalLayout_3.addWidget(self.heightSpinBox)


        self.horizontalLayout_4.addLayout(self.verticalLayout_3)


        self.gridLayout.addLayout(self.horizontalLayout_4, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 4, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.genotypeLineEdit)
        self.label_2.setBuddy(self.geneticSexComboBox)
        self.label_3.setBuddy(self.devStageComboBox)
        self.ageLabel.setBuddy(self.ageSpinBox)
        self.label_4.setBuddy(self.weightSpinBox)
        self.label_5.setBuddy(self.heightSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BiometricsWidget)

        QMetaObject.connectSlotsByName(BiometricsWidget)
    # setupUi

    def retranslateUi(self, BiometricsWidget):
        BiometricsWidget.setWindowTitle(QCoreApplication.translate("BiometricsWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("BiometricsWidget", u"Genotype:", None))
#if QT_CONFIG(tooltip)
        self.label_2.setToolTip(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_2.setStatusTip(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_2.setWhatsThis(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(whatsthis)
        self.label_2.setText(QCoreApplication.translate("BiometricsWidget", u"Sex:", None))
#if QT_CONFIG(tooltip)
        self.geneticSexComboBox.setToolTip(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.geneticSexComboBox.setStatusTip(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.geneticSexComboBox.setWhatsThis(QCoreApplication.translate("BiometricsWidget", u"Genetic sex", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.label_3.setToolTip(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_3.setStatusTip(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_3.setWhatsThis(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(whatsthis)
        self.label_3.setText(QCoreApplication.translate("BiometricsWidget", u"Stage:", None))
#if QT_CONFIG(tooltip)
        self.devStageComboBox.setToolTip(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.devStageComboBox.setStatusTip(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.devStageComboBox.setWhatsThis(QCoreApplication.translate("BiometricsWidget", u"Developmental stage", None))
#endif // QT_CONFIG(whatsthis)
        self.ageLabel.setText(QCoreApplication.translate("BiometricsWidget", u"Age:", None))
        self.label_4.setText(QCoreApplication.translate("BiometricsWidget", u"Weight:", None))
        self.label_5.setText(QCoreApplication.translate("BiometricsWidget", u"Height:", None))
    # retranslateUi

