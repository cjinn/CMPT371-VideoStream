import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time
import math
import UDPPackets as udp

# Constants
DEFAULT_HOST="localhost"
DEFAULT_PORT=8082
STREAM_CAMERA = 0
SOCKET_TYPE_TCP="TCP"
SOCKET_TYPE_UDP="UDP"
MAX_NUM_CLIENTS = 1 # only one client
MESSAGE_BUFFER_SIZE = 20000 # Massive buffer to store image frames

SMALL_HEIGHT = 100
SMALL_WIDTH = 50
SMALL_RESOLUTION = (SMALL_HEIGHT, SMALL_WIDTH) # Small resolution to not overwhelm the buffer

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
            self.UDPHandler = udp.UDPPacketHandler()

        print("Starting up camera")
        self.capture = cv2.VideoCapture(videoPath)
        time.sleep(2) # Warm up the camera

    def streamUDP(self):
        frameIndex = 0
        t1 = time.time()
        t0 = t1

        while True:
            frame = self.grabEncodedFrame()
            packets = self.UDPHandler.breakupPayload(frameIndex, frame, udp.MAX_PACKET_SIZE)

            for packet in packets:
                self.clientSocket.sendto(packet.encode(), (self.host, self.port))
            frameIndex += 1

            if frameIndex % 30 == 0:
                t1 = time.time()
                frameRate = str(30/(t1 - t0))
                t0 = t1
                print("Stream FPS: " + frameRate)

    def streamTCP(self):
        frameIndex = 0
        while True:
            frame = self.grabEncodedFrame()

            # Serialise frame before sending. Not intended for production
            data = pickle.dumps(frame) 
            msgSize = struct.pack("L", len(data))
            self.clientSocket.sendall(msgSize + data)
            frameIndex += 1

            if frameIndex % 30 == 0:
                t1 = time.time()
                frameRate = str(30/(t1 - t0))
                t0 = t1
                print("Stream FPS: " + frameRate)                

    def beginStreaming(self):
        if self.socketType == SOCKET_TYPE_TCP:
            print("Beginning streaming TCP")
            self.streamTCP()
        elif self.socketType == SOCKET_TYPE_UDP:
            print("Beginning streaming UDP")
            self.streamUDP()

    def grabEncodedFrame(self):
        ret, frame = self.capture.read()
        frame = cv2.resize(frame, SMALL_RESOLUTION)

        print(frame.shape)

        return frame

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
            self.UDPHandler = udp.UDPPacketHandler()
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
        serverSock = self.serverSocket
        time.sleep(2)

        while True:
            # Grab as much data from buffer
            data += serverSock.recv(MESSAGE_BUFFER_SIZE)
            packet = udp.UDPPacket.decode(data)
            packetSize = packet.headerSize + len(packet.payload)
            data = data[packetSize:]

            # Display frame when fully reassembled
            frameBytes = self.UDPHandler.reassemblePackets(packet)

            if frameBytes != None:
                print(type(frameBytes))
                print(len(frameBytes))
                frame = np.frombuffer(frameBytes, np.int8)
                frame.reshape(SMALL_HEIGHT, SMALL_WIDTH, 3)

                cv2.namedWindow("Video Stream")
                cv2.imshow('frame',frame)
                cv2.waitKey(1)               
    
    def run(self):
        try:
            if self.socketType == SOCKET_TYPE_TCP:
                print("Running TCP server")
                self.runTCP()
            elif self.socketType == SOCKET_TYPE_UDP:
                print("Running UDP server")
                self.runUDP()
        finally:
            self.close()
    
    def close(self):
        self.serverSocket.close()

if __name__ == '__main__':
    videoServer = VideoServer(DEFAULT_HOST, DEFAULT_PORT, SOCKET_TYPE_UDP)
    videoServer.run()
