from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn


from OnlineHandler import OnlineHandler

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class JTLOM:
    def __init__(self,http_port):
        self.runningTests = []
        self.http_port = http_port
        self.server = ThreadedHTTPServer(('', http_port), OnlineHandler)
    def startserver(self):
        print 'Httpserver was started on port: ', self.http_port
        self.server.serve_forever()




