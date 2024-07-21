# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# run this in a Scipyen session
# assumes the following:
# • SignalViewer_1 is a signal viewer window 
# • base_000* are neo.Block objects (e.g. Clampex runs)
k = 0
block = base_0001 # will modify base_0001 !
blocks = [base_0002, base_0003, base_0003, base_0004, base_0005, base_0006, base_0008]
sigview = sv.SignalViewer()
sigview.plot(block, showFrame=len(block.segments)-1)
def update():
    global k, blocks, block
    if k < len(blocks):
        block.segments.extend(blocks[k].segments)
        sigview.plot(block, showFrame = len(block.segments)-1)
        k += 1
    # you may want to call this:
    mainWindow.workspaceModel.update()

timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(5000)

#####
