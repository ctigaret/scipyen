# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'triggerdetect.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

from gui.widgets.small_widgets import QuantitySpinBox

class Ui_TriggerDetectWidget(object):
    def setupUi(self, TriggerDetectWidget):
        if not TriggerDetectWidget.objectName():
            TriggerDetectWidget.setObjectName(u"TriggerDetectWidget")
        TriggerDetectWidget.resize(613, 270)
        self.gridLayout = QGridLayout(TriggerDetectWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.presynGroupBox = QGroupBox(TriggerDetectWidget)
        self.presynGroupBox.setObjectName(u"presynGroupBox")
        self.presynGroupBox.setCheckable(True)
        self.presynGroupBox.setChecked(False)
        self.verticalLayout = QVBoxLayout(self.presynGroupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_4 = QLabel(self.presynGroupBox)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_4.addWidget(self.label_4)

        self.presynChannelSpinBox = QSpinBox(self.presynGroupBox)
        self.presynChannelSpinBox.setObjectName(u"presynChannelSpinBox")

        self.horizontalLayout_4.addWidget(self.presynChannelSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_12 = QLabel(self.presynGroupBox)
        self.label_12.setObjectName(u"label_12")

        self.horizontalLayout_6.addWidget(self.label_12)

        self.presynStartDoubleSpinBox = QuantitySpinBox(self.presynGroupBox)
        self.presynStartDoubleSpinBox.setObjectName(u"presynStartDoubleSpinBox")

        self.horizontalLayout_6.addWidget(self.presynStartDoubleSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_13 = QLabel(self.presynGroupBox)
        self.label_13.setObjectName(u"label_13")

        self.horizontalLayout_7.addWidget(self.label_13)

        self.presynStopDoubleSpinBox = QuantitySpinBox(self.presynGroupBox)
        self.presynStopDoubleSpinBox.setObjectName(u"presynStopDoubleSpinBox")

        self.horizontalLayout_7.addWidget(self.presynStopDoubleSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_8 = QLabel(self.presynGroupBox)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_5.addWidget(self.label_8)

        self.presynNameLineEdit = QLineEdit(self.presynGroupBox)
        self.presynNameLineEdit.setObjectName(u"presynNameLineEdit")
        self.presynNameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout_5.addWidget(self.presynNameLineEdit)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.presynHiLogicCheckBox = QCheckBox(self.presynGroupBox)
        self.presynHiLogicCheckBox.setObjectName(u"presynHiLogicCheckBox")
        self.presynHiLogicCheckBox.setChecked(True)

        self.verticalLayout.addWidget(self.presynHiLogicCheckBox)


        self.horizontalLayout.addWidget(self.presynGroupBox)

        self.postsynGroupBox = QGroupBox(TriggerDetectWidget)
        self.postsynGroupBox.setObjectName(u"postsynGroupBox")
        self.postsynGroupBox.setCheckable(True)
        self.postsynGroupBox.setChecked(False)
        self.verticalLayout_2 = QVBoxLayout(self.postsynGroupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_5 = QLabel(self.postsynGroupBox)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_8.addWidget(self.label_5)

        self.postsynChannelSpinBox = QSpinBox(self.postsynGroupBox)
        self.postsynChannelSpinBox.setObjectName(u"postsynChannelSpinBox")

        self.horizontalLayout_8.addWidget(self.postsynChannelSpinBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_14 = QLabel(self.postsynGroupBox)
        self.label_14.setObjectName(u"label_14")

        self.horizontalLayout_10.addWidget(self.label_14)

        self.postsynStartDoubleSpinBox = QuantitySpinBox(self.postsynGroupBox)
        self.postsynStartDoubleSpinBox.setObjectName(u"postsynStartDoubleSpinBox")

        self.horizontalLayout_10.addWidget(self.postsynStartDoubleSpinBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.label_15 = QLabel(self.postsynGroupBox)
        self.label_15.setObjectName(u"label_15")

        self.horizontalLayout_11.addWidget(self.label_15)

        self.postsynStopDoubleSpinBox = QuantitySpinBox(self.postsynGroupBox)
        self.postsynStopDoubleSpinBox.setObjectName(u"postsynStopDoubleSpinBox")

        self.horizontalLayout_11.addWidget(self.postsynStopDoubleSpinBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_11)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_9 = QLabel(self.postsynGroupBox)
        self.label_9.setObjectName(u"label_9")

        self.horizontalLayout_9.addWidget(self.label_9)

        self.postsynNameLineEdit = QLineEdit(self.postsynGroupBox)
        self.postsynNameLineEdit.setObjectName(u"postsynNameLineEdit")
        self.postsynNameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout_9.addWidget(self.postsynNameLineEdit)


        self.verticalLayout_2.addLayout(self.horizontalLayout_9)

        self.postsynHiLogicCheckBox = QCheckBox(self.postsynGroupBox)
        self.postsynHiLogicCheckBox.setObjectName(u"postsynHiLogicCheckBox")
        self.postsynHiLogicCheckBox.setChecked(True)

        self.verticalLayout_2.addWidget(self.postsynHiLogicCheckBox)


        self.horizontalLayout.addWidget(self.postsynGroupBox)

        self.photoGroupBox = QGroupBox(TriggerDetectWidget)
        self.photoGroupBox.setObjectName(u"photoGroupBox")
        self.photoGroupBox.setCheckable(True)
        self.photoGroupBox.setChecked(False)
        self.verticalLayout_3 = QVBoxLayout(self.photoGroupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.label_6 = QLabel(self.photoGroupBox)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_12.addWidget(self.label_6)

        self.photoChannelSpinBox = QSpinBox(self.photoGroupBox)
        self.photoChannelSpinBox.setObjectName(u"photoChannelSpinBox")

        self.horizontalLayout_12.addWidget(self.photoChannelSpinBox)


        self.verticalLayout_3.addLayout(self.horizontalLayout_12)

        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.label_16 = QLabel(self.photoGroupBox)
        self.label_16.setObjectName(u"label_16")

        self.horizontalLayout_14.addWidget(self.label_16)

        self.photoStartDoubleSpinBox = QuantitySpinBox(self.photoGroupBox)
        self.photoStartDoubleSpinBox.setObjectName(u"photoStartDoubleSpinBox")

        self.horizontalLayout_14.addWidget(self.photoStartDoubleSpinBox)


        self.verticalLayout_3.addLayout(self.horizontalLayout_14)

        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.label_17 = QLabel(self.photoGroupBox)
        self.label_17.setObjectName(u"label_17")

        self.horizontalLayout_15.addWidget(self.label_17)

        self.photoStopDoubleSpinBox = QuantitySpinBox(self.photoGroupBox)
        self.photoStopDoubleSpinBox.setObjectName(u"photoStopDoubleSpinBox")

        self.horizontalLayout_15.addWidget(self.photoStopDoubleSpinBox)


        self.verticalLayout_3.addLayout(self.horizontalLayout_15)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.label_10 = QLabel(self.photoGroupBox)
        self.label_10.setObjectName(u"label_10")

        self.horizontalLayout_13.addWidget(self.label_10)

        self.photoNameLineEdit = QLineEdit(self.photoGroupBox)
        self.photoNameLineEdit.setObjectName(u"photoNameLineEdit")
        self.photoNameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout_13.addWidget(self.photoNameLineEdit)


        self.verticalLayout_3.addLayout(self.horizontalLayout_13)

        self.photoStimHiLogicCheckBox = QCheckBox(self.photoGroupBox)
        self.photoStimHiLogicCheckBox.setObjectName(u"photoStimHiLogicCheckBox")
        self.photoStimHiLogicCheckBox.setChecked(True)

        self.verticalLayout_3.addWidget(self.photoStimHiLogicCheckBox)


        self.horizontalLayout.addWidget(self.photoGroupBox)

        self.imagingGroupBox = QGroupBox(TriggerDetectWidget)
        self.imagingGroupBox.setObjectName(u"imagingGroupBox")
        self.imagingGroupBox.setCheckable(True)
        self.imagingGroupBox.setChecked(False)
        self.verticalLayout_4 = QVBoxLayout(self.imagingGroupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.label_7 = QLabel(self.imagingGroupBox)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_16.addWidget(self.label_7)

        self.imagingChannelSpinBox = QSpinBox(self.imagingGroupBox)
        self.imagingChannelSpinBox.setObjectName(u"imagingChannelSpinBox")

        self.horizontalLayout_16.addWidget(self.imagingChannelSpinBox)


        self.verticalLayout_4.addLayout(self.horizontalLayout_16)

        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.label_18 = QLabel(self.imagingGroupBox)
        self.label_18.setObjectName(u"label_18")

        self.horizontalLayout_18.addWidget(self.label_18)

        self.imagingStartDoubleSpinBox = QuantitySpinBox(self.imagingGroupBox)
        self.imagingStartDoubleSpinBox.setObjectName(u"imagingStartDoubleSpinBox")

        self.horizontalLayout_18.addWidget(self.imagingStartDoubleSpinBox)


        self.verticalLayout_4.addLayout(self.horizontalLayout_18)

        self.horizontalLayout_19 = QHBoxLayout()
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.label_19 = QLabel(self.imagingGroupBox)
        self.label_19.setObjectName(u"label_19")

        self.horizontalLayout_19.addWidget(self.label_19)

        self.imagingStopDoubleSpinBox = QuantitySpinBox(self.imagingGroupBox)
        self.imagingStopDoubleSpinBox.setObjectName(u"imagingStopDoubleSpinBox")

        self.horizontalLayout_19.addWidget(self.imagingStopDoubleSpinBox)


        self.verticalLayout_4.addLayout(self.horizontalLayout_19)

        self.horizontalLayout_17 = QHBoxLayout()
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.label_11 = QLabel(self.imagingGroupBox)
        self.label_11.setObjectName(u"label_11")

        self.horizontalLayout_17.addWidget(self.label_11)

        self.imagingNameLineEdit = QLineEdit(self.imagingGroupBox)
        self.imagingNameLineEdit.setObjectName(u"imagingNameLineEdit")
        self.imagingNameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout_17.addWidget(self.imagingNameLineEdit)


        self.verticalLayout_4.addLayout(self.horizontalLayout_17)

        self.imagingHiLogicCheckBox = QCheckBox(self.imagingGroupBox)
        self.imagingHiLogicCheckBox.setObjectName(u"imagingHiLogicCheckBox")
        self.imagingHiLogicCheckBox.setChecked(True)

        self.verticalLayout_4.addWidget(self.imagingHiLogicCheckBox)


        self.horizontalLayout.addWidget(self.imagingGroupBox)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.reltimesCheckBox = QCheckBox(TriggerDetectWidget)
        self.reltimesCheckBox.setObjectName(u"reltimesCheckBox")
        self.reltimesCheckBox.setChecked(True)

        self.horizontalLayout_2.addWidget(self.reltimesCheckBox)

        self.allSegmentsCheckBox = QCheckBox(TriggerDetectWidget)
        self.allSegmentsCheckBox.setObjectName(u"allSegmentsCheckBox")

        self.horizontalLayout_2.addWidget(self.allSegmentsCheckBox)

        self.detectPushButton = QPushButton(TriggerDetectWidget)
        self.detectPushButton.setObjectName(u"detectPushButton")
        icon = QIcon(QIcon.fromTheme(u"edit-find"))
        self.detectPushButton.setIcon(icon)
        self.detectPushButton.setFlat(True)

        self.horizontalLayout_2.addWidget(self.detectPushButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_4.setBuddy(self.presynChannelSpinBox)
        self.label_12.setBuddy(self.presynStartDoubleSpinBox)
        self.label_13.setBuddy(self.presynStopDoubleSpinBox)
        self.label_8.setBuddy(self.presynNameLineEdit)
        self.label_5.setBuddy(self.postsynChannelSpinBox)
        self.label_14.setBuddy(self.postsynStartDoubleSpinBox)
        self.label_15.setBuddy(self.postsynStopDoubleSpinBox)
        self.label_9.setBuddy(self.postsynNameLineEdit)
        self.label_6.setBuddy(self.photoChannelSpinBox)
        self.label_16.setBuddy(self.photoStartDoubleSpinBox)
        self.label_17.setBuddy(self.photoStopDoubleSpinBox)
        self.label_10.setBuddy(self.photoNameLineEdit)
        self.label_7.setBuddy(self.imagingChannelSpinBox)
        self.label_18.setBuddy(self.imagingStartDoubleSpinBox)
        self.label_19.setBuddy(self.imagingStopDoubleSpinBox)
        self.label_11.setBuddy(self.imagingNameLineEdit)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.presynGroupBox, self.presynChannelSpinBox)
        QWidget.setTabOrder(self.presynChannelSpinBox, self.presynStartDoubleSpinBox)
        QWidget.setTabOrder(self.presynStartDoubleSpinBox, self.presynStopDoubleSpinBox)
        QWidget.setTabOrder(self.presynStopDoubleSpinBox, self.presynNameLineEdit)
        QWidget.setTabOrder(self.presynNameLineEdit, self.postsynGroupBox)
        QWidget.setTabOrder(self.postsynGroupBox, self.postsynChannelSpinBox)
        QWidget.setTabOrder(self.postsynChannelSpinBox, self.postsynStartDoubleSpinBox)
        QWidget.setTabOrder(self.postsynStartDoubleSpinBox, self.postsynStopDoubleSpinBox)
        QWidget.setTabOrder(self.postsynStopDoubleSpinBox, self.postsynNameLineEdit)
        QWidget.setTabOrder(self.postsynNameLineEdit, self.photoGroupBox)
        QWidget.setTabOrder(self.photoGroupBox, self.photoChannelSpinBox)
        QWidget.setTabOrder(self.photoChannelSpinBox, self.photoStartDoubleSpinBox)
        QWidget.setTabOrder(self.photoStartDoubleSpinBox, self.photoStopDoubleSpinBox)
        QWidget.setTabOrder(self.photoStopDoubleSpinBox, self.photoNameLineEdit)
        QWidget.setTabOrder(self.photoNameLineEdit, self.imagingGroupBox)
        QWidget.setTabOrder(self.imagingGroupBox, self.imagingChannelSpinBox)
        QWidget.setTabOrder(self.imagingChannelSpinBox, self.imagingStartDoubleSpinBox)
        QWidget.setTabOrder(self.imagingStartDoubleSpinBox, self.imagingStopDoubleSpinBox)
        QWidget.setTabOrder(self.imagingStopDoubleSpinBox, self.imagingNameLineEdit)

        self.retranslateUi(TriggerDetectWidget)

        QMetaObject.connectSlotsByName(TriggerDetectWidget)
    # setupUi

    def retranslateUi(self, TriggerDetectWidget):
        TriggerDetectWidget.setWindowTitle(QCoreApplication.translate("TriggerDetectWidget", u"TriggerDetectWidget", None))
#if QT_CONFIG(tooltip)
        TriggerDetectWidget.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Trigger Detection Widget", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        TriggerDetectWidget.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Trigger Detection Widget", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        TriggerDetectWidget.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"Trigger Detection Widget", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.presynGroupBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Triggers for presynaptic simulation", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.presynGroupBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Triggers for presynaptic simulation", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.presynGroupBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>Triggers for presynaptic simulation via simulation (extracellular) electrodes.</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.presynGroupBox.setTitle(QCoreApplication.translate("TriggerDetectWidget", u"Pres&ynaptic", None))
        self.label_4.setText(QCoreApplication.translate("TriggerDetectWidget", u"Channel:", None))
        self.label_12.setText(QCoreApplication.translate("TriggerDetectWidget", u"Start:", None))
        self.presynStartDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_13.setText(QCoreApplication.translate("TriggerDetectWidget", u"Stop:", None))
        self.presynStopDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_8.setText(QCoreApplication.translate("TriggerDetectWidget", u"Name:", None))
        self.presynNameLineEdit.setText(QCoreApplication.translate("TriggerDetectWidget", u"pre", None))
#if QT_CONFIG(tooltip)
        self.presynHiLogicCheckBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Use high logic", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.presynHiLogicCheckBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Direction of TTL-like waveforms", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.presynHiLogicCheckBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>When checked, TTL-like waveforms are expected to follow an &quot;up&quot; logic, </p><p>(i.e., they are low-to-high, or upwards deflections).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.presynHiLogicCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"High Logic", None))
#if QT_CONFIG(tooltip)
        self.postsynGroupBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Triggers for postsynaptic stimulation", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.postsynGroupBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Triggers for postsynaptic stimulation", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.postsynGroupBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>Triggers for postsynaptic stimulation (e.g. current injection via patch electrode, or antidromic stimulation with extracellular electrodes).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.postsynGroupBox.setTitle(QCoreApplication.translate("TriggerDetectWidget", u"Pos&tynaptic", None))
        self.label_5.setText(QCoreApplication.translate("TriggerDetectWidget", u"Channel:", None))
        self.label_14.setText(QCoreApplication.translate("TriggerDetectWidget", u"Start:", None))
        self.postsynStartDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_15.setText(QCoreApplication.translate("TriggerDetectWidget", u"Stop:", None))
        self.postsynStopDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_9.setText(QCoreApplication.translate("TriggerDetectWidget", u"Name:", None))
        self.postsynNameLineEdit.setText(QCoreApplication.translate("TriggerDetectWidget", u"post", None))
#if QT_CONFIG(tooltip)
        self.postsynHiLogicCheckBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Use high logic", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.postsynHiLogicCheckBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Direction of TTL-like waveforms", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.postsynHiLogicCheckBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>When checked, TTL-like waveforms are expected to follow an &quot;up&quot; logic, </p><p>(i.e., they are low-to-high, or upwards deflections).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.postsynHiLogicCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"High Logic", None))
#if QT_CONFIG(tooltip)
        self.photoGroupBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Trigger for light pulses", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.photoGroupBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Trigger for light pulses", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.photoGroupBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>Trigger for light pulses (e.g. uncaging pulses, light-sensitive in channels, pohotoconversion of fluorescent proteins, etc.).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.photoGroupBox.setTitle(QCoreApplication.translate("TriggerDetectWidget", u"Photostim&ulation", None))
        self.label_6.setText(QCoreApplication.translate("TriggerDetectWidget", u"Channel:", None))
        self.label_16.setText(QCoreApplication.translate("TriggerDetectWidget", u"Start:", None))
        self.photoStartDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_17.setText(QCoreApplication.translate("TriggerDetectWidget", u"Stop:", None))
        self.photoStopDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_10.setText(QCoreApplication.translate("TriggerDetectWidget", u"Name:", None))
        self.photoNameLineEdit.setText(QCoreApplication.translate("TriggerDetectWidget", u"photo", None))
#if QT_CONFIG(tooltip)
        self.photoStimHiLogicCheckBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Use high logic", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.photoStimHiLogicCheckBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Direction of TTL-like waveforms", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.photoStimHiLogicCheckBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>When checked, TTL-like waveforms are expected to follow an &quot;up&quot; logic, </p><p>(i.e., they are low-to-high, or upwards deflections).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.photoStimHiLogicCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"High Logic", None))
#if QT_CONFIG(tooltip)
        self.imagingGroupBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Imaging frame trigger", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.imagingGroupBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Imaging frame trigger", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.imagingGroupBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>Trigger that initiates one frame of laser scan imaging (not to be confused with a line imaging trigger, which synchronizes the initiation of a single scanning line).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.imagingGroupBox.setTitle(QCoreApplication.translate("TriggerDetectWidget", u"Ima&ging frame", None))
        self.label_7.setText(QCoreApplication.translate("TriggerDetectWidget", u"Channel:", None))
        self.label_18.setText(QCoreApplication.translate("TriggerDetectWidget", u"Start:", None))
        self.imagingStartDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_19.setText(QCoreApplication.translate("TriggerDetectWidget", u"Stop:", None))
        self.imagingStopDoubleSpinBox.setSuffix(QCoreApplication.translate("TriggerDetectWidget", u" s", None))
        self.label_11.setText(QCoreApplication.translate("TriggerDetectWidget", u"Name:", None))
        self.imagingNameLineEdit.setText(QCoreApplication.translate("TriggerDetectWidget", u"frame", None))
#if QT_CONFIG(tooltip)
        self.imagingHiLogicCheckBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Use high logic", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.imagingHiLogicCheckBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Direction of TTL-like waveforms", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.imagingHiLogicCheckBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"<html><head/><body><p>When checked, TTL-like waveforms are expected to follow an &quot;up&quot; logic, </p><p>(i.e., they are low-to-high, or upwards deflections).</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.imagingHiLogicCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"High Logic", None))
#if QT_CONFIG(tooltip)
        self.reltimesCheckBox.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"When checked, start/stop search times are relative to the signal start", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.reltimesCheckBox.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"When checked, start/stop search times are relative to the signal start", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.reltimesCheckBox.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"When checked, start/stop search times are relative to the signal start", None))
#endif // QT_CONFIG(whatsthis)
        self.reltimesCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"Relative", None))
        self.allSegmentsCheckBox.setText(QCoreApplication.translate("TriggerDetectWidget", u"All segments", None))
#if QT_CONFIG(tooltip)
        self.detectPushButton.setToolTip(QCoreApplication.translate("TriggerDetectWidget", u"Detect events from trigger signals", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.detectPushButton.setStatusTip(QCoreApplication.translate("TriggerDetectWidget", u"Detect events from trigger signals", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.detectPushButton.setWhatsThis(QCoreApplication.translate("TriggerDetectWidget", u"Detect events from trigger signals", None))
#endif // QT_CONFIG(whatsthis)
        self.detectPushButton.setText(QCoreApplication.translate("TriggerDetectWidget", u"Detect", None))
    # retranslateUi

