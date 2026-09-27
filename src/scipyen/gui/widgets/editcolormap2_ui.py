# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'editcolormap2.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSlider, QSpacerItem, QVBoxLayout, QWidget)

class Ui_EditColorMapWidget(object):
    def setupUi(self, EditColorMapWidget):
        if not EditColorMapWidget.objectName():
            EditColorMapWidget.setObjectName(u"EditColorMapWidget")
        EditColorMapWidget.resize(286, 135)
        EditColorMapWidget.setAutoFillBackground(False)
        self.gridLayout = QGridLayout(EditColorMapWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.colorMapLabel = QLabel(EditColorMapWidget)
        self.colorMapLabel.setObjectName(u"colorMapLabel")

        self.horizontalLayout_3.addWidget(self.colorMapLabel)

        self.colorMapsComboBox = QComboBox(EditColorMapWidget)
        self.colorMapsComboBox.setObjectName(u"colorMapsComboBox")

        self.horizontalLayout_3.addWidget(self.colorMapsComboBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.gammaLabel = QLabel(EditColorMapWidget)
        self.gammaLabel.setObjectName(u"gammaLabel")

        self.horizontalLayout.addWidget(self.gammaLabel)

        self.gammaBox = QDoubleSpinBox(EditColorMapWidget)
        self.gammaBox.setObjectName(u"gammaBox")

        self.horizontalLayout.addWidget(self.gammaBox)

        self.gammaSlider = QSlider(EditColorMapWidget)
        self.gammaSlider.setObjectName(u"gammaSlider")
        self.gammaSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout.addWidget(self.gammaSlider)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.okButton = QPushButton(EditColorMapWidget)
        self.okButton.setObjectName(u"okButton")

        self.horizontalLayout_2.addWidget(self.okButton)

        self.applyButton = QPushButton(EditColorMapWidget)
        self.applyButton.setObjectName(u"applyButton")

        self.horizontalLayout_2.addWidget(self.applyButton)

        self.cancelButton = QPushButton(EditColorMapWidget)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout_2.addWidget(self.cancelButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)


        self.retranslateUi(EditColorMapWidget)

        self.okButton.setDefault(True)


        QMetaObject.connectSlotsByName(EditColorMapWidget)
    # setupUi

    def retranslateUi(self, EditColorMapWidget):
        EditColorMapWidget.setWindowTitle(QCoreApplication.translate("EditColorMapWidget", u"Edit Color Map", None))
        self.colorMapLabel.setText(QCoreApplication.translate("EditColorMapWidget", u"Select Color Map:", None))
        self.gammaLabel.setText(QCoreApplication.translate("EditColorMapWidget", u"Gamma", None))
#if QT_CONFIG(tooltip)
        self.okButton.setToolTip(QCoreApplication.translate("EditColorMapWidget", u"Apply color map and close this window", None))
#endif // QT_CONFIG(tooltip)
        self.okButton.setText(QCoreApplication.translate("EditColorMapWidget", u"OK", None))
#if QT_CONFIG(tooltip)
        self.applyButton.setToolTip(QCoreApplication.translate("EditColorMapWidget", u"Apply changes", None))
#endif // QT_CONFIG(tooltip)
        self.applyButton.setText(QCoreApplication.translate("EditColorMapWidget", u"Apply", None))
#if QT_CONFIG(tooltip)
        self.cancelButton.setToolTip(QCoreApplication.translate("EditColorMapWidget", u"Close window, discard changes", None))
#endif // QT_CONFIG(tooltip)
        self.cancelButton.setText(QCoreApplication.translate("EditColorMapWidget", u"Cancel", None))
    # retranslateUi

