# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'inlinefiledirchooser.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QSizePolicy,
    QSpacerItem, QWidget)

from gui.widgets.small_widgets import ElidedPushButton

class Ui_InlineFileDirChooser(object):
    def setupUi(self, InlineFileDirChooser):
        if not InlineFileDirChooser.objectName():
            InlineFileDirChooser.setObjectName(u"InlineFileDirChooser")
        InlineFileDirChooser.resize(246, 46)
        self.horizontalLayout_2 = QHBoxLayout(InlineFileDirChooser)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.launchPushButton = ElidedPushButton(InlineFileDirChooser)
        self.launchPushButton.setObjectName(u"launchPushButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.launchPushButton.sizePolicy().hasHeightForWidth())
        self.launchPushButton.setSizePolicy(sizePolicy)
        self.launchPushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.launchPushButton)

        self.dirsOnlyCheckBox = QCheckBox(InlineFileDirChooser)
        self.dirsOnlyCheckBox.setObjectName(u"dirsOnlyCheckBox")
        icon = QIcon(QIcon.fromTheme(u"folder"))
        self.dirsOnlyCheckBox.setIcon(icon)

        self.horizontalLayout.addWidget(self.dirsOnlyCheckBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.horizontalLayout_2.addLayout(self.horizontalLayout)


        self.retranslateUi(InlineFileDirChooser)

        QMetaObject.connectSlotsByName(InlineFileDirChooser)
    # setupUi

    def retranslateUi(self, InlineFileDirChooser):
        InlineFileDirChooser.setWindowTitle(QCoreApplication.translate("InlineFileDirChooser", u"Form", None))
#if QT_CONFIG(tooltip)
        self.launchPushButton.setToolTip(QCoreApplication.translate("InlineFileDirChooser", u"Click to choose path", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.launchPushButton.setStatusTip(QCoreApplication.translate("InlineFileDirChooser", u"Click to choose path", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.launchPushButton.setWhatsThis(QCoreApplication.translate("InlineFileDirChooser", u"Click to choose path", None))
#endif // QT_CONFIG(whatsthis)
        self.launchPushButton.setText(QCoreApplication.translate("InlineFileDirChooser", u"Path...", None))
#if QT_CONFIG(tooltip)
        self.dirsOnlyCheckBox.setToolTip(QCoreApplication.translate("InlineFileDirChooser", u"Restrict to directories", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.dirsOnlyCheckBox.setStatusTip(QCoreApplication.translate("InlineFileDirChooser", u"Restrict to directories", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.dirsOnlyCheckBox.setWhatsThis(QCoreApplication.translate("InlineFileDirChooser", u"Restrict to directories", None))
#endif // QT_CONFIG(whatsthis)
        self.dirsOnlyCheckBox.setText(QCoreApplication.translate("InlineFileDirChooser", u"Directories", None))
    # retranslateUi

