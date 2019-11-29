# Source: https://github.com/jeremyfix/udp_video_streaming
import math

# Constants
MAX_PACKET_SIZE = 200

# UDP Packet object to assist multi-datagrams
class UDPPacket:
    headerSize = 16 # bytes

    def __init__(self, msgIndex: int, packetIndex: int, numPackets: int, payload: memoryview):
        self.msgIndex       = msgIndex 
        self.packetIndex    = packetIndex
        self.numPackets     = numPackets
        self.payload = payload
        self.header = self.msgIndex.to_bytes  (4, 'big')+\
                      self.packetIndex.to_bytes  (4, 'big')+\
                      self.numPackets.to_bytes (4, 'big')+\
                      len(self.payload).to_bytes(4, 'big')
    
    # Decode packet structure from message
    def decode(msg: bytes):
        msgIndex        = int.from_bytes(msg[:4],    'big')
        packetIndex     = int.from_bytes(msg[4:8],   'big')
        numPackets      = int.from_bytes(msg[8:12],   'big')
        payloadSize     = int.from_bytes(msg[12:16], 'big')

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
    def breakupPayload(msgIndex: int, payload: bytes, maxPacketSize: int):
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

if __name__ == '__main__':
    import numpy as np
    import random
    import cv2

    def cv2_decode_image_buffer(img_buffer):
        img_array = np.frombuffer(img_buffer, dtype=np.dtype('uint8'))
        # Decode a colored image
        return  cv2.imdecode(img_array, flags=cv2.IMREAD_UNCHANGED)

    def cv2_encode_image(cv2_img, jpeg_quality):
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        result, buf = cv2.imencode('.jpg', cv2_img, encode_params)
        return buf.tobytes()

    teapotImg = cv2.imread('teapot.jpg')

    # Build up a collection of messages
    packets = []
    img0 = cv2_encode_image(teapotImg, 10)
    img1 = cv2_encode_image(teapotImg, 100)

    packets += UDPPacketHandler.breakupPayload(msgIndex=0, payload=img0, maxPacketSize=100)
    packets += UDPPacketHandler.breakupPayload(msgIndex=1, payload=img1, maxPacketSize=60000)

    # Shuffle the packets to see if we can handle disordered packets
    random.shuffle(packets)

    print("A total of {} packets are considered sequentially".format(len(packets)))

    packet_processor = UDPPacketHandler()
    for p in packets:
        data = packet_processor.reassemblePackets(p)
        if data is not None:
            print("Got a frame !")
            img = cv2_decode_image_buffer(data)
            cv2.imshow('Image', img)
            cv2.waitKey()
