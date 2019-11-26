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
            try:
                ret, frame = self.capture.read()

                with lock:
                    outputFrame = frame.copy()

                cv2.imshow("frame", frame)
                cv2.waitKey(1)
                    
            except KeyboardInterrupt:
                self.close()
                return

    def streamVideo(self):
        global outputFrame, lock
    
        while True:
            # wait until the lock is acquired
            with lock:
                # check if the output frame is available, otherwise skip the iteration of the loop
                if outputFrame is None:
                    continue
    
                # encode the frame in JPEG format
                (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
    
                # ensure the frame was successfully encoded
                if not flag:
                    continue

            byteStr = b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n'
            return byteStr
    
    def close(self):
        self.capture.release()
        cv2.destroyAllWindows()
            