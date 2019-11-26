import http.server
import socketserver

from os import curdir, sep

# Constants
PORT = 8081
HOST = 'localhost'

class WebServerHandler(http.server.BaseHTTPRequestHandler):
    # Handler for GET Requests
    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"

        try:
            sendReply = False
            if self.path.endswith(".html"):
                mimeType = 'text/html'
                sendReply = True
            elif self.path.endswith(".jpg"):
                mimeType = 'image/jpg'
                sendReply = True
            elif self.path.endswith(".js"):
                mimeType = 'application/javascript'
                sendReply = True
            elif self.path.endswith(".js"):
                mimeType = 'text/css'
                sendReply = True
            # elif self.path.endswith(".stream"):
            #     # To-do: Implement video streaming here
            #     mimeType=""

            if sendReply == True:
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

class WebServer():
    def __init__(self, host=HOST, port=PORT, serverType="TCP"):
        self.host = host
        self.port = port
        # self.handler = http.server.SimpleHTTPRequestHandler
        self.handler = WebServerHandler

        if serverType == "TCP":
            self.server = socketserver.TCPServer((self.host, self.port), self.handler)
        # elif serverType == "UDP"
        #     self.server = socketserver.UDPServer((self.host, self.port), self.handler) # To-do: UDP
    
    def run(self):
        try:
            print("Serving at Port: ", self.port)
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down server")
            self.server.socket.close()

if __name__ == '__main__':
    webserver = WebServer()
    webserver.run()