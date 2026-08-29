# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'recordingsourcewidget.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
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
    QSpinBox, QTabWidget, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.tableeditorwidget import TableEditorWidget

class Ui_RecordingSourceWidget(object):
    def setupUi(self, RecordingSourceWidget):
        if not RecordingSourceWidget.objectName():
            RecordingSourceWidget.setObjectName(u"RecordingSourceWidget")
        RecordingSourceWidget.resize(372, 233)
        self.gridLayout_2 = QGridLayout(RecordingSourceWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.nameDescriptionWidget = NameDescriptionWidget(RecordingSourceWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout_2.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(RecordingSourceWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.adcSpinBox = QSpinBox(RecordingSourceWidget)
        self.adcSpinBox.setObjectName(u"adcSpinBox")

        self.horizontalLayout.addWidget(self.adcSpinBox)

        self.label_3 = QLabel(RecordingSourceWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.dacSpinBox = QSpinBox(RecordingSourceWidget)
        self.dacSpinBox.setObjectName(u"dacSpinBox")

        self.horizontalLayout.addWidget(self.dacSpinBox)

        self.label_4 = QLabel(RecordingSourceWidget)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout.addWidget(self.label_4)

        self.electrodeModeComboBox = QComboBox(RecordingSourceWidget)
        self.electrodeModeComboBox.setObjectName(u"electrodeModeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.electrodeModeComboBox.sizePolicy().hasHeightForWidth())
        self.electrodeModeComboBox.setSizePolicy(sizePolicy)
        self.electrodeModeComboBox.setFrame(True)

        self.horizontalLayout.addWidget(self.electrodeModeComboBox)


        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.auxInPushButton = QPushButton(RecordingSourceWidget)
        self.auxInPushButton.setObjectName(u"auxInPushButton")
        self.auxInPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.auxInPushButton)

        self.auxOutPushButton = QPushButton(RecordingSourceWidget)
        self.auxOutPushButton.setObjectName(u"auxOutPushButton")
        self.auxOutPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.auxOutPushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)

        self.tabWidget = QTabWidget(RecordingSourceWidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.stimulusChannelsTab = QWidget()
        self.stimulusChannelsTab.setObjectName(u"stimulusChannelsTab")
        self.gridLayout = QGridLayout(self.stimulusChannelsTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.stimulusListTable = TableEditorWidget(self.stimulusChannelsTab)
        self.stimulusListTable.setObjectName(u"stimulusListTable")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.stimulusListTable.sizePolicy().hasHeightForWidth())
        self.stimulusListTable.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.stimulusListTable, 0, 0, 1, 1)

        self.tabWidget.addTab(self.stimulusChannelsTab, "")
        self.synapticPathwaysTab = QWidget()
        self.synapticPathwaysTab.setObjectName(u"synapticPathwaysTab")
        self.gridLayout_3 = QGridLayout(self.synapticPathwaysTab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.synapticPathwaysTable = TableEditorWidget(self.synapticPathwaysTab)
        self.synapticPathwaysTable.setObjectName(u"synapticPathwaysTable")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.synapticPathwaysTable.sizePolicy().hasHeightForWidth())
        self.synapticPathwaysTable.setSizePolicy(sizePolicy2)

        self.gridLayout_3.addWidget(self.synapticPathwaysTable, 0, 0, 1, 1)

        self.tabWidget.addTab(self.synapticPathwaysTab, "")

        self.gridLayout_2.addWidget(self.tabWidget, 3, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.createObjectPushButton = QPushButton(RecordingSourceWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout_7.addWidget(self.createObjectPushButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_2)


        self.gridLayout_2.addLayout(self.horizontalLayout_7, 4, 0, 1, 1)


        self.retranslateUi(RecordingSourceWidget)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(RecordingSourceWidget)
    # setupUi

    def retranslateUi(self, RecordingSourceWidget):
        RecordingSourceWidget.setWindowTitle(QCoreApplication.translate("RecordingSourceWidget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("RecordingSourceWidget", u"ADC:", None))
        self.label_3.setText(QCoreApplication.translate("RecordingSourceWidget", u"DAC:", None))
#if QT_CONFIG(tooltip)
        self.label_4.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Recording Electrode Mode", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_4.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Recording Electrode Mode", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_4.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Recording Electrode Mode", None))
#endif // QT_CONFIG(whatsthis)
        self.label_4.setText(QCoreApplication.translate("RecordingSourceWidget", u"<html><head/><body><p>Electrode<br/>Mode:</p></body></html>", None))
        self.auxInPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"Auxiliary Inputs...", None))
        self.auxOutPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"Auxiliary Outputs...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.stimulusChannelsTab), QCoreApplication.translate("RecordingSourceWidget", u"Simulus Channels", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.synapticPathwaysTab), QCoreApplication.translate("RecordingSourceWidget", u"Synaptic Pathways", None))
#if QT_CONFIG(tooltip)
        self.createObjectPushButton.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.createObjectPushButton.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.createObjectPushButton.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(whatsthis)
        self.createObjectPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"New", None))
    # retranslateUi

