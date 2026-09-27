# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'axescalibrationdialog2.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QRadioButton, QSizePolicy, QSpinBox, QTabWidget,
    QWidget)

from gui.widgets.small_widgets import QuantityChooserWidget

class Ui_AxesCalibrationDialog(object):
    def setupUi(self, AxesCalibrationDialog):
        if not AxesCalibrationDialog.objectName():
            AxesCalibrationDialog.setObjectName(u"AxesCalibrationDialog")
        AxesCalibrationDialog.setWindowModality(Qt.WindowModality.WindowModal)
        AxesCalibrationDialog.resize(401, 505)
        AxesCalibrationDialog.setModal(True)
        self.gridLayout_4 = QGridLayout(AxesCalibrationDialog)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.buttonBox = QDialogButtonBox(AxesCalibrationDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout_4.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.tabWidget = QTabWidget(AxesCalibrationDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidgetPage1 = QWidget()
        self.tabWidgetPage1.setObjectName(u"tabWidgetPage1")
        self.gridLayout_3 = QGridLayout(self.tabWidgetPage1)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.tabWidgetPage1)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QSize(20, 0))

        self.horizontalLayout.addWidget(self.label)

        self.axisIndexSpinBox = QSpinBox(self.tabWidgetPage1)
        self.axisIndexSpinBox.setObjectName(u"axisIndexSpinBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.axisIndexSpinBox.sizePolicy().hasHeightForWidth())
        self.axisIndexSpinBox.setSizePolicy(sizePolicy1)
        self.axisIndexSpinBox.setMinimumSize(QSize(20, 0))

        self.horizontalLayout.addWidget(self.axisIndexSpinBox)

        self.axisInfoLabel = QLabel(self.tabWidgetPage1)
        self.axisInfoLabel.setObjectName(u"axisInfoLabel")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(4)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.axisInfoLabel.sizePolicy().hasHeightForWidth())
        self.axisInfoLabel.setSizePolicy(sizePolicy2)
        self.axisInfoLabel.setFrameShape(QFrame.Shape.StyledPanel)
        self.axisInfoLabel.setFrameShadow(QFrame.Shadow.Sunken)
        self.axisInfoLabel.setMidLineWidth(1)
        self.axisInfoLabel.setScaledContents(True)
        self.axisInfoLabel.setWordWrap(True)
        self.axisInfoLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.horizontalLayout.addWidget(self.axisInfoLabel)


        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.axisCalibrationGroupBox = QGroupBox(self.tabWidgetPage1)
        self.axisCalibrationGroupBox.setObjectName(u"axisCalibrationGroupBox")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.axisCalibrationGroupBox.sizePolicy().hasHeightForWidth())
        self.axisCalibrationGroupBox.setSizePolicy(sizePolicy3)
        self.gridLayout_2 = QGridLayout(self.axisCalibrationGroupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_5 = QLabel(self.axisCalibrationGroupBox)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_2.addWidget(self.label_5, 0, 0, 1, 1)

        self.axisUnitSelectionWidget = QuantityChooserWidget(self.axisCalibrationGroupBox)
        self.axisUnitSelectionWidget.setObjectName(u"axisUnitSelectionWidget")

        self.gridLayout_2.addWidget(self.axisUnitSelectionWidget, 0, 1, 1, 1)

        self.label_2 = QLabel(self.axisCalibrationGroupBox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.axisOriginSpinBox = QDoubleSpinBox(self.axisCalibrationGroupBox)
        self.axisOriginSpinBox.setObjectName(u"axisOriginSpinBox")
        self.axisOriginSpinBox.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.axisOriginSpinBox, 1, 1, 1, 1)

        self.label_8 = QLabel(self.axisCalibrationGroupBox)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_2.addWidget(self.label_8, 2, 0, 1, 1)

        self.lineEdit_2 = QLineEdit(self.axisCalibrationGroupBox)
        self.lineEdit_2.setObjectName(u"lineEdit_2")

        self.gridLayout_2.addWidget(self.lineEdit_2, 2, 1, 1, 1)

        self.groupBox = QGroupBox(self.axisCalibrationGroupBox)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.axisResolutionRadioButton = QRadioButton(self.groupBox)
        self.axisResolutionRadioButton.setObjectName(u"axisResolutionRadioButton")
        self.axisResolutionRadioButton.setChecked(True)

        self.gridLayout.addWidget(self.axisResolutionRadioButton, 0, 0, 1, 1)

        self.axisResolutionSpinBox = QDoubleSpinBox(self.groupBox)
        self.axisResolutionSpinBox.setObjectName(u"axisResolutionSpinBox")
        self.axisResolutionSpinBox.setEnabled(True)
        self.axisResolutionSpinBox.setReadOnly(False)
        self.axisResolutionSpinBox.setDecimals(4)
        self.axisResolutionSpinBox.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.axisResolutionSpinBox, 0, 1, 1, 1)

        self.axisSampleDistanceRadioButton = QRadioButton(self.groupBox)
        self.axisSampleDistanceRadioButton.setObjectName(u"axisSampleDistanceRadioButton")

        self.gridLayout.addWidget(self.axisSampleDistanceRadioButton, 1, 0, 1, 1)

        self.axisSampleDistanceSpinBox = QSpinBox(self.groupBox)
        self.axisSampleDistanceSpinBox.setObjectName(u"axisSampleDistanceSpinBox")
        self.axisSampleDistanceSpinBox.setMaximum(1000000000)

        self.gridLayout.addWidget(self.axisSampleDistanceSpinBox, 1, 1, 1, 1)

        self.axisCalibratedDistanceRadioButton = QRadioButton(self.groupBox)
        self.axisCalibratedDistanceRadioButton.setObjectName(u"axisCalibratedDistanceRadioButton")

        self.gridLayout.addWidget(self.axisCalibratedDistanceRadioButton, 2, 0, 1, 1)

        self.axisCalibratedDistanceSpinBox = QDoubleSpinBox(self.groupBox)
        self.axisCalibratedDistanceSpinBox.setObjectName(u"axisCalibratedDistanceSpinBox")
        self.axisCalibratedDistanceSpinBox.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.axisCalibratedDistanceSpinBox, 2, 1, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 3, 0, 1, 2)


        self.gridLayout_3.addWidget(self.axisCalibrationGroupBox, 1, 0, 1, 1)

        self.axisDescriptionEdit = QPlainTextEdit(self.tabWidgetPage1)
        self.axisDescriptionEdit.setObjectName(u"axisDescriptionEdit")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(1)
        sizePolicy4.setHeightForWidth(self.axisDescriptionEdit.sizePolicy().hasHeightForWidth())
        self.axisDescriptionEdit.setSizePolicy(sizePolicy4)

        self.gridLayout_3.addWidget(self.axisDescriptionEdit, 2, 0, 1, 1)

        self.tabWidget.addTab(self.tabWidgetPage1, "")
        self.tabWidgetPage2 = QWidget()
        self.tabWidgetPage2.setObjectName(u"tabWidgetPage2")
        self.gridLayout_6 = QGridLayout(self.tabWidgetPage2)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_3 = QLabel(self.tabWidgetPage2)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.label_3)

        self.channelIndexSpinBox = QSpinBox(self.tabWidgetPage2)
        self.channelIndexSpinBox.setObjectName(u"channelIndexSpinBox")
        sizePolicy1.setHeightForWidth(self.channelIndexSpinBox.sizePolicy().hasHeightForWidth())
        self.channelIndexSpinBox.setSizePolicy(sizePolicy1)
        self.channelIndexSpinBox.setMinimumSize(QSize(20, 0))

        self.horizontalLayout_2.addWidget(self.channelIndexSpinBox)

        self.channelInfoLabel = QLabel(self.tabWidgetPage2)
        self.channelInfoLabel.setObjectName(u"channelInfoLabel")
        sizePolicy2.setHeightForWidth(self.channelInfoLabel.sizePolicy().hasHeightForWidth())
        self.channelInfoLabel.setSizePolicy(sizePolicy2)
        self.channelInfoLabel.setFrameShape(QFrame.Shape.StyledPanel)
        self.channelInfoLabel.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.channelInfoLabel)


        self.gridLayout_6.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)

        self.channelCalibrationGroupBox = QGroupBox(self.tabWidgetPage2)
        self.channelCalibrationGroupBox.setObjectName(u"channelCalibrationGroupBox")
        sizePolicy3.setHeightForWidth(self.channelCalibrationGroupBox.sizePolicy().hasHeightForWidth())
        self.channelCalibrationGroupBox.setSizePolicy(sizePolicy3)
        self.gridLayout_5 = QGridLayout(self.channelCalibrationGroupBox)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.label_6 = QLabel(self.channelCalibrationGroupBox)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_5.addWidget(self.label_6, 0, 0, 1, 1)

        self.channelUnitSelectionWidget = QuantityChooserWidget(self.channelCalibrationGroupBox)
        self.channelUnitSelectionWidget.setObjectName(u"channelUnitSelectionWidget")

        self.gridLayout_5.addWidget(self.channelUnitSelectionWidget, 0, 1, 1, 1)

        self.label_7 = QLabel(self.channelCalibrationGroupBox)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_5.addWidget(self.label_7, 1, 0, 1, 1)

        self.channelMinimumDoubleSpinBox = QDoubleSpinBox(self.channelCalibrationGroupBox)
        self.channelMinimumDoubleSpinBox.setObjectName(u"channelMinimumDoubleSpinBox")

        self.gridLayout_5.addWidget(self.channelMinimumDoubleSpinBox, 1, 1, 1, 1)

        self.label_9 = QLabel(self.channelCalibrationGroupBox)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout_5.addWidget(self.label_9, 2, 0, 1, 1)

        self.channelMaximumDoubleSpinBox = QDoubleSpinBox(self.channelCalibrationGroupBox)
        self.channelMaximumDoubleSpinBox.setObjectName(u"channelMaximumDoubleSpinBox")

        self.gridLayout_5.addWidget(self.channelMaximumDoubleSpinBox, 2, 1, 1, 1)

        self.channelCalibrationFunctionTextEdit = QPlainTextEdit(self.channelCalibrationGroupBox)
        self.channelCalibrationFunctionTextEdit.setObjectName(u"channelCalibrationFunctionTextEdit")

        self.gridLayout_5.addWidget(self.channelCalibrationFunctionTextEdit, 3, 0, 1, 2)

        self.label_4 = QLabel(self.channelCalibrationGroupBox)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_5.addWidget(self.label_4, 4, 0, 1, 1)

        self.lineEdit = QLineEdit(self.channelCalibrationGroupBox)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout_5.addWidget(self.lineEdit, 4, 1, 1, 1)


        self.gridLayout_6.addWidget(self.channelCalibrationGroupBox, 1, 0, 1, 1)

        self.channelDescriptionEdit = QPlainTextEdit(self.tabWidgetPage2)
        self.channelDescriptionEdit.setObjectName(u"channelDescriptionEdit")
        sizePolicy4.setHeightForWidth(self.channelDescriptionEdit.sizePolicy().hasHeightForWidth())
        self.channelDescriptionEdit.setSizePolicy(sizePolicy4)

        self.gridLayout_6.addWidget(self.channelDescriptionEdit, 2, 0, 1, 1)

        self.tabWidget.addTab(self.tabWidgetPage2, "")

        self.gridLayout_4.addWidget(self.tabWidget, 0, 0, 1, 1)


        self.retranslateUi(AxesCalibrationDialog)
        self.buttonBox.accepted.connect(AxesCalibrationDialog.accept)
        self.buttonBox.rejected.connect(AxesCalibrationDialog.reject)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(AxesCalibrationDialog)
    # setupUi

    def retranslateUi(self, AxesCalibrationDialog):
        AxesCalibrationDialog.setWindowTitle(QCoreApplication.translate("AxesCalibrationDialog", u"Axes Calibration", None))
        self.label.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Axis:", None))
