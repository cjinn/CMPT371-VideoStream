import http.server
import socketserver
import Camera as camera

from os import curdir, sep
import time
import threading

# Constants
PORT = 8081
HOST = 'localhost'

# Variables
lock = threading.Lock() # ensure thread-safe

class WebServerHandler(http.server.BaseHTTPRequestHandler):
    # Handler for GET Requests
    def do_GET(self):
        global camera

        if self.path == "/":
            self.path = "/index.html"

        try:
            sendReply = False
            mimeType = self.getMimeType()
            if mimeType != '':
                sendReply = True
            
            if self.path.endswith(".stream"):
                self.send_response(200)
                self.send_header('Content-type', mimeType)
                self.end_headers()
                self.stream()
            elif sendReply == True:
                f = open(curdir + sep + self.path)
                print(curdir + sep + self.path)
                self.send_response(200)
                self.send_header('Content-type', mimeType)
                self.end_headers()
                body = f.read()
                self.wfile.write(body.encode("utf-8")) # Need to encode the data
                f.close()
            return
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)

    def stream(self):
        with lock:
            self.streaming = True
        while self.streaming:
            self.wfile.write(camera.streamVideo())

    def getMimeType(self):
        mimeType = ''

        if self.path.endswith(".html"):
            mimeType = 'text/html'
        elif self.path.endswith(".jpg"):
            mimeType = 'image/jpg'
        elif self.path.endswith(".js"):
            mimeType = 'application/javascript'
        elif self.path.endswith(".css"):
            mimeType = 'text/css'
        elif self.path.endswith(".stream"):
            # mimeType = 'image/jpg'
            mimeType = 'multipart/x-mixed-replace; boundary=frame'
        
        return mimeType

    def endStream(self):
        with lock:
            self.streaming = False

class WebServer():
    def __init__(self, host=HOST, port=PORT, serverType="TCP"):
        self.running = True
        self.host = host
        self.port = port
        self.handler = WebServerHandler

        if serverType == "TCP":
            self.server = socketserver.TCPServer((self.host, self.port), self.handler)
        elif serverType == "UDP":
            self.server = socketserver.UDPServer((self.host, self.port), self.handler)
    def run(self):
        try:
            print("Serving at Port: ", self.port)
            self.server.serve_forever()
                
        except KeyboardInterrupt:
            self.close()

    def close(self):
        self.running = False
        print("Shutting down server")
        self.server.socket.close()

if __name__ == '__main__':
    camera = camera.Camera()
    cameraThread = threading.Thread(target=camera.displayVideo, args=())
    daemon = True
    cameraThread.start()

    webserver = WebServer()
    webserver.run()
