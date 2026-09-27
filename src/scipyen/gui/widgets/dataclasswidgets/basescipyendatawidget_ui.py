# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'basescipyendatawidget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QToolButton, QWidget)

from gui.widgets.small_widgets import QuantitySpinBox

class Ui_BaseScipyenDataWidget(object):
    def setupUi(self, BaseScipyenDataWidget):
        if not BaseScipyenDataWidget.objectName():
            BaseScipyenDataWidget.setObjectName(u"BaseScipyenDataWidget")
        BaseScipyenDataWidget.resize(484, 258)
        self.gridLayout = QGridLayout(BaseScipyenDataWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.dataVarNameLabel = QLabel(BaseScipyenDataWidget)
        self.dataVarNameLabel.setObjectName(u"dataVarNameLabel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dataVarNameLabel.sizePolicy().hasHeightForWidth())
        self.dataVarNameLabel.setSizePolicy(sizePolicy)
        self.dataVarNameLabel.setFrameShape(QFrame.Shape.NoFrame)
        self.dataVarNameLabel.setFrameShadow(QFrame.Shadow.Plain)
        self.dataVarNameLabel.setLineWidth(0)
        self.dataVarNameLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.horizontalLayout_3.addWidget(self.dataVarNameLabel)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout_3, 0, 0, 1, 1)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.nameLabel = QLabel(BaseScipyenDataWidget)
        self.nameLabel.setObjectName(u"nameLabel")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.nameLabel)

        self.dataNameLineEdit = QLineEdit(BaseScipyenDataWidget)
        self.dataNameLineEdit.setObjectName(u"dataNameLineEdit")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(10)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.dataNameLineEdit.sizePolicy().hasHeightForWidth())
        self.dataNameLineEdit.setSizePolicy(sizePolicy1)
        self.dataNameLineEdit.setClearButtonEnabled(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.dataNameLineEdit)

        self.sourceIDLabel = QLabel(BaseScipyenDataWidget)
        self.sourceIDLabel.setObjectName(u"sourceIDLabel")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.sourceIDLabel.sizePolicy().hasHeightForWidth())
        self.sourceIDLabel.setSizePolicy(sizePolicy2)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.sourceIDLabel)

        self.sourceIDLineEdit = QLineEdit(BaseScipyenDataWidget)
        self.sourceIDLineEdit.setObjectName(u"sourceIDLineEdit")
        sizePolicy1.setHeightForWidth(self.sourceIDLineEdit.sizePolicy().hasHeightForWidth())
        self.sourceIDLineEdit.setSizePolicy(sizePolicy1)
        self.sourceIDLineEdit.setClearButtonEnabled(True)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.sourceIDLineEdit)

        self.cellIDLabel = QLabel(BaseScipyenDataWidget)
        self.cellIDLabel.setObjectName(u"cellIDLabel")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.cellIDLabel.sizePolicy().hasHeightForWidth())
        self.cellIDLabel.setSizePolicy(sizePolicy3)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.cellIDLabel)

        self.cellIDLineEdit = QLineEdit(BaseScipyenDataWidget)
        self.cellIDLineEdit.setObjectName(u"cellIDLineEdit")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.cellIDLineEdit.sizePolicy().hasHeightForWidth())
        self.cellIDLineEdit.setSizePolicy(sizePolicy4)
        self.cellIDLineEdit.setClearButtonEnabled(True)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.cellIDLineEdit)

        self.fieldIDLabel = QLabel(BaseScipyenDataWidget)
        self.fieldIDLabel.setObjectName(u"fieldIDLabel")
        sizePolicy3.setHeightForWidth(self.fieldIDLabel.sizePolicy().hasHeightForWidth())
        self.fieldIDLabel.setSizePolicy(sizePolicy3)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.fieldIDLabel)

        self.fieldIDLineEdit = QLineEdit(BaseScipyenDataWidget)
        self.fieldIDLineEdit.setObjectName(u"fieldIDLineEdit")
        sizePolicy4.setHeightForWidth(self.fieldIDLineEdit.sizePolicy().hasHeightForWidth())
        self.fieldIDLineEdit.setSizePolicy(sizePolicy4)
        self.fieldIDLineEdit.setClearButtonEnabled(True)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.fieldIDLineEdit)


        self.gridLayout.addLayout(self.formLayout, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.ageLabel = QLabel(BaseScipyenDataWidget)
        self.ageLabel.setObjectName(u"ageLabel")

        self.horizontalLayout_2.addWidget(self.ageLabel)

        self.ageSpinBox = QuantitySpinBox(BaseScipyenDataWidget)
        self.ageSpinBox.setObjectName(u"ageSpinBox")

        self.horizontalLayout_2.addWidget(self.ageSpinBox)

        self.sexLabel = QLabel(BaseScipyenDataWidget)
        self.sexLabel.setObjectName(u"sexLabel")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.sexLabel.sizePolicy().hasHeightForWidth())
        self.sexLabel.setSizePolicy(sizePolicy5)

        self.horizontalLayout_2.addWidget(self.sexLabel)

        self.sexComboBox = QComboBox(BaseScipyenDataWidget)
        self.sexComboBox.setObjectName(u"sexComboBox")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.sexComboBox.sizePolicy().hasHeightForWidth())
        self.sexComboBox.setSizePolicy(sizePolicy6)
        self.sexComboBox.setMinimumSize(QSize(80, 0))
        self.sexComboBox.setMaxVisibleItems(3)
        self.sexComboBox.setMaxCount(3)
        self.sexComboBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sexComboBox.setMinimumContentsLength(3)

        self.horizontalLayout_2.addWidget(self.sexComboBox)

        self.genotypeLabel = QLabel(BaseScipyenDataWidget)
        self.genotypeLabel.setObjectName(u"genotypeLabel")
        sizePolicy5.setHeightForWidth(self.genotypeLabel.sizePolicy().hasHeightForWidth())
        self.genotypeLabel.setSizePolicy(sizePolicy5)

        self.horizontalLayout_2.addWidget(self.genotypeLabel)

        self.genotypeComboBox = QComboBox(BaseScipyenDataWidget)
        self.genotypeComboBox.setObjectName(u"genotypeComboBox")
        sizePolicy6.setHeightForWidth(self.genotypeComboBox.sizePolicy().hasHeightForWidth())
        self.genotypeComboBox.setSizePolicy(sizePolicy6)
        self.genotypeComboBox.setMinimumSize(QSize(80, 0))
        self.genotypeComboBox.setEditable(True)
        self.genotypeComboBox.setMaxVisibleItems(50)

        self.horizontalLayout_2.addWidget(self.genotypeComboBox)


        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.biometricsToolButton = QToolButton(BaseScipyenDataWidget)
        self.biometricsToolButton.setObjectName(u"biometricsToolButton")
        icon = QIcon(QIcon.fromTheme(u"package"))
        self.biometricsToolButton.setIcon(icon)
        self.biometricsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.biometricsToolButton)

        self.procedureToolButton = QToolButton(BaseScipyenDataWidget)
        self.procedureToolButton.setObjectName(u"procedureToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"configure"))
        self.procedureToolButton.setIcon(icon1)
        self.procedureToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.procedureToolButton)

        self.triggersToolButton = QToolButton(BaseScipyenDataWidget)
        self.triggersToolButton.setObjectName(u"triggersToolButton")
        icon2 = QIcon(QIcon.fromTheme(u"network-connect"))
        self.triggersToolButton.setIcon(icon2)
        self.triggersToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.triggersToolButton)

        self.dateTimeToolButton = QToolButton(BaseScipyenDataWidget)
        self.dateTimeToolButton.setObjectName(u"dateTimeToolButton")
        icon3 = QIcon(QIcon.fromTheme(u"change-date-symbolic"))
        self.dateTimeToolButton.setIcon(icon3)
        self.dateTimeToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.dateTimeToolButton)

        self.annotationsToolButton = QToolButton(BaseScipyenDataWidget)
        self.annotationsToolButton.setObjectName(u"annotationsToolButton")
        icon4 = QIcon(QIcon.fromTheme(u"settings-configure"))
        self.annotationsToolButton.setIcon(icon4)
        self.annotationsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.annotationsToolButton)

        self.notesToolButton = QToolButton(BaseScipyenDataWidget)
        self.notesToolButton.setObjectName(u"notesToolButton")
        icon5 = QIcon(QIcon.fromTheme(u"description"))
        self.notesToolButton.setIcon(icon5)
        self.notesToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.notesToolButton)

        self.exportToolButton = QToolButton(BaseScipyenDataWidget)
        self.exportToolButton.setObjectName(u"exportToolButton")
        icon6 = QIcon(QIcon.fromTheme(u"document-export"))
        self.exportToolButton.setIcon(icon6)
        self.exportToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.exportToolButton)

        self.saveToolButton = QToolButton(BaseScipyenDataWidget)
        self.saveToolButton.setObjectName(u"saveToolButton")
        icon7 = QIcon(QIcon.fromTheme(u"document-save"))
        self.saveToolButton.setIcon(icon7)
        self.saveToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.saveToolButton)

        self.importToolButton = QToolButton(BaseScipyenDataWidget)
        self.importToolButton.setObjectName(u"importToolButton")
        icon8 = QIcon(QIcon.fromTheme(u"document-import"))
        self.importToolButton.setIcon(icon8)
        self.importToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.importToolButton)

        self.loadToolButton = QToolButton(BaseScipyenDataWidget)
        self.loadToolButton.setObjectName(u"loadToolButton")
        icon9 = QIcon(QIcon.fromTheme(u"document-open"))
        self.loadToolButton.setIcon(icon9)
        self.loadToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.loadToolButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.nameLabel.setBuddy(self.dataNameLineEdit)
        self.sourceIDLabel.setBuddy(self.sourceIDLineEdit)
        self.cellIDLabel.setBuddy(self.cellIDLineEdit)
        self.fieldIDLabel.setBuddy(self.fieldIDLineEdit)
        self.ageLabel.setBuddy(self.ageSpinBox)
        self.sexLabel.setBuddy(self.sexComboBox)
        self.genotypeLabel.setBuddy(self.genotypeComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BaseScipyenDataWidget)

        QMetaObject.connectSlotsByName(BaseScipyenDataWidget)
    # setupUi

    def retranslateUi(self, BaseScipyenDataWidget):
        BaseScipyenDataWidget.setWindowTitle(QCoreApplication.translate("BaseScipyenDataWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.dataVarNameLabel.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Name of the variable in the workspace", None))