#if QT_CONFIG(tooltip)
        self.axisIndexSpinBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select axis index", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisIndexSpinBox.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select axis index", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisIndexSpinBox.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"<html><head/><body><p>Select the axis to calibrate, given the index of the axis. </p><p><a href=\"https://numpy.org/doc/stable/index.html\"><span style=\" text-decoration: underline; color:#72b925;\">Numpy arrays</span></a> associate a Cartesian system of axes, which are indexed starting with 0. <span style=\" font-style:italic;\">1D arrays have a single axis</span>. </p><p>For generic numpy arrays with at least two dimensions, the first axis (axis 0) is the vertical axis: iterating along its dimension points to an array &quot;row&quot;. </p><p><br/></p><p>The <a href=\"https://ukoethe.github.io/vigra/\"><span style=\" font-weight:600; text-decoration: underline; color:#72b925;\">Vigra</span></a> library introduces the VigraArray, an enhanced form of numpy arrays where each axis has defined semantic (e.g. , space, time, etc) encapsulated in the concept of AxisTags. It is often useful to attach a physical dimension to such axes (units of measure for distance, time, etc). </p><p><br/></p><p>A VigraArray can have"
                        " an additional axis representing the &quot;channel&quot; axis. This is useful particularly for multi-band, or multi-channel, images. In single-band images the channel axis, when present, has size 1 (a &quot;singleton&quot; axis). It makes sense to attach units of measure to this axis, too, thus giving a physical meaning to the channel data, when appropriate.</p><p><br/></p><p>Raster image data represented by classes in the <a href=\"https://www.qt.io/\"><span style=\" font-weight:600; text-decoration: underline; color:#72b925;\">Qt framework</span></a> (QImage, QPixmap) by definition have only two axes corresponding to the Cartesian system of the image. </p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.axisInfoLabel.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis length (samples)", None))
