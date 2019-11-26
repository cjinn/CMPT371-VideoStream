import cv2
import threading
import time

# Variables
outputFrame = None
lock = threading.Lock() # ensure thread-safe

class Camera():
    def __init__(self):
        self.capture = cv2.VideoCapture(0)
        time.sleep(5)
    
    def displayVideo(self):
        global outputFrame, lock

        while True:
            ret, frame = self.capture.read()

            with lock:
                outputFrame = frame.copy()

            cv2.imshow("frame", frame)
            cv2.waitKey(1)

    def streamVideo(self):
        # grab global references to the output frame and lock variables
        global outputFrame, lock
    
        # loop over frames from the output stream
        while True:
            # wait until the lock is acquired
            with lock:
                # check if the output frame is available, otherwise skip
                # the iteration of the loop
                if outputFrame is None:
                    continue
    
                # encode the frame in JPEG format
                (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
    
                # ensure the frame was successfully encoded
                if not flag:
                    continue

            byteStr = b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n'
            return byteStr
    
            # yield the output frame in the byte format
            # yield(byteStr)

            