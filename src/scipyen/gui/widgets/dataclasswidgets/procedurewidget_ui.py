# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'procedurewidget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QTabWidget, QWidget)

from gui.widgets.dataclasswidgets.asruwidgets.asruwidget import ASRUWidget
from gui.widgets.dataclasswidgets.asruwidgets.pplprotocolstepwidget import PPLProtocolStepWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_ProcedureWidget(object):
    def setupUi(self, ProcedureWidget):
        if not ProcedureWidget.objectName():
            ProcedureWidget.setObjectName(u"ProcedureWidget")
        ProcedureWidget.resize(300, 179)
        self.gridLayout_4 = QGridLayout(ProcedureWidget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.nameDescriptionWidget = NameDescriptionWidget(ProcedureWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout_4.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(ProcedureWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.typeComboBox = QComboBox(ProcedureWidget)
        self.typeComboBox.setObjectName(u"typeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.typeComboBox.sizePolicy().hasHeightForWidth())
        self.typeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.typeComboBox)

        self.isRegulatedCheckBox = QCheckBox(ProcedureWidget)
        self.isRegulatedCheckBox.setObjectName(u"isRegulatedCheckBox")

        self.horizontalLayout.addWidget(self.isRegulatedCheckBox)


        self.gridLayout_4.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.asruTabWidget = QTabWidget(ProcedureWidget)
        self.asruTabWidget.setObjectName(u"asruTabWidget")
        self.asruTabWidget.setEnabled(False)
        self.pplTab = QWidget()
        self.pplTab.setObjectName(u"pplTab")
        self.gridLayout = QGridLayout(self.pplTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pplWidget = ASRUWidget(self.pplTab)
        self.pplWidget.setObjectName(u"pplWidget")

        self.gridLayout.addWidget(self.pplWidget, 0, 0, 1, 1)

        self.asruTabWidget.addTab(self.pplTab, "")
        self.pilTab = QWidget()
        self.pilTab.setObjectName(u"pilTab")
        self.gridLayout_2 = QGridLayout(self.pilTab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pilWidget = ASRUWidget(self.pilTab)
        self.pilWidget.setObjectName(u"pilWidget")

        self.gridLayout_2.addWidget(self.pilWidget, 0, 0, 1, 1)

        self.asruTabWidget.addTab(self.pilTab, "")
        self.protocolTab = QWidget()
        self.protocolTab.setObjectName(u"protocolTab")
        self.gridLayout_3 = QGridLayout(self.protocolTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.protocolWidget = PPLProtocolStepWidget(self.protocolTab)
        self.protocolWidget.setObjectName(u"protocolWidget")

        self.gridLayout_3.addWidget(self.protocolWidget, 0, 0, 1, 1)

        self.protocolStepWidget = PPLProtocolStepWidget(self.protocolTab)
        self.protocolStepWidget.setObjectName(u"protocolStepWidget")

        self.gridLayout_3.addWidget(self.protocolStepWidget, 1, 0, 1, 1)

        self.asruTabWidget.addTab(self.protocolTab, "")

        self.gridLayout_4.addWidget(self.asruTabWidget, 2, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(126, 28, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_4.addItem(self.verticalSpacer, 3, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.typeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ProcedureWidget)

        self.asruTabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ProcedureWidget)
    # setupUi

    def retranslateUi(self, ProcedureWidget):
        ProcedureWidget.setWindowTitle(QCoreApplication.translate("ProcedureWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("ProcedureWidget", u"Type:", None))
        self.isRegulatedCheckBox.setText(QCoreApplication.translate("ProcedureWidget", u"Regulated", None))
        self.asruTabWidget.setTabText(self.asruTabWidget.indexOf(self.pplTab), QCoreApplication.translate("ProcedureWidget", u"PPL", None))
        self.asruTabWidget.setTabText(self.asruTabWidget.indexOf(self.pilTab), QCoreApplication.translate("ProcedureWidget", u"PIL", None))
        self.asruTabWidget.setTabText(self.asruTabWidget.indexOf(self.protocolTab), QCoreApplication.translate("ProcedureWidget", u"Protocol and Step", None))
    # retranslateUi

