import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time
import math

# Constants
DEFAULT_HOST="localhost"
DEFAULT_PORT=8082
STREAM_CAMERA = 0
SOCKET_TYPE_TCP="TCP"
SOCKET_TYPE_UDP="UDP"
MAX_NUM_CLIENTS = 1 # only one client
MESSAGE_BUFFER_SIZE = 20000 # Massive buffer to store image frames
SMALL_RESOLUTION = (100, 50) # Small resolution to not overwhelm the buffer

# UDP Packet object to assist multi-datagrams
class UDPPacket:
    headerSize = 20 # bytes

    def __init__(self, msgIndex: int, packetIndex: int, numPackets: int, payload: memoryview):
        self.msgIndex       = msgIndex 
        self.packetIndex    = packetIndex
        self.numPackets     = numPackets
        self.payload = payload
        self.header = self.msgIndex.to_bytes  (4, 'big')+\
                      self.packetIndex.to_bytes  (4, 'big')+\
                      self.numPackets.to_bytes (4, 'big')+\
                      len(self.payload).to_bytes(8, 'big')
    
    # Decode packet structure from message
    def decode(self, msg: bytes):
        msgIndex        = int.from_bytes(msg[:4],    'big')
        packetIndex     = int.from_bytes(msg[4:8],   'big')
        numPackets      = int.from_bytes(msg[8:12],   'big')
        payloadSize     = int.from_bytes(msg[12:20], 'big')

        packet = UDPPacket(msgIndex, packetIndex, numPackets, msg[16:16 + payloadSize])
        return packet
    
    # Encode a packet
    def encode(self):
        return self.header + self.payload

# UDP Packet Handler
class UDPPacketHandler:
    def __init__(self):
        self.currentMsgIndex = None
        self.packets = []
        self.numWaitingPackets = None
    
    # Reassemble packets into an object
    def reassemblePackets(self, packet: UDPPacket):
        if (self.currentMsgIndex is None or packet.msgIndex > self.currentMsgIndex):
            # First packet, or we drop all packets in favour of recent packets
            self.currentMsgIndex = packet.msgIndex
            self.packets = [b'']*packet.numPackets
            self.numWaitingPackets = packet.numPackets
        
        # Drop frame because too old
        if packet.msgIndex < self.currentMsgIndex:
            return

        self.packets[packet.packetIndex] = packet.payload
        self.numWaitingPackets -= 1

        # If all packets has been collected, build full message
        if self.numWaitingPackets == 0:
            return b''.join(self.packets)

    # Break up an object into a list of packets
    def breakupPayload(self, msgIndex: int, payload: bytes, maxPacketSize: int):
        payloadChunkSize = maxPacketSize - UDPPacket.headerSize
        numPackets = math.ceil(len(payload)/payloadChunkSize)
        packets = []

        payloadView = memoryview(payload)

        # Stuff data into a list of packets
        for iterator in range(numPackets - 1):
            startByte = iterator*payloadChunkSize
            endByte = (iterator + 1)*payloadChunkSize
            packets.append(UDPPacket(msgIndex, iterator, numPackets, payloadView[startByte:endByte]))
        
        # Process last packet
        startByte = (numPackets - 1)*payloadChunkSize
        packets.append(UDPPacket(msgIndex, numPackets - 1, numPackets, payloadView[startByte:]))

        return packets

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
        while True:
            frame = self.grabEncodedFrame()

            # Serialise frame before sending. Not intended for production
            data = pickle.dumps(frame) 
            msgSize = struct.pack("L", len(data))
            self.clientSocket.sendto(msgSize + data, (self.host, self.port))

    def streamTCP(self):
        while True:
            frame = self.grabEncodedFrame()

            # Serialise frame before sending. Not intended for production
            data = pickle.dumps(frame) 
            msgSize = struct.pack("L", len(data))
            self.clientSocket.sendall(msgSize + data)

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

        # Encoding frame to make it smaller
        encodeParams = [20]
        result, encodedFrame = cv2.imencode('.jpg', frame, encodeParams)

        return encodedFrame

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
            frame = cv2.imdecode(frame, 1)
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
            frame = cv2.imdecode(frame, 1)
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
