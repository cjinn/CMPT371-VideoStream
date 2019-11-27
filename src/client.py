import VideoStream as vs

client = vs.VideoClient(vs.DEFAULT_HOST, vs.DEFAULT_PORT, vs.SOCKET_TYPE_UDP)
client.beginStreaming()