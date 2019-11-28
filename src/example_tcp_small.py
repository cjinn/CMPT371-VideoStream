import VideoStream as vs
import threading
import time

host = vs.DEFAULT_HOST
port = vs.DEFAULT_PORT
socketType = vs.SOCKET_TYPE_TCP
bufferSize = 1024 # Small buffer size

# Set up and run server
server = vs.VideoServer(host, port, socketType, bufferSize)
serverThread = threading.Thread(target=server.run)
serverThread.setDaemon(True)
serverThread.start()

time.sleep(3) # Give time for the server to be up and running

# Set up and run client
client = vs.VideoClient(host, port, socketType)
clientThread = threading.Thread(target=client.run)
clientThread.setDaemon(True)
clientThread.start()

# Run until end of program (i.e keyboard interrupt)
try:
    while True:
        time.sleep(1)
finally:
    print("Program ended")
