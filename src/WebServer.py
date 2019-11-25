import http.server
import socketserver

# Constants
PORT = 8081
HOST = 'localhost'

class WebServer():
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.handler = http.server.SimpleHTTPRequestHandler
    
    def run(self):
        with socketserver.TCPServer((self.host, self.port), self.handler) as httpd:
            print("Serving at Port: ", self.port)
            httpd.serve_forever()


if __name__ == '__main__':
    webserver = WebServer()
    webserver.run()