#endif // QT_CONFIG(tooltip)
        self.dataVarNameLabel.setText("")
        self.nameLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Name:", None))
#if QT_CONFIG(tooltip)
        self.dataNameLineEdit.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Data name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.dataNameLineEdit.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Data name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.dataNameLineEdit.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Data name", None))
#endif // QT_CONFIG(whatsthis)
        self.sourceIDLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Source:", None))
        self.cellIDLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Cell:", None))
#if QT_CONFIG(tooltip)
        self.cellIDLineEdit.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Cell name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.cellIDLineEdit.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Cell name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.cellIDLineEdit.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Cell name", None))
#endif // QT_CONFIG(whatsthis)
        self.fieldIDLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Field:", None))
#if QT_CONFIG(tooltip)
        self.fieldIDLineEdit.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Field name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.fieldIDLineEdit.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Field name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.fieldIDLineEdit.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Field name", None))
#endif // QT_CONFIG(whatsthis)
        self.ageLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Age:", None))
        self.sexLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Sex:", None))
#if QT_CONFIG(tooltip)
        self.sexComboBox.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Genetic sex", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.sexComboBox.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Genetic sex", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.sexComboBox.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Genetic sex", None))
#endif // QT_CONFIG(whatsthis)
        self.sexComboBox.setCurrentText("")
        self.genotypeLabel.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Genotype:", None))
