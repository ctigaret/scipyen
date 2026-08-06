# __scipyen_plugin__
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import traceback
import cv2 as cv
import numpy as np

def startLiveImaging(camera:int = 0, grayscale:bool=False):
    # cap = cv.VideoCapture(-1)
    cap = cv.VideoCapture()
    if not cap.open(camera):
        print("Cannot open camera")
        return 
    cv.namedWindow("Live", cv.WINDOW_NORMAL)
    while(True):
        ret, frame = cap.read()
        if not ret:
            break
        if grayscale:
            frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow("Live", frame)
        key = cv.waitKey(1)
        # print(key)
        if key & 0xFF == ord('q'):
            break
    print("Live imaging stopped and you may close the Live window; to restart, use the Live Imaging menu item to launch a new window")
    cap.release()

def closeLiveWindow():
    cv.destroyWindow("Live")
    # cv.destroyAllWindows()

def launch():
    try:
        startLiveImaging()
    except:
        traceback.print_exc()



def init_scipyen_plugin():
    return {"Applications|Live Video":launch}
