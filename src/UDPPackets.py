import math

# Constants
MAX_PACKET_SIZE = 100

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