#if QT_CONFIG(tooltip)
        self.genotypeComboBox.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Genotype", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.genotypeComboBox.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Genotype", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.genotypeComboBox.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Genotype", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.biometricsToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional biometrics", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.biometricsToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional biometrics", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.biometricsToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional biometrics", None))
#endif // QT_CONFIG(whatsthis)
        self.biometricsToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Biometrics", None))
#if QT_CONFIG(tooltip)
        self.procedureToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Procedure (treatment, etc)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.procedureToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Procedure (treatment, etc)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.procedureToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Procedure (treatment, etc)", None))
#endif // QT_CONFIG(whatsthis)
        self.procedureToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Procedure", None))
#if QT_CONFIG(tooltip)
        self.triggersToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Detect and edit trigger protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.triggersToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Detect and edit trigger protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.triggersToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Detect and edit trigger protocols", None))
#endif // QT_CONFIG(whatsthis)
        self.triggersToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Triggers", None))
#if QT_CONFIG(tooltip)
        self.dateTimeToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Date, time of recording and  analysis", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.dateTimeToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Date, time of recording and  analysis", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.dateTimeToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Date, time of recording and  analysis", None))
#endif // QT_CONFIG(whatsthis)
        self.dateTimeToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Date, time", None))
#if QT_CONFIG(tooltip)
        self.annotationsToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional structured descriptors (key, value pairs)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.annotationsToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional structured descriptors (key, value pairs)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.annotationsToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Additional structured descriptors (key, value pairs)", None))
#endif // QT_CONFIG(whatsthis)
        self.annotationsToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Annotations", None))
#if QT_CONFIG(tooltip)
        self.notesToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Edit description (notes)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.notesToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Edit description (notes)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.notesToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Edit description (notes)", None))
#endif // QT_CONFIG(whatsthis)
        self.notesToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Notes", None))
#if QT_CONFIG(tooltip)
        self.exportToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Export metadata to workspace object", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.exportToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Export metadata to workspace object", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.exportToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Export metadata to workspace object", None))
#endif // QT_CONFIG(whatsthis)
        self.exportToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Export", None))
#if QT_CONFIG(tooltip)
        self.saveToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Save metadata to file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.saveToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Save metadata to file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.saveToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Save metadata to file", None))
#endif // QT_CONFIG(whatsthis)
        self.saveToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Save", None))
#if QT_CONFIG(tooltip)
        self.importToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Import metadata from workspace object", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.importToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Import metadata from workspace object", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.importToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Import metadata from workspace object", None))
#endif // QT_CONFIG(whatsthis)
        self.importToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Import", None))
#if QT_CONFIG(tooltip)
        self.loadToolButton.setToolTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Load meta-data from file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.loadToolButton.setStatusTip(QCoreApplication.translate("BaseScipyenDataWidget", u"Load meta-data from file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.loadToolButton.setWhatsThis(QCoreApplication.translate("BaseScipyenDataWidget", u"Load meta-data from file", None))
#endif // QT_CONFIG(whatsthis)
        self.loadToolButton.setText(QCoreApplication.translate("BaseScipyenDataWidget", u"Load from file", None))
    # retranslateUi

