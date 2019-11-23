import cv2
import numpy as np
import socket
import sys
import pickle
import struct
import time

## Constants
STREAM_CAMERA = 0

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8091
MESSAGE_BUFFER_SIZE = 4096 # May change this
PROTOCOL_TYPE_UDP = 'UDP'
PROTOCOL_TYPE_TCP = 'TCP'

MAX_NUM_CLIENTS = 1 # To-do: Support multiple clients

class Client():
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, protocolType=PROTOCOL_TYPE_TCP):
        # To-do: Implement UDP
        self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.clientSocket.connect((host, port)) # Assumes server is up and broadcasting

    def beginDisplaying(self):
        data = ""
        payloadSize = struct.calcsize("H")

        while True:
            # Retrieve message size
            while len(data) < payloadSize:
                data += self.clientSocket.recv(MESSAGE_BUFFER_SIZE)

            packedMsgSize = data[:payloadSize]
            data = data[payloadSize:]
            msgSize = struct.unpack("L", packedMsgSize)[0] ### CHANGED

            # Retrieve all data based on message size
            while len(data) < msgSize:
                data += self.clientSocket.recv(MESSAGE_BUFFER_SIZE)

            frameData = data[:msgSize]
            data = data[msgSize:]

            # Extract frame
            frame = pickle.loads(frameData) # Assuming data is okay

            # Display
            cv2.imshow('frame', frame)
            cv2.waitKey(1)

    def close(self):
        self.clientSocket.close()

class Server():
    def __init__(self, host='', port=DEFAULT_PORT, protocolType=PROTOCOL_TYPE_TCP, streamVideoLocation = STREAM_CAMERA):
        ## Setting up Server
        # To-do: Implement UDP
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Socket created using TCP')
        self.serverSocket.bind((host, port))
        print('Socket bind complete')
        self.serverSocket.listen(MAX_NUM_CLIENTS)
        print('Socket now listening')
        self.clients = []

        ## Setting up Camera
        # To-do: VideoCapture from video file
        self.capture = cv2.VideoCapture(streamVideoLocation)
    
    def handlerAccept(self):
        connection = self.serverSocket.accept()
        print("New client!")
        self.clients.append(connection)
        self.client = connection

    def beginBroadcast(self):
        # To-do: Able to broadcast without waiting for a client
        # Currently, the handlerAccept is a blocking call which prevents 
        # the while(1) loop from executing
        self.handlerAccept()

        print("Server begin broadcasting")
        while True:
            # Read and serialise frame
            ret, frame = self.capture.read()
            data = pickle.dumps(frame)

            # Send data if there are clients
            dataLength = struct.pack("L", len(data)) 
            for client in self.clients:
                client.send(dataLength + data)
            # self.client.send(dataLength + data)
    
    def close(self):
        # To-do: Notify clients that server is closing
        self.serverSocket.close()

if __name__ == '__main__':
    host = Server()
    host.beginBroadcast()
