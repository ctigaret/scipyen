# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PrairieImporter.ui'
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
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QSizePolicy, QSpacerItem, QToolButton,
    QVBoxLayout, QWidget)

class Ui_PrairieImporterDialog(object):
    def setupUi(self, PrairieImporterDialog):
        if not PrairieImporterDialog.objectName():
            PrairieImporterDialog.setObjectName(u"PrairieImporterDialog")
        PrairieImporterDialog.resize(366, 488)
        self.gridLayout_3 = QGridLayout(PrairieImporterDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.dataFilesGroupBox = QGroupBox(PrairieImporterDialog)
        self.dataFilesGroupBox.setObjectName(u"dataFilesGroupBox")
        self.verticalLayout_5 = QVBoxLayout(self.dataFilesGroupBox)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.dataFilesGroupBox)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.pvScanFileChooserToolButton = QToolButton(self.dataFilesGroupBox)
        self.pvScanFileChooserToolButton.setObjectName(u"pvScanFileChooserToolButton")
        icon = QIcon(QIcon.fromTheme(u"document-open"))
        self.pvScanFileChooserToolButton.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pvScanFileChooserToolButton)

        self.pvScanImportFromWorkspaceToolButton = QToolButton(self.dataFilesGroupBox)
        self.pvScanImportFromWorkspaceToolButton.setObjectName(u"pvScanImportFromWorkspaceToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"document-import"))
        self.pvScanImportFromWorkspaceToolButton.setIcon(icon1)

        self.horizontalLayout_2.addWidget(self.pvScanImportFromWorkspaceToolButton)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.pvScanFileNameLineEdit = QLineEdit(self.dataFilesGroupBox)
        self.pvScanFileNameLineEdit.setObjectName(u"pvScanFileNameLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pvScanFileNameLineEdit.sizePolicy().hasHeightForWidth())
        self.pvScanFileNameLineEdit.setSizePolicy(sizePolicy)
        self.pvScanFileNameLineEdit.setClearButtonEnabled(True)

        self.verticalLayout_4.addWidget(self.pvScanFileNameLineEdit)


        self.verticalLayout_5.addLayout(self.verticalLayout_4)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_3 = QLabel(self.dataFilesGroupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setWordWrap(True)

        self.horizontalLayout.addWidget(self.label_3)

        self.ephysFileChooserToolButton = QToolButton(self.dataFilesGroupBox)
        self.ephysFileChooserToolButton.setObjectName(u"ephysFileChooserToolButton")
        self.ephysFileChooserToolButton.setIcon(icon)

        self.horizontalLayout.addWidget(self.ephysFileChooserToolButton)

        self.ephysImportFromWorkspaceToolButon = QToolButton(self.dataFilesGroupBox)
        self.ephysImportFromWorkspaceToolButon.setObjectName(u"ephysImportFromWorkspaceToolButon")
        self.ephysImportFromWorkspaceToolButon.setIcon(icon1)

        self.horizontalLayout.addWidget(self.ephysImportFromWorkspaceToolButon)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.ephysFileNameLineEdit = QLineEdit(self.dataFilesGroupBox)
        self.ephysFileNameLineEdit.setObjectName(u"ephysFileNameLineEdit")
        sizePolicy.setHeightForWidth(self.ephysFileNameLineEdit.sizePolicy().hasHeightForWidth())
        self.ephysFileNameLineEdit.setSizePolicy(sizePolicy)

        self.verticalLayout_2.addWidget(self.ephysFileNameLineEdit)


        self.verticalLayout_5.addLayout(self.verticalLayout_2)


        self.gridLayout_3.addWidget(self.dataFilesGroupBox, 0, 0, 1, 1)

        self.scanDataGroupBox = QGroupBox(PrairieImporterDialog)
        self.scanDataGroupBox.setObjectName(u"scanDataGroupBox")
        self.gridLayout_2 = QGridLayout(self.scanDataGroupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.protocolsGroupBox = QGroupBox(self.scanDataGroupBox)
        self.protocolsGroupBox.setObjectName(u"protocolsGroupBox")
        self.gridLayout = QGridLayout(self.protocolsGroupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.detectTriggersToolButton = QToolButton(self.protocolsGroupBox)
        self.detectTriggersToolButton.setObjectName(u"detectTriggersToolButton")
        icon2 = QIcon(QIcon.fromTheme(u"tools-wizard"))
        self.detectTriggersToolButton.setIcon(icon2)

        self.horizontalLayout_3.addWidget(self.detectTriggersToolButton)

        self.editTriggerProtocolsToolButton = QToolButton(self.protocolsGroupBox)
        self.editTriggerProtocolsToolButton.setObjectName(u"editTriggerProtocolsToolButton")
        icon3 = QIcon(QIcon.fromTheme(u"document-edit"))
        self.editTriggerProtocolsToolButton.setIcon(icon3)

        self.horizontalLayout_3.addWidget(self.editTriggerProtocolsToolButton)

        self.triggerProtocolFileChooserToolButton = QToolButton(self.protocolsGroupBox)
        self.triggerProtocolFileChooserToolButton.setObjectName(u"triggerProtocolFileChooserToolButton")
        self.triggerProtocolFileChooserToolButton.setIcon(icon)

        self.horizontalLayout_3.addWidget(self.triggerProtocolFileChooserToolButton)

        self.protocolsImportToolButton = QToolButton(self.protocolsGroupBox)
        self.protocolsImportToolButton.setObjectName(u"protocolsImportToolButton")
        self.protocolsImportToolButton.setIcon(icon1)

        self.horizontalLayout_3.addWidget(self.protocolsImportToolButton)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.triggerProtocolFileNameLineEdit = QLineEdit(self.protocolsGroupBox)
        self.triggerProtocolFileNameLineEdit.setObjectName(u"triggerProtocolFileNameLineEdit")
        sizePolicy.setHeightForWidth(self.triggerProtocolFileNameLineEdit.sizePolicy().hasHeightForWidth())
        self.triggerProtocolFileNameLineEdit.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.triggerProtocolFileNameLineEdit)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.protocolsGroupBox, 0, 0, 1, 1)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_2 = QLabel(self.scanDataGroupBox)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_4.addWidget(self.label_2)

        self.optionsFileNameLineEdit = QLineEdit(self.scanDataGroupBox)
        self.optionsFileNameLineEdit.setObjectName(u"optionsFileNameLineEdit")
        sizePolicy.setHeightForWidth(self.optionsFileNameLineEdit.sizePolicy().hasHeightForWidth())
        self.optionsFileNameLineEdit.setSizePolicy(sizePolicy)
        self.optionsFileNameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout_4.addWidget(self.optionsFileNameLineEdit)

        self.optionsFileChooserToolButton = QToolButton(self.scanDataGroupBox)
        self.optionsFileChooserToolButton.setObjectName(u"optionsFileChooserToolButton")
        self.optionsFileChooserToolButton.setIcon(icon)

        self.horizontalLayout_4.addWidget(self.optionsFileChooserToolButton)

        self.optionsImportToolButton = QToolButton(self.scanDataGroupBox)
        self.optionsImportToolButton.setObjectName(u"optionsImportToolButton")
        self.optionsImportToolButton.setIcon(icon1)

        self.horizontalLayout_4.addWidget(self.optionsImportToolButton)


        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_5 = QLabel(self.scanDataGroupBox)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_5.addWidget(self.label_5)

        self.dataNameLineEdit = QLineEdit(self.scanDataGroupBox)
        self.dataNameLineEdit.setObjectName(u"dataNameLineEdit")

        self.horizontalLayout_5.addWidget(self.dataNameLineEdit)

        self.buildScandataToolButton = QToolButton(self.scanDataGroupBox)
        self.buildScandataToolButton.setObjectName(u"buildScandataToolButton")
        icon4 = QIcon(QIcon.fromTheme(u"run-build"))
        self.buildScandataToolButton.setIcon(icon4)

        self.horizontalLayout_5.addWidget(self.buildScandataToolButton)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)


        self.gridLayout_2.addLayout(self.verticalLayout_3, 1, 0, 1, 1)


        self.gridLayout_3.addWidget(self.scanDataGroupBox, 1, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(PrairieImporterDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout_3.addWidget(self.buttonBox, 2, 0, 1, 1)

        QWidget.setTabOrder(self.dataNameLineEdit, self.buildScandataToolButton)
        QWidget.setTabOrder(self.buildScandataToolButton, self.pvScanFileNameLineEdit)
        QWidget.setTabOrder(self.pvScanFileNameLineEdit, self.pvScanFileChooserToolButton)
        QWidget.setTabOrder(self.pvScanFileChooserToolButton, self.pvScanImportFromWorkspaceToolButton)
        QWidget.setTabOrder(self.pvScanImportFromWorkspaceToolButton, self.ephysFileNameLineEdit)
        QWidget.setTabOrder(self.ephysFileNameLineEdit, self.ephysFileChooserToolButton)
        QWidget.setTabOrder(self.ephysFileChooserToolButton, self.ephysImportFromWorkspaceToolButon)
        QWidget.setTabOrder(self.ephysImportFromWorkspaceToolButon, self.triggerProtocolFileNameLineEdit)
        QWidget.setTabOrder(self.triggerProtocolFileNameLineEdit, self.detectTriggersToolButton)
        QWidget.setTabOrder(self.detectTriggersToolButton, self.editTriggerProtocolsToolButton)
        QWidget.setTabOrder(self.editTriggerProtocolsToolButton, self.triggerProtocolFileChooserToolButton)
        QWidget.setTabOrder(self.triggerProtocolFileChooserToolButton, self.protocolsImportToolButton)
        QWidget.setTabOrder(self.protocolsImportToolButton, self.optionsFileNameLineEdit)
        QWidget.setTabOrder(self.optionsFileNameLineEdit, self.optionsFileChooserToolButton)
        QWidget.setTabOrder(self.optionsFileChooserToolButton, self.optionsImportToolButton)

        self.retranslateUi(PrairieImporterDialog)
        self.buttonBox.accepted.connect(PrairieImporterDialog.accept)
        self.buttonBox.rejected.connect(PrairieImporterDialog.reject)

        QMetaObject.connectSlotsByName(PrairieImporterDialog)
    # setupUi

    def retranslateUi(self, PrairieImporterDialog):
        PrairieImporterDialog.setWindowTitle(QCoreApplication.translate("PrairieImporterDialog", u"Import PrairieView", None))
        self.dataFilesGroupBox.setTitle(QCoreApplication.translate("PrairieImporterDialog", u"Data files", None))
        self.label.setText(QCoreApplication.translate("PrairieImporterDialog", u"PrairieView Scan file", None))
#if QT_CONFIG(tooltip)
        self.pvScanFileChooserToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Open PrairieView Scan file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.pvScanFileChooserToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Open PrairieView Scan file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.pvScanFileChooserToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Open PrairieView Scan file", None))
#endif // QT_CONFIG(whatsthis)
        self.pvScanFileChooserToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.pvScanImportFromWorkspaceToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Import PrairieView Scan object", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.pvScanImportFromWorkspaceToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Import PrairieView Scan object", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.pvScanImportFromWorkspaceToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p align=\"justify\">Import PVScan object from  workspace, or create and import a PVScan  from an appropriate XML DOM document in the workspace,</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.pvScanImportFromWorkspaceToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.pvScanFileNameLineEdit.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"PV Scan XML file name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.pvScanFileNameLineEdit.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"PV Scan XML file name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.pvScanFileNameLineEdit.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>XML file output by PrairieView, which contains PVScan information</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.label_3.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Electrophysiology files", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_3.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Electrophysiology files", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_3.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"One or more electrophysiology files recorded during the PrairieeView files", None))
#endif // QT_CONFIG(whatsthis)
        self.label_3.setText(QCoreApplication.translate("PrairieImporterDialog", u"Electrophysiology file(s)", None))
#if QT_CONFIG(tooltip)
        self.ephysFileChooserToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Open electrophysiology file(s)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.ephysFileChooserToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Open electrophysiology file(s)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.ephysFileChooserToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Open electrophysiology file(s)", None))
#endif // QT_CONFIG(whatsthis)
        self.ephysFileChooserToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.ephysImportFromWorkspaceToolButon.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Import electrophysiology", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.ephysImportFromWorkspaceToolButon.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Import electrophysiology", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.ephysImportFromWorkspaceToolButon.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Import electrophysiology from an workspace object: a neo.Block or ScanData.</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.ephysImportFromWorkspaceToolButon.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.ephysFileNameLineEdit.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Electrophysiology file name(s) separated by OS-specific path separator (':' on Linux and MacOS, ';' on Windows)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.ephysFileNameLineEdit.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Electrophysiology file name(s) separated by OS-specific path separator (':' on Linux and MacOS, ';' on Windows)", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.ephysFileNameLineEdit.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Names of electrophysiolopgy file(s). These can be axon binary files, or a pickle file with the electrophysiology data.</p><p>These MUST be separated by the OS-specific path separator, for example</p><p> &quot;:&quot; on POSIX OSes such as, Linux, MacOS X</p><p>&quot;;&quot; on Windows</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.scanDataGroupBox.setTitle(QCoreApplication.translate("PrairieImporterDialog", u"ScanData", None))
        self.protocolsGroupBox.setTitle(QCoreApplication.translate("PrairieImporterDialog", u"Trigger Protocols", None))
#if QT_CONFIG(tooltip)
        self.detectTriggersToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Detect triggers from electrophysiology", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.detectTriggersToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Detect triggers from electrophysiology", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.detectTriggersToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Detect triggers from electrophysiology", None))
#endif // QT_CONFIG(whatsthis)
        self.detectTriggersToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.editTriggerProtocolsToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Edit trigger protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.editTriggerProtocolsToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Edit trigger protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.editTriggerProtocolsToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Edit trigger protocols", None))
#endif // QT_CONFIG(whatsthis)
        self.editTriggerProtocolsToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"Edit Protocols", None))
#if QT_CONFIG(tooltip)
        self.triggerProtocolFileChooserToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Open protocol file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.triggerProtocolFileChooserToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Open protocol file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.triggerProtocolFileChooserToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Open protocol file", None))
#endif // QT_CONFIG(whatsthis)
        self.triggerProtocolFileChooserToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.protocolsImportToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Import trigger protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.protocolsImportToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Import trigger protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.protocolsImportToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Import trigger protocols from a workspace object: a TriggerProtocol, a neo.Block, or ScanData.</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.protocolsImportToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.triggerProtocolFileNameLineEdit.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Trigger protocols file name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.triggerProtocolFileNameLineEdit.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Trigger protocols file name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.triggerProtocolFileNameLineEdit.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Pickle file containing trigger protocols.</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.label_2.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"ScanData analysis options", None))
