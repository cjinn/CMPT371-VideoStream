import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time
import math
import UDPPackets as udp
import threading

# Constants
DEFAULT_HOST="localhost"
DEFAULT_PORT=8082
STREAM_CAMERA = 0
SOCKET_TYPE_TCP="TCP"
SOCKET_TYPE_UDP="UDP"
MAX_NUM_CLIENTS = 1 # only one client
DEFAULT_MESSAGE_BUFFER_SIZE = 10000 # Optimal buffer size to store image frames for both UDP and TCP

# Variables
clientLock = threading.Lock() # lock for client
serverLock = threading.Lock() # lock for server

# Client sending video frames to a server
class VideoClient():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_UDP, videoPath=STREAM_CAMERA):
        # Initialisation
        print("[Client]: Initialising Video Client")
        self.socketType = socketType
        self.host = host
        self.port = port
        self.frames = []
        self.running = False

        if socketType == SOCKET_TYPE_TCP:
            self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            print("[Client]: Opening port " + str(port))
            self.clientSocket.connect((host, port))
        elif socketType == SOCKET_TYPE_UDP:
            self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        print("[Client]: Starting up camera")
        self.capture = cv2.VideoCapture(videoPath)
        time.sleep(2) # Warm up the camera

    def streamUDP(self):
        frameIndex = 0
        t1 = time.time()
        t0 = t1
        handler = udp.UDPPacketHandler
        waitTimer = 1

        try:
            while self.running:
                if len(self.frames) <= 0:
                    print(["[Client]: Starved of frames!"])
                    print(["[Client]: Sleep for " + str(waitTimer) + " second"])
                    time.sleep(waitTimer)
                    waitTimer += 1
                    continue
                else:
                    with clientLock:
                        encodedFrame = self.frames.pop(0)
                    waitTimer = 1
                packets = handler.breakupPayload(msgIndex=frameIndex, payload=encodedFrame, maxPacketSize=udp.MAX_PACKET_SIZE)

                for packet in packets:
                    self.clientSocket.sendto(packet.encode(), (self.host, self.port))
                frameIndex += 1

                if frameIndex % 30 == 0:
                    t1 = time.time()
                    frameRate = str(30/(t1 - t0))
                    t0 = t1
                    print("[Client]: Stream FPS: " + frameRate)
        except KeyboardInterrupt:
            self.close()
        finally:
            self.close()

    # Source: https://stackoverflow.com/a/55432139
    def streamTCP(self):
        frameIndex = 0
        t1 = time.time()
        t0 = t1
        waitTimer = 1

        try:
            while self.running:
                if len(self.frames) <= 0:
                    print(["[Client]: Starved of frames!"])
                    print(["[Client]: Sleep for " + str(waitTimer) + " second"])
                    time.sleep(waitTimer)
                    waitTimer += 1
                    continue
                else:
                    with clientLock:
                        frame = self.frames.pop(0)
                    waitTimer = 1

                # Serialise frame before sending. Not intended for production
                data = pickle.dumps(frame) 
                msgSize = struct.pack("L", len(data))
                self.clientSocket.sendall(msgSize + data)
                frameIndex += 1

                if frameIndex % 30 == 0:
                    t1 = time.time()
                    frameRate = str(30/(t1 - t0))
                    t0 = t1
                    print("[Client]: Stream FPS: " + frameRate)
        except KeyboardInterrupt:
            self.close()
        finally:
            self.close()

    def run(self):
        self.running = True
        if self.socketType == SOCKET_TYPE_TCP:
            # Begin grabbing frames in a different thread
            grabFrameThread = threading.Thread(target=self.grabFrame)
            grabFrameThread.setDaemon(True)
            grabFrameThread.start()
            time.sleep(2) # Grab some frames before we begin streaming

            print("[Client]: Beginning streaming TCP")
            self.streamTCP()
        elif self.socketType == SOCKET_TYPE_UDP:
            # Begin grabbing frames in a different thread
            grabFrameThread = threading.Thread(target=self.grabEncodedFrame)
            grabFrameThread.setDaemon(True)
            grabFrameThread.start()
            time.sleep(2) # Grab some frames before we begin streaming
        
            print("[Client]: Beginning streaming UDP")
            self.streamUDP()
    
    def close(self):
        print("[Client]: Closing")
        self.running = False
        self.capture.release()

    def grabFrame(self):
        while self.running:
            ret, frame = self.capture.read()
            with clientLock:
                self.frames.append(frame)

    def grabEncodedFrame(self):
        while self.running:
            ret, frame = self.capture.read()
            encodedFrame = self.encodeFrame(frame)
            with clientLock:
                self.frames.append(encodedFrame)

    def encodeFrame(self, frame, jpegQuality=50):
        encodeParams = [int(cv2.IMWRITE_JPEG_QUALITY), jpegQuality]
        result, buf = cv2.imencode('.jpg', frame, encodeParams)
        return buf.tobytes()

