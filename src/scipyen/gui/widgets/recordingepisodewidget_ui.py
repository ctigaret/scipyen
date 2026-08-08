# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'recordingepisodewidget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDateTimeEdit, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QToolButton, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_RecordingEpisodeWidget(object):
    def setupUi(self, RecordingEpisodeWidget):
        if not RecordingEpisodeWidget.objectName():
            RecordingEpisodeWidget.setObjectName(u"RecordingEpisodeWidget")
        RecordingEpisodeWidget.resize(329, 246)
        self.gridLayout_2 = QGridLayout(RecordingEpisodeWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(RecordingEpisodeWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.protocolNameLabel = QLabel(RecordingEpisodeWidget)
        self.protocolNameLabel.setObjectName(u"protocolNameLabel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.protocolNameLabel.sizePolicy().hasHeightForWidth())
        self.protocolNameLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.protocolNameLabel)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.previewProtocolToolButton = QToolButton(RecordingEpisodeWidget)
        self.previewProtocolToolButton.setObjectName(u"previewProtocolToolButton")
        icon = QIcon(QIcon.fromTheme(u"view-list-tree"))
        self.previewProtocolToolButton.setIcon(icon)
        self.previewProtocolToolButton.setCheckable(False)
        self.previewProtocolToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.previewProtocolToolButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)

        self.nameDescriptionWidget = NameDescriptionWidget(RecordingEpisodeWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout_2.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.episodeBoundariesGridLayout = QGridLayout()
        self.episodeBoundariesGridLayout.setObjectName(u"episodeBoundariesGridLayout")
        self.label_4 = QLabel(RecordingEpisodeWidget)
        self.label_4.setObjectName(u"label_4")

        self.episodeBoundariesGridLayout.addWidget(self.label_4, 0, 0, 1, 1)

        self.episodeBeginDateTimeEdit = QDateTimeEdit(RecordingEpisodeWidget)
        self.episodeBeginDateTimeEdit.setObjectName(u"episodeBeginDateTimeEdit")

        self.episodeBoundariesGridLayout.addWidget(self.episodeBeginDateTimeEdit, 0, 1, 1, 1)

        self.label_6 = QLabel(RecordingEpisodeWidget)
        self.label_6.setObjectName(u"label_6")

        self.episodeBoundariesGridLayout.addWidget(self.label_6, 0, 2, 1, 1)

        self.firstFrameSpinBox = QSpinBox(RecordingEpisodeWidget)
        self.firstFrameSpinBox.setObjectName(u"firstFrameSpinBox")

        self.episodeBoundariesGridLayout.addWidget(self.firstFrameSpinBox, 0, 3, 1, 1)

        self.label_5 = QLabel(RecordingEpisodeWidget)
        self.label_5.setObjectName(u"label_5")

        self.episodeBoundariesGridLayout.addWidget(self.label_5, 1, 0, 1, 1)

        self.episodeEndDateTimeEdit = QDateTimeEdit(RecordingEpisodeWidget)
        self.episodeEndDateTimeEdit.setObjectName(u"episodeEndDateTimeEdit")

        self.episodeBoundariesGridLayout.addWidget(self.episodeEndDateTimeEdit, 1, 1, 1, 1)

        self.label_7 = QLabel(RecordingEpisodeWidget)
        self.label_7.setObjectName(u"label_7")

        self.episodeBoundariesGridLayout.addWidget(self.label_7, 1, 2, 1, 1)

        self.nFramesSpinBox = QSpinBox(RecordingEpisodeWidget)
        self.nFramesSpinBox.setObjectName(u"nFramesSpinBox")

        self.episodeBoundariesGridLayout.addWidget(self.nFramesSpinBox, 1, 3, 1, 1)


        self.gridLayout_2.addLayout(self.episodeBoundariesGridLayout, 5, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_2 = QLabel(RecordingEpisodeWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_5.addWidget(self.label_2)

        self.episodeTypeComboBox = QComboBox(RecordingEpisodeWidget)
        self.episodeTypeComboBox.setObjectName(u"episodeTypeComboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.episodeTypeComboBox.sizePolicy().hasHeightForWidth())
        self.episodeTypeComboBox.setSizePolicy(sizePolicy1)

        self.horizontalLayout_5.addWidget(self.episodeTypeComboBox)


        self.gridLayout_2.addLayout(self.horizontalLayout_5, 1, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.createObjectPushButton = QPushButton(RecordingEpisodeWidget)
        self.createObjectPushButton.setObjectName(u"createObjectPushButton")
        self.createObjectPushButton.setFlat(True)

        self.horizontalLayout_4.addWidget(self.createObjectPushButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)


        self.gridLayout_2.addLayout(self.horizontalLayout_4, 6, 0, 1, 1)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_8 = QLabel(RecordingEpisodeWidget)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_6.addWidget(self.label_8)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_4)

        self.toggleProcedureEditor = QToolButton(RecordingEpisodeWidget)
        self.toggleProcedureEditor.setObjectName(u"toggleProcedureEditor")
        icon1 = QIcon(QIcon.fromTheme(u"arrow-right-double"))
        self.toggleProcedureEditor.setIcon(icon1)
        self.toggleProcedureEditor.setCheckable(True)
        self.toggleProcedureEditor.setAutoRaise(True)

        self.horizontalLayout_6.addWidget(self.toggleProcedureEditor)


        self.gridLayout_2.addLayout(self.horizontalLayout_6, 2, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_4.setBuddy(self.episodeBeginDateTimeEdit)
        self.label_6.setBuddy(self.firstFrameSpinBox)
        self.label_5.setBuddy(self.episodeEndDateTimeEdit)
        self.label_7.setBuddy(self.nFramesSpinBox)
        self.label_2.setBuddy(self.episodeTypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(RecordingEpisodeWidget)

        QMetaObject.connectSlotsByName(RecordingEpisodeWidget)
    # setupUi

    def retranslateUi(self, RecordingEpisodeWidget):
        RecordingEpisodeWidget.setWindowTitle(QCoreApplication.translate("RecordingEpisodeWidget", u"Form", None))
        self.label_3.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Recording Protocol:", None))
        self.protocolNameLabel.setText("")
#if QT_CONFIG(tooltip)
        self.previewProtocolToolButton.setToolTip(QCoreApplication.translate("RecordingEpisodeWidget", u"View protocol", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.previewProtocolToolButton.setStatusTip(QCoreApplication.translate("RecordingEpisodeWidget", u"View protocol", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.previewProtocolToolButton.setWhatsThis(QCoreApplication.translate("RecordingEpisodeWidget", u"View protocol", None))
#endif // QT_CONFIG(whatsthis)
        self.previewProtocolToolButton.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Preview Protocol", None))
        self.label_4.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Begins:", None))
        self.label_6.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"First Frame: ", None))
#if QT_CONFIG(tooltip)
        self.firstFrameSpinBox.setToolTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Index of first frame", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.firstFrameSpinBox.setStatusTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Index of first frame", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.firstFrameSpinBox.setWhatsThis(QCoreApplication.translate("RecordingEpisodeWidget", u"Index of first frame", None))
#endif // QT_CONFIG(whatsthis)
        self.label_5.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Ends:", None))
        self.label_7.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Frames: ", None))
#if QT_CONFIG(tooltip)
        self.nFramesSpinBox.setToolTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Number of frames in the episode", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.nFramesSpinBox.setStatusTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Number of frames in the episode", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.nFramesSpinBox.setWhatsThis(QCoreApplication.translate("RecordingEpisodeWidget", u"Number of frames in the episode", None))
#endif // QT_CONFIG(whatsthis)
        self.label_2.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Episode Type:", None))
#if QT_CONFIG(tooltip)
        self.createObjectPushButton.setToolTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Create a new recording episode", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.createObjectPushButton.setStatusTip(QCoreApplication.translate("RecordingEpisodeWidget", u"Create a new recording episode", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.createObjectPushButton.setWhatsThis(QCoreApplication.translate("RecordingEpisodeWidget", u"Create a new recording episode", None))
#endif // QT_CONFIG(whatsthis)
        self.createObjectPushButton.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"New", None))
        self.label_8.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Procedure:", None))
        self.toggleProcedureEditor.setText(QCoreApplication.translate("RecordingEpisodeWidget", u"Edit Procedure", None))
    # retranslateUi

