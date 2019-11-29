from flask import Response
from flask import Flask
from flask import render_template
import threading
import datetime
import time
import cv2
import VideoStream as vs

# Constants
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080

# Variables
lock = threading.Lock()
server = vs.VideoServer()
serverThread = threading.Thread(target=server.run)
serverThread.setDaemon(True)
serverThread.start()

app = Flask(__name__)

@app.route("/")
def index():
    # Return the rendered template
    return render_template("index.html")

def generateVideoFrames():
    while True:
        result, outputFrame = server.exportFrame()

        # Check if there is an output frame
        if result == False:
            continue
        
        # encode the frame in JPEG format
        (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

        if not flag:
            continue
        
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generateVideoFrames(), mimeType="multipart/x-mixed-replace; boundary=frame")

# check to see if this is the main thread of execution
if __name__ == '__main__':
    # Running app
    app.run(DEFAULT_HOST, DEFAULT_PORT, debug=True, threaded=True, use_reloader=False)
