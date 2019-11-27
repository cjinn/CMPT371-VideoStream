import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time

# Constants
DEFAULT_HOST="localhost"
DEFAULT_PORT=8082
STREAM_CAMERA = 0
SOCKET_TYPE_TCP="TCP"
SOCKET_TYPE_UDP="UDP"
MAX_NUM_CLIENTS = 1 # only one client
MESSAGE_BUFFER_SIZE = 4096 # Massive buffer to store image frames
SMALL_RESOLUTION = (50, 20) # Small resolution to not overwhelm the buffer

# Client sending video frames to a server
class VideoClient():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_TCP, videoPath=STREAM_CAMERA):
        # Initialisation
        self.socketType = socketType
        self.host = host
        self.port = port

        if socketType == SOCKET_TYPE_TCP:
            self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            print("Opening port " + str(port))
            self.clientSocket.connect((host, port))
        elif socketType == SOCKET_TYPE_UDP:
            self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        print("Starting up camera")
        self.capture = cv2.VideoCapture(videoPath)
        time.sleep(2) # Warm up the camera

    def streamUDP(self):
        ret, frame = self.capture.read()
        frame = cv2.resize(frame, SMALL_RESOLUTION)

        # Serialise frame before sending. Not intended for production
        data = pickle.dumps(frame) 
        msgSize = struct.pack("L", len(data))
        self.clientSocket.sendto(msgSize + data, (self.host, self.port))

    def streamTCP(self):
        ret, frame = self.capture.read()
        frame = cv2.resize(frame, SMALL_RESOLUTION)

        # Serialise frame before sending. Not intended for production
        data = pickle.dumps(frame) 
        msgSize = struct.pack("L", len(data))
        self.clientSocket.sendall(msgSize + data)

    def beginStreaming(self):
        print("Beginning streaming")
        while True:
            if self.socketType == SOCKET_TYPE_TCP:
                self.streamTCP()
            elif self.socketType == SOCKET_TYPE_UDP:
                self.streamUDP()

class VideoServer():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_TCP):
        # Initialisation
        self.socketType = socketType
        self.host = host
        self.port = port

        if socketType == SOCKET_TYPE_TCP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        elif socketType == SOCKET_TYPE_UDP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.serverSocket.bind((host, port))

    def runTCP(self):
        self.serverSocket.listen(MAX_NUM_CLIENTS)
        print("Video socket ready to listen")

        connection, address = self.serverSocket.accept()
        print("Accepted a client!")
        data = b''
        payloadSize = struct.calcsize("L")

        while True:
            while len(data) < payloadSize:
                data += connection.recv(MESSAGE_BUFFER_SIZE)
            packedMsgSize = data[:payloadSize]
            data = data[payloadSize:]
            msgSize = struct.unpack("L", packedMsgSize)[0]

            # Retrieve data based on message size
            while len(data) < msgSize:
                data += connection.recv(MESSAGE_BUFFER_SIZE)
            frameData = data[:msgSize]
            data = data[msgSize:]

            frame = pickle.loads(frameData)
            cv2.imshow('frame',frame)
            cv2.waitKey(1)


    def runUDP(self):
        data = b''
        payloadSize = struct.calcsize("L")
        serverSock = self.serverSocket

        while True:
            while len(data) < payloadSize:
                data += serverSock.recv(MESSAGE_BUFFER_SIZE)
            packedMsgSize = data[:payloadSize]
            data = data[payloadSize:]
            msgSize = struct.unpack("L", packedMsgSize)[0]

            # Retrieve data based on message size
            while len(data) < msgSize:
                data += serverSock.recv(MESSAGE_BUFFER_SIZE)
            frameData = data[:msgSize]
            data = data[msgSize:]

            frame = pickle.loads(frameData)
            cv2.imshow('frame',frame)
            cv2.waitKey(1)    
    
    def run(self):
        try:
            print("Running server")
            if self.socketType == SOCKET_TYPE_TCP:
                self.runTCP()
            elif self.socketType == SOCKET_TYPE_UDP:
                self.runUDP()
        except KeyboardInterrupt:
            self.close()
    
    def close(self):
        self.serverSocket.close()

if __name__ == '__main__':
    videoServer = VideoServer(DEFAULT_HOST, DEFAULT_PORT, SOCKET_TYPE_UDP)
    videoServer.run()