#endif // QT_CONFIG(tooltip)
        self.axisInfoLabel.setText("")
#if QT_CONFIG(tooltip)
        self.axisCalibrationGroupBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrate axis. Selected parameter below will be calculated based on the value of the other two", None))
#endif // QT_CONFIG(tooltip)
        self.axisCalibrationGroupBox.setTitle(QCoreApplication.translate("AxesCalibrationDialog", u"Axis Calibration", None))
#if QT_CONFIG(tooltip)
        self.label_5.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_5.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_5.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(whatsthis)
        self.label_5.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Axis units:", None))
        self.label_2.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Axis origin:", None))
#if QT_CONFIG(tooltip)
        self.axisOriginSpinBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis origin in physical units", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisOriginSpinBox.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis origin in physical units", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisOriginSpinBox.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Axis origin in physical units", None))
#endif // QT_CONFIG(whatsthis)
        self.label_8.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Axis name:", None))
#if QT_CONFIG(tooltip)
        self.groupBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Selected parameter to calculate using the values of other two parameters.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.groupBox.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Selected parameter to calculate using the values of other two parameters.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.groupBox.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Selected parameter to calculate using the values of other two parameters.", None))
#endif // QT_CONFIG(whatsthis)
        self.groupBox.setTitle(QCoreApplication.translate("AxesCalibrationDialog", u"Calculate", None))
