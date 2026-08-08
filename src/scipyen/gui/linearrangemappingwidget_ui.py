# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'linearrangemappingwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_LinearRangeMappingWidget(object):
    def setupUi(self, LinearRangeMappingWidget):
        if not LinearRangeMappingWidget.objectName():
            LinearRangeMappingWidget.setObjectName(u"LinearRangeMappingWidget")
        LinearRangeMappingWidget.resize(367, 262)
        self.verticalLayout_2 = QVBoxLayout(LinearRangeMappingWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.sourceRangeGroupBox = QGroupBox(LinearRangeMappingWidget)
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


        self.verticalLayout_2.addWidget(self.sourceRangeGroupBox)

        self.verticalSpacer = QSpacerItem(20, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.targetRangeGroupBox = QGroupBox(LinearRangeMappingWidget)
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


        self.verticalLayout_2.addWidget(self.targetRangeGroupBox)

        self.verticalSpacer_2 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.applyToGroupBox = QGroupBox(LinearRangeMappingWidget)
        self.applyToGroupBox.setObjectName(u"applyToGroupBox")
        self.verticalLayout = QVBoxLayout(self.applyToGroupBox)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.applyToDisplayCheckBox = QCheckBox(self.applyToGroupBox)
        self.applyToDisplayCheckBox.setObjectName(u"applyToDisplayCheckBox")
        self.applyToDisplayCheckBox.setChecked(True)

        self.verticalLayout.addWidget(self.applyToDisplayCheckBox)

        self.applyToSourceCheckBox = QCheckBox(self.applyToGroupBox)
        self.applyToSourceCheckBox.setObjectName(u"applyToSourceCheckBox")

        self.verticalLayout.addWidget(self.applyToSourceCheckBox)


        self.horizontalLayout_4.addWidget(self.applyToGroupBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.revertGroupBox = QGroupBox(LinearRangeMappingWidget)
        self.revertGroupBox.setObjectName(u"revertGroupBox")
        self.revertGroupBox.setCheckable(False)
        self.horizontalLayout_3 = QHBoxLayout(self.revertGroupBox)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.revertDisplayPushButton = QPushButton(self.revertGroupBox)
        self.revertDisplayPushButton.setObjectName(u"revertDisplayPushButton")

        self.horizontalLayout_3.addWidget(self.revertDisplayPushButton)

        self.revertSourcePushButton = QPushButton(self.revertGroupBox)
        self.revertSourcePushButton.setObjectName(u"revertSourcePushButton")

        self.horizontalLayout_3.addWidget(self.revertSourcePushButton)

        self.revertBothPushButton = QPushButton(self.revertGroupBox)
        self.revertBothPushButton.setObjectName(u"revertBothPushButton")

        self.horizontalLayout_3.addWidget(self.revertBothPushButton)


        self.horizontalLayout_4.addWidget(self.revertGroupBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_4)

#if QT_CONFIG(shortcut)
        self.oldMinLabel.setBuddy(self.oldRangeMinSpinBox)
        self.oldMaxLabel.setBuddy(self.oldRangeMaxSpinBox)
        self.newMinLabel.setBuddy(self.newRangeMinSpinBox)
        self.newMaxLabel.setBuddy(self.newRangeMaxSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(LinearRangeMappingWidget)

        QMetaObject.connectSlotsByName(LinearRangeMappingWidget)
    # setupUi

    def retranslateUi(self, LinearRangeMappingWidget):
        LinearRangeMappingWidget.setWindowTitle(QCoreApplication.translate("LinearRangeMappingWidget", u"Linear Range Mapping", None))
        self.sourceRangeGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingWidget", u"Source Range", None))
        self.oldMinLabel.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Min:", None))
        self.oldMaxLabel.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Ma&x:", None))
        self.autoOldRangeButton.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Auto", None))
        self.targetRangeGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingWidget", u"Target Range", None))
        self.newMinLabel.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Min:", None))
        self.newMaxLabel.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Max:", None))
        self.autoNewRangeButton.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Auto", None))
        self.applyToGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingWidget", u"Apply to:", None))
        self.applyToDisplayCheckBox.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Display", None))
        self.applyToSourceCheckBox.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Source", None))
        self.revertGroupBox.setTitle(QCoreApplication.translate("LinearRangeMappingWidget", u"Revert", None))
        self.revertDisplayPushButton.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Display", None))
        self.revertSourcePushButton.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Source", None))
        self.revertBothPushButton.setText(QCoreApplication.translate("LinearRangeMappingWidget", u"Both", None))
    # retranslateUi

