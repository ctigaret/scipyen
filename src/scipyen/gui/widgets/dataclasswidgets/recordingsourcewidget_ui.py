# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'recordingsourcewidget.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
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
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.tableeditorwidget import TableEditorWidget

class Ui_RecordingSourceWidget(object):
    def setupUi(self, RecordingSourceWidget):
        if not RecordingSourceWidget.objectName():
            RecordingSourceWidget.setObjectName(u"RecordingSourceWidget")
        RecordingSourceWidget.resize(392, 390)
        self.verticalLayout_2 = QVBoxLayout(RecordingSourceWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.newSourcesLayout = QHBoxLayout()
        self.newSourcesLayout.setObjectName(u"newSourcesLayout")
        self.createObjectPushButton = QPushButton(RecordingSourceWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        icon = QIcon(QIcon.fromTheme(u"document-new"))
        self.createObjectPushButton.setIcon(icon)
        self.createObjectPushButton.setFlat(False)

        self.newSourcesLayout.addWidget(self.createObjectPushButton)

        self.createTwoPathwaysSourcePushButton = QPushButton(RecordingSourceWidget)
        self.createTwoPathwaysSourcePushButton.setObjectName(u"createTwoPathwaysSourcePushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.createTwoPathwaysSourcePushButton.sizePolicy().hasHeightForWidth())
        self.createTwoPathwaysSourcePushButton.setSizePolicy(sizePolicy)
        icon1 = QIcon(QIcon.fromTheme(u"document-new-from-template"))
        self.createTwoPathwaysSourcePushButton.setIcon(icon1)

        self.newSourcesLayout.addWidget(self.createTwoPathwaysSourcePushButton)


        self.verticalLayout_2.addLayout(self.newSourcesLayout)

        self.nameDescriptionWidget = NameDescriptionWidget(RecordingSourceWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.verticalLayout_2.addWidget(self.nameDescriptionWidget)

        self.channelsLayout = QHBoxLayout()
        self.channelsLayout.setObjectName(u"channelsLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(RecordingSourceWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.adcSpinBox = QSpinBox(RecordingSourceWidget)
        self.adcSpinBox.setObjectName(u"adcSpinBox")
        sizePolicy.setHeightForWidth(self.adcSpinBox.sizePolicy().hasHeightForWidth())
        self.adcSpinBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.adcSpinBox)

        self.label_3 = QLabel(RecordingSourceWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.dacSpinBox = QSpinBox(RecordingSourceWidget)
        self.dacSpinBox.setObjectName(u"dacSpinBox")
        sizePolicy.setHeightForWidth(self.dacSpinBox.sizePolicy().hasHeightForWidth())
        self.dacSpinBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.dacSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_4 = QLabel(RecordingSourceWidget)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_2.addWidget(self.label_4)

        self.electrodeModeComboBox = QComboBox(RecordingSourceWidget)
        self.electrodeModeComboBox.setObjectName(u"electrodeModeComboBox")
        sizePolicy.setHeightForWidth(self.electrodeModeComboBox.sizePolicy().hasHeightForWidth())
        self.electrodeModeComboBox.setSizePolicy(sizePolicy)
        self.electrodeModeComboBox.setFrame(True)

        self.horizontalLayout_2.addWidget(self.electrodeModeComboBox)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.channelsLayout.addLayout(self.verticalLayout)

        self.groupBox = QGroupBox(RecordingSourceWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.auxInPushButton = QPushButton(self.groupBox)
        self.auxInPushButton.setObjectName(u"auxInPushButton")
        self.auxInPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.auxInPushButton)

        self.auxOutPushButton = QPushButton(self.groupBox)
        self.auxOutPushButton.setObjectName(u"auxOutPushButton")
        self.auxOutPushButton.setFlat(False)

        self.horizontalLayout_3.addWidget(self.auxOutPushButton)


        self.channelsLayout.addWidget(self.groupBox)


        self.verticalLayout_2.addLayout(self.channelsLayout)

        self.channelsAndPathwaysTabWidget = QTabWidget(RecordingSourceWidget)
        self.channelsAndPathwaysTabWidget.setObjectName(u"channelsAndPathwaysTabWidget")
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

        self.channelsAndPathwaysTabWidget.addTab(self.stimulusChannelsTab, "")
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

        self.channelsAndPathwaysTabWidget.addTab(self.synapticPathwaysTab, "")

        self.verticalLayout_2.addWidget(self.channelsAndPathwaysTabWidget)


        self.retranslateUi(RecordingSourceWidget)

        self.channelsAndPathwaysTabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(RecordingSourceWidget)
    # setupUi

    def retranslateUi(self, RecordingSourceWidget):
        RecordingSourceWidget.setWindowTitle(QCoreApplication.translate("RecordingSourceWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.createObjectPushButton.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.createObjectPushButton.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.createObjectPushButton.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Create a new RecordingSource from current data", None))
#endif // QT_CONFIG(whatsthis)
        self.createObjectPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"New Source", None))
#if QT_CONFIG(tooltip)
        self.createTwoPathwaysSourcePushButton.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a two-pathway source directly", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.createTwoPathwaysSourcePushButton.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Create a two-pathway source directly", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.createTwoPathwaysSourcePushButton.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Create a two-pathway source directly", None))
#endif // QT_CONFIG(whatsthis)
        self.createTwoPathwaysSourcePushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"New Two-Pathways Source", None))
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
        self.groupBox.setTitle(QCoreApplication.translate("RecordingSourceWidget", u"Auxiliary", None))
#if QT_CONFIG(tooltip)
        self.auxInPushButton.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary inputs", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.auxInPushButton.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary inputs", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.auxInPushButton.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary inputs", None))
#endif // QT_CONFIG(whatsthis)
        self.auxInPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"Inputs...", None))
#if QT_CONFIG(tooltip)
        self.auxOutPushButton.setToolTip(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary outputs", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.auxOutPushButton.setStatusTip(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary outputs", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.auxOutPushButton.setWhatsThis(QCoreApplication.translate("RecordingSourceWidget", u"Configure auxiliary outputs", None))
#endif // QT_CONFIG(whatsthis)
        self.auxOutPushButton.setText(QCoreApplication.translate("RecordingSourceWidget", u"Outputs...", None))
        self.channelsAndPathwaysTabWidget.setTabText(self.channelsAndPathwaysTabWidget.indexOf(self.stimulusChannelsTab), QCoreApplication.translate("RecordingSourceWidget", u"Simulus Channels", None))
        self.channelsAndPathwaysTabWidget.setTabText(self.channelsAndPathwaysTabWidget.indexOf(self.synapticPathwaysTab), QCoreApplication.translate("RecordingSourceWidget", u"Synaptic Pathways", None))
    # retranslateUi