#if QT_CONFIG(tooltip)
        self.axisResolutionRadioButton.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Resolution (units / pixel)\n"
"Select this to calculate it using Distance in pixels and Calibrated length.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisResolutionRadioButton.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis resolution (size of one pixel in calibrated units)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisResolutionRadioButton.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Axis resolution (size of one pixel in calibrated units)", None))
#endif // QT_CONFIG(whatsthis)
        self.axisResolutionRadioButton.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Resolu&tion", None))
#if QT_CONFIG(tooltip)
        self.axisResolutionSpinBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis resolution (size of one pixel in calibrated units)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisResolutionSpinBox.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis resolution (size of one pixel in calibrated units)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisResolutionSpinBox.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Axis resolution (size of one pixel in calibrated units)", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.axisSampleDistanceRadioButton.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in samples, along the selected axis.\n"
"Select this to calculate it based on Resolution and Calibrated distance", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisSampleDistanceRadioButton.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in samples, along the selected axis.\\nSelect this to calculate it based on Resolution and Calibrated distance", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisSampleDistanceRadioButton.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in samples, along the selected axis.\n"
"Select this to calculate it based on Resolution and Calibrated distance", None))
#endif // QT_CONFIG(whatsthis)
        self.axisSampleDistanceRadioButton.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in samples", None))
