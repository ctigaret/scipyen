# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'linearrangemappingdialog.ui'
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

class Ui_LinearRangeMappingDialog(object):
    def setupUi(self, LinearRangeMappingDialog):
        if not LinearRangeMappingDialog.objectName():
            LinearRangeMappingDialog.setObjectName(u"LinearRangeMappingDialog")
        LinearRangeMappingDialog.resize(339, 246)
        self.verticalLayout = QVBoxLayout(LinearRangeMappingDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.sourceRangeGroupBox = QGroupBox(LinearRangeMappingDialog)
        self.sourceRangeGroupBox.setObjectName(u"sourceRangeGroupBox")
        self.horizontalLayout = QHBoxLayout(self.sourceRangeGroupBox)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.oldMinLabel = QLabel(self.sourceRangeGroupBox)
        self.oldMinLabel.setObjectName(u"oldMinLabel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.oldMinLabel.sizePolicy().hasHeightForWidth())
        self.oldMinLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.oldMinLabel)

        self.oldRangeMinSpinBox = QDoubleSpinBox(self.sourceRangeGroupBox)
        self.oldRangeMinSpinBox.setObjectName(u"oldRangeMinSpinBox")
        self.oldRangeMinSpinBox.setMouseTracking(True)

        self.horizontalLayout.addWidget(self.oldRangeMinSpinBox)

        self.oldMaxLabel = QLabel(self.sourceRangeGroupBox)
        self.oldMaxLabel.setObjectName(u"oldMaxLabel")
        sizePolicy.setHeightForWidth(self.oldMaxLabel.sizePolicy().hasHeightForWidth())
        self.oldMaxLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.oldMaxLabel)

        self.oldRangeMaxSpinBox = QDoubleSpinBox(self.sourceRangeGroupBox)
        self.oldRangeMaxSpinBox.setObjectName(u"oldRangeMaxSpinBox")
        self.oldRangeMaxSpinBox.setMouseTracking(True)

        self.horizontalLayout.addWidget(self.oldRangeMaxSpinBox)

        self.autoOldRangeButton = QPushButton(self.sourceRangeGroupBox)
        self.autoOldRangeButton.setObjectName(u"autoOldRangeButton")

        self.horizontalLayout.addWidget(self.autoOldRangeButton)


        self.verticalLayout.addWidget(self.sourceRangeGroupBox)

        self.targetRangeGroupBox = QGroupBox(LinearRangeMappingDialog)
        self.targetRangeGroupBox.setObjectName(u"targetRangeGroupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.targetRangeGroupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.newMinLabel = QLabel(self.targetRangeGroupBox)
        self.newMinLabel.setObjectName(u"newMinLabel")
        sizePolicy.setHeightForWidth(self.newMinLabel.sizePolicy().hasHeightForWidth())
        self.newMinLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.newMinLabel)

        self.newRangeMinSpinBox = QDoubleSpinBox(self.targetRangeGroupBox)
        self.newRangeMinSpinBox.setObjectName(u"newRangeMinSpinBox")
        self.newRangeMinSpinBox.setMouseTracking(True)

        self.horizontalLayout_2.addWidget(self.newRangeMinSpinBox)

        self.newMaxLabel = QLabel(self.targetRangeGroupBox)
        self.newMaxLabel.setObjectName(u"newMaxLabel")
        sizePolicy.setHeightForWidth(self.newMaxLabel.sizePolicy().hasHeightForWidth())
        self.newMaxLabel.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.newMaxLabel)

        self.newRangeMaxSpinBox = QDoubleSpinBox(self.targetRangeGroupBox)
        self.newRangeMaxSpinBox.setObjectName(u"newRangeMaxSpinBox")
        self.newRangeMaxSpinBox.setMouseTracking(True)

        self.horizontalLayout_2.addWidget(self.newRangeMaxSpinBox)

        self.autoNewRangeButton = QPushButton(self.targetRangeGroupBox)
        self.autoNewRangeButton.setObjectName(u"autoNewRangeButton")

        self.horizontalLayout_2.addWidget(self.autoNewRangeButton)


        self.verticalLayout.addWidget(self.targetRangeGroupBox)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)

        self.applyPushButton = QPushButton(LinearRangeMappingDialog)
        self.applyPushButton.setObjectName(u"applyPushButton")

        self.horizontalLayout_3.addWidget(self.applyPushButton)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.verticalSpacer_2 = QSpacerItem(20, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.buttonBox = QDialogButtonBox(LinearRangeMappingDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)

#if QT_CONFIG(shortcut)
        self.oldMinLabel.setBuddy(self.oldRangeMinSpinBox)
        self.oldMaxLabel.setBuddy(self.oldRangeMaxSpinBox)
        self.newMinLabel.setBuddy(self.newRangeMinSpinBox)
        self.newMaxLabel.setBuddy(self.newRangeMaxSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(LinearRangeMappingDialog)
        self.buttonBox.accepted.connect(LinearRangeMappingDialog.accept)
        self.buttonBox.rejected.connect(LinearRangeMappingDialog.reject)

        QMetaObject.connectSlotsByName(LinearRangeMappingDialog)
    # setupUi

    def retranslateUi(self, LinearRangeMappingDialog):
        LinearRangeMappingDialog.setWindowTitle(QCoreApplication.translate("LinearRangeMappingDialog", u"Dialog", None))
        self.sourceRangeGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingDialog", u"Source Range", None))
        self.oldMinLabel.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Min:", None))
        self.oldMaxLabel.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Ma&x:", None))
        self.autoOldRangeButton.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Auto", None))
        self.targetRangeGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingDialog", u"Target Range", None))
        self.newMinLabel.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Min:", None))
        self.newMaxLabel.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Max:", None))
        self.autoNewRangeButton.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Auto", None))
#if QT_CONFIG(tooltip)
        self.applyPushButton.setToolTip(QCoreApplication.translate("LinearRangeMappingDialog", u"Apply transform to data", None))
#endif // QT_CONFIG(tooltip)
        self.applyPushButton.setText(QCoreApplication.translate("LinearRangeMappingDialog", u"Apply", None))
    # retranslateUi

