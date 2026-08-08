# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'itemslistdialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractScrollArea, QApplication, QDialog,
    QDialogButtonBox, QGridLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_ItemsListDialog(object):
    def setupUi(self, ItemsListDialog):
        if not ItemsListDialog.objectName():
            ItemsListDialog.setObjectName(u"ItemsListDialog")
        ItemsListDialog.setWindowModality(Qt.WindowModality.WindowModal)
        ItemsListDialog.resize(248, 313)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ItemsListDialog.sizePolicy().hasHeightForWidth())
        ItemsListDialog.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(ItemsListDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.listWidget = QListWidget(ItemsListDialog)
        self.listWidget.setObjectName(u"listWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy1)
        self.listWidget.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        self.verticalLayout.addWidget(self.listWidget)

        self.searchLineEdit = QLineEdit(ItemsListDialog)
        self.searchLineEdit.setObjectName(u"searchLineEdit")
        self.searchLineEdit.setClearButtonEnabled(True)

        self.verticalLayout.addWidget(self.searchLineEdit)

        self.infoLabel = QLabel(ItemsListDialog)
        self.infoLabel.setObjectName(u"infoLabel")

        self.verticalLayout.addWidget(self.infoLabel)

        self.buttonBox = QDialogButtonBox(ItemsListDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(ItemsListDialog)
        self.buttonBox.accepted.connect(ItemsListDialog.accept)
        self.buttonBox.rejected.connect(ItemsListDialog.reject)

        QMetaObject.connectSlotsByName(ItemsListDialog)
    # setupUi

    def retranslateUi(self, ItemsListDialog):
        ItemsListDialog.setWindowTitle(QCoreApplication.translate("ItemsListDialog", u"Select from list", None))
#if QT_CONFIG(tooltip)
        self.searchLineEdit.setToolTip(QCoreApplication.translate("ItemsListDialog", u"Type here to search", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.searchLineEdit.setStatusTip(QCoreApplication.translate("ItemsListDialog", u"Type here to search", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.searchLineEdit.setWhatsThis(QCoreApplication.translate("ItemsListDialog", u"Type here to search", None))
#endif // QT_CONFIG(whatsthis)
        self.searchLineEdit.setPlaceholderText(QCoreApplication.translate("ItemsListDialog", u"<type to search>", None))
        self.infoLabel.setText("")
    # retranslateUi