#if QT_CONFIG(tooltip)
        self.axisSampleDistanceSpinBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in pixels along the selected axis", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisSampleDistanceSpinBox.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in pixels along the selected ax", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisSampleDistanceSpinBox.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in pixels along the selected ax", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.axisCalibratedDistanceRadioButton.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrated distance in physical units.\n"
"Select this to calculate it based on Resolution and Distance in pixels", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.axisCalibratedDistanceRadioButton.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrated distance in physical units.\\nSelect this to calculate it based on Resolution and Distance in pixels", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.axisCalibratedDistanceRadioButton.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrated distance in physical units.\n"
"Select this to calculate it based on Resolution and Distance in pixels", None))
#endif // QT_CONFIG(whatsthis)
        self.axisCalibratedDistanceRadioButton.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrated distance", None))
#if QT_CONFIG(tooltip)
        self.axisCalibratedDistanceSpinBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Distance in calibrated units", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.axisDescriptionEdit.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Axis description", None))
#endif // QT_CONFIG(tooltip)
        self.axisDescriptionEdit.setPlaceholderText(QCoreApplication.translate("AxesCalibrationDialog", u"Axis description", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabWidgetPage1), QCoreApplication.translate("AxesCalibrationDialog", u"Axis", None))
        self.label_3.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Channel:", None))
        self.channelInfoLabel.setText("")
#if QT_CONFIG(tooltip)
        self.channelCalibrationGroupBox.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Calibrate axis. Selected parameter below will be calculated based on the value of the other two", None))
#endif // QT_CONFIG(tooltip)
        self.channelCalibrationGroupBox.setTitle(QCoreApplication.translate("AxesCalibrationDialog", u"Channel Calibration", None))
#if QT_CONFIG(tooltip)
        self.label_6.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_6.setStatusTip(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_6.setWhatsThis(QCoreApplication.translate("AxesCalibrationDialog", u"Select a physical unit", None))
#endif // QT_CONFIG(whatsthis)
        self.label_6.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Units:", None))
        self.label_7.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Minimum:", None))
        self.label_9.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Maximum:", None))
        self.channelCalibrationFunctionTextEdit.setPlaceholderText(QCoreApplication.translate("AxesCalibrationDialog", u"Channel calibration expression e.g. 2.3 * pq.micromolar * x / dF/F_max, where dF/F_max is a numeric dimensionless constant", None))
        self.label_4.setText(QCoreApplication.translate("AxesCalibrationDialog", u"Name:", None))
#if QT_CONFIG(tooltip)
        self.channelDescriptionEdit.setToolTip(QCoreApplication.translate("AxesCalibrationDialog", u"Channel description", None))
#endif // QT_CONFIG(tooltip)
        self.channelDescriptionEdit.setPlaceholderText(QCoreApplication.translate("AxesCalibrationDialog", u"Channel description", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabWidgetPage2), QCoreApplication.translate("AxesCalibrationDialog", u"Channels", None))
    # retranslateUi

