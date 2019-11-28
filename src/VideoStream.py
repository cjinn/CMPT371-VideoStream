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
MESSAGE_BUFFER_SIZE = 20000 # Massive buffer to store image frames

# Variables
lock = threading.Lock() # lock for frames

# Client sending video frames to a server
class VideoClient():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_TCP, videoPath=STREAM_CAMERA):
        # Initialisation
        self.socketType = socketType
        self.host = host
        self.port = port
        self.encodedFrames = []
        self.running = True

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

        try:
            while self.running:
                with lock:
                    encodedFrame = self.encodedFrames.pop(0)
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

    def streamTCP(self):
        frameIndex = 0
        t1 = time.time()
        t0 = t1

        try:
            while self.running:
                with lock:
                    encodedFrame = self.encodedFrames.pop(0)

                # Serialise frame before sending. Not intended for production
                data = pickle.dumps(encodedFrame) 
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
        
        # Begin grabbing frames in a different thread
        grabFrameThread = threading.Thread(target=self.grabFrame)
        grabFrameThread.setDaemon(True)
        grabFrameThread.start()
        time.sleep(1)

        if self.socketType == SOCKET_TYPE_TCP:
            print("[Client]: Beginning streaming TCP")
            self.streamTCP()
        elif self.socketType == SOCKET_TYPE_UDP:
            print("[Client]: Beginning streaming UDP")
            self.streamUDP()
    
    def close(self):
        self.running = False
        self.capture.release()

    def grabFrame(self):
        while self.running:
            ret, frame = self.capture.read()
            encodedFrame = self.encodeFrame(frame)
            with lock:
                self.encodedFrames.append(encodedFrame)

    def encodeFrame(self, frame, jpegQuality=50):
        encodeParams = [int(cv2.IMWRITE_JPEG_QUALITY), jpegQuality]
        result, buf = cv2.imencode('.jpg', frame, encodeParams)
        return buf.tobytes()

class VideoServer():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, socketType=SOCKET_TYPE_TCP):
        # Initialisation
        self.socketType = socketType
        self.host = host
        self.port = port
        self.running = False

        if socketType == SOCKET_TYPE_TCP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        elif socketType == SOCKET_TYPE_UDP:
            self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.UDPHandler = udp.UDPPacketHandler()
        self.serverSocket.bind((host, port))

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
            frameIndex += 1

            if frameIndex % 30 == 0:
                t1 = time.time()
                frameRate = str(30/(t1 - t0))
                t0 = t1
                print("[Server]: Stream FPS: " + frameRate)


    def runUDP(self):
        data = b''
        serverSock = self.serverSocket
        time.sleep(2)

        frameIndex = 0
        t1 = time.time()
        t0 = 0

        while self.running:
            # Grab as much data from buffer
            data += serverSock.recv(MESSAGE_BUFFER_SIZE)
            packet = udp.UDPPacket.decode(data)
            packetSize = packet.headerSize + len(packet.payload)
            data = data[packetSize:]

            # Display frame when fully reassembled
            frameBytes = self.UDPHandler.reassemblePackets(packet)

            if frameBytes != None:
                frame = self.decodeFrame(frameBytes)
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
    
    def close(self):
        self.serverSocket.close()
        self.running = False

if __name__ == '__main__':
    # Set up server
    server = VideoServer(DEFAULT_HOST, DEFAULT_PORT, SOCKET_TYPE_UDP)
    serverThread = threading.Thread(target=server.run)
    serverThread.setDaemon(True)

    # Set up client
    client = VideoClient(DEFAULT_HOST, DEFAULT_PORT, SOCKET_TYPE_UDP)
    clientThread = threading.Thread(target=client.run)
    clientThread.setDaemon(True)

    # Begin running until keyboard interrupt
    serverThread.start()
    clientThread.start()

    try:
        while True:
            time.sleep(1)
    finally:
        print("End program")
