# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'TestParamsWidget2JIjrmn.ui'
##
## Created by: Qt User Interface Compiler version 5.15.6
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *  # type: ignore
from PySide2.QtGui import *  # type: ignore
from PySide2.QtWidgets import *  # type: ignore


class Ui_TestParametersWidget2(object):
    def setupUi(self, TestParametersWidget2):
        if not TestParametersWidget2.objectName():
            TestParametersWidget2.setObjectName(u"TestParametersWidget2")
        TestParametersWidget2.resize(306, 108)
        self.gridLayout = QGridLayout(TestParametersWidget2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widgetsLayout = QGridLayout()
        self.widgetsLayout.setObjectName(u"widgetsLayout")
        self.label_Parameters_header = QLabel(TestParametersWidget2)
        self.label_Parameters_header.setObjectName(u"label_Parameters_header")

        self.widgetsLayout.addWidget(self.label_Parameters_header, 0, 0, 1, 1)

        self.label_Initial_Value_header = QLabel(TestParametersWidget2)
        self.label_Initial_Value_header.setObjectName(u"label_Initial_Value_header")

        self.widgetsLayout.addWidget(self.label_Initial_Value_header, 0, 1, 1, 1)

        self.label_Lower_Bound_header = QLabel(TestParametersWidget2)
        self.label_Lower_Bound_header.setObjectName(u"label_Lower_Bound_header")

        self.widgetsLayout.addWidget(self.label_Lower_Bound_header, 0, 2, 1, 1)

        self.label_Upper_Bound_header = QLabel(TestParametersWidget2)
        self.label_Upper_Bound_header.setObjectName(u"label_Upper_Bound_header")

        self.widgetsLayout.addWidget(self.label_Upper_Bound_header, 0, 3, 1, 1)

        self.label_alpha = QLabel(TestParametersWidget2)
        self.label_alpha.setObjectName(u"label_alpha")

        self.widgetsLayout.addWidget(self.label_alpha, 1, 0, 1, 1)

        self.alpha_Initial_Value_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.alpha_Initial_Value_spinBox.setObjectName(u"alpha_Initial_Value_spinBox")

        self.widgetsLayout.addWidget(self.alpha_Initial_Value_spinBox, 1, 1, 1, 1)

        self.alpha_Lower_Bound_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.alpha_Lower_Bound_spinBox.setObjectName(u"alpha_Lower_Bound_spinBox")

        self.widgetsLayout.addWidget(self.alpha_Lower_Bound_spinBox, 1, 2, 1, 1)

        self.alpha_Upper_Bound_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.alpha_Upper_Bound_spinBox.setObjectName(u"alpha_Upper_Bound_spinBox")

        self.widgetsLayout.addWidget(self.alpha_Upper_Bound_spinBox, 1, 3, 1, 1)

        self.label_beta = QLabel(TestParametersWidget2)
        self.label_beta.setObjectName(u"label_beta")

        self.widgetsLayout.addWidget(self.label_beta, 2, 0, 1, 1)

        self.beta_Initial_Value_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.beta_Initial_Value_spinBox.setObjectName(u"beta_Initial_Value_spinBox")

        self.widgetsLayout.addWidget(self.beta_Initial_Value_spinBox, 2, 1, 1, 1)

        self.beta_Lower_Bound_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.beta_Lower_Bound_spinBox.setObjectName(u"beta_Lower_Bound_spinBox")

        self.widgetsLayout.addWidget(self.beta_Lower_Bound_spinBox, 2, 2, 1, 1)

        self.beta_Upper_Bound_spinBox = QDoubleSpinBox(TestParametersWidget2)
        self.beta_Upper_Bound_spinBox.setObjectName(u"beta_Upper_Bound_spinBox")

        self.widgetsLayout.addWidget(self.beta_Upper_Bound_spinBox, 2, 3, 1, 1)


        self.gridLayout.addLayout(self.widgetsLayout, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 3, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(TestParametersWidget2)

        QMetaObject.connectSlotsByName(TestParametersWidget2)
    # setupUi

    def retranslateUi(self, TestParametersWidget2):
        TestParametersWidget2.setWindowTitle(QCoreApplication.translate("TestParametersWidget2", u"Form", None))
        self.label_Parameters_header.setText(QCoreApplication.translate("TestParametersWidget2", u"Parameters", None))
        self.label_Initial_Value_header.setText(QCoreApplication.translate("TestParametersWidget2", u"Initial Value:", None))
        self.label_Lower_Bound_header.setText(QCoreApplication.translate("TestParametersWidget2", u"Lower Bound:", None))
        self.label_Upper_Bound_header.setText(QCoreApplication.translate("TestParametersWidget2", u"Upper Bound:", None))
        self.label_alpha.setText(QCoreApplication.translate("TestParametersWidget2", u"\u03b1", None))
        self.label_beta.setText(QCoreApplication.translate("TestParametersWidget2", u"\u03b2", None))
    # retranslateUi