#endif // QT_CONFIG(tooltip)
        self.label_2.setText(QCoreApplication.translate("PrairieImporterDialog", u"Options", None))
#if QT_CONFIG(tooltip)
        self.optionsFileNameLineEdit.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Options file name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.optionsFileNameLineEdit.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Options file name", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.optionsFileNameLineEdit.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Pickle file with EPSCaT options</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.optionsFileChooserToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Open options file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.optionsFileChooserToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Open options file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.optionsFileChooserToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Open options file", None))
#endif // QT_CONFIG(whatsthis)
        self.optionsFileChooserToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.optionsImportToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Import options", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.optionsImportToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Import options", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.optionsImportToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"<html><head/><body><p>Import EPSCaT Options from an object in the workspace, which  can be a dict, a DataBag, or another ScanData object.</p><p><br/></p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.optionsImportToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.label_5.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Name of the resulting ScanData object", None))
#endif // QT_CONFIG(tooltip)
        self.label_5.setText(QCoreApplication.translate("PrairieImporterDialog", u"Name  ", None))
#if QT_CONFIG(tooltip)
        self.buildScandataToolButton.setToolTip(QCoreApplication.translate("PrairieImporterDialog", u"Build Scandata", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.buildScandataToolButton.setStatusTip(QCoreApplication.translate("PrairieImporterDialog", u"Build Scandata", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.buildScandataToolButton.setWhatsThis(QCoreApplication.translate("PrairieImporterDialog", u"Build Scandata", None))
#endif // QT_CONFIG(whatsthis)
        self.buildScandataToolButton.setText(QCoreApplication.translate("PrairieImporterDialog", u"Build", None))
    # retranslateUi

