# CMPT371-VideoStream
Server-client communications for video streaming using either TCP or UDP. The client will be streaming a video and sending it to a server. Currently, only one client is being supported for simplicity.

## Lingo
FPS - Frame per second

# Requirements
## Hardware Required
- Windows computer
- Camera plugged into the computer

## Software Required
- Python 3.XX
- pip

The only external Python libraries needed are numpy and opencv.

# Quick-Run Instructions
1. Run: ``pip install -r requirements.txt`` where this README.md exists
2. Navigate to '/src'
3. Run the python command "python3 VideoStream.py"

# TCP vs UDP
## What is TCP?
TCP (Transmission Control Protocol) is a communication protocol that sends packets of data between devices reliability. It connects process-to-process and has a huge emphasis on making sure data arrives at the other end securely. While this is perfect for lossless communication, it is not fast and is not ideal for video streaming.

My TCP implementation is influenced by [nareddyt's answer on StackOverflow](https://stackoverflow.com/a/55432139).

## What is UDP?
UDP (User Datagram Protocol) is an alternative communications protocol to TCP. It is primarily used for low-latency and loss-tolerating connections. While it is not as reliable, it is  much faster and perceived latency will be much lower.

To support video streaming, I have implemented [jeremyfix's UDP Protocol](https://github.com/jeremyfix/udp_video_streaming)) which helps to organise the UDP Datagrams. The protocol will also abandon any old frames in favour of new frames.

To test the protocol, simply run UDPPackets.py. It will take teapot.jpg, encode it, send the packets to itself in a random fashion, decode it, and display it.

## Comparison with Buffer Size
I will compare both TCP and UDP using the example.py files, each differing by the following buffer sizes:
- Small (1024 bytes)
- Default (10,000 bytes)
- Big (30,000 bytes)

I chose to use buffer size as it illustrates the strengths and weaknesses of TCP and UDP easily.

My camera will be [Microsoft Lifecam HD-3000](https://www.amazon.ca/Microsoft-Lifecam-HD-3000-Webcam-Black/dp/B009VL9YJ2), offering (roughly) 24 fps with 720p resolution. The ideal benchmark will be the server displaying 24 FPS of my webcam feed.

## TCP
### example_tcp_small.py
Run in a terminal ``python3 example_tcp_small.py``

The server is struggling to display frames as the server buffer size is the bottleneck, lowering the server's FPS. This is because the server can only accept a limited amount of frames before it simply drops new packets. This leads to a performance of ~8 FPS. Eventually, the program ends due to the client running out of memory waiting to send all of its frames. 

### example_tcp_big.py
Run in a terminal ``python3 example_tcp_big.py``

Because of the bigger buffer size, TCP client is able to fit multiple frames when sending packets to the server. This leads to an interesting problem of the client being starved of frames.

The current workaround is to force the client to sleep until more frames are retrieved. Unfortunately, this means that the server will periodically is starved of frames to display. This makes a jarring experience for the user as the video stream will periodically pause before it "catches up".

The streaming performance varies from ~3 FPS (due to the client starved of frames) to 80 FPS due to the server receiving (and displaying) multiple frames at once.

## example_tcp_default.py
Run in a terminal ``python3 example_tcp_default.py``

At a buffer size of 10,000 bytes, TCP works well for both communications. No observable problems are noticed. The FPS performance is roughly 24.

## UDP
### Run Instructions
1. Run in terminal: ``python3 example_udp_small.py``
2. Run in a different terminal: ``python3 example_udp_big.py``
3. Run in a different terminal: ``python3 example_udp_default.py``

### Results
Interestingly, UDP offers no performance difference at all buffer sizes. Both the client and server have roughly the same performance of 20-24 FPS. This illustrates the scalability of UDP and offers new possibilities to stream UDP across the web.

## Web Server
To stream the video to a web server, I followed [Adrian Rosebrock's post](https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/).

The method employed is to continually replace the image from the URL endpoint "/video_feed" to the HTML image tag ``<img>`` continually with the frames outputted from the video stream.

Note that the web server does not support multi-browser.

### Run Instructions
1. Open a terminal and run ``python3 WebServer.py``
2. Open a different and run ``python3 client.py``
3. After a few seconds, open a web browser and navigate to ``localhost:6175``

## Conclusion
UDP offers better streaming performance than TCP due to the inherent nature of not considering reliability below the application-layer.

From this project, it reveals the hidden potential for UDP for streaming, especially for real-time applications on servers with small buffer sizes.

# Other Sources
- [OpenCV](https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_video_display/py_video_display.html)
- [TCP Communication in Python](https://wiki.python.org/moin/TcpCommunication)
- [UDP Communication in Python](https://wiki.python.org/moin/UdpCommunication)