class VideoServer():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_UDP, msgBufferSize=DEFAULT_MESSAGE_BUFFER_SIZE):
        # Initialisation
        print("[Server]: Initialising Video Server")
        self.socketType = socketType
        self.host = host
        self.port = port
        self.msgBufferSize = msgBufferSize
        self.running = False
        self.frames = []

        if socketType == SOCKET_TYPE_TCP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        elif socketType == SOCKET_TYPE_UDP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.UDPHandler = udp.UDPPacketHandler()
        self.serverSocket.bind((host, port))

    # Source: https://stackoverflow.com/a/55432139
    def runTCP(self):
        self.serverSocket.listen(MAX_NUM_CLIENTS)
        print("[Server]: Video socket ready to listen")

        connection, address = self.serverSocket.accept()
        print("[Server]: Accepted a client!")
        data = b''
        payloadSize = struct.calcsize("L")

        frameIndex = 0
        t1 = time.time()
        t0 = t1

        while self.running:
            while len(data) < payloadSize:
                data += connection.recv(self.msgBufferSize)
            packedMsgSize = data[:payloadSize]
            data = data[payloadSize:]
            msgSize = struct.unpack("L", packedMsgSize)[0]

            # Retrieve data based on message size
            while len(data) < msgSize:
                data += connection.recv(self.msgBufferSize)
            frameData = data[:msgSize]
            data = data[msgSize:]
            frame = pickle.loads(frameData)

            with serverLock:
                self.frames.append(frame)
                # Drop old frames to not fill up the buffer
                if len(self.frames) > 180:
                    self.frames.pop(0)
            
            cv2.imshow('frame', frame)
            cv2.waitKey(1)
            frameIndex += 1

            if frameIndex % 30 == 0:
                t1 = time.time()
                frameRate = str(30/(t1 - t0))
                t0 = t1
                print("[Server]: Stream FPS: " + frameRate)

    def runUDP(self):
        serverSock = self.serverSocket

        data = b''
        frameIndex = 0
        t1 = time.time()
        t0 = 0

        while self.running:
            # Grab as much data from buffer
            data += serverSock.recv(self.msgBufferSize)
            packet = udp.UDPPacket.decode(data)
            packetSize = packet.headerSize + len(packet.payload)
            data = data[packetSize:]

            # Display frame when fully reassembled
            frameBytes = self.UDPHandler.reassemblePackets(packet)

            if frameBytes != None:
                frame = self.decodeFrame(frameBytes)
                with serverLock:
                    self.frames.append(frame)
                    # Drop old frames to not fill up the buffer
                    if len(self.frames) > 180:
                        self.frames.pop(0)
                
                cv2.imshow('frame',frame)
                cv2.waitKey(1)
                frameIndex += 1

                if frameIndex % 30 == 0:
                    t1 = time.time()
                    frameRate = str(30/(t1 - t0))
                    t0 = t1
                    print("[Server]: Stream FPS: " + frameRate)
    
    def run(self):
        try:
            self.running = True
            if self.socketType == SOCKET_TYPE_TCP:
                print("[Server]: Running TCP server")
                self.runTCP()
            elif self.socketType == SOCKET_TYPE_UDP:
                print("[Server]: Running UDP server")
                self.runUDP()
        except KeyboardInterrupt:
            self.close()
        finally:
            self.close()
    
    def decodeFrame(self, frameBuffer):
        frameArray = np.frombuffer(frameBuffer, dtype=np.dtype('uint8'))
        return cv2.imdecode(frameArray, flags=cv2.IMREAD_UNCHANGED)

    def exportFrame(self):
        result = False
        outputFrame = None
        if len(self.frames) > 0:
            with serverLock:
                outputFrame = self.frames.pop(0)
                result = True
        return (result, outputFrame)
    
    def close(self):
        print("[Server]: Closing")
        self.serverSocket.close()
        self.running = False

if __name__ == '__main__':
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    socketType = SOCKET_TYPE_UDP

    # Set up and run server
    server = VideoServer(host, port, socketType)
    serverThread = threading.Thread(target=server.run)
    serverThread.setDaemon(True)
    serverThread.start()

    time.sleep(3) # Give time for the server to be up and running

    # Set up and run client
    client = VideoClient(host, port, socketType)
    clientThread = threading.Thread(target=client.run)
    clientThread.setDaemon(True)
    clientThread.start()

    # Run until end of program (i.e keyboard interrupt)
    try:
        while True:
            time.sleep(1)
    finally:
        print("Program ended")
