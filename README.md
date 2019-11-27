# CMPT371-VideoStream
Server-client communications for video streaming

# Requirements
## Hardware Required
- Windows computer
- Camera plugged into the computer

## Software Required
- Python 3.XX
- pip

# Instructions
1. Run: `pip install -r requirements.txt` where this README.md exists
2. Navigate to '/src'
3. Run the python command "python Webserver.py"
4. On your web browser, navigate to "[http://localhost:8081/](http://localhost:8081/)"

# Sources
- [OpenCV](https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_video_display/py_video_display.html)
- [TCP Communication in Python](https://wiki.python.org/moin/TcpCommunication)
- [UDP Communication in Python](https://wiki.python.org/moin/UdpCommunication)
- [HTTP Server](https://docs.python.org/3/library/http.server.html)
- [SocketServer](https://docs.python.org/2/library/socketserver.html)

# Known Bugs
- Shutting down server does not work properly
