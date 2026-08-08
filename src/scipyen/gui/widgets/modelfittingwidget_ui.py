# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ModelFittingWidget.ui'
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
    QLabel, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QSplitter,
    QVBoxLayout, QWidget)

from gui.widgets.small_widgets import QuantitySpinBox
from gui.widgets.svgwidgets import SimpleSVGWidget
from gui.widgets.tableeditorwidget import TableEditorWidget

class Ui_ModelFittingWidget(object):
    def setupUi(self, ModelFittingWidget):
        if not ModelFittingWidget.objectName():
            ModelFittingWidget.setObjectName(u"ModelFittingWidget")
        ModelFittingWidget.resize(581, 459)
        self.gridLayout = QGridLayout(ModelFittingWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.modelNameHLayout = QHBoxLayout()
        self.modelNameHLayout.setObjectName(u"modelNameHLayout")
        self.modelNameLabel = QLabel(ModelFittingWidget)
        self.modelNameLabel.setObjectName(u"modelNameLabel")

        self.modelNameHLayout.addWidget(self.modelNameLabel)

        self.modeNameHSpacer = QSpacerItem(28, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.modelNameHLayout.addItem(self.modeNameHSpacer)

        self.waveformExpressionPushButton = QPushButton(ModelFittingWidget)
        self.waveformExpressionPushButton.setObjectName(u"waveformExpressionPushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.waveformExpressionPushButton.sizePolicy().hasHeightForWidth())
        self.waveformExpressionPushButton.setSizePolicy(sizePolicy)
        icon = QIcon(QIcon.fromTheme(u"mathmode"))
        self.waveformExpressionPushButton.setIcon(icon)
        self.waveformExpressionPushButton.setFlat(True)

        self.modelNameHLayout.addWidget(self.waveformExpressionPushButton)


        self.gridLayout.addLayout(self.modelNameHLayout, 0, 0, 1, 1)

        self.labelsSplitter = QSplitter(ModelFittingWidget)
        self.labelsSplitter.setObjectName(u"labelsSplitter")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.labelsSplitter.sizePolicy().hasHeightForWidth())
        self.labelsSplitter.setSizePolicy(sizePolicy1)
        self.labelsSplitter.setOrientation(Qt.Orientation.Vertical)
        self.svgWidget = SimpleSVGWidget(self.labelsSplitter)
        self.svgWidget.setObjectName(u"svgWidget")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(self.svgWidget.sizePolicy().hasHeightForWidth())
        self.svgWidget.setSizePolicy(sizePolicy2)
        self.svgWidget.setMinimumSize(QSize(24, 24))
        self.svgWidget.setAutoFillBackground(True)
        self.labelsSplitter.addWidget(self.svgWidget)
        self.controlsSplitter = QSplitter(self.labelsSplitter)
        self.controlsSplitter.setObjectName(u"controlsSplitter")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.controlsSplitter.sizePolicy().hasHeightForWidth())
        self.controlsSplitter.setSizePolicy(sizePolicy3)
        self.controlsSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.controlsSplitter.setOpaqueResize(True)
        self.controlsSplitter.setChildrenCollapsible(True)
        self.layoutWidget = QWidget(self.controlsSplitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.controlsVerticalLayout = QVBoxLayout(self.layoutWidget)
        self.controlsVerticalLayout.setObjectName(u"controlsVerticalLayout")
        self.controlsVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.domainStartLabel = QLabel(self.layoutWidget)
        self.domainStartLabel.setObjectName(u"domainStartLabel")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.domainStartLabel.sizePolicy().hasHeightForWidth())
        self.domainStartLabel.setSizePolicy(sizePolicy4)

        self.controlsVerticalLayout.addWidget(self.domainStartLabel)

        self.startSpinBox = QuantitySpinBox(self.layoutWidget)
        self.startSpinBox.setObjectName(u"startSpinBox")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(1)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.startSpinBox.sizePolicy().hasHeightForWidth())
        self.startSpinBox.setSizePolicy(sizePolicy5)

        self.controlsVerticalLayout.addWidget(self.startSpinBox)

        self.label_Duration = QLabel(self.layoutWidget)
        self.label_Duration.setObjectName(u"label_Duration")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.label_Duration.sizePolicy().hasHeightForWidth())
        self.label_Duration.setSizePolicy(sizePolicy6)

        self.controlsVerticalLayout.addWidget(self.label_Duration)

        self.durationSpinBox = QuantitySpinBox(self.layoutWidget)
        self.durationSpinBox.setObjectName(u"durationSpinBox")
        sizePolicy5.setHeightForWidth(self.durationSpinBox.sizePolicy().hasHeightForWidth())
        self.durationSpinBox.setSizePolicy(sizePolicy5)

        self.controlsVerticalLayout.addWidget(self.durationSpinBox)

        self.samplingRateLabel = QLabel(self.layoutWidget)
        self.samplingRateLabel.setObjectName(u"samplingRateLabel")
        sizePolicy6.setHeightForWidth(self.samplingRateLabel.sizePolicy().hasHeightForWidth())
        self.samplingRateLabel.setSizePolicy(sizePolicy6)
        self.samplingRateLabel.setTextFormat(Qt.TextFormat.AutoText)
        self.samplingRateLabel.setWordWrap(False)

        self.controlsVerticalLayout.addWidget(self.samplingRateLabel)

        self.samplingRateSpinBox = QuantitySpinBox(self.layoutWidget)
        self.samplingRateSpinBox.setObjectName(u"samplingRateSpinBox")
        sizePolicy5.setHeightForWidth(self.samplingRateSpinBox.sizePolicy().hasHeightForWidth())
        self.samplingRateSpinBox.setSizePolicy(sizePolicy5)

        self.controlsVerticalLayout.addWidget(self.samplingRateSpinBox)

        self.waveUnitsHorizontalLayout = QHBoxLayout()
        self.waveUnitsHorizontalLayout.setObjectName(u"waveUnitsHorizontalLayout")
        self.waveformUnitsLabel = QLabel(self.layoutWidget)
        self.waveformUnitsLabel.setObjectName(u"waveformUnitsLabel")
        sizePolicy6.setHeightForWidth(self.waveformUnitsLabel.sizePolicy().hasHeightForWidth())
        self.waveformUnitsLabel.setSizePolicy(sizePolicy6)

        self.waveUnitsHorizontalLayout.addWidget(self.waveformUnitsLabel)

        self.unitsLabel = QLabel(self.layoutWidget)
        self.unitsLabel.setObjectName(u"unitsLabel")
        sizePolicy6.setHeightForWidth(self.unitsLabel.sizePolicy().hasHeightForWidth())
        self.unitsLabel.setSizePolicy(sizePolicy6)

        self.waveUnitsHorizontalLayout.addWidget(self.unitsLabel)

        self.waveformUnitsPushButton = QPushButton(self.layoutWidget)
        self.waveformUnitsPushButton.setObjectName(u"waveformUnitsPushButton")
        sizePolicy6.setHeightForWidth(self.waveformUnitsPushButton.sizePolicy().hasHeightForWidth())
        self.waveformUnitsPushButton.setSizePolicy(sizePolicy6)

        self.waveUnitsHorizontalLayout.addWidget(self.waveformUnitsPushButton)


        self.controlsVerticalLayout.addLayout(self.waveUnitsHorizontalLayout)

        self.scrollArea = QScrollArea(self.layoutWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        sizePolicy3.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy3)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 332, 128))
        sizePolicy3.setHeightForWidth(self.scrollAreaWidgetContents.sizePolicy().hasHeightForWidth())
        self.scrollAreaWidgetContents.setSizePolicy(sizePolicy3)
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.fitResultsTextEdit = QPlainTextEdit(self.scrollAreaWidgetContents)
        self.fitResultsTextEdit.setObjectName(u"fitResultsTextEdit")
        sizePolicy3.setHeightForWidth(self.fitResultsTextEdit.sizePolicy().hasHeightForWidth())
        self.fitResultsTextEdit.setSizePolicy(sizePolicy3)
        self.fitResultsTextEdit.setReadOnly(True)

        self.gridLayout_2.addWidget(self.fitResultsTextEdit, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.controlsVerticalLayout.addWidget(self.scrollArea)

        self.controlsSplitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.controlsSplitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.coefficientsTableVerticalLayout = QVBoxLayout(self.layoutWidget1)
        self.coefficientsTableVerticalLayout.setObjectName(u"coefficientsTableVerticalLayout")
        self.coefficientsTableVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.modelCoefficientsTable = TableEditorWidget(self.layoutWidget1)
        self.modelCoefficientsTable.setObjectName(u"modelCoefficientsTable")
        sizePolicy2.setHeightForWidth(self.modelCoefficientsTable.sizePolicy().hasHeightForWidth())
        self.modelCoefficientsTable.setSizePolicy(sizePolicy2)
        self.modelCoefficientsTable.setMinimumSize(QSize(64, 64))

        self.coefficientsTableVerticalLayout.addWidget(self.modelCoefficientsTable)

        self.rowManipulationButtonsLayout = QHBoxLayout()
        self.rowManipulationButtonsLayout.setObjectName(u"rowManipulationButtonsLayout")
        self.addStarredRowsPushButton = QPushButton(self.layoutWidget1)
        self.addStarredRowsPushButton.setObjectName(u"addStarredRowsPushButton")
        sizePolicy.setHeightForWidth(self.addStarredRowsPushButton.sizePolicy().hasHeightForWidth())
        self.addStarredRowsPushButton.setSizePolicy(sizePolicy)
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ListAdd))
        self.addStarredRowsPushButton.setIcon(icon1)
        self.addStarredRowsPushButton.setFlat(True)

        self.rowManipulationButtonsLayout.addWidget(self.addStarredRowsPushButton)

        self.removeStarredRowsPushButton = QPushButton(self.layoutWidget1)
        self.removeStarredRowsPushButton.setObjectName(u"removeStarredRowsPushButton")
        sizePolicy.setHeightForWidth(self.removeStarredRowsPushButton.sizePolicy().hasHeightForWidth())
        self.removeStarredRowsPushButton.setSizePolicy(sizePolicy)
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ListRemove))
        self.removeStarredRowsPushButton.setIcon(icon2)
        self.removeStarredRowsPushButton.setFlat(True)

        self.rowManipulationButtonsLayout.addWidget(self.removeStarredRowsPushButton)


        self.coefficientsTableVerticalLayout.addLayout(self.rowManipulationButtonsLayout)

        self.controlsSplitter.addWidget(self.layoutWidget1)
        self.labelsSplitter.addWidget(self.controlsSplitter)

        self.gridLayout.addWidget(self.labelsSplitter, 1, 0, 1, 1)

        self.waveControlAndDisplayHLayout = QHBoxLayout()
        self.waveControlAndDisplayHLayout.setObjectName(u"waveControlAndDisplayHLayout")
        self.makeUnitAmplitudePushButton = QPushButton(ModelFittingWidget)
        self.makeUnitAmplitudePushButton.setObjectName(u"makeUnitAmplitudePushButton")
        sizePolicy4.setHeightForWidth(self.makeUnitAmplitudePushButton.sizePolicy().hasHeightForWidth())
        self.makeUnitAmplitudePushButton.setSizePolicy(sizePolicy4)
        self.makeUnitAmplitudePushButton.setFlat(True)

        self.waveControlAndDisplayHLayout.addWidget(self.makeUnitAmplitudePushButton)

        self.generateWaveformPushButton = QPushButton(ModelFittingWidget)
        self.generateWaveformPushButton.setObjectName(u"generateWaveformPushButton")
        sizePolicy4.setHeightForWidth(self.generateWaveformPushButton.sizePolicy().hasHeightForWidth())
        self.generateWaveformPushButton.setSizePolicy(sizePolicy4)
        icon3 = QIcon(QIcon.fromTheme(u"waveform"))
        self.generateWaveformPushButton.setIcon(icon3)
        self.generateWaveformPushButton.setFlat(True)

        self.waveControlAndDisplayHLayout.addWidget(self.generateWaveformPushButton)

        self.overlayDataCheckbox = QCheckBox(ModelFittingWidget)
        self.overlayDataCheckbox.setObjectName(u"overlayDataCheckbox")
        sizePolicy4.setHeightForWidth(self.overlayDataCheckbox.sizePolicy().hasHeightForWidth())
        self.overlayDataCheckbox.setSizePolicy(sizePolicy4)
        icon4 = QIcon(QIcon.fromTheme(u"layer-visible-on"))
        self.overlayDataCheckbox.setIcon(icon4)

        self.waveControlAndDisplayHLayout.addWidget(self.overlayDataCheckbox)

        self.fitDataPushButton = QPushButton(ModelFittingWidget)
        self.fitDataPushButton.setObjectName(u"fitDataPushButton")
        sizePolicy4.setHeightForWidth(self.fitDataPushButton.sizePolicy().hasHeightForWidth())
        self.fitDataPushButton.setSizePolicy(sizePolicy4)
        icon5 = QIcon(QIcon.fromTheme(u"labplot-xy-fit-curve"))
        self.fitDataPushButton.setIcon(icon5)
        self.fitDataPushButton.setFlat(True)

        self.waveControlAndDisplayHLayout.addWidget(self.fitDataPushButton)

        self.exportFitResultPushButton = QPushButton(ModelFittingWidget)
        self.exportFitResultPushButton.setObjectName(u"exportFitResultPushButton")
        icon6 = QIcon(QIcon.fromTheme(u"document-export"))
        self.exportFitResultPushButton.setIcon(icon6)
        self.exportFitResultPushButton.setFlat(True)

        self.waveControlAndDisplayHLayout.addWidget(self.exportFitResultPushButton)

        self.channelSpinBox = QSpinBox(ModelFittingWidget)
        self.channelSpinBox.setObjectName(u"channelSpinBox")
        sizePolicy4.setHeightForWidth(self.channelSpinBox.sizePolicy().hasHeightForWidth())
        self.channelSpinBox.setSizePolicy(sizePolicy4)
        self.channelSpinBox.setMaximum(9999)

        self.waveControlAndDisplayHLayout.addWidget(self.channelSpinBox)

        self.pythonHelpPushButton = QPushButton(ModelFittingWidget)
        self.pythonHelpPushButton.setObjectName(u"pythonHelpPushButton")
        sizePolicy4.setHeightForWidth(self.pythonHelpPushButton.sizePolicy().hasHeightForWidth())
        self.pythonHelpPushButton.setSizePolicy(sizePolicy4)
        icon7 = QIcon(QIcon.fromTheme(u"info"))
        self.pythonHelpPushButton.setIcon(icon7)
        self.pythonHelpPushButton.setFlat(True)

        self.waveControlAndDisplayHLayout.addWidget(self.pythonHelpPushButton)

        self.waveControlHSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.waveControlAndDisplayHLayout.addItem(self.waveControlHSpacer)


        self.gridLayout.addLayout(self.waveControlAndDisplayHLayout, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_Duration.setBuddy(self.durationSpinBox)
        self.samplingRateLabel.setBuddy(self.samplingRateSpinBox)
        self.waveformUnitsLabel.setBuddy(self.waveformUnitsPushButton)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ModelFittingWidget)

        QMetaObject.connectSlotsByName(ModelFittingWidget)
    # setupUi

    def retranslateUi(self, ModelFittingWidget):
        ModelFittingWidget.setWindowTitle(QCoreApplication.translate("ModelFittingWidget", u"ModelFittingWidget", None))
