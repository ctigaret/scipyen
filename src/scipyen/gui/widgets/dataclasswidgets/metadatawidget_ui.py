# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'metadatawidget.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
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
from PySide6.QtWidgets import (QApplication, QDateTimeEdit, QGridLayout, QHBoxLayout,
    QLabel, QSizePolicy, QSpacerItem, QToolButton,
    QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_MetaDataWidget(object):
    def setupUi(self, MetaDataWidget):
        if not MetaDataWidget.objectName():
            MetaDataWidget.setObjectName(u"MetaDataWidget")
        MetaDataWidget.resize(270, 177)
        self.gridLayout = QGridLayout(MetaDataWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_5 = QLabel(MetaDataWidget)
        self.label_5.setObjectName(u"label_5")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.label_5)

        self.analysisDateTimeEdit = QDateTimeEdit(MetaDataWidget)
        self.analysisDateTimeEdit.setObjectName(u"analysisDateTimeEdit")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.analysisDateTimeEdit.sizePolicy().hasHeightForWidth())
        self.analysisDateTimeEdit.setSizePolicy(sizePolicy1)

        self.horizontalLayout_3.addWidget(self.analysisDateTimeEdit)


        self.gridLayout.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_4 = QLabel(MetaDataWidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.horizontalLayout_5.addWidget(self.label_4)

        self.procedureNameTypeLabel = QLabel(MetaDataWidget)
        self.procedureNameTypeLabel.setObjectName(u"procedureNameTypeLabel")

        self.horizontalLayout_5.addWidget(self.procedureNameTypeLabel)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_2)

        self.toggleProcedureEditorToolButton = QToolButton(MetaDataWidget)
        self.toggleProcedureEditorToolButton.setObjectName(u"toggleProcedureEditorToolButton")
        icon = QIcon(QIcon.fromTheme(u"document-properties"))
        self.toggleProcedureEditorToolButton.setIcon(icon)
        self.toggleProcedureEditorToolButton.setCheckable(True)
        self.toggleProcedureEditorToolButton.setAutoRaise(True)

        self.horizontalLayout_5.addWidget(self.toggleProcedureEditorToolButton)


        self.gridLayout.addLayout(self.horizontalLayout_5, 5, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(MetaDataWidget)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label)

        self.fileOriginLabel = QLabel(MetaDataWidget)
        self.fileOriginLabel.setObjectName(u"fileOriginLabel")
        sizePolicy1.setHeightForWidth(self.fileOriginLabel.sizePolicy().hasHeightForWidth())
        self.fileOriginLabel.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.fileOriginLabel)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.nameDescriptionWidget = NameDescriptionWidget(MetaDataWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_2 = QLabel(MetaDataWidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.horizontalLayout_4.addWidget(self.label_2)

        self.biologicalSourceNameTypeLabel = QLabel(MetaDataWidget)
        self.biologicalSourceNameTypeLabel.setObjectName(u"biologicalSourceNameTypeLabel")

        self.horizontalLayout_4.addWidget(self.biologicalSourceNameTypeLabel)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.toggleSourceEditorToolButton = QToolButton(MetaDataWidget)
        self.toggleSourceEditorToolButton.setObjectName(u"toggleSourceEditorToolButton")
        self.toggleSourceEditorToolButton.setIcon(icon)
        self.toggleSourceEditorToolButton.setCheckable(True)
        self.toggleSourceEditorToolButton.setAutoRaise(True)

        self.horizontalLayout_4.addWidget(self.toggleSourceEditorToolButton)


        self.gridLayout.addLayout(self.horizontalLayout_4, 4, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_3 = QLabel(MetaDataWidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.label_3)

        self.recDateTimeLabel = QLabel(MetaDataWidget)
        self.recDateTimeLabel.setObjectName(u"recDateTimeLabel")
        sizePolicy1.setHeightForWidth(self.recDateTimeLabel.sizePolicy().hasHeightForWidth())
        self.recDateTimeLabel.setSizePolicy(sizePolicy1)

        self.horizontalLayout_2.addWidget(self.recDateTimeLabel)


        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)


        self.retranslateUi(MetaDataWidget)

        QMetaObject.connectSlotsByName(MetaDataWidget)
    # setupUi

    def retranslateUi(self, MetaDataWidget):
        MetaDataWidget.setWindowTitle(QCoreApplication.translate("MetaDataWidget", u"Form", None))
        self.label_5.setText(QCoreApplication.translate("MetaDataWidget", u"Analysed: ", None))
        self.label_4.setText(QCoreApplication.translate("MetaDataWidget", u"Procedure: ", None))
        self.procedureNameTypeLabel.setText("")
#if QT_CONFIG(tooltip)
        self.toggleProcedureEditorToolButton.setToolTip(QCoreApplication.translate("MetaDataWidget", u"Edit procedure", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleProcedureEditorToolButton.setStatusTip(QCoreApplication.translate("MetaDataWidget", u"Edit procedure", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleProcedureEditorToolButton.setWhatsThis(QCoreApplication.translate("MetaDataWidget", u"Edit procedure", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleProcedureEditorToolButton.setText(QCoreApplication.translate("MetaDataWidget", u"Procedure Editor", None))
        self.label.setText(QCoreApplication.translate("MetaDataWidget", u"File Origin: ", None))
        self.fileOriginLabel.setText(QCoreApplication.translate("MetaDataWidget", u"_file_origin_datetime_", None))
        self.label_2.setText(QCoreApplication.translate("MetaDataWidget", u"Biological Source: ", None))
        self.biologicalSourceNameTypeLabel.setText("")
#if QT_CONFIG(tooltip)
        self.toggleSourceEditorToolButton.setToolTip(QCoreApplication.translate("MetaDataWidget", u"Edit Source", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleSourceEditorToolButton.setStatusTip(QCoreApplication.translate("MetaDataWidget", u"Edit Source", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleSourceEditorToolButton.setWhatsThis(QCoreApplication.translate("MetaDataWidget", u"Edit Source", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleSourceEditorToolButton.setText(QCoreApplication.translate("MetaDataWidget", u"Source Editor", None))
        self.label_3.setText(QCoreApplication.translate("MetaDataWidget", u"Recorded: ", None))
        self.recDateTimeLabel.setText(QCoreApplication.translate("MetaDataWidget", u"_rec_datetime_", None))
    # retranslateUi

