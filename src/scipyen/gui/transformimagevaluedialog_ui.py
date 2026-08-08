# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'transformimagevaluedialog.ui'
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
    QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_TransformImageValueDialog(object):
    def setupUi(self, TransformImageValueDialog):
        if not TransformImageValueDialog.objectName():
            TransformImageValueDialog.setObjectName(u"TransformImageValueDialog")
        TransformImageValueDialog.resize(429, 168)
        self.verticalLayout = QVBoxLayout(TransformImageValueDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.sourceRangeGroupBox = QGroupBox(TransformImageValueDialog)
        self.sourceRangeGroupBox.setObjectName(u"sourceRangeGroupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.sourceRangeGroupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.rangeMinLabel = QLabel(self.sourceRangeGroupBox)
        self.rangeMinLabel.setObjectName(u"rangeMinLabel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rangeMinLabel.sizePolicy().hasHeightForWidth())
        self.rangeMinLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.rangeMinLabel)

        self.rangeMinSpinBox = QDoubleSpinBox(self.sourceRangeGroupBox)
        self.rangeMinSpinBox.setObjectName(u"rangeMinSpinBox")
        self.rangeMinSpinBox.setMouseTracking(True)

        self.horizontalLayout_2.addWidget(self.rangeMinSpinBox)

        self.rangeMaxLabel = QLabel(self.sourceRangeGroupBox)
        self.rangeMaxLabel.setObjectName(u"rangeMaxLabel")
        sizePolicy.setHeightForWidth(self.rangeMaxLabel.sizePolicy().hasHeightForWidth())
        self.rangeMaxLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.rangeMaxLabel)

        self.rangeMaxSpinBox = QDoubleSpinBox(self.sourceRangeGroupBox)
        self.rangeMaxSpinBox.setObjectName(u"rangeMaxSpinBox")
        self.rangeMaxSpinBox.setMouseTracking(True)

        self.horizontalLayout_2.addWidget(self.rangeMaxSpinBox)

        self.autoRangePushButton = QPushButton(self.sourceRangeGroupBox)
        self.autoRangePushButton.setObjectName(u"autoRangePushButton")

        self.horizontalLayout_2.addWidget(self.autoRangePushButton)

        self.defaultRangePushButton = QPushButton(self.sourceRangeGroupBox)
        self.defaultRangePushButton.setObjectName(u"defaultRangePushButton")

        self.horizontalLayout_2.addWidget(self.defaultRangePushButton)


        self.verticalLayout.addWidget(self.sourceRangeGroupBox)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.factorLabel = QLabel(TransformImageValueDialog)
        self.factorLabel.setObjectName(u"factorLabel")

        self.horizontalLayout.addWidget(self.factorLabel)

        self.factorSpinBox = QDoubleSpinBox(TransformImageValueDialog)
        self.factorSpinBox.setObjectName(u"factorSpinBox")
        self.factorSpinBox.setMouseTracking(True)

        self.horizontalLayout.addWidget(self.factorSpinBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.applyPushButton = QPushButton(TransformImageValueDialog)
        self.applyPushButton.setObjectName(u"applyPushButton")

        self.horizontalLayout.addWidget(self.applyPushButton)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.verticalSpacer_2 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.buttonBox = QDialogButtonBox(TransformImageValueDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)

#if QT_CONFIG(shortcut)
        self.rangeMinLabel.setBuddy(self.rangeMinSpinBox)
        self.rangeMaxLabel.setBuddy(self.rangeMaxSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(TransformImageValueDialog)
        self.buttonBox.accepted.connect(TransformImageValueDialog.accept)
        self.buttonBox.rejected.connect(TransformImageValueDialog.reject)

        QMetaObject.connectSlotsByName(TransformImageValueDialog)
    # setupUi

    def retranslateUi(self, TransformImageValueDialog):
        TransformImageValueDialog.setWindowTitle(QCoreApplication.translate("TransformImageValueDialog", u"Dialog", None))
        self.sourceRangeGroupBox.setTitle(QCoreApplication.translate("TransformImageValueDialog", u"Source Range", None))
        self.rangeMinLabel.setText(QCoreApplication.translate("TransformImageValueDialog", u"Min:", None))
        self.rangeMaxLabel.setText(QCoreApplication.translate("TransformImageValueDialog", u"Ma&x:", None))
        self.autoRangePushButton.setText(QCoreApplication.translate("TransformImageValueDialog", u"Auto", None))
        self.defaultRangePushButton.setText(QCoreApplication.translate("TransformImageValueDialog", u"Default", None))
        self.factorLabel.setText(QCoreApplication.translate("TransformImageValueDialog", u"Factor", None))
#if QT_CONFIG(statustip)
        self.applyPushButton.setStatusTip(QCoreApplication.translate("TransformImageValueDialog", u"Apply transformation to source data", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.applyPushButton.setWhatsThis(QCoreApplication.translate("TransformImageValueDialog", u"Apply transformation to source data", None))
#endif // QT_CONFIG(whatsthis)
        self.applyPushButton.setText(QCoreApplication.translate("TransformImageValueDialog", u"Apply", None))
    # retranslateUi