#if QT_CONFIG(accessibility)
        ModelFittingWidget.setAccessibleName(QCoreApplication.translate("ModelFittingWidget", u"ModelFittingWidget", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.modelNameLabel.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Model name (may be different from the name of the Python function)", None))
#endif // QT_CONFIG(tooltip)
        self.modelNameLabel.setText("")
#if QT_CONFIG(tooltip)
        self.waveformExpressionPushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Reveal the model's mathematical expression in a separate window", None))
#endif // QT_CONFIG(tooltip)
        self.waveformExpressionPushButton.setText("")
#if QT_CONFIG(tooltip)
        self.svgWidget.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Mathematical expression implemented by the model function", None))
#endif // QT_CONFIG(tooltip)
        self.domainStartLabel.setText(QCoreApplication.translate("ModelFittingWidget", u"Start:", None))
#if QT_CONFIG(tooltip)
        self.label_Duration.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Duration of synthetic mPSC waveform", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_Duration.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Duration of synthetic mPSC waveform", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_Duration.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Duration of synthetic mPSC waveform", None))
#endif // QT_CONFIG(whatsthis)
        self.label_Duration.setText(QCoreApplication.translate("ModelFittingWidget", u"Extent:", None))
#if QT_CONFIG(tooltip)
        self.durationSpinBox.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Duration of the model waveform", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.durationSpinBox.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Duration of synthetic mPSC waveform", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.durationSpinBox.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Duration of synthetic mPSC waveform", None))
#endif // QT_CONFIG(whatsthis)
        self.samplingRateLabel.setText(QCoreApplication.translate("ModelFittingWidget", u"Sampling Rate:", None))
#if QT_CONFIG(tooltip)
        self.samplingRateSpinBox.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Sampling rate used to generate the model waveform", None))
#endif // QT_CONFIG(tooltip)
        self.waveformUnitsLabel.setText(QCoreApplication.translate("ModelFittingWidget", u"Wave Units:", None))
        self.unitsLabel.setText("")
#if QT_CONFIG(tooltip)
        self.waveformUnitsPushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Choose physical units for the model waveform", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.waveformUnitsPushButton.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Choose waveform units", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.waveformUnitsPushButton.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Choose waveform units", None))
#endif // QT_CONFIG(whatsthis)
        self.waveformUnitsPushButton.setText(QCoreApplication.translate("ModelFittingWidget", u"Change", None))
#if QT_CONFIG(tooltip)
        self.fitResultsTextEdit.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Goodness of fit", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.modelCoefficientsTable.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Model coefficient values used for waveform generation and curve fitting", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.modelCoefficientsTable.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Model coefficient values used for waveform generation and curve fitting", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.modelCoefficientsTable.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Model coefficient values used for waveform generation and curve fitting", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.addStarredRowsPushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Add one instance each, of starred coefficients", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.addStarredRowsPushButton.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Add one instance each, of starred coefficients", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.addStarredRowsPushButton.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Add one instance each, of starred coefficients", None))
#endif // QT_CONFIG(whatsthis)
        self.addStarredRowsPushButton.setText(QCoreApplication.translate("ModelFittingWidget", u"Add", None))
#if QT_CONFIG(tooltip)
        self.removeStarredRowsPushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Remove one instance each, of starred coefficients", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.removeStarredRowsPushButton.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Remove one instance each, of starred coefficients", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.removeStarredRowsPushButton.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Remove one instance each, of starred coefficients", None))
#endif // QT_CONFIG(whatsthis)
        self.removeStarredRowsPushButton.setText(QCoreApplication.translate("ModelFittingWidget", u"Remove", None))
#if QT_CONFIG(tooltip)
        self.makeUnitAmplitudePushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Adjust \u03b2 such that the model has unit amplitude", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.makeUnitAmplitudePushButton.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Adjust \u03b2 such that the model has unit amplitude", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.makeUnitAmplitudePushButton.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Adjust \u03b2 such that the model has unit amplitude", None))
#endif // QT_CONFIG(whatsthis)
        self.makeUnitAmplitudePushButton.setText(QCoreApplication.translate("ModelFittingWidget", u"Unit Amplitude", None))
#if QT_CONFIG(tooltip)
        self.generateWaveformPushButton.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Generate the model waveform using the initial coefficient values, duration and sampling rate", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.generateWaveformPushButton.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Generate waveform", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.generateWaveformPushButton.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Generate waveform", None))
#endif // QT_CONFIG(whatsthis)
        self.generateWaveformPushButton.setText("")
#if QT_CONFIG(tooltip)
        self.overlayDataCheckbox.setToolTip(QCoreApplication.translate("ModelFittingWidget", u"Show waveform with data", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.overlayDataCheckbox.setStatusTip(QCoreApplication.translate("ModelFittingWidget", u"Show waveform with data", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.overlayDataCheckbox.setWhatsThis(QCoreApplication.translate("ModelFittingWidget", u"Show waveform with data", None))
#endif // QT_CONFIG(whatsthis)
        self.overlayDataCheckbox.setText("")
        self.fitDataPushButton.setText("")
        self.exportFitResultPushButton.setText("")
        self.pythonHelpPushButton.setText("")
    # retranslateUi